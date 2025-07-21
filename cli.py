"""
PATH: ./wix-scraper/

Functions:
- prompt_yes_no(msg): Prompts user for a yes/no response in the terminal.
- main(): Executes scraper and/or diff comparison workflows based on user prompts.
"""

import asyncio
from utils.scrape import main as run_scraper
from utils.compare import cli as run_diff


def prompt_yes_no(msg: str) -> bool:
    while True:
        response = input(f"{msg} (y/n): ").strip().lower()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        else:
            print("Please enter 'y' or 'n'.")


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