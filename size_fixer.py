#!/bin/python

import argparse
import datetime
import multiprocessing
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


class CommandError(Exception):
    def __init__(self, output):
        self.stdout = self.stderr = None
        if output is not None:
            if output[0] is not None:
                self.stdout = output[0].decode("utf-8")
            if output[1] is not None:
                self.stderr = output[1].decode("utf-8")

    def __str__(self):
        print(f"stdout: {self.stdout}\n\nstderr: {self.stderr}")


def run_command(command, *, stdin=subprocess.PIPE, ignore_stdout=False):
    command = shlex.split(command)

    stdout = subprocess.PIPE
    if ignore_stdout:
        stdout = None
    process = subprocess.Popen(command, shell=False, stdout=stdout, stderr=stdout)
    output = process.communicate()
    return_value = process.wait()

    if return_value != 0:
        raise CommandError(output)


def get_files(directory):
    result = []
    for folder, _, files in os.walk(directory):
        result += [Path(os.path.join(folder, f)) for f in files]
    return result


def downscale_file(root_dir, dst_dir, file, max_size):
    print(f"  {file}: ", end="")

    # Prepare output paths
    path = Path(file)
    suffix = file.relative_to(root_dir)
    out_path = dst_dir / suffix
    out_path.parent.mkdir(parents=True, exist_ok=True)
    extension = path.suffix.lower()

    # HEIC conversion
    is_heic = extension == ".heic"
    if is_heic:
        tmp_path = out_path.with_suffix(".tmp.jpg")
        command = f'heif-convert "{path}" "{tmp_path}"'
        run_command(command)

        path = tmp_path
        out_path = out_path.with_suffix(".jpg")

    # Get filesize
    original_size = path.stat().st_size

    # Early returns
    if original_size <= max_size:
        shutil.copyfile(path, out_path)
        print(" (SIZE OK)")
        return

    # Perform actual conversion
    if extension in [".heic", ".png", ".jpg"]:
        factor = max_size / original_size
        factor = factor ** (1 / 2)
        factor = int(factor * 100) + 1
        factor = max(factor, 50)
        print(f"Image scaled down to {factor}%   ", end="")
        command = f'convert -resize {factor}% -quality 80% "{path}" "{out_path}"'
        run_command(command)
    elif extension in [".mp4", ".mov"]:
        print("Video encoded with libx265 code with crf=28   ", end="")
        command = f'ffmpeg -i "{path}" -vcodec libx265 -crf 28 "{out_path}" -y'
        run_command(command)
    else:
        print(" (UNKNOWN FORMAT) copying without changes")
        shutil.copyfile(path, out_path)
        return

    #  Remove temporary file from HEIC conversion
    if is_heic:
        tmp_path.unlink()

    # Summarize
    new_size = out_path.stat().st_size
    success = "SUCCESS" if new_size < max_size else "STILL TOO BIG"
    print(f"{int(original_size/1024)}KiB -> {int(new_size/1024)}KiB ({success})")


if __name__ == "__main__":
    # fmt: off
    arg_parser = argparse.ArgumentParser(description="Downscale images to match given disk size constraints.", allow_abbrev=False)
    arg_parser.add_argument("-d", "--directory", type=Path, required=True, help="Directory with photos")
    arg_parser.add_argument("-o", "--output", type=Path, required=True, help="Output directory")
    arg_parser.add_argument("-m", "--max-size", type=int, required=True, help="Max size of a photo in KiB")
    arg_parser.add_argument("-p", "--processes", type=int, required=True, help="Number of processes to perform the operations in parallel")
    args = arg_parser.parse_args()
    # fmt: on

    # Verify passed directories
    if not args.directory.is_dir():
        print("ERROR: specified directory does not exist.")
        sys.exit(1)
    if args.directory.is_relative_to(args.output) or args.output.is_relative_to(args.directory):
        print("ERROR: src and dst directories cannot be contained in each other")
        sys.exit(1)
    args.output.mkdir(parents=True, exist_ok=True)

    # Traverse the files and put them in a list
    files = get_files(args.directory)

    print("Performing a downscale operation")
    print(f"  src_dir = {args.directory}")
    print(f"  dst_dir = {args.output}")
    print(f"  max_size = {args.max_size}KiB")
    print(f"  processes = {args.processes}")
    print()
    max_size_in_bytes = args.max_size * 1024
    if args.processes < 1:
        print("ERROR: processes must be a positive value")
        sys.exit(1)
    elif args.processes == 1:
        for file in files:
            downscale_file(args.directory, args.output, file, max_size_in_bytes)
    else:
        asyncs = []
        with multiprocessing.Pool(args.processes) as pool:
            for file in files:
                a = pool.apply_async(downscale_file, args=(args.directory, args.output, file, max_size_in_bytes))
                asyncs.append(a)
            for a in asyncs:
                a.wait()
