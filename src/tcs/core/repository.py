import json
import os
from typing import Dict, Optional, Tuple

from .utils import read_file, write_file


class RepositoryOperations:
    """
    Repository paths, initialization, and shared repository state helpers.
    """

    @classmethod
    def init(cls, root_dir: str, directory_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Initialize a new repository on disk.
        """
        root_dir = cls._create_repo_directory(root_dir, directory_name)
        root_dir = os.path.abspath(root_dir)
        tcs_dir = os.path.join(root_dir, cls.REPO_DIR_NAME)
        objects_dir = os.path.join(tcs_dir, cls.OBJECTS_DIR_NAME)
        refs_dir = os.path.join(tcs_dir, cls.REFS_DIR_NAME)
        config_path = os.path.join(tcs_dir, cls.CONFIG_FILE_NAME)

        if os.path.exists(tcs_dir):
            return False, "TCS directory already initialized."

        cls._create_tcs_structure(tcs_dir, objects_dir, refs_dir, config_path)
        return True, f"Initialized empty TCS repository in {tcs_dir}"

    @staticmethod
    def _create_repo_directory(root_dir: str, directory_name: Optional[str]) -> str:
        """
        Return the repository root, creating a named child directory when requested.
        """
        if directory_name:
            new_dir = os.path.join(root_dir, directory_name)
            os.makedirs(new_dir, exist_ok=True)
            return new_dir
        return root_dir

    @classmethod
    def _create_tcs_structure(
        cls,
        tcs_dir: str,
        objects_dir: str,
        refs_dir: str,
        config_path: str,
    ) -> None:
        """
        Create the initial .tcs directory tree and repository metadata files.
        """
        os.makedirs(tcs_dir, exist_ok=True)
        os.makedirs(objects_dir, exist_ok=True)
        os.makedirs(refs_dir, exist_ok=True)
        os.makedirs(os.path.join(refs_dir, cls.HEADS_DIR_NAME), exist_ok=True)

        index_path = os.path.join(tcs_dir, cls.INDEX_FILE_NAME)
        head_path = os.path.join(refs_dir, cls.HEAD_FILE_NAME)
        main_branch_path = os.path.join(
            refs_dir,
            cls.HEADS_DIR_NAME,
            cls.DEFAULT_BRANCH,
        )

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"user.name": "", "user.email": ""}, f, indent=2)

        with open(main_branch_path, "w", encoding="utf-8") as f:
            f.write("")

        with open(head_path, "w", encoding="utf-8") as f:
            f.write(f"ref: refs/heads/{cls.DEFAULT_BRANCH}")

    def _load_index(self) -> Dict[str, str]:
        """
        Load the staging index from disk.
        """
        if os.path.exists(self.index_path):
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_index(self, index: Dict[str, str]) -> None:
        """
        Persist the staging index to disk.
        """
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    def _load_config(self) -> Dict[str, str]:
        """
        Load repository config values from disk.
        """
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"user.name": "", "user.email": ""}

    def _save_config(self, config: Dict[str, str]) -> None:
        """
        Persist repository config values to disk.
        """
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def _branch_path(self, branch_name: str) -> str:
        """
        Return the absolute path for a local branch reference file.
        """
        return os.path.join(self.refs_heads_dir, branch_name)

    def _object_path(self, object_hash: str) -> str:
        """
        Return the absolute path for a stored object hash.
        """
        return os.path.join(self.objects_dir, object_hash)

    def _read_head(self) -> str:
        """
        Read the raw HEAD file content.
        """
        if os.path.exists(self.head_path):
            return read_file(self.head_path).decode().strip()
        return ""

    def _get_head_ref(self) -> Optional[str]:
        """
        Return the symbolic HEAD reference path, if HEAD is attached.
        """
        head = self._read_head()
        if head.startswith("ref: "):
            return head[5:].strip()
        return None

    def _is_detached_head(self) -> bool:
        """
        Return True when HEAD stores a commit hash instead of a branch ref.
        """
        head = self._read_head()
        return bool(head) and not head.startswith("ref: ")

    def _set_head_ref(self, ref_path: str) -> None:
        """
        Point HEAD at a symbolic branch reference.
        """
        write_file(self.head_path, f"ref: {ref_path}".encode())

    def _set_detached_head(self, commit_hash: str) -> None:
        """
        Store a commit hash directly in HEAD.
        """
        write_file(self.head_path, commit_hash.encode())

    def _get_branch_commit(self, branch_name: str) -> Optional[str]:
        """
        Return the commit hash currently stored for a branch.
        """
        branch_path = self._branch_path(branch_name)
        if not os.path.exists(branch_path):
            return None

        commit_hash = read_file(branch_path).decode().strip()
        return commit_hash or None

    def _get_head_commit(self) -> Optional[str]:
        """
        Resolve HEAD to its current commit hash, if one exists.
        """
        head = self._read_head()
        if not head:
            return None

        if head.startswith("ref: "):
            ref_path = head[5:].strip()
            abs_ref_path = os.path.join(self.tcs_dir, ref_path)
            if not os.path.exists(abs_ref_path):
                return None
            commit_hash = read_file(abs_ref_path).decode().strip()
            return commit_hash or None

        return head or None

    def _resolve_commit_hash(self, ref_or_hash: str) -> str:
        """
        Resolve a branch name or validate an explicit commit hash.
        """
        branch_path = self._branch_path(ref_or_hash)
        if os.path.exists(branch_path):
            commit_hash = self._get_branch_commit(ref_or_hash)
            if not commit_hash:
                raise ValueError(f"Branch '{ref_or_hash}' has no commits yet.")
            return commit_hash

        self._read_commit_object(ref_or_hash)
        return ref_or_hash

    def _update_head(self, commit_hash: str) -> None:
        """
        Update the current branch ref or detached HEAD to a commit hash.
        """
        head = self._read_head()
        if head.startswith("ref: "):
            ref_path = head[5:].strip()
            abs_ref_path = os.path.join(self.tcs_dir, ref_path)
            os.makedirs(os.path.dirname(abs_ref_path), exist_ok=True)
            write_file(abs_ref_path, commit_hash.encode())
        else:
            self._set_detached_head(commit_hash)
