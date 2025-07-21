"""
PATH: ./wix-scraper/utils/diffscripts/

Functions:
- sha256_hash_file(filePath): Hashes a single file using SHA-256 and returns (filename, hash).
- hash_directory_multithreaded(path): Computes hashes of all files in a directory using multithreading.
- is_timestamped_dir(name): Checks if a directory name follows the DD-HHMMSS timestamp format.
- sort_dirs_if_timestamped(dir1, dir2): If both directories are timestamped, returns them in chronological order.
- compare_hash_dicts(dict1, dict2): Compares two hash dictionaries and returns changed, added, and removed filenames.
- hash_and_compare(directory1, directory2): Hashes files in both directories (in parallel) and returns lists of changed, added, and removed files.
"""

import re, hashlib, argparse, logging
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.configs.config import setup_logger
lgg = setup_logger(logging.INFO)


def sha256_hash_file(file_path: Path) -> tuple[str, str] | None:
    if not file_path.is_file():
        return None

    sha256 = hashlib.sha256()
    try:
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return file_path.name, sha256.hexdigest()
    except Exception as e:
        lgg.er(f"Could not hash '{file_path}': {e}")
        return None


def hash_directory_multithreaded(path: str) -> dict[str, str]:
    dir_path = Path(path).resolve()
    if not dir_path.is_dir():
        lgg.w(f"Directory does not exist: {dir_path}")
        return {}

    file_paths = [p for p in dir_path.rglob("*") if p.is_file()]
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
    return bool(re.match(r"\d{8}-\d{6}$", name))


def sort_dirs_if_timestamped(dir1: str, dir2: str) -> tuple[str, str]:
    base1, base2 = Path(dir1).name, Path(dir2).name
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
    parser.add_argument("olddir", nargs="?", help="Path to the old directory (positional)")
    parser.add_argument("newdir", nargs="?", help="Path to the new directory (positional)")

    args = parser.parse_args()

    dir1 = Path(args.olddir).resolve() if args.olddir else None
    dir2 = Path(args.newdir).resolve() if args.newdir else None

    if not dir1 or not dir2:
        parser.error("You must provide both directories as positional arguments, preferably as [oldDir] [newDir].")

    dir1_str, dir2_str = sort_dirs_if_timestamped(str(dir1), str(dir2))
    lgg.i(f"Comparing directories:\n  OLD: {dir1_str}\n  NEW: {dir2_str}")

    differences, added_files, removed_files = hash_and_compare(dir1_str, dir2_str)
    print((differences, added_files, removed_files))