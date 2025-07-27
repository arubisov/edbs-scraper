"""
PATH: ./wix-scraper/utils/

Functions:
- prompt_yes_no(message): Repeatedly prompts the user for a yes/no input and returns True or False.
- get_directory_input(prompt_text): Prompts the user for a valid directory path and validates its existence.
- is_timestamped_dir(name): Returns True if the given directory name matches the YYYYMMDD-HHMMSS timestamp format.
- run_comparison(dir1, dir2): Confirms timestamp sort order and prompts user for comparison approval.
- main(old_dir, new_dir): Executes hashing and diff generation between the given directories.
- cli(): CLI interface for directory input, comparison validation, and main execution call.
"""

import argparse
import re
from pathlib import Path

from utils.configs.logger import logger
from utils.diffscripts.diffgen import generate_diff_report
from utils.diffscripts.hashcomparator import hash_and_compare
from utils.yn import prompt_yes_no


def get_directory_input(prompt_text: str) -> Path:
    while True:
        path = Path(input(f"{prompt_text}: ").strip()).resolve()
        if path.is_dir():
            return path
        logger.error("Input directory path does not exist", path=path)


def is_timestamped_dir(name: str) -> bool:
    return bool(re.match(r"^\d{8}-\d{6}$", name))


def run_comparison(dir1: Path, dir2: Path) -> tuple[Path, Path] | None:
    base1_input = dir1.name
    base2_input = dir2.name

    if is_timestamped_dir(base1_input) and is_timestamped_dir(base2_input):
        if base1_input > base2_input:
            logger.warning(
                "Old directory appears newer than new directory; check order.",
                old_dir=base1_input,
                new_dir=base2_input,
            )
            if not prompt_yes_no(
                "Would you like to auto-sort them (older first) before proceeding?"
            ):
                logger.info("Operation cancelled by user.")
                return None
            logger.info(
                "Auto-sorting directories for comparison.",
                old_dir=base2_input,
                new_dir=base1_input,
            )
            dir1, dir2 = dir2, dir1

    logger.info(
        "About to compare directories.",
        old_dir=str(dir1),
        new_dir=str(dir2),
    )
    if not prompt_yes_no("Proceed with comparison?"):
        logger.info("Operation cancelled by user.")
        return None

    return dir1, dir2


def main(old_dir: Path, new_dir: Path) -> None:
    differences, added_files, removed_files = hash_and_compare(str(old_dir), str(new_dir))
    generate_diff_report(differences, added_files, removed_files, str(old_dir), str(new_dir))


def cli():
    parser = argparse.ArgumentParser(description="Execution handler for hash & diff tools.")
    parser.add_argument("olddir", nargs="?", help="Old directory (positional)")
    parser.add_argument("newdir", nargs="?", help="New directory (positional)")
    args = parser.parse_args()

    dir1 = (
        Path(args.olddir).resolve()
        if args.olddir
        else get_directory_input("Enter path to OLD directory")
    )
    dir2 = (
        Path(args.newdir).resolve()
        if args.newdir
        else get_directory_input("Enter path to NEW directory")
    )

    sorted_dirs = run_comparison(dir1, dir2)
    if not sorted_dirs:
        return

    old_dir, new_dir = sorted_dirs
    main(old_dir, new_dir)


if __name__ == "__main__":
    cli()
