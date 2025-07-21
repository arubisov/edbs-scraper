"""
PATH: ./wix-scraper/

Functions:
- prompt_yes_no(msg): Prompts user for a yes/no response in the terminal.
- main(): Executes scraper and/or diff comparison workflows based on user prompts.
"""

import asyncio
from utils.scrape import main as run_scraper
from utils.compare import cli as run_diff
from utils.yn import prompt_yes_no


def main():
    if prompt_yes_no("Do you want to run the scraper?"):
        print("Launching scraper...")
        asyncio.run(run_scraper())

    if prompt_yes_no("Do you want to run a diff comparison?"):
        print("Launching comparison CLI...")
        run_diff()

    print("\nCLI workflow complete.")


if __name__ == "__main__":
    main()