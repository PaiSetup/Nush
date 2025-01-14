#!/bin/python

import argparse
import sys
from collections import Counter
from pathlib import Path


class FileInfo:
    def __init__(self, path):
        self.path = path
        self.is_indexed = True
        try:
            self.index = int(path.stem)
            self.index_length = len(path.stem)
        except ValueError:
            self.is_indexed = False


def get_duplicates(file_infos):
    duplicate_map = {}
    for file in file_infos:
        if file.index not in duplicate_map:
            duplicate_map[file.index] = [file]
        else:
            duplicate_map[file.index].append(file)

    duplicate_map = {index: files for index, files in duplicate_map.items() if len(files) != 1}
    return duplicate_map


if __name__ == "__main__":
    # fmt: off
    arg_parser = argparse.ArgumentParser(description="Add leading zero to files with indexed names like 001.jpg", allow_abbrev=False)
    arg_parser.add_argument("directory", type=Path, help="Directories with indexed files")
    arg_parser.add_argument("-v", "--verbose", action="store_true", help="Show verbose output")
    arg_parser.add_argument("-n", "--dryrun", action="store_true", help="Do not perform any action.")
    args = arg_parser.parse_args()
    # fmt: on

    # Get all files in the directory
    files = []
    for file in args.directory.iterdir():
        files.append(FileInfo(file))
    if not files:
        sys.exit(0)

    # Validate all files are indexed
    non_indexed = [f for f in files if not f.is_indexed]
    if non_indexed:
        print("ERROR: some filenames are not indexed")
        for f in non_indexed:
            print(f"  {f.path.name}")
            sys.exit(1)

    # Validate all indices have the same length
    lenghts = (f.index_length for f in files)
    lenghts = Counter(lenghts)
    if len(lenghts) != 1:
        print("ERROR: different index lengths")
        for length, count in lenghts.items():
            print(f"  {count} files with index length {length}")
        sys.exit(1)

    # Validate there are no duplicates
    duplicates = get_duplicates(files)
    if duplicates:
        print("ERROR: duplicate indices")
        for duplicate_files in duplicates.values():
            names = [str(f.path.name) for f in duplicate_files]
            names = ", ".join(names)
            print(f"  {names}")
        sys.exit(1)

    # Prepare rename list
    src_index_length = list(lenghts.keys())[0]
    dst_index_length = src_index_length + 1
    rename_list = []
    for file in files:
        src_path = file.path

        dst_stem = str(file.index).zfill(dst_index_length)
        dst_path = file.path.with_stem(dst_stem)

        rename_list.append((src_path, dst_path))

    # Verbose output
    if args.verbose:
        print("Rename list:")
        for src, dst in rename_list:
            print(f"  {src} -> {dst}")
        print()

    # Perform actual purpose of the script
    if args.dryrun:
        print("Performing a dry run (no action done)")
    else:
        print(f"Performing index extension from {src_index_length} to {dst_index_length}")
        for src, dst in rename_list:
            src.rename(dst)
