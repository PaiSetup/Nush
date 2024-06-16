import hashlib
import json
import os
import shutil
import enum
from pathlib import Path

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
            self._metadata = TagEngine._read_metadata(self.get_metadata_file())

            if self._metadata is None:
                self._state = TagEngineState.InvalidData
            else:
                self._state = TagEngineState.Loaded
        else:
            self._state = TagEngineState.NotLoaded

    def initialize(self):
        self._root_dir = Path(os.path.abspath(os.curdir))
        self._metadata = {
            "files": {},
            "tags": {},
        }
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

    @staticmethod
    def _read_metadata(file_path):
        with open(file_path, "r") as file:
            metadata = json.load(file)

        # Simple basic validation
        if "files" not in metadata:
            return False
        if "tags" not in metadata:
            return False

        return metadata

    def _get_root_dir_path(self):
        return self._root_dir

    def _get_symlink_root(self):
        return self._root_dir / tagged_directory_name

    def get_state(self):
        return self._state

    def get_metadata_file(self):
        return self._root_dir / metadata_file_name

    def save(self):
        real_file = self.get_metadata_file()
        tmp_file = self._get_root_dir_path() / metadata_file_name_tmp

        with open(tmp_file, "w") as file:
            self._root_dir / metadata_file_name
            content = json.dump(self._metadata, file, indent=4)
        shutil.move(tmp_file, real_file)

    def _get_taggable_files(self):
        for root, dirs, files in os.walk(self._get_root_dir_path()):
            for file_name in files:
                file_path = Path(os.path.abspath(os.path.join(root, file_name)))
                if file_path.is_relative_to(self._get_symlink_root()):
                    continue
                if file_name == metadata_file_name:
                    continue
                yield file_path

    def generate(self):
        def symlink(real_file_path, symlink_dir):
            real_file_path = Path(real_file_path).absolute()
            symlink_dir = Path(symlink_dir).absolute()

            symlink_dir.mkdir(parents=True, exist_ok=True)
            symlink_path = symlink_dir / real_file_path.name
            if symlink_path.exists():
                symlink_path.unlink()
            os.symlink(real_file_path, symlink_path)

        a = list(self._get_taggable_files())

        for file_path in self._get_taggable_files():
            file_hash = TagEngine._get_file_hash(file_path)
            if file_hash is None:
                print(f"File {file_path} does not exist")
                continue
            if file_hash not in self._metadata["files"]:
                # print(f"No tags for {file_path}")
                continue

            file_tags = self._metadata["files"][file_hash]["tags"]
            # print(f"Symlinking {file_path} {file_hash}")
            for category, values in file_tags.items():
                for value in values:
                    symlink_dir = f"{self._get_symlink_root()}/{category}/{value}"
                    symlink(file_path, symlink_dir)

    def dump_raw_metadata_to_console(self):
        print(json.dumps(self._metadata, indent=4))

    def get_tag_categories(self):
        return list(self._metadata["tags"].keys())

    def get_tag_values(self, category):
        return list(self._metadata["tags"][category])

    def add_tag(self, category, value):
        if category not in self._metadata["tags"]:
            raise Exception("Invalid category")  # TODO
        if value in self._metadata["tags"][category]:
            return False
        self._metadata["tags"][category].append(value)
        return True

    def get_tags_for_file(self, file, category):
        file_hash = TagEngine._get_file_hash(file)
        if file_hash is None:
            return None
        if file_hash not in self._metadata["files"]:
            return None
        categories = self._metadata["files"][file_hash]["tags"]
        if category not in categories:
            return None
        return categories[category]

    def set_tags(self, file, tags):
        file_hash = TagEngine._get_file_hash(file)
        if file_hash is None:
            raise Exception("Wrong file in set_tags")  # TODO

        # Create new entry, if file is not in the database. Only tags can be changed. Rest is of metadata
        # is constant. Hash is unique identifier. Path is only for sanity checks, but it's not used.
        if file_hash not in self._metadata["files"]:
            self._metadata["files"][file_hash] = {
                "path": str(file),
                "tags": {},
            }

        # Entry must be created by now. Set the tags
        self._metadata["files"][file_hash]["tags"] = dict(tags)

    @staticmethod
    def _get_file_hash(file_path):
        try:
            file_size = os.path.getsize(file_path)
        except FileNotFoundError:
            return None
        bytes_left = min(128 * 1024, file_size)
        chunk_size = 8096

        hash_function = hashlib.new("blake2b")
        with open(file_path, "rb") as file:
            while bytes_left != 0:
                current_chunk_size = min(chunk_size, bytes_left)
                chunk = file.read(current_chunk_size)
                hash_function.update(chunk)
                bytes_left -= current_chunk_size
        return hash_function.hexdigest()[0:48]
