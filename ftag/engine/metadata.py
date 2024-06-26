import json
import re
import shutil

from engine.exception import TagEngineException
from engine.hash import get_file_hash

name_regex = "^[A-Za-z][A-Za-z_0-9]*$"


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
