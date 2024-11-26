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
from enum import Enum
from pathlib import Path


class CommandError(Exception):
    def __init__(self, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        print(f"stdout: {self.stdout}\n\nstderr: {self.stderr}")


def run_command(command, *, stdin=subprocess.PIPE):
    # Run command
    command = shlex.split(command)
    process = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Process output
    (stdout_data, stderr_data) = process.communicate()
    if stdout_data is not None:
        stdout_data = stdout_data.decode("utf-8")
    if stderr_data is not None:
        stderr_data = stderr_data.decode("utf-8")

    # Check return value
    return_value = process.wait()
    if return_value != 0:
        raise CommandError(stdout_data, stderr_data)

    # Return stdout
    return stdout_data


def get_files(directory):
    result = []
    for folder, _, files in os.walk(directory):
        result += [Path(os.path.join(folder, f)) for f in files]
    return result


def generate_str_percentage(value, max_value):
    if value <= max_value:
        return "OK"
    else:
        percentage = ((value - max_value) / max_value) * 100
        return f"{percentage:.1f}% TOO BIG"


def downscale_video(inp_path, out_path, max_video_bitrate_bps):
    def get_bitrate(path):
        probe_command = f'ffprobe -v quiet -select_streams v:0 -show_entries stream=bit_rate -of default=noprint_wrappers=1:nokey=1 "{path}"'
        bitrate = run_command(probe_command)
        bitrate = bitrate.strip()
        return int(bitrate)

    str_file = f"{inp_path} -> {out_path}"

    # Try to early return
    original_size = inp_path.stat().st_size
    original_bitrate = get_bitrate(inp_path)
    if original_bitrate <= max_video_bitrate_bps:
        shutil.copyfile(inp_path, out_path)
        return f"Video copied {str_file} (bitrate was {original_bitrate//1024} KBPS)"

    # Perform downscaling
    command = f'ffmpeg -i "{inp_path}" -filter:v "scale" -b:v {max_video_bitrate_bps} "{out_path}" -y'
    run_command(command)
    new_size = out_path.stat().st_size
    new_bitrate = get_bitrate(out_path)

    # Prepare result string
    str_size = f"{original_size//1024}KiB->{new_size//1024}KiB"
    str_bitrate = f"{original_bitrate//1024}KBPS->{new_bitrate//1024}KBPS"
    str_bitrate_result = f"(BITRATE {generate_str_percentage(new_bitrate, max_video_bitrate_bps)})"
    return f"Video scaled {str_file} {str_size}, {str_bitrate} {str_bitrate_result}"


def downscale_image(inp_path, out_path, max_image_size_bytes):
    str_file = f"{inp_path} -> {out_path}"

    # Try to early return
    original_size = inp_path.stat().st_size
    if original_size < max_image_size_bytes:
        shutil.copyfile(inp_path, out_path)
        return f"Image copied {str_file}"

    # Perform downscaling
    factor = max_image_size_bytes / original_size
    factor = factor ** (1 / 2)
    factor = int(factor * 100) + 1
    factor = max(factor, 50)
    print(f"Image scaled down to {factor}%   ", end="")
    command = f'convert -resize {factor}% -quality 80% "{inp_path}" "{out_path}"'
    run_command(command)
    new_size = out_path.stat().st_size

    # Prepare result string
    str_size = f"{original_size//1024}KiB->{new_size//1024}KiB"
    str_size_result = f"(SIZE {generate_str_percentage(new_size, max_image_size_bytes)})"
    return f"Image scaled {str_file} {str_size} {str_size_result}"


def downscale_image_heic(inp_path, out_path, max_image_size_bytes):
    if inp_path.suffix.lower() != ".heic":
        raise ValueError("Input path is expected to have .heic extension.")
    if out_path.suffix.lower() != ".jpg":
        raise ValueError("Output path is expected to have .jpg extension.")

    # First convert from .heic to .jpg
    inp_path_jpg = out_path.with_suffix(".heic.jpg")
    command = f'heif-convert "{inp_path}" "{inp_path_jpg}"'
    run_command(command)

    # Downscale the .jpg
    result = downscale_image(inp_path_jpg, out_path, max_image_size_bytes)

    # Remove temporary input jpg
    inp_path_jpg.unlink()

    return result


def downscale_file(root_dir, dst_dir, file, max_image_size_bytes, max_video_bitrate_bps):
    print(f"Start processing {file}")

    # Prepare output paths
    inp_path = Path(file)
    out_path = dst_dir / file.relative_to(root_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Perform downscaling based on extension
    extension = inp_path.suffix.lower()
    if extension in [".heic"]:
        out_path = out_path.with_suffix(".jpg")
        result = downscale_image_heic(inp_path, out_path, max_image_size_bytes)
    elif extension in [".png", ".jpg"]:
        result = downscale_image(inp_path, out_path, max_image_size_bytes)
    elif extension in [".mp4", ".mov", ".mpg"]:
        result = downscale_video(inp_path, out_path, max_video_bitrate_bps)
    else:
        shutil.copyfile(inp_path, out_path)
        result = f"File copied {inp_path} (UNKNOWN FORMAT)"

    # Summarize
    print(result)


if __name__ == "__main__":
    # fmt: off
    arg_parser = argparse.ArgumentParser(description="Downscale images to match given disk size constraints.", allow_abbrev=False)
    arg_parser.add_argument("-d", "--directory", type=Path, required=True, help="Directory with photos")
    arg_parser.add_argument("-o", "--output", type=Path, required=True, help="Output directory")
    arg_parser.add_argument("-mi", "--max-image-size", type=int, default=1024, help="Max size of images in KiB")
    arg_parser.add_argument("-mv", "--max-video-bitrate", type=int, default=4096, help="Max bitrate of video in KBPS")
    arg_parser.add_argument("-p", "--processes", type=int, default=6, help="Number of processes to perform the operations in parallel")
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
    print(f"  max_image_size = {args.max_image_size}KiB")
    print(f"  max_video_bitrate = {args.max_video_bitrate}KBPS")
    print(f"  processes = {args.processes}")
    print()

    max_image_size_bytes = args.max_image_size * 1000
    max_video_bitrate_bps = args.max_video_bitrate * 1000

    if args.processes < 1:
        print("ERROR: processes must be a positive value")
        sys.exit(1)
    elif args.processes == 1:
        for file in files:
            downscale_file(args.directory, args.output, file, max_image_size_bytes, max_video_bitrate_bps)
    else:
        asyncs = []
        with multiprocessing.Pool(args.processes) as pool:
            for file in files:
                a = pool.apply_async(downscale_file, args=(args.directory, args.output, file, max_image_size_bytes, max_video_bitrate_bps))
                asyncs.append(a)
            for a in asyncs:
                a.wait()
