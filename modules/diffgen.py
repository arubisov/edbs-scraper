"""
diffgen.py - updated 2025-07-17

Functions:
- generate_diff_report(filenames, addedFiles, removedFiles, dir1, dir2):
  Compares matching files line-by-line and outputs a diff report, including added and removed files.
"""

import os, logging, shutil
from difflib import SequenceMatcher
from . import logconfig
lgg = logconfig.setup_logger(logging.INFO)

def generate_diff_report(changed_files, added_files, removed_files, dir1, dir2):
    # Derive base names of input directories
    name1 = os.path.basename(os.path.normpath(dir1))
    name2 = os.path.basename(os.path.normpath(dir2))
    filename_out = f"{name1}_{name2}.diff.txt"

    # Use NEW (more recent) directory's name for export folder
    export_folder_name = name2
    base_dir = os.path.dirname(os.path.abspath(__file__))
    exports_dir = os.path.join(base_dir, "..", "results", "exports", export_folder_name)
    os.makedirs(exports_dir, exist_ok=True)

    output_file = os.path.join(exports_dir, filename_out)

    with open(output_file, "w", encoding="utf-8") as out:
        for filename in changed_files:
            file1_path = os.path.join(dir1, filename)
            file2_path = os.path.join(dir2, filename)

            try:
                with open(file1_path, "r", encoding="utf-8") as f1, open(file2_path, "r", encoding="utf-8") as f2:
                    lines1 = f1.readlines()
                    lines2 = f2.readlines()

                matcher = SequenceMatcher(None, lines1, lines2)
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag == 'equal':
                        continue  # Skip unchanged parts

                    out.write(f"\n--- Change ({tag.upper()}): {filename}\n")

                    if tag in ('replace', 'delete'):
                        out.write(f"<<<< {name1}/{filename} [lines {i1 + 1}-{i2}]\n")
                        out.writelines(line if line.strip() else "[BLANK LINE]\n" for line in lines1[i1:i2])

                    if tag in ('replace', 'insert'):
                        out.write(f">>>> {name2}/{filename} [lines {j1 + 1}-{j2}]\n")
                        out.writelines(line if line.strip() else "[BLANK LINE]\n" for line in lines2[j1:j2])

                    out.write("\n")  # Visual separation between chunks

            except FileNotFoundError as e:
                out.write(f"Error: {e}\n")
            except Exception as e:
                out.write(f"Unexpected error comparing {filename}: {e}\n")

        # Summary of added and removed files
        out.write("\n-----------------------\nAdded files:\n")
        out.writelines(f"{file}\n" for file in added_files) if added_files else out.write("(None)\n")

        out.write("\n------------------------\nRemoved files:\n")
        out.writelines(f"{file}\n" for file in removed_files) if removed_files else out.write("(None)\n")

    lgg.i(f"Differences written to: {output_file}")

    # Copy added files to ./results/exports/[new]
    for file in added_files:
        src_path = os.path.join(dir2, file)
        dst_path = os.path.join(exports_dir, file)
        try:
            shutil.copy2(src_path, dst_path)
            lgg.i(f"Exported added file: {file}")
        except Exception as e:
            lgg.i(f"Failed to export '{file}': {e}")

    # Copy changed files to ./results/exports/[new]
    for file in changed_files:
        src_path = os.path.join(dir2, file)
        dst_path = os.path.join(exports_dir, file)
        try:
            shutil.copy2(src_path, dst_path)
            lgg.i(f"Exported changed file: {file}")
        except Exception as e:
            lgg.i(f"Failed to export changed file '{file}': {e}")