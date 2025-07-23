# EDBS Scraper

WIP. We started with https://github.com/ryanhlewis/WixScraper and it was a bust.

basic operation:

Create local .env file with keys required by config.py model.

```
uv run --env-file .env python -m utils.scrape
<remove PDFs from export/new_folder>
uv run --env-file .env python -m utils.compare <old_folder> <new_folder>
uv run --env-file .env python -m utils.extract_artifacts_v1.py <new_folder>
uv run --env-file .env python -m utils.summarize <path_to_diff_file>
uv run --env-file .env python -m utils.send_email <new_folder>
```
