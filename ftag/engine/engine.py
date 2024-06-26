import enum
import os
import random
import shutil
from pathlib import Path

from engine.exception import TagEngineException
from engine.hash import get_file_hash
from engine.metadata import TagEngineMetadata

tagged_directory_name = "ftags"
metadata_file_name = "ftags.json"
metadata_file_name_tmp = "ftags_tmp.json"


class TagEngineState(enum.Enum):
    NotLoaded = enum.auto()
    InvalidData = enum.auto()
    Loaded = enum.auto()


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

    def get_categories(self):
        return self._metadata.get_categories()

    def get_tags_for_category(self, category):
        return self._metadata.get_tags_for_category(category)

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
        categories = self._metadata.get_categories()
        files = self._get_taggable_files()
        if randomize:
            files = list(files)
            random.shuffle(files)
        return (f for f in files if self._metadata.is_untagged(f, categories))

    def generate_all_symlinks(self, cleanup):
        if cleanup:
            symlink_root = self._get_symlink_root()
            if symlink_root.exists():
                shutil.rmtree(symlink_root)

        for file_path in self._get_taggable_files():
            self.generate_symlink(file_path)

    def generate_symlink(self, file_path):
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
        file_hash = get_file_hash(file_path)
        if file_hash is None:
            print(f"File {file_path} does not exist")
            return

        # Get tags of the file as a dictionary - key is category name, value is list of tags
        try:
            file_tags = self._metadata.get_tags_for_file(file_path, None)
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
        if category is None:
            raise TagEngineException("Category must be specified")
        return self._metadata.get_tags_for_file(file_path, category)

    def set_tags(self, file_path, tags):
        self._metadata.set_tags(file_path, tags)
