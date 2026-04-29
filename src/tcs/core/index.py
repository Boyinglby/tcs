import os
from typing import Dict

from .utils import calculate_hash, read_file, write_file


class IndexOperations:
    """
    Index and staging commands.
    """

    def _load_staged_files(self) -> Dict[str, str]:
        """
        Load staged files from the index.
        """
        return self._load_index()

    def _get_staged_files(self) -> Dict[str, str]:
        """
        Return the current staged file snapshot.
        """
        return self._load_index()

    def _save_staged_files(self, staged_files: Dict[str, str]) -> None:
        """
        Save the staged file snapshot to the index.
        """
        self._save_index(staged_files)

    def _update_index(self, file_path: str, hash_value: str) -> None:
        """
        Record a repository-relative file path and object hash in the index.
        """
        rel_path = os.path.relpath(os.path.abspath(file_path), self.root_dir)
        index = self._load_index()
        index[rel_path] = hash_value
        self._save_index(index)

    def add(self, file_path: str) -> str:
        """
        Stage a file by storing its content object and updating the index.
        """
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        content = read_file(abs_path)
        hash_value = calculate_hash(content)

        object_path = self._object_path(hash_value)
        if not os.path.exists(object_path):
            write_file(object_path, content)

        self._update_index(abs_path, hash_value)
        return hash_value
