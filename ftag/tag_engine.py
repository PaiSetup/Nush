import enum
import json
import os
import random
import re
import shutil
from pathlib import Path

from utils import get_file_hash

tagged_directory_name = "ftags"
metadata_file_name = "ftags.json"
metadata_file_name_tmp = "ftags_tmp.json"
name_regex = "^[A-Za-z][A-Za-z_0-9]*$"


class TagEngineState(enum.Enum):
    NotLoaded = enum.auto()
    InvalidData = enum.auto()
    Loaded = enum.auto()


class TagEngineException(Exception):
    def __init__(self, message, developer_error=False):
        self.message = message
        if developer_error and message is not None:
            self.message += " This is a developer error. It should never happen and it's likely a bug in ftag."


class TagEngineMetadata:
    def __init__(self, metadata_file_path):
        if metadata_file_path is not None:
            self.load(metadata_file_path)
        else:
            self.load_empty()

    def load_empty(self):
        self._metadata = {
            "files": {},
            "tags": {},
        }

    def load(self, metadata_file_path):
        with open(metadata_file_path, "r") as file:
            self._metadata = json.load(file)

        # Simple basic validation
        if "files" not in self._metadata:
            return False
        if "tags" not in self._metadata:
            return False

    def save(self, metadata_file_path, tmp_file):
        with open(tmp_file, "w") as file:
            content = json.dump(self._metadata, file, indent=4)
        shutil.move(tmp_file, metadata_file_path)

    def is_untagged(self, file_path, categories):
        file_hash = get_file_hash(file_path)
        if file_hash not in self._metadata["files"]:
            return True

        file_tags = list(self._metadata["files"][file_hash]["tags"].keys())
        return any((c not in file_tags for c in categories))

    def get_tag_categories(self):
        return list(self._metadata["tags"].keys())

    def get_tag_values(self, category):
        return list(self._metadata["tags"][category])

    def get_file_tags(self, file_path):
        file_hash = get_file_hash(file_path)
        if file_hash is None:
            raise TagEngineException(f"File {file_path} does not exist")

        if file_hash not in self._metadata["files"]:
            raise TagEngineException(f"File {file_path} is not tagged")

        return self._metadata["files"][file_hash]["tags"]

    def get_tags_for_file(self, file_path, category):
        tags = self.get_file_tags(file_path)
        if category not in tags:
            raise TagEngineException(f"File {file_path} is not tagged for category {category}")
        return tags[category]

    def add_category(self, category_name):
        if not re.match(name_regex, category_name):
            raise TagEngineException(f'Category name "{category_name}" is not allowed.')
        if category_name in self._metadata["tags"]:
            raise TagEngineException(f'Category name "{category_name}" already exists.')
        self._metadata["tags"][category_name] = []

    def add_tag(self, category, new_tag):
        if not re.match(name_regex, new_tag):
            raise TagEngineException(f'Tag name "{new_tag}" is not allowed.')
        if category not in self._metadata["tags"]:
            raise TagEngineException(f'Unknown category "{category}"', developer_error=True)
        if new_tag in self._metadata["tags"][category]:
            raise TagEngineException(f'Tag "{new_tag}" already exists')
        self._metadata["tags"][category].append(new_tag)

    def set_tags(self, file_path, tags):
        file_hash = get_file_hash(file_path)
        if file_hash is None:
            raise TagEngineException(f"File {file_path} does not exist")

        # Create new entry, if file is not in the database. Only tags can be changed. Rest of the metadata
        # is constant. Hash is unique identifier. Path is only for sanity checks, but it's not used.
        if file_hash not in self._metadata["files"]:
            self._metadata["files"][file_hash] = {
                "path": str(file.absolute().relative_to(self._get_root_dir_path())),
                "tags": {},
            }

        # Entry must be created by now. Set the tags
        self._metadata["files"][file_hash]["tags"] = dict(tags)


class TagEngine:
    def __init__(self):
        self._root_dir = None
        self._metadata = None

        self._root_dir = TagEngine._find_root_dir()
        if self._root_dir is not None:
            self._metadata = TagEngineMetadata(self.get_metadata_file())

            if self._metadata is None:
                self._state = TagEngineState.InvalidData
            else:
                self._state = TagEngineState.Loaded
        else:
            self._state = TagEngineState.NotLoaded

    def initialize(self):
        self._root_dir = Path(os.path.abspath(os.curdir))
        self._metadata = TagEngineMetadata(None)
        self.save()
        self._state = TagEngineState.Loaded

    @staticmethod
    def _find_root_dir():
        previous_path = None
        current_path = Path(os.path.abspath(os.curdir))
        while current_path != previous_path:
            ftags_path = current_path / metadata_file_name
            if ftags_path.is_file():
                return current_path

            previous_path = current_path
            current_path = current_path.parent
        return None

    def _get_root_dir_path(self):
        return self._root_dir

    def _get_symlink_root(self):
        return self._root_dir / tagged_directory_name

    def get_state(self):
        return self._state

    def get_metadata_file(self):
        return self._root_dir / metadata_file_name

    def get_tag_categories(self):
        return self._metadata.get_tag_categories()

    def get_tag_values(self, category):
        return self._metadata.get_tag_values(category)

    def save(self):
        real_file = self.get_metadata_file()
        tmp_file = self._get_root_dir_path() / metadata_file_name_tmp
        self._metadata.save(real_file, tmp_file)

    def _get_taggable_files(self):
        for root, dirs, files in os.walk(self._get_root_dir_path()):
            for file_name in files:
                file_path = Path(os.path.abspath(os.path.join(root, file_name)))
                if file_path.is_relative_to(self._get_symlink_root()):
                    continue
                if file_name == metadata_file_name:
                    continue
                yield file_path

    def get_untagged_files(self, randomize=True):
        categories = self._metadata.get_tag_categories()
        files = self._get_taggable_files()
        if randomize:
            files = list(files)
            random.shuffle(files)
        return (f for f in files if self._metadata.is_untagged(f, categories))

    def generate_all_files(self, cleanup):
        if cleanup:
            symlink_root = self._get_symlink_root()
            if symlink_root.exists():
                shutil.rmtree(symlink_root)

        for file_path in self._get_taggable_files():
            self.generate_file(file_path)

    def generate_file(self, file_path):
        # Define a helper function for generating a symlink.
        def symlink(real_file_path, symlink_dir, file_hash):
            real_file_path = Path(real_file_path).absolute()
            symlink_dir = Path(symlink_dir).absolute()

            symlink_dir.mkdir(parents=True, exist_ok=True)
            symlink_name = f"{file_hash}{real_file_path.suffix}"
            symlink_path = symlink_dir / symlink_name
            if symlink_path.exists():
                symlink_path.unlink()
            os.symlink(real_file_path, symlink_path)

        # Calculate hash of the file.
        file_hash = TagEngine._get_file_hash(file_path)
        if file_hash is None:
            print(f"File {file_path} does not exist")
            return

        # Get tags of the file as a dictionary - key is category name, value is list of tags
        try:
            file_tags = self._metadata.get_file_tags(file_path)
        except TagEngineException as e:
            print(e.message)
            return

        # Iterate over all tags assigned to this file and generate symlinks for each one.
        for category, values in file_tags.items():
            for value in values:
                symlink_dir = f"{self._get_symlink_root()}/{category}/{value}"
                symlink(file_path, symlink_dir, file_hash)

    def add_category(self, category_name):
        self._metadata.add_category(category_name)

    def add_tag(self, category, new_tag):
        self._metadata.add_tag(category_name)

    def get_tags_for_file(self, file_path, category):
        return self._metadata.get_tags_for_file(file_path, category)

    def set_tags(self, file_path, tags):
        self._metadata.set_tags(file_path, tags)
