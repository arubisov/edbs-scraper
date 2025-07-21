import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse

import aiofiles
from pdfminer.high_level import extract_text as extract_pdf_text
from playwright.async_api import APIResponse, Response

logger = logging.getLogger(__name__)


class PDFHandler:
    def __init__(self, output_dir: Path, queue: asyncio.Queue, context, metrics_store: dict = None):
        self.out_dir = output_dir  # This should be the /results/[timestamp]/pdf directory
        self.queue = queue
        self.context = context
        self.metrics = metrics_store or {
            "pdfs_downloaded": 0,
            "failures": 0,
            "retries": 0,
        }
        self.out_dir.mkdir(parents=True, exist_ok=True)

    async def run_workers(self, count: int = 2):
        await asyncio.gather(*(self.worker() for _ in range(count)))

    async def worker(self):
        while True:
            url = await self.queue.get()
            if url is None:
                break  # poison pill
            try:
                await self.download_and_process_pdf(url)
            except Exception as e:
                self.metrics["failures"] += 1
                logger.warning("PDF handling failed for %s: %s", url, e)
            finally:
                self.queue.task_done()

    async def download_and_process_pdf(self, url: str):
        try:
            res = await self.context.request.get(url)
            await self.handle_response(res)
        except Exception as e:
            self.metrics["retries"] += 1
            logger.warning("Initial fetch failed for %s: %s — Retrying...", url, e)
            try:
                fresh_res = await self.context.request.get(url)
                await self.handle_response(fresh_res, is_retry=True)
            except Exception as retry_err:
                self.metrics["failures"] += 1
                logger.error("Retry also failed for %s: %s", url, retry_err)

    async def handle_response(self, res: Response | APIResponse, is_retry: bool = False):
        ctype = res.headers.get("content-type", "")
        if "application/pdf" not in ctype.lower():
            logger.debug("Skipped non-PDF content-type: %s (%s)", ctype, res.url)
            return

        try:
            data = await res.body()
            await self.save_pdf(res.url, res.status, data)
        except Exception as e:
            if is_retry:
                self.metrics["failures"] += 1
                logger.warning("PDF save failed for %s: %s", res.url, e)
            else:
                raise e

    async def save_pdf(self, url: str, status: int, data: bytes):
        name = urlparse(url).path.split("/")[-1] or "doc.pdf"
        pdf_path = self.out_dir / name
        text_path = pdf_path.with_suffix(".pdf.txt")

        if pdf_path.exists():
            logger.info("Skipping existing PDF: %s", name)
            return

        if status != 200:
            logger.warning("HTTP %d while fetching %s", status, url)
            self.metrics["failures"] += 1
            return

        async with aiofiles.open(pdf_path, "wb") as f:
            await f.write(data)

        text = await asyncio.to_thread(extract_pdf_text, pdf_path)
        async with aiofiles.open(text_path, "w", encoding="utf-8") as f:
            await f.write(text)

        self.metrics["pdfs_downloaded"] += 1
        logger.info("PDF processed and saved: %s", pdf_path)