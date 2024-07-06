import enum
import os
import random
import re
from pathlib import Path

from engine.exception import TagEngineException
from engine.metadata import TagEngineMetadata
from engine.misc import get_file_hash, get_file_mime_type
from engine.symlinker import Symlinker

metadata_directory_name = ".ftag"
tagged_directory_name = "ftags"
metadata_file_name = "db.json"
metadata_file_name_tmp = "db_tmp.json"


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
        self._symlinker = Symlinker(self._root_dir / tagged_directory_name)

    def initialize(self):
        self._root_dir = Path(os.path.abspath(os.curdir))
        self._metadata = TagEngineMetadata(None)
        self._symlinker = Symlinker(self._root_dir / tagged_directory_name)
        self._state = TagEngineState.Loaded

    @staticmethod
    def _find_root_dir():
        previous_path = None
        current_path = Path(os.path.abspath(os.curdir))
        while current_path != previous_path:
            ftags_path = current_path / metadata_directory_name / metadata_file_name
            if ftags_path.is_file():
                return current_path

            previous_path = current_path
            current_path = current_path.parent
        return None

    def _get_root_dir_path(self):
        return self._root_dir

    def get_state(self):
        return self._state

    def _get_metadata_dir_path(self):
        return self._root_dir / metadata_directory_name

    def get_metadata_file(self):
        return self._root_dir / metadata_directory_name / metadata_file_name

    def _get_metadata_tmp_file(self):
        return self._root_dir / metadata_directory_name / metadata_file_name_tmp

    def get_categories(self):
        return self._metadata.get_categories()

    def get_tags_for_category(self, category):
        return self._metadata.get_tags_for_category(category)

    def save(self):
        real_file = self.get_metadata_file()
        tmp_file = self._get_metadata_tmp_file()
        self._metadata.save(real_file, tmp_file)

    def _get_taggable_files(self):
        for root, dirs, files in os.walk(self._get_root_dir_path()):
            for file_name in files:
                if Path(root) == self._get_metadata_dir_path():
                    continue

                file_path = Path(os.path.abspath(os.path.join(root, file_name)))
                if file_path.is_relative_to(self._symlinker.get_root()):
                    continue

                if not self._matches_path_filters(file_path):
                    continue

                if not self._matches_mime_filters(file_path):
                    continue

                yield file_path

    def _matches_mime_filters(self, file_path):
        mime_filters = self._metadata.get_mime_filters()
        if len(mime_filters) == 0:
            return True

        mime_type = get_file_mime_type(file_path)
        if mime_type is None:
            return False

        for mime_filter in mime_filters:
            if re.match(mime_filter, mime_type):
                return True
        return False

    def _matches_path_filters(self, file_path):
        path_filters = self._metadata.get_path_filters()
        if len(path_filters) == 0:
            return True

        file_path = str(file_path.absolute().relative_to(self._get_root_dir_path()))
        for path_filter in path_filters:
            if re.search(path_filter, str(file_path)):
                return True
        return False

    def _setup_symlinks_for_file(self, file_path, create):
        try:
            file_tags = self._metadata.get_tags_for_file(file_path, None)
        except TagEngineException as e:
            file_tags = None
            print(e.message)
        if file_tags is None:
            return

        queries = (query for query in self._metadata.get_query_names() if self._metadata.matches_query(query, file_path))
        self._symlinker.setup_symlinks_for_file(file_path, file_tags, queries, create)

    def get_untagged_files_statistics(self):
        categories = self._metadata.get_categories()
        taggable_files = list(self._get_taggable_files())
        untagged_files = [f for f in taggable_files if self._metadata.is_untagged(f, categories)]
        return {
            "num_taggable_files": len(taggable_files),
            "num_untagged_files": len(untagged_files),
        }

    def get_untagged_files(self, randomize=True):
        categories = self._metadata.get_categories()
        files = self._get_taggable_files()

        if randomize:
            files = list(files)
            random.shuffle(files)

        files = (f for f in files if self._metadata.is_untagged(f, categories))
        return files

    def add_category(self, category):
        self._metadata.add_category(category)

    def add_mime_filter(self, new_filter):
        self._metadata.add_mime_filter(new_filter)

    def add_path_filter(self, new_filter):
        self._metadata.add_path_filter(new_filter)

    def add_query(self, query_name, rules):
        self._metadata.add_query(query_name, rules)

        matching_files = (file for file in self._get_taggable_files() if self._metadata.matches_query(query_name, file))
        self._symlinker.setup_symlinks_for_query(query_name, matching_files, True)

    def add_tag(self, category, new_tag):
        self._metadata.add_tag(category, new_tag)

    def get_tags_for_file(self, file_path, category):
        if category is None:
            raise TagEngineException("Category must be specified")
        return self._metadata.get_tags_for_file(file_path, category)

    def set_tags(self, file_path, tags):
        self._setup_symlinks_for_file(file_path, False)
        self._metadata.set_tags(file_path, tags, self._get_root_dir_path())
        self._setup_symlinks_for_file(file_path, True)

    def generate_all_symlinks(self):
        self._symlinker.cleanup()

        for file_path in self._get_taggable_files():
            self._setup_symlinks_for_file(file_path, True)
