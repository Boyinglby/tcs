import json
import os
from datetime import datetime
from typing import Any, Dict, Iterator, Optional, Tuple

from .utils import calculate_hash, read_file, write_file


class CommitOperations:
    """
    Commit object storage and history traversal.
    """

    def _create_commit_object(
        self,
        message: str,
        parent_hash: Optional[str],
        merge_parent_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build the serializable commit object for the current index snapshot.
        """
        config = self._load_config()
        commit_obj = {
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "author_name": config.get("user.name", ""),
            "author_email": config.get("user.email", ""),
            "files": self._get_staged_files(),
            "parent": parent_hash,
        }
        if merge_parent_hash is not None:
            commit_obj["merge_parent"] = merge_parent_hash
        return commit_obj

    def _write_commit_object(self, commit_obj: Dict[str, Any]) -> str:
        """
        Store a commit object and return its content hash.
        """
        commit_content = json.dumps(commit_obj, sort_keys=True).encode()
        commit_hash = calculate_hash(commit_content)
        commit_path = self._object_path(commit_hash)

        if not os.path.exists(commit_path):
            write_file(commit_path, commit_content)

        return commit_hash

    def _read_commit_object(self, commit_hash: str) -> Dict[str, Any]:
        """
        Load and decode a commit object by hash.
        """
        commit_path = self._object_path(commit_hash)
        if not os.path.exists(commit_path):
            raise ValueError(f"Invalid commit hash: {commit_hash}")

        commit_content = read_file(commit_path)
        return json.loads(commit_content.decode())

    def commit(self, message: str) -> str:
        """
        Create a commit from the current staged file snapshot.
        """
        if not message or not message.strip():
            raise ValueError("Commit message cannot be empty.")

        staged_files = self._get_staged_files()
        if not staged_files:
            raise ValueError("No staged changes to commit.")

        parent_hash = self._get_head_commit()
        commit_obj = self._create_commit_object(message.strip(), parent_hash)
        commit_hash = self._write_commit_object(commit_obj)
        self._update_head(commit_hash)
        return commit_hash

    def log(self) -> Iterator[Tuple[str, Dict[str, Any]]]:
        """
        Yield commits from HEAD backward through first-parent history.
        """
        commit_hash = self._get_head_commit()
        while commit_hash:
            commit_obj = self._read_commit_object(commit_hash)
            yield commit_hash, commit_obj
            commit_hash = commit_obj.get("parent")
