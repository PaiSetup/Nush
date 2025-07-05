import os
import shutil

from engine.exception import TagEngineException
from engine.misc import get_file_hash


class Symlinker:
    def __init__(self, symlink_root):
        self._symlink_root = symlink_root

    def get_root(self):
        return self._symlink_root

    def _get_symlink_path(self, category, value, file_path):
        file_hash = get_file_hash(file_path)[:6]
        symlink_dir = self._symlink_root / category / value
        symlink_name = f"{file_path.stem}_{file_hash}{file_path.suffix}"
        return symlink_dir / symlink_name

    def _get_query_symlink_path(self, query_name, file_path):
        file_hash = get_file_hash(file_path)
        symlink_dir = self._symlink_root / "queries" / query_name
        symlink_name = f"{file_hash}{file_path.suffix}"
        return symlink_dir / symlink_name

    def _create_symlink(self, real_file_path, symlink_path):
        # TODO should we really do this?
        if not real_file_path.is_absolute():
            raise TagEngineException(f"Path {real_file_path} is not absolute")

        symlink_path.parent.mkdir(parents=True, exist_ok=True)
        symlink_path.unlink(missing_ok=True)
        os.symlink(real_file_path, symlink_path)

    def _setup_symlink(self, real_file_path, symlink_path, create):
        if create:
            self._create_symlink(real_file_path, symlink_path)
        else:
            symlink_path.unlink(missing_ok=True)

    def cleanup(self):
        if not self._symlink_root.exists():
            return

        for file_path in self._symlink_root.rglob("*"):
            if file_path.is_file() or file_path.is_symlink():
                file_path.unlink()

    def setup_symlinks_for_query(self, query_name, matching_files, create):
        for file_path in matching_files:
            file_path_absolute = file_path.absolute()
            symlink_path = self._get_query_symlink_path(query_name, file_path)
            self._setup_symlink(file_path_absolute, symlink_path, create)

    def setup_symlinks_for_file(self, file_path, matching_tags, matching_queries, create):
        file_path_absolute = file_path.absolute()

        # Iterate over all tags assigned to this file and remove its symlinks
        for category, values in matching_tags.items():
            for value in values:
                symlink_path = self._get_symlink_path(category, value, file_path)
                self._setup_symlink(file_path_absolute, symlink_path, create)

        # Iterate over all queries and remove symlinks for matching ones.
        for query_name in matching_queries:
            symlink_path = self._get_query_symlink_path(query_name, file_path)
            self._setup_symlink(file_path_absolute, symlink_path, create)
