# Wix Scraper

WIP. We started with https://github.com/ryanhlewis/WixScraper and it was a bust.

basic operation:

Create local .env file with keys required by config.py model.

```
uv run --env-file .env python scrape.py
<remove PDFs from export/new_folder>
uv run --env-file .env python compare.py <old_folder> <new_folder>
uv run --env-file .env python utils/extract_artifacts_v1.py <new_folder>
uv run summarize.py <path_to_diff_file>
uv run --env-file .env python send_email.py <new_folder>
```
