import asyncio
import logging
import re
from datetime import datetime
from operator import is_
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import aiofiles
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text as extract_pdf_text
from playwright.async_api import (
    APIResponse,
    BrowserContext,
    Response,
    TimeoutError,
    async_playwright,
)
from playwright_stealth import Stealth

from config import settings

START_URL = settings.start_url
WIX_PASSWORD = settings.wix_password
URL_BLACKLIST = settings.url_blacklist
CONCURRENCY = 5
OUT_DIR = Path("results") / datetime.now().strftime("%y%m%d-%H%M%S")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
metrics = {
    "pages_queued": 0,
    "pages_done": 0,
    "pdfs_downloaded": 0,
    "retries": 0,
    "failures": 0,
}


async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    visited, to_visit = set(), {START_URL}
    async with Stealth().use_async(async_playwright()) as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        sem = asyncio.Semaphore(CONCURRENCY)

        # -- PDF interception -------------------------------------------------
        async def handle_response(res: Response):
            ctype = res.headers.get("content-type", "")
            if "application/pdf" in ctype.lower():
                try:
                    await handle_pdf(res)
                except Exception as e:
                    metrics["retries"] += 1
                    logging.warning(
                        "Initial PDF fetch failed for %s: %s. Retrying with fresh request",
                        res.url,
                        e,
                        exc_info=logging.getLogger().isEnabledFor(logging.DEBUG),
                    )
                    fresh_res = await context.request.get(res.url)
                    await handle_pdf(fresh_res, is_retry=True)

        context.on("response", handle_response)

        async def worker():
            while to_visit:
                url = to_visit.pop()
                if not url or url in visited or url in URL_BLACKLIST:
                    continue
                visited.add(url)
                async with sem:
                    # if href is to a PDF, use GET directly instead of page.goto()
                    if url.lower().endswith(".pdf"):
                        res = await context.request.get(url)
                        await handle_pdf(res)
                    else:
                        try:
                            await process_page(context, url, to_visit, visited)
                        except Exception as e:
                            metrics["failures"] += 1
                            logging.warning(
                                "Error processing page %s: %s",
                                url,
                                e,
                                exc_info=logging.getLogger().isEnabledFor(logging.DEBUG),
                            )
                metrics["pages_queued"] = len(to_visit)
                logging.info(
                    "Metrics: queued=%d, done_pages=%d, done_pdfs=%d, retries=%d, failures=%d",
                    metrics["pages_queued"],
                    metrics["pages_done"],
                    metrics["pdfs_downloaded"],
                    metrics["retries"],
                    metrics["failures"],
                )

        await asyncio.gather(*(worker() for _ in range(CONCURRENCY)))
        await browser.close()


async def handle_pdf(res: Response | APIResponse, is_retry: bool = False):
    try:
        data = await res.body()
        await save_pdf(res.url, res.status, data)
    except Exception as e:
        if is_retry:
            metrics["failures"] += 1
            logging.warning(
                "PDF save failed for %s: %s",
                res.url,
                e,
                exc_info=logging.getLogger().isEnabledFor(logging.DEBUG),
            )
        else:
            raise e


async def save_pdf(url: str, status: int, data: bytes):
    name = urlparse(url).path.split("/")[-1] or "doc.pdf"
    path = OUT_DIR / name

    # avoid duplicate download
    if path.exists():
        logging.info("Skipping PDF download - already exists: %s", name)
        return

    if status != 200:
        logging.warning("HTTP error %d fetching PDF for %s", status, url)
        metrics["failures"] += 1
        return

    # save pdf
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)

    # save extracted text
    text = await asyncio.to_thread(extract_pdf_text, path)
    text_path = path.with_suffix(path.suffix + ".txt")
    async with aiofiles.open(text_path, "w", encoding="utf-8") as f:
        await f.write(text)

    metrics["pdfs_downloaded"] += 1
    logging.info("PDF saved: %s", path)


async def process_page(context: BrowserContext, url: str, to_visit: set, visited: set):
    retry_page = False

    page = await context.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=45000)
    except Exception as e:
        logging.warning(
            "Error navigating to %s: %s",
            url,
            e,
            exc_info=logging.getLogger().isEnabledFor(logging.DEBUG),
        )
        await page.close()
        metrics["failures"] += 1
        return

    # → handle password‐protected pages
    try:
        selector = 'input[type="password"]'
        if await page.query_selector(selector):
            # main frame
            await page.fill(selector, WIX_PASSWORD)
            await page.keyboard.press("Enter")
            await page.locator(selector).wait_for(state="detached", timeout=9999)
            await page.locator("#SITE_CONTAINER").wait_for(state="visible", timeout=10000)
            await page.wait_for_load_state("networkidle", timeout=30001)
    except TimeoutError as te:
        logging.warning("Timeout error on %s - accepting partial download - {%s}", url, te)
    except Exception as e:
        logging.warning(
            "Password entry failed for %s: %s",
            url,
            e,
            exc_info=logging.getLogger().isEnabledFor(logging.DEBUG),
        )

    texts = []
    for frame in page.frames:
        try:
            body_txt = await frame.evaluate("document.body && document.body.innerText")
            if body_txt:
                texts.append(body_txt.strip())
        except Exception:
            pass  # cross‑origin iframes sometimes block JS

    # if the first line says "ERROR: FORBIDDEN", retry later
    first_line = texts[0].splitlines()[0] if texts else ""
    if first_line.strip() == "ERROR: FORBIDDEN":
        logging.warning("Forbidden error on %s - queued for retry", url)
        retry_page = True
    if first_line.strip() == "Password Protected":
        logging.warning("Password protection error on %s - queued for retry", url)
        retry_page = True

    if retry_page:
        visited.remove(url)
        to_visit.add(url)
        await page.close()
        await asyncio.sleep(5)
        metrics["retries"] += 1
        return

    # persist
    fname = url_to_filename(url)
    text_path = OUT_DIR / f"{fname}.txt"
    async with aiofiles.open(text_path, "w", encoding="utf-8") as f:
        await f.write("\n\n".join(texts))
    logging.info("Text saved: %s", fname)
    metrics["pages_done"] += 1

    # discover internal links (only in main frame to avoid Wix assets)
    html = await page.content()
    for link in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        u = urljoin(url, link["href"])
        u, _ = urldefrag(u)  # strip #anchors
        if is_same_domain(u) and u not in visited:
            to_visit.add(u)

    # click through tabs
    tabs = await page.get_by_role("tab").all()
    for tab in tabs:
        try:
            await tab.click()
            # wait for the PDF response to fire your save handler (equivalent to sleep)
            await page.wait_for_timeout(500)
        except Exception as e:
            metrics["failures"] += 1
            logging.warning(
                "Tab click failed for %s: %s",
                url,
                e,
                exc_info=logging.getLogger().isEnabledFor(logging.DEBUG),
            )

    await page.close()


def url_to_filename(u: str) -> str:
    clean = re.sub(r"[^\w\-]+", "_", u)
    return clean[:180]


def is_same_domain(u: str) -> bool:
    return urlparse(u).netloc == urlparse(START_URL).netloc


if __name__ == "__main__":
    asyncio.run(main())
