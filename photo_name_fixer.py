#!/bin/python

import argparse
import datetime
import os
import re
import shutil
import sys
import zoneinfo
from pathlib import Path

match_year = r"20[0-9]{2}"
match_month = r"0[0-9]|1[0-2]"
match_day = r"[0-2][0-9]|3[0-1]"
match_hour = r"[0-1][0-9]|2[0-4]"
match_minute = r"[0-5][0-9]"
match_second = match_minute
match_millisecond = r"[0-9][0-9][0-9]"
match_sep1 = r"-?"
match_sep2 = r"[_ ]"


class NameFixer:
    def __init__(self, allow_metadata, timezone):
        self._prefixes = r"IMG-|IMG_|VID_|VideoCapture_"
        self._suffixes = r"_HDR|-WA[0-9]+|_TIMEBURST[0-9]+|_[0-9]+|~[0-9]+| ?\([0-9]+\)"
        self.disassemble_functions = [
            self.disassemble_yymmdd_hhmmss,
            self.disassemble_yymmdd_wa,
            self.disassemble_yymmdd,
        ]
        if allow_metadata:
            self.timezone = timezone
            self.disassemble_functions.append(self.disassembly_from_metadata)

    def fix(self, name):
        path = Path(name)

        disassembly_comment, tokens = self.disassemble(path)
        if tokens is None:
            return (None, None)
        else:
            return (disassembly_comment, self.assemble(path.parent, tokens, path.suffix))

    def assemble(self, dir, tokens, extension):
        (year, month, day, hour, minute, second) = tokens
        return Path(dir, f"{year:04}{month:02}{day:02}_{hour:02}{minute:02}{second:02}{extension}")

    def disassemble(self, path):
        for fn in self.disassemble_functions:
            result = fn(path)
            if result is not None:
                return (fn.__name__, result)
        return (None, None)

    def disassemble_yymmdd_hhmmss(self, path):
        """
        Takes names in format YYYYMMDD_HHMMSS, such as "20220714_103015". Date and hour tokens can be extracted directly from name.
        """
        pattern = (
            f"^({self._prefixes})?"
            f"({match_year}){match_sep1}({match_month}){match_sep1}({match_day})"
            f"{match_sep2}"
            f"({match_hour}){match_sep1}({match_minute}){match_sep1}({match_second}){match_sep1}({match_millisecond})?"
            f"($|{self._suffixes})"
        )
        result = re.search(pattern, path.stem)
        if result is None:
            return None

        result = result.groups()
        result = result[1:4] + result[4:7]
        return result

    def disassemble_yymmdd_hhmmss_hyphens_space(self, path):
        """
        Takes names in format "YYYY-MM-DD HH-MM-SS", such as "2024-08-24 19-31-14". Date and hour tokens can be extracted directly from name.
        """
        result = re.search(
            f"^({self._prefixes})?({match_year})-({match_month})-({match_day}) ({match_hour})({match_minute})({match_second})({match_millisecond})?($|{self._suffixes})",
            path.stem,
        )
        if result is None:
            return None
        result = result.groups()
        result = result[1:4] + result[5:8]
        return result

    def disassemble_yymmdd_wa(self, path):
        """
        Takes names in format YYYYMMDD with WA suffix, such as "20220714-WA0001". Date tokens can be extracted directly from name. Hour tokens cannot be
        extracted and they are assigned made up values based on index after 'WA'.
        """
        result = re.search(
            f"^({self._prefixes})?({match_year})({match_month})({match_day})-WA([0-9]+)",
            path.stem,
        )
        if result is None:
            return None
        result = result.groups()

        time = (
            int(result[4]) // 3600,
            int(result[4]) // 60 % 60,
            int(result[4]) % 60,
        )
        result = result[1:4] + time
        return result

    def disassemble_yymmdd(self, path):
        """
        Takes names in format YYYYMMDD, such as "20220714". Date tokens can be extracted directly from name. Hour tokens cannot be
        extracted and they are assigned as 0.
        """
        result = re.search(
            f"^({self._prefixes})?({match_year})({match_month})({match_day})($|{self._suffixes})",
            path.stem,
        )
        if result is None:
            return None
        result = result.groups()
        result = result[1:4] + (0, 0, 0)
        return result

    def disassembly_from_metadata(self, path):
        """
        This function processes files from which we cannot extract all date/time tokens just by filename. They can be instead extracted
        from file metadata. This is not very reliable though - metadata can be broken by various programs and editing.
          - IMG_XXXX - some phones just assign an increasing index to all photos
          - IMG-YYYYMMDD-WAXXXX - WhatsApp places send date and some increasing index as a filename
        """

        # Match our path to one of patterns
        patterns = [
            f"(IMG|VID)-{match_year}{match_month}{match_day}-WA[0-9]+",
            "IMG_[A-Z]?[0-9]+",
        ]
        patterns = [f"(^{x}$)" for x in patterns]
        pattern = "|".join(patterns)
        result = re.match(
            pattern,
            path.stem,
        )
        if result is None:
            return None

        # Get earliest timestamp that we have
        stat = path.stat()
        unix_timestamp = min(stat.st_ctime, stat.st_mtime, stat.st_atime)

        # Convert to tuple
        date = datetime.datetime.fromtimestamp(unix_timestamp, self.timezone)
        date_str = date.strftime("%Y-%m-%d-%H-%M-%S")
        date_tokens = tuple(date_str.split("-"))
        return date_tokens


class RenameMap:
    def __init__(self):
        self._map = {}
        self._disassembly_info = {}

    def add(self, src, dst, disassembly_comment):
        self._map[src] = dst
        self._disassembly_info[src] = disassembly_comment

    def has_none(self):
        return None in self._map.values()

    def point_to_directory(self, root_src_dirs, root_dst_dir):
        new_map = {}
        for src, dst in self._map.items():
            if dst is None:
                new_dst = None
                continue
            else:
                # Find directory's suffix. For example if:
                #  - directory is /home/maciej/photos/
                #  - our photo is /home/maciej/photos/first_day/11.jpg
                # then the suffix is 'first_day/11.jpg'
                suffix = None
                for root_src_dir in root_src_dirs:
                    try:
                        suffix = dst.relative_to(root_src_dir)
                    except ValueError:
                        continue
                if suffix is None:
                    raise ValueError(f"Could not find path suffix for {dst}")

                # Add the suffix to new destination
                new_dst = Path(root_dst_dir, suffix)
            new_map[src] = new_dst

        # Update self
        self._map = new_map

    def make_unique(self):
        seen_values = set()
        for src, dst in self._map.items():
            actual_dst = dst

            if actual_dst in seen_values:
                for i in range(1, 999999):
                    actual_dst = Path(dst.parent, f"{dst.stem}_{i}{dst.suffix}")
                    if actual_dst not in seen_values:
                        self._map[src] = actual_dst
                        break

            seen_values.add(actual_dst)

    def to_string(self, only_nones):
        result = ""
        result += "{\n"
        max_src_length = max((len(x) for x in self._map.keys()))
        max_dst_length = max((len(str(x)) for x in self._map.values()))
        for src, dst in self._map.items():
            if not only_nones or str(dst).startswith("None"):
                disassembly_comment = self._disassembly_info[src]
                result += f"    {src: <{max_src_length}}   -> {str(dst): <{max_dst_length}}   ({disassembly_comment}) \n"
        result += "}"
        return result

    def __iter__(self):
        return iter(self._map.items())


def get_files(directories):
    result = []
    for directory in directories:
        for folder, _, files in os.walk(directory):
            result += [os.path.join(folder, f) for f in files]
    return result


def copy_files(rename_map, dst_dir):
    dst_dir = Path(dst_dir)
    if dst_dir.exists():
        print("ERROR: specify nonexistant directory for copy operation")
        sys.exit(1)

    print("Performing a copy operation")
    dst_dir.mkdir(parents=True)
    for src, dst in rename_map:
        shutil.copyfile(src, dst)


def rename_files(rename_map):
    print("Performing an in-place rename operation")
    for src, dst in rename_map:
        shutil.move(src, dst)


if __name__ == "__main__":
    # fmt: off
    arg_parser = argparse.ArgumentParser(description="Fix names of photos generated by different phones/cameras", allow_abbrev=False)
    arg_parser.add_argument("-v", "--verbose", action="store_true", help="show verbose output")
    arg_parser.add_argument("-n", "--dryrun", action="store_true", help="do not perform any action. Default if neither --copyto, nor --renameinplace was specified.")
    arg_parser.add_argument("-d", "--directories", nargs='+', type=Path, required=True, help="Directories with photos")
    arg_parser.add_argument("-c", "--copyto", type=Path, help="Perform a copy operation to specified path")
    arg_parser.add_argument("-i", "--renameinplace", action="store_true", help="Perform a rename operation on input files")
    arg_parser.add_argument("-m", "--allowmetadata", action="store_true", help="Allow looking at file metadata to find out the date. Not recommended. Requires --timezone.")
    arg_parser.add_argument("-t", "--timezone", type=str, help="Timezone used for extracting date from metadata.")
    args = arg_parser.parse_args()
    # fmt: on

    if args.allowmetadata:
        try:
            timezone = zoneinfo.ZoneInfo(args.timezone)
        except:
            print("ERROR: specify a valid timezone when allowing metadata.")
            sys.exit(1)

    # Verify directory with images
    for directory in args.directories:
        if not directory.is_dir():
            print(f'ERROR: specified directory "{directory}" does not exist.')
            sys.exit(1)

    # Get files and prepare a rename map - a dictionary in which key is old filename and value is new filename
    name_fixer = NameFixer(args.allowmetadata, timezone)
    rename_map = RenameMap()
    files = get_files(args.directories)
    for file in files:
        disassembly_comment, dst = name_fixer.fix(file)
        rename_map.add(file, dst, disassembly_comment)

    if args.copyto:
        rename_map.point_to_directory(args.directories, args.copyto)

    # Verify rename map
    if rename_map.has_none():
        print("ERROR: some filenames were not matched. Aborting.")
        print(rename_map.to_string(True))
        sys.exit(1)

    # Add sufixes to duplicate values
    rename_map.make_unique()

    # Verbose output
    if args.verbose:
        print("Rename map:")
        print(rename_map.to_string(False))
        print()

    # Perform actual purpose of the script
    if args.dryrun:
        print("Performing a dry run (no action done)")
    else:
        if args.copyto:
            copy_files(rename_map, args.copyto)
        elif args.renameinplace:
            rename_files(rename_map)
