"""
Single entry-pont to execute the full pipeline
"""

import asyncio

from utils.compare import cli as run_diff
from utils.scrape import main as run_scraper


def main():
    print("Launching scraper...")
    asyncio.run(run_scraper())

    print("Launching comparison...")
    run_diff()

    # TODO: add summarization

    # TODO: add email delivery

    print("\nWorkflow complete.")


if __name__ == "__main__":
    main()
