"""
PATH: ./wix-scraper/utils/

Functions:
- main(): Orchestrates the full scraping workflow, including PDF extraction and diff generation.
- process_page(context, url, to_visit, visited, pdf_queue): Navigates a page, handles authentication, saves text, and enqueues new links.
- url_to_filename(u): Converts a URL into a safe filename.
- is_same_domain(u): Checks if a URL is from the same domain as the starting point.
"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import aiofiles
from bs4 import BeautifulSoup
from playwright.async_api import BrowserContext, Response, TimeoutError, async_playwright
from playwright_stealth import Stealth

from utils.configs.config import settings
from utils.multimedia.pdfhandler import PDFHandler  # NEW

START_URL = settings.start_url
WIX_PASSWORD = settings.wix_password
URL_BLACKLIST = settings.url_blacklist
CONCURRENCY = 5
BASE_DIR = Path(__file__).resolve().parents[1]  # /wix-scraper/
RESULTS_ROOT = BASE_DIR / "results"
TIMESTAMP = datetime.now().strftime("%y%m%d-%H%M%S")
OUT_DIR = RESULTS_ROOT / TIMESTAMP
PDF_DIR = OUT_DIR / "pdf"

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
    pdf_queue = asyncio.Queue()

    async with Stealth().use_async(async_playwright()) as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        sem = asyncio.Semaphore(CONCURRENCY)

        # PDF handler
        pdf_handler = PDFHandler(PDF_DIR, pdf_queue, context, metrics)
        pdf_worker_task = asyncio.create_task(pdf_handler.run_workers(3))

        async def handle_response(res: Response):
            ctype = res.headers.get("content-type", "")
            if "application/pdf" in ctype.lower():
                await pdf_queue.put(res.url)

        context.on("response", handle_response)

        async def worker():
            while to_visit:
                url = to_visit.pop()
                if not url or url in visited or url in URL_BLACKLIST:
                    continue
                visited.add(url)
                async with sem:
                    if url.lower().endswith(".pdf"):
                        await pdf_queue.put(url)
                    else:
                        try:
                            await process_page(context, url, to_visit, visited, pdf_queue)
                        except Exception as e:
                            metrics["failures"] += 1
                            logging.warning("Error processing page %s: %s", url, e, exc_info=True)
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

        await pdf_queue.join()
        for _ in range(3):
            await pdf_queue.put(None)  # shut down signal

        await pdf_worker_task
        await browser.close()


async def process_page(
    context: BrowserContext, url: str, to_visit: set, visited: set, pdf_queue: asyncio.Queue
):
    retry_page = False

    logging.info(f"Visiting page {url}")

    page = await context.new_page()

    try:
        await page.goto(url, wait_until="networkidle", timeout=45000)
    except Exception as e:
        logging.warning("Error navigating to %s: %s", url, e, exc_info=True)
        await page.close()
        metrics["failures"] += 1
        return

    try:
        selector = 'input[type="password"]'
        if await page.query_selector(selector):
            await page.fill(selector, WIX_PASSWORD)
            await page.keyboard.press("Enter")
            await page.locator(selector).wait_for(state="detached", timeout=9999)
            await page.locator("#SITE_CONTAINER").wait_for(state="visible", timeout=10000)
            await page.wait_for_load_state("networkidle", timeout=30001)
    except TimeoutError as te:
        logging.warning("Timeout error on %s - accepting partial download - {%s}", url, te)
    except Exception as e:
        logging.warning("Password entry failed for %s: %s", url, e, exc_info=True)

    texts = []
    for frame in page.frames:
        try:
            body_txt = await frame.evaluate("document.body && document.body.innerText")
            if body_txt:
                texts.append(body_txt.strip())
        except Exception:
            pass

    first_line = texts[0].splitlines()[0] if texts else ""
    if first_line.strip() in {"ERROR: FORBIDDEN", "Password Protected"}:
        logging.warning("Access denied on %s - queued for retry", url)
        visited.remove(url)
        to_visit.add(url)
        await page.close()
        await asyncio.sleep(5)
        metrics["retries"] += 1
        return

    fname = url_to_filename(url)
    text_path = OUT_DIR / f"{fname}.txt"
    async with aiofiles.open(text_path, "w", encoding="utf-8") as f:
        await f.write("\n\n".join(texts))
    logging.info("Text saved: %s", fname)
    metrics["pages_done"] += 1

    html = await page.content()
    for link in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        u = urljoin(url, link["href"])
        u, _ = urldefrag(u)
        if is_same_domain(u) and u not in visited:
            to_visit.add(u)

    tabs = await page.get_by_role("tab").all()
    for tab in tabs:
        try:
            await tab.click()
            await page.wait_for_timeout(500)
        except Exception as e:
            metrics["failures"] += 1
            logging.warning("Tab click failed for %s: %s", url, e, exc_info=True)

    await page.close()


def url_to_filename(u: str) -> str:
    return re.sub(r"[^\w\-]+", "_", u)[:180]


def is_same_domain(u: str) -> bool:
    if urlparse(u).netloc != urlparse(START_URL).netloc:
        logging.warning(f"Detected link to external domain: {u}")
        return False
    return True


if __name__ == "__main__":
    asyncio.run(main())
