import os
from typing import Any, Dict, List, Tuple

from .utils import calculate_hash, list_files, read_file


class StatusOperations:
    """
    Working tree inspection and status reporting.
    """

    def _get_working_tree_changes(self, staged_files: Dict[str, str]) -> Tuple[List[str], List[str], List[str]]:
        modified: List[str] = []
        untracked: List[str] = []
        deleted: List[str] = []

        tracked_paths = set(staged_files.keys())

        for file_path in list_files(self.root_dir):
            rel_path = os.path.relpath(file_path, self.root_dir)

            if rel_path.startswith(self.REPO_DIR_NAME):
                continue

            if rel_path not in tracked_paths:
                untracked.append(rel_path)
            else:
                current_hash = calculate_hash(read_file(file_path))
                if current_hash != staged_files[rel_path]:
                    modified.append(rel_path)

        for rel_path in tracked_paths:
            abs_path = os.path.join(self.root_dir, rel_path)
            if not os.path.exists(abs_path):
                deleted.append(rel_path)

        return modified, untracked, deleted

    def status(self) -> Dict[str, Any]:
        staged = self._get_staged_files()
        modified, untracked, deleted = self._get_working_tree_changes(staged)

        return {
            "staged": staged,
            "modified": modified,
            "untracked": untracked,
            "deleted": deleted,
        }
