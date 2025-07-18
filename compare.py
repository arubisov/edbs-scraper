"""
compare.py - updated 2025-07-17

Functions:
- prompt_yes_no(message): Repeatedly prompts the user for a yes/no input and returns True or False.
- get_directory_input(prompt_text): Prompts the user for a valid directory path and validates its existence.
- is_timestamped_dir(name): Returns True if the given directory name matches the YYYYMMDD-HHMMSS timestamp format.
- sort_by_timestamp_if_possible(dir1, dir2): If both directories are timestamped, returns them in chronological order.
- run_comparison(dir1, dir2): Handles ordering logic, prompts the user for confirmation, runs the hash comparison, and generates the diff report.
- main(): Parses CLI arguments or prompts the user, then kicks off the directory comparison process.
"""

import os, re, argparse, logging
from modules.logconfig import setup_logger
from modules.hashcomparator import hash_and_compare
from modules.diffgen import generate_diff_report
lgg = setup_logger(logging.INFO)

def prompt_yes_no(message: str) -> bool:
    while True:
        response = input(f"{message} (y/n): ").strip().lower()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        else:
            print("Please enter 'y' or 'n'.")


def get_directory_input(prompt_text: str) -> str:
    while True:
        path = input(f"{prompt_text}: ").strip()
        if os.path.isdir(path):
            return path
        lgg.er("That path does not exist. Try again.")


def is_timestamped_dir(name: str) -> bool:
    return bool(re.match(r"^\d{8}-\d{6}$", os.path.basename(name)))

def run_comparison(dir1: str, dir2: str) -> tuple[str, str] | None:
    base1_input = os.path.basename(os.path.normpath(dir1))
    base2_input = os.path.basename(os.path.normpath(dir2))

    if is_timestamped_dir(base1_input) and is_timestamped_dir(base2_input):
        if base1_input > base2_input:
            lgg.w(f"'{base1_input}' appears newer than '{base2_input}', but was passed as the OLD directory.")
            if not prompt_yes_no("Would you like to auto-sort them (older first) before proceeding?"):
                lgg.i("Operation cancelled.")
                return None
            lgg.i(f"Auto-sorting directories: {base2_input} (OLD), {base1_input} (NEW)")
            dir1, dir2 = dir2, dir1

    lgg.w(f"You are about to compare:\n  OLD: {dir1}\n  NEW: {dir2}")
    if not prompt_yes_no("Proceed with comparison?"):
        lgg.i("Operation cancelled.")
        return None

    return dir1, dir2

def main(old_dir: str, new_dir: str) -> None:
    differences, added_files, removed_files = hash_and_compare(old_dir, new_dir)
    generate_diff_report(differences, added_files, removed_files, old_dir, new_dir)


def cli():
    parser = argparse.ArgumentParser(description="Execution handler for hash & diff tools.")
    parser.add_argument("olddir", nargs="?", help="Old directory (positional)")
    parser.add_argument("newdir", nargs="?", help="New directory (positional)")

    args = parser.parse_args()

    # Priority: positional > prompt
    dir1 = args.olddir or get_directory_input("Enter path to OLD directory")
    dir2 = args.newdir or get_directory_input("Enter path to NEW directory")

    sorted_dirs = run_comparison(dir1, dir2)
    if not sorted_dirs:
        return

    old_dir, new_dir = sorted_dirs
    main(old_dir, new_dir)


if __name__ == "__main__":
    cli()