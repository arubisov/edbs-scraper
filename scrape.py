import asyncio, os, re, aiofiles
from urllib.parse import urljoin, urlparse, urldefrag
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text as extract_pdf_text
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

START_URL      = os.getenv("START_URL")
WIX_PASSWORD   = os.getenv("WIX_PASSWORD")
CONCURRENCY    = 5
OUT_DIR        = "scraped_text"

async def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    visited, to_visit = set(), {START_URL}
    async with Stealth().use_async(async_playwright()) as pw:
        browser  = await pw.chromium.launch(headless=True)
        context  = await browser.new_context()
        sem      = asyncio.Semaphore(CONCURRENCY)

        # -- PDF interception -------------------------------------------------
        async def handle_response(res):
            ctype = res.headers.get("content-type", "")
            if "application/pdf" in ctype.lower():
                try:
                    await save_pdf(res, context)
                except Exception as e:
                    print("⚠️ PDF save failed for", res.url, e)

        context.on("response", handle_response)

        async def worker():
            while to_visit:
                url = to_visit.pop()
                await asyncio.sleep(3)
                print(f"[{len(to_visit)} in queue] ...waiting 3 sec before visiting {url}")
                if url in visited: continue
                visited.add(url)
                async with sem:
                    # handle PDF links directly rather than navigating to them
                    if url.lower().endswith(".pdf"):
                        try:
                            res = await context.request.get(url)
                            await save_pdf(res, context)
                        except Exception as e:
                            print("⚠️ PDF save failed for", url, e)
                    else:
                        await process_page(context, url, to_visit, visited)

        await asyncio.gather(*(worker() for _ in range(CONCURRENCY)))
        await browser.close()

async def save_pdf(res, context):
    url  = res.url
    name = urlparse(url).path.split("/")[-1] or "doc.pdf"
    path = os.path.join(OUT_DIR, name)
    
    # avoid duplicate download
    if os.path.exists(path):
        print(f"Skipping PDF download - already exists - {name}")
        return
    
    try:
        response = await context.request.get(url)
        if response.status != 200:
            print(f"⚠️ HTTP error {response.status} fetching PDF for {url}")
            return
        data = await response.body()
    except Exception as e:
        print(f"⚠️ HTTP GET failed for {url}", e)
        return
    
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)
    # optional: extract text immediately
    text = extract_pdf_text(path)
    async with aiofiles.open(path + ".txt", "w", encoding="utf-8") as f:
        await f.write(text)
        
    print(f"✅ PDF saved: {path}")

async def process_page(context, url, to_visit, visited):
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=45000)
    except Exception as e:
        print("⚠️", url, e)
        await page.close()
        return
    
    # → handle password‐protected pages
    try:
        selector = 'input[type="password"]'
        if await page.query_selector(selector):
            # main frame
            await page.fill(selector, WIX_PASSWORD)
            await page.keyboard.press("Enter")
            await page.wait_for_selector(selector, state="detached", timeout=5000)
            await page.wait_for_selector('#SITE_CONTAINER', timeout=10000)
            await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception as e:
        print("⚠️ password entry failed for", url, e)

    texts = []
    for frame in page.frames:
        try:
            body_txt = await frame.evaluate("document.body && document.body.innerText")
            if body_txt:
                texts.append(body_txt.strip())
        except Exception:
            pass        # cross‑origin iframes sometimes block JS

    # if the first line says "ERROR: FORBIDDEN", retry later
    nav_error = False
    first_line = texts[0].splitlines()[0] if texts else ""
    if first_line.strip() == "ERROR: FORBIDDEN":
        print(f"⚠️ Forbidden error on {url} - retrying later")
        nav_error = True
    if first_line.strip() == "Password Protected":
        print(f"⚠️ Password protection error on {url} - retrying later")
        nav_error = True
        
    if nav_error:
        visited.remove(url)
        to_visit.add(url)
        await page.close()
        await asyncio.sleep(5)
        return

    # persist
    fname = url_to_filename(url)
    async with aiofiles.open(os.path.join(OUT_DIR, fname + ".txt"), "w",
                             encoding="utf-8") as f:
        await f.write("\n\n".join(texts))
    print(f"✅ Text saved: {fname}")

    # discover internal links (only in main frame to avoid Wix assets)
    html = await page.content()
    for link in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        u = urljoin(url, link["href"])
        u, _ = urldefrag(u)             # strip #anchors
        if is_same_domain(u) and u not in visited:
            to_visit.add(u)

    # click through tabs
    tabs = await page.query_selector_all('[role="tab"]')
    for tab in tabs:
        try:
            await tab.click()
            # wait for the PDF response to fire your save handler
            await page.wait_for_timeout(500)
        except Exception as e:
            print("⚠️ clicking tab failed for", url, e)

    await page.close()

def url_to_filename(u:str) -> str:
    clean = re.sub(r"[^\w\-]+", "_", u)
    return clean[:180]

def is_same_domain(u:str) -> bool:
    return urlparse(u).netloc == urlparse(START_URL).netloc

if __name__ == "__main__":
    asyncio.run(main())