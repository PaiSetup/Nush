#!/bin/python

import argparse
import enum
import re
import shutil
from pathlib import Path

import music_tag


class MusicTaggerException(Exception):
    pass


class OperationMode(enum.Enum):
    Copy = "c"
    RenameInPlace = "r"


class EnumAction(argparse.Action):
    def __init__(self, **kwargs):
        # Pop off the type value
        enum_type = kwargs.pop("type", None)

        # Ensure an Enum subclass is provided
        if enum_type is None:
            raise ValueError("type must be assigned an Enum when using EnumAction")
        if not issubclass(enum_type, enum.Enum):
            raise TypeError("type must be an Enum when using EnumAction")

        # Generate choices from the Enum
        choices = [x.value for x in enum_type]
        kwargs.setdefault("choices", tuple(choices))

        # Append available options to help message
        if "help" not in kwargs:
            kwargs["help"] = ""
        kwargs["help"] += "Available options: "
        kwargs["help"] += ", ".join([f"'{x}'" for x in choices])
        kwargs["help"] += "."

        super(EnumAction, self).__init__(**kwargs)

        self._enum = enum_type

    def __call__(self, parser, namespace, values, option_string=None):
        # Convert value back into an Enum
        value = self._enum(values)
        setattr(namespace, self.dest, value)


class MusicFile:
    def __init__(self, src_path, author):
        self._src_path = src_path
        self._author = author
        self._title = self._extract_title_from_filename(author)
        self._dst_filename = f"{self._author} - {self._title}{self._src_path.suffix}"

    @staticmethod
    def gather(source_dir, author):
        allowed_extensions = [
            ".mp3",
            ".flac",
            ".mp4",
        ]

        music_files = []
        for file in source_dir.rglob("*"):
            if file.suffix not in allowed_extensions:
                continue
            if not file.is_file():
                continue
            print(f"\t{file}")
            music_files.append(MusicFile(file, author))

        # Ensure there are no duplicates. Shitty O(n^2) implementation, but it doesn't matter for ~30 files.
        for i, x in enumerate(music_files):
            for y in music_files[i + 1 :]:
                if x._title == y._title:
                    raise MusicTaggerException(f'Duplicate found in music files: "{x._title}"')

        # Get cover image
        allowed_cover_image_names = [
            "cover.jpg",
            "cover.png",
            "icon.jpg",
            "icon.png",
        ]
        cover_image_path = None
        for name in allowed_cover_image_names:
            file = source_dir / name
            if file.is_file():
                cover_image_path = file
                break

        return music_files, cover_image_path

    def _extract_title_from_filename(self, author):
        patterns = [
            "[0-9]+[. -]+(.*)",  # e.g. "01. Fear of the dark"
            f"{author} - (.*)",  # e.g. "Iron Maiden - Fear of the dark"
            "([A-Za-z '0-9]+)",  # e.g. "Fear of the dark"
        ]
        for pattern in patterns:
            result = re.match(pattern, self._src_path.stem)
            if result is not None:
                return result.groups()[0]
        raise MusicTaggerException(f"Could not extract title of {self._src_path}")

    def copy(self, dst_dir, dry_run):
        self._dst_path = dst_dir / self._dst_filename
        print(f"\tCopy {self._src_path} -> {self._dst_path}")
        if not dry_run:
            shutil.copy(self._src_path, self._dst_path)

    def rename(self, dry_run):
        dst_dir = self._src_path.parent
        self._dst_path = dst_dir / self._dst_filename
        print(f"\tRename {self._src_path} -> {self._dst_path}")
        if not dry_run:
            self._src_path.rename(self._dst_path)

    def tag(self, cover_image_path, dry_run):
        print(f"\t{self._dst_path.name:50}   author={self._author}   title={self._title}    cover={cover_image_path}")
        if dry_run:
            return

        tag_object = music_tag.load_file(self._dst_path)

        tags_to_delete = [
            "year",
            "albumartist",
            "album artist",
            "comment",
            "genre",
            "tracknumber",
            "totaldiscs",
            "totaltracks",
            "Total Discs",
            "Total Tracks",
        ]
        for tag in tags_to_delete:
            tag_object.remove_tag(tag)

        # Some tags cannot by remove nicely with libraries API, so we do this.
        # Got the idea from https://github.com/KristoforMaynard/music-tag/issues/28
        tags_to_delete_with_bruteforce = [
            "ALBUM ARTIST",
            "TOTALTRACKS",
            "TOTALDISCS",
        ]
        for tag in tags_to_delete_with_bruteforce:
            if tag in tag_object.mfile.tags:
                del tag_object.mfile.tags[tag]

        if cover_image_path is None:
            tag_object.remove_tag("artwork")
        else:
            with open(cover_image_path, "rb") as img_in:
                tag_object["artwork"] = img_in.read()
            tag_object["artwork"].first.thumbnail([64, 64])
            tag_object["artwork"].first.raw_thumbnail([64, 64])

        tag_object["title"] = self._title
        tag_object["artist"] = self._author
        tag_object["album"] = self._author
        tag_object["albumartist"] = self._author

        tag_object.save()


if __name__ == "__main__":
    # fmt: off
    arg_parser = argparse.ArgumentParser(description="Renames and sets metadata for music files in the way that I like.", allow_abbrev=False)
    arg_parser.add_argument("-d", "--directory", type=Path, required=True, help="Directory with music files")
    arg_parser.add_argument("-a", "--author", type=str, required=True, help="Name of the author")
    arg_parser.add_argument("-m", "--mode", type=OperationMode, action=EnumAction, required=True, help="Perform a copy operation to specified path")
    arg_parser.add_argument("-n", "--dry_run", action="store_true", help="do not perform any action.")
    args = arg_parser.parse_args()
    # fmt: on

    print("Gathering music files")
    files, cover_image_path = MusicFile.gather(args.directory, args.author)
    print()

    print("Adjusting filenames")
    if args.mode == OperationMode.Copy:
        # Prepare destination directory
        dst_dir = args.directory.parent / f"{args.directory.name}_tagged"
        if not args.dry_run:
            if dst_dir.is_dir():
                shutil.rmtree(dst_dir)
            dst_dir.mkdir()

        # Copy all files
        for file in files:
            file.copy(dst_dir, args.dry_run)

        # Copy cover
        if cover_image_path is not None:
            print(f"\tCopy {cover_image_path} -> {dst_dir / cover_image_path.name}")
            if not args.dry_run:
                shutil.copy(cover_image_path, dst_dir / cover_image_path.name)
    elif args.mode == OperationMode.RenameInPlace:
        # Rename all files
        for file in files:
            file.rename(args.dry_run)
    else:
        raise MusicTaggerException("Unknown operation mode")
    print()

    print("Setting metadata")
    for file in files:
        file.tag(cover_image_path, args.dry_run)
        file.tag(cover_image_path, args.dry_run)
    print()
