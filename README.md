# EDBS Scraper

![Python ≥3.11](https://img.shields.io/badge/python-%3E%3D3.11-blue)

[Event Driven Broadcast Simulation (EDBS)]((https://www.edbsportal.com/)) is a password-protected Wix platform.

**EDBS Scraper** automates:

- Authenticated crawling of the EDBS portal
- PDF download & text extraction
- Difference detection between runs
- Summarization of changes via OpenAI
- Email delivery of results via Gmail API

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Full Pipeline](#full-pipeline-recommended)
  - [Individual Steps](#individual-steps)
- [Future work](#future-work)

---

## Prerequisites

- **[uv](https://docs.astral.sh/uv/)** (for dependency & environment management)
- **OpenAI API credentials** (for diff summarization)
- **Gmail API credentials** (for email delivery)

---

## Installation

1. Clone this repository.

2. Install uv (if not already):
   ```bash
   curl -sSL https://install.astral.sh | bash
   ```

3. Create .venv and sync dependencies:
   ```bash
   uv sync
   ```

4. Install playwright:
    ```bash
    playwright install
    ```

---

## Configuration

1. Follow the `.env.example` to create a `.env` file in the project root

2. **Gmail API**:
   - Follow the [Gmail Python Quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python).
   - Place the downloaded `credentials.json` in the project root.
   - On first run, `token.json` will be generated.

---

## Usage

### Full Pipeline (recommended)

Runs scraping → diff comparison (→ summarization → email delivery):

```bash
uv run python main.py
```

### Individual Steps

- **Scrape website**
  ```bash
  uv run python -m utils.scrape
  ```
- **Compare runs**
  ```bash
  uv run python -m utils.compare <old_folder> <new_folder>
  ```
- **Summarize diffs**
  ```bash
  uv run python -m utils.summarize <path_to_diff_file>
  ```
- **Send email**
  ```bash
  uv run python -m utils.send_email <new_folder>
  ```

#### Output

Scrape outputs (text files, PDFs) are written to:

```
results/<timestamp>/
```

Diff outputs are written to:

```
results/exports/<timestamp>/
```

Summary output is written to:
```
results/exports/<timestamp>/<timestamp_from>-<timestamp_to>.diff.txt
```

## Future Work

- See branch `feature/vulnerability-check` which begins to implement the `uv run python -m utils.extract_artifacts_v1 <folder>`.
  - Intent is to check pages and PDFs for vulnerabilities: watering hole attacks to foreign IP/domain, base64 encoded shell or PowerShell scrips, prompt injection attacks, etc.
  - This would be a new step after scrape and before compare.
- Multimedia handling for image and video. There is a lot of multimedia content on EDBS that is currently ignored. Simple AI captioning or summarization pipeline could be effective.
