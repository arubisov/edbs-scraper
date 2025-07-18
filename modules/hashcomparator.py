"""
hashcomparator.py - updated 2025-07-17

Functions:
- sha256_hash_file(filePath): Hashes a single file using SHA-256 and returns (filename, hash).
- hash_directory_multithreaded(path): Computes hashes of all files in a directory using multithreading.
- is_timestamped_dir(name): Checks if a directory name follows the DD-HHMMSS timestamp format.
- sort_dirs_if_timestamped(dir1, dir2): If both directories are timestamped, returns them in chronological order.
- compare_hash_dicts(dict1, dict2): Compares two hash dictionaries and returns changed, added, and removed filenames.
- hash_and_compare(directory1, directory2): Hashes files in both directories (in parallel) and returns lists of changed, added, and removed files.
"""

import os, re, hashlib, argparse, logging
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from logconfig import setup_logger
lgg = setup_logger(logging.INFO)


def sha256_hash_file(filePath: str) -> Optional[tuple[str, str]]:
    if not os.path.isfile(filePath):
        return None
    sha256 = hashlib.sha256()
    try:
        with open(filePath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return os.path.basename(filePath), sha256.hexdigest()
    except Exception as e:
        lgg.er(f"Could not hash '{filePath}': {e}")
        return None


def hash_directory_multithreaded(path: str) -> dict[str, str]:
    if not os.path.isdir(path):
        lgg.w(f"Directory does not exist: {path}")
        return {}

    file_paths = [os.path.join(path, f) for f in os.listdir(path)]
    hashes = {}

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(sha256_hash_file, fp): fp for fp in file_paths}
        for future in as_completed(futures):
            result = future.result()
            if result:
                fileName, hashVal = result
                hashes[fileName] = hashVal

    return hashes


def is_timestamped_dir(name: str) -> bool:
    return bool(re.match(r"\d{2}-\d{6}$", os.path.basename(name)))


def sort_dirs_if_timestamped(dir1: str, dir2: str) -> tuple[str, str]:
    base1, base2 = os.path.basename(dir1), os.path.basename(dir2)
    if is_timestamped_dir(base1) and is_timestamped_dir(base2):
        try:
            ts1 = datetime.strptime(base1, "%y%m%d-%H%M%S")
            ts2 = datetime.strptime(base2, "%y%m%d-%H%M%S")
            return (dir1, dir2) if ts1 < ts2 else (dir2, dir1)
        except ValueError:
            pass
    return dir1, dir2


def compare_hash_dicts(dict1: dict[str, str], dict2: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())

    removed = sorted(keys1 - keys2)
    added = sorted(keys2 - keys1)
    common = keys1 & keys2

    lgg.i("Comparison Results:")

    if removed:
        lgg.i("Files only in Directory 1 (removed):")
        for k in removed:
            lgg.i(f"  {k}")

    if added:
        lgg.i("Files only in Directory 2 (added):")
        for k in added:
            lgg.i(f"  {k}")

    changed = sorted([k for k in common if dict1[k] != dict2[k]])
    if changed:
        lgg.i("Files with same name but different content:")
        for k in changed:
            lgg.i(f"  {k}")

    matches = [k for k in common if dict1[k] == dict2[k]]
    if matches:
        lgg.i(f"{len(matches)} identical files found.")

    if not any([removed, added, changed]):
        lgg.i("All files match exactly.")

    return changed, added, removed


def hash_and_compare(directory1: str, directory2: str) -> tuple[list[str], list[str], list[str]]:
    if not directory1 or not directory2:
        raise ValueError("Both directory1 and directory2 must be provided.")

    directory1, directory2 = sort_dirs_if_timestamped(directory1, directory2)

    with ThreadPoolExecutor() as executor:
        future1 = executor.submit(hash_directory_multithreaded, directory1)
        future2 = executor.submit(hash_directory_multithreaded, directory2)
        hashDict1 = future1.result()
        hashDict2 = future2.result()

    return compare_hash_dicts(hashDict1, hashDict2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare two directories of .txt files using SHA-256 hashes."
    )

    parser.add_argument("olddir", nargs="?", help="Path to the old directory (positional or --olddirectory)")
    parser.add_argument("newdir", nargs="?", help="Path to the new directory (positional or --newdirectory)")

    args = parser.parse_args()

    dir1 = args.olddir_kw or args.olddir
    dir2 = args.newdir_kw or args.newdir

    if not dir1 or not dir2:
        parser.error("You must provide both directories either as positional or keyword arguments.")

    dir1, dir2 = sort_dirs_if_timestamped(dir1, dir2)
    lgg.i(f"Comparing directories:\n  OLD: {dir1}\n  NEW: {dir2}")

    differences, added_files, removed_files = hash_and_compare(dir1, dir2)
    print((differences, added_files, removed_files))