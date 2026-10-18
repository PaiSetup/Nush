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
from enum import Enum, auto
from pathlib import Path


class FileType(Enum):
    ImageHeic = auto()
    Image = auto()
    Video = auto()
    Unknown = auto()


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


def get_file_type(path):
    extension = path.suffix.lower()
    if extension == ".heic":
        return FileType.ImageHeic
    if extension in (".png", ".jpg"):
        return FileType.Image
    if extension in (".mp4", ".mov", ".mpg"):
        return FileType.Video
    return FileType.Unknown


def get_files(directory):
    result = {file_type: [] for file_type in FileType}
    for folder, _, files in os.walk(directory):
        for f in files:
            path = Path(os.path.join(folder, f))
            result[get_file_type(path)].append(path)
    return result


def generate_str_percentage(value, max_value):
    if value <= max_value:
        return ""
    else:
        percentage = ((value - max_value) / max_value) * 100
        return f"({percentage:.1f}% TOO BIG)"


def downscale_video(inp_path, out_path, max_video_bitrate_bps, min_bpp=0.06):
    """
    Limits video bitrate, keeping seeking fast and the result widely playable.

    - If the bitrate cap gives fewer than min_bpp bits per pixel at the source
      resolution, the video is also downscaled to the largest size that does
      (the source size itself is tried first, then a standard ladder).
    - Output is always 8-bit H.264 Main, no B-frames, ~1 s GOP, so it seeks
      fast and hardware-decodes everywhere. 10-bit sources are converted and
      HDR (HLG/PQ) sources are tone-mapped to SDR BT.709.
    - Rotation tags (phone videos) are handled: ffmpeg rotates before filters.
    """
    import json
    import shlex

    def parse_fps(value):
        try:
            num, den = map(int, str(value).split("/"))
            return num / den if den else 0.0
        except (ValueError, TypeError):
            return 0.0

    def probe(path):
        cmd = (
            "ffprobe -v quiet -select_streams v:0 "
            "-show_entries stream=width,height,avg_frame_rate,r_frame_rate,bit_rate,color_transfer"
            ":format=bit_rate,duration,size "
            f"-of json {shlex.quote(str(path))}"
        )
        out = run_command(cmd)
        if isinstance(out, bytes):
            out = out.decode()
        data = json.loads(out)
        s = data["streams"][0]
        fmt = data.get("format", {})

        fps = parse_fps(s.get("avg_frame_rate")) or parse_fps(s.get("r_frame_rate")) or 30.0

        # Some containers (e.g. mkv) don't store a per-stream bitrate
        bitrate = s.get("bit_rate") or fmt.get("bit_rate")
        if not bitrate and fmt.get("duration") and fmt.get("size"):
            bitrate = float(fmt["size"]) * 8 / float(fmt["duration"])
        if not bitrate:
            raise RuntimeError(f"Cannot determine bitrate of {path}")

        return int(s["width"]), int(s["height"]), fps, int(float(bitrate)), s.get("color_transfer", "") or ""

    def get_bitrate(path):
        return probe(path)[3]

    def pick_short_side(width, height, fps):
        """Largest short-side size that reaches min_bpp at the bitrate cap."""
        short = min(width, height)
        long = max(width, height)
        ladder = [2160, 1440, 1080, 720, 480]
        candidates = [short] + [s for s in ladder if s < short]
        for s in candidates:
            pixels = s * (long * s / short)
            if max_video_bitrate_bps / (pixels * fps) >= min_bpp:
                return s
        # Nothing reaches min_bpp: use the smallest step (never upscale)
        return min(short, ladder[-1])

    # Try to early return
    original_size = inp_path.stat().st_size
    width, height, fps, original_bitrate, color_transfer = probe(inp_path)
    if original_bitrate <= max_video_bitrate_bps:
        shutil.copyfile(inp_path, out_path)
        return f"DONE {inp_path.name}: copy (video bitrate already ok)"

    # Build the filter chain
    short_side = pick_short_side(width, height, fps)
    downscaled = short_side < min(width, height)
    filters = []
    if downscaled:
        # iw/ih are the post-rotation frame size, so this works for any orientation
        filters.append(f"scale=w='if(gt(iw,ih),-2,{short_side})':h='if(gt(iw,ih),{short_side},-2)'")
    color_opts = ""
    if color_transfer in ("arib-std-b67", "smpte2084"):
        # HDR (HLG / PQ) -> SDR BT.709
        filters.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709," "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv")
        color_opts = "-colorspace bt709 -color_primaries bt709 -color_trc bt709 "
    filters.append("format=yuv420p")  # 8-bit, required for H.264 Main
    vf = shlex.quote(",".join(filters))

    gop = max(1, round(fps))  # keyframe about every second

    def build_command(audio_opts):
        return (
            f"ffmpeg -nostdin -hide_banner -i {shlex.quote(str(inp_path))} "
            f"-map 0:v:0 -map 0:a? -dn -sn "
            f"-vf {vf} {color_opts}"
            f"-c:v libx264 -profile:v main -bf 0 -g {gop} "
            f"-b:v {max_video_bitrate_bps} -maxrate {max_video_bitrate_bps} "
            f"-bufsize {2 * max_video_bitrate_bps} "
            f"{audio_opts} -movflags +faststart "
            f"{shlex.quote(str(out_path))} -y"
        )

    # Perform downscaling / re-encoding (fall back to AAC if audio can't be copied)
    try:
        try:
            run_command(build_command("-c:a copy"))
        except CommandError:
            run_command(build_command("-c:a aac -b:a 160k"))
    except Exception:
        out_path.unlink(missing_ok=True)  # don't leave a broken partial file
        raise

    new_size = out_path.stat().st_size
    new_bitrate = get_bitrate(out_path)

    # Prepare result string
    str_size = f"{original_size//1024}KiB->{new_size//1024}KiB"
    str_bitrate = f"{original_bitrate//1024}KBPS->{new_bitrate//1024}KBPS"
    str_bitrate_result = generate_str_percentage(new_bitrate, max_video_bitrate_bps)
    return f"DONE {inp_path.name}: video downscaled {str_size}, {str_bitrate} {str_size_result}"


def downscale_image(inp_path, out_path, max_image_size_bytes):
    # Try to early return
    original_size = inp_path.stat().st_size
    if original_size < max_image_size_bytes:
        shutil.copyfile(inp_path, out_path)
        return f"DONE {inp_path.name}: copy (image size already ok)"

    # Perform downscaling
    factor = max_image_size_bytes / original_size
    factor = factor ** (1 / 2)
    factor = int(factor * 100) + 1
    factor = max(factor, 50)
    command = f'convert -resize {factor}% -quality 80% "{inp_path}" "{out_path}"'
    run_command(command)
    new_size = out_path.stat().st_size

    # Prepare result string
    str_size = f"{original_size//1024}KiB->{new_size//1024}KiB"
    str_size_result = generate_str_percentage(new_size, max_image_size_bytes)
    return f"DONE {inp_path.name}: image downscaled {str_size} {str_size_result}"


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


def downscale_file(root_dir, dst_dir, file, file_type, max_image_size_bytes, max_video_bitrate_bps):
    # Prepare output paths
    inp_path = Path(file)
    out_path = dst_dir / file.relative_to(root_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Perform downscaling based on file type
    if file_type == FileType.ImageHeic:
        out_path = out_path.with_suffix(".jpg")
        result = downscale_image_heic(inp_path, out_path, max_image_size_bytes)
    elif file_type == FileType.Image:
        result = downscale_image(inp_path, out_path, max_image_size_bytes)
    elif file_type == FileType.Video:
        result = downscale_video(inp_path, out_path, max_video_bitrate_bps)
    else:
        shutil.copyfile(inp_path, out_path)
        result = f"DONE {inp_path.name}: copy (unknown format)"

    # Summarize
    print(result)


if __name__ == "__main__":
    # fmt: off
    arg_parser = argparse.ArgumentParser(description="Downscale images to match given disk size constraints.", allow_abbrev=False)
    arg_parser.add_argument("-d", "--directory", type=Path, required=True, help="Directory with photos")
    arg_parser.add_argument("-o", "--output", type=Path, required=True, help="Output directory")
    arg_parser.add_argument("-mi", "--max-image-size", type=int, default=1024, help="Max size of images in KiB")
    arg_parser.add_argument("-mv", "--max-video-bitrate", type=int, default=2048, help="Max bitrate of video in KBPS")
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

    # Traverse the files and group them by type
    files = get_files(args.directory)

    max_image_size_bytes = args.max_image_size * 1000
    max_video_bitrate_bps = args.max_video_bitrate * 1000

    print("Performing a downscale operation")
    print(f"  src_dir = {args.directory}")
    print(f"  dst_dir = {args.output}")
    print(f"  max_image_size = {args.max_image_size}KiB")
    print(f"  max_video_bitrate = {args.max_video_bitrate}KBPS")
    print()

    # Pool sizes
    video_processes = 1
    image_processes = max((os.cpu_count() or 1) - 2, 1)

    with multiprocessing.Pool(image_processes) as image_pool, multiprocessing.Pool(video_processes) as video_pool:
        asyncs = []

        for file_type in (FileType.Image, FileType.ImageHeic, FileType.Unknown):
            for file in files[file_type]:
                task_args = (args.directory, args.output, file, file_type, max_image_size_bytes, max_video_bitrate_bps)
                asyncs.append(image_pool.apply_async(downscale_file, args=task_args))

        for file in files[FileType.Video]:
            task_args = (args.directory, args.output, file, FileType.Video, max_image_size_bytes, max_video_bitrate_bps)
            asyncs.append(video_pool.apply_async(downscale_file, args=task_args))

        # Wait for everything before the pools are torn down
        for a in asyncs:
            a.wait()
