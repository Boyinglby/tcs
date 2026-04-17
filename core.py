import os
import json
import difflib
from datetime import datetime
from typing import Any, Dict, Iterator, Optional, Tuple, List

from utils import read_file, write_file, list_files, calculate_hash


class TinyControlSystem:
    """
    A tiny version control system.

    This class manages repository initialization, staging, committing,
    status inspection, history traversal, branches, checkout, and diffs.
    """

    REPO_DIR_NAME = ".tcs"
    OBJECTS_DIR_NAME = "objects"
    REFS_DIR_NAME = "refs"
    HEADS_DIR_NAME = "heads"
    INDEX_FILE_NAME = "index"
    CONFIG_FILE_NAME = "config.json"
    HEAD_FILE_NAME = "HEAD"
    DEFAULT_BRANCH = "main"

    SUPPORTED_CONFIG_KEYS = ("user.name", "user.email")

    def __init__(self, root_dir: str) -> None:
        self.root_dir: str = os.path.abspath(root_dir)
        self.tcs_dir: str = os.path.join(self.root_dir, self.REPO_DIR_NAME)
        self.objects_dir: str = os.path.join(self.tcs_dir, self.OBJECTS_DIR_NAME)
        self.refs_dir: str = os.path.join(self.tcs_dir, self.REFS_DIR_NAME)
        self.index_path: str = os.path.join(self.tcs_dir, self.INDEX_FILE_NAME)
        self.config_path: str = os.path.join(self.tcs_dir, self.CONFIG_FILE_NAME)
        self.refs_heads_dir: str = os.path.join(self.refs_dir, self.HEADS_DIR_NAME)
        self.head_path: str = os.path.join(self.refs_dir, self.HEAD_FILE_NAME)

    # ---------------------------------------------------------------------
    # Repository initialization
    # ---------------------------------------------------------------------

    @classmethod
    def init(cls, root_dir: str, directory_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Initialize a new repository on disk.
        """
        root_dir = cls._create_repo_directory(root_dir, directory_name)
        vcs = cls(root_dir)

        if os.path.exists(vcs.tcs_dir):
            return False, "TCS directory already initialized."

        cls._create_tcs_structure(vcs.tcs_dir, vcs.objects_dir, vcs.refs_dir, vcs.config_path)
        return True, f"Initialized empty TCS repository in {vcs.tcs_dir}"

    @staticmethod
    def _create_repo_directory(root_dir: str, directory_name: Optional[str]) -> str:
        if directory_name:
            new_dir = os.path.join(root_dir, directory_name)
            os.makedirs(new_dir, exist_ok=True)
            return new_dir
        return root_dir

    @staticmethod
    def _create_tcs_structure(
        tcs_dir: str,
        objects_dir: str,
        refs_dir: str,
        config_path: str,
    ) -> None:
        os.makedirs(tcs_dir, exist_ok=True)
        os.makedirs(objects_dir, exist_ok=True)
        os.makedirs(refs_dir, exist_ok=True)
        os.makedirs(os.path.join(refs_dir, TinyControlSystem.HEADS_DIR_NAME), exist_ok=True)

        index_path = os.path.join(tcs_dir, TinyControlSystem.INDEX_FILE_NAME)
        head_path = os.path.join(refs_dir, TinyControlSystem.HEAD_FILE_NAME)
        main_branch_path = os.path.join(
            refs_dir,
            TinyControlSystem.HEADS_DIR_NAME,
            TinyControlSystem.DEFAULT_BRANCH,
        )

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"user.name": "", "user.email": ""}, f, indent=2)

        with open(main_branch_path, "w", encoding="utf-8") as f:
            f.write("")

        with open(head_path, "w", encoding="utf-8") as f:
            f.write(f"ref: refs/heads/{TinyControlSystem.DEFAULT_BRANCH}")

    # ---------------------------------------------------------------------
    # Generic load/save helpers
    # ---------------------------------------------------------------------

    def _load_index(self) -> Dict[str, str]:
        if os.path.exists(self.index_path):
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_index(self, index: Dict[str, str]) -> None:
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    def _load_config(self) -> Dict[str, str]:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"user.name": "", "user.email": ""}

    def _save_config(self, config: Dict[str, str]) -> None:
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    # ---------------------------------------------------------------------
    # Path helpers
    # ---------------------------------------------------------------------

    def _branch_path(self, branch_name: str) -> str:
        return os.path.join(self.refs_heads_dir, branch_name)

    def _object_path(self, object_hash: str) -> str:
        return os.path.join(self.objects_dir, object_hash)

    # ---------------------------------------------------------------------
    # HEAD / branch helpers
    # ---------------------------------------------------------------------

    def _read_head(self) -> str:
        if os.path.exists(self.head_path):
            return read_file(self.head_path).decode().strip()
        return ""

    def _get_head_ref(self) -> Optional[str]:
        head = self._read_head()
        if head.startswith("ref: "):
            return head[5:].strip()
        return None

    def _is_detached_head(self) -> bool:
        head = self._read_head()
        return bool(head) and not head.startswith("ref: ")

    def _set_head_ref(self, ref_path: str) -> None:
        write_file(self.head_path, f"ref: {ref_path}".encode())

    def _set_detached_head(self, commit_hash: str) -> None:
        write_file(self.head_path, commit_hash.encode())

    def _get_branch_commit(self, branch_name: str) -> Optional[str]:
        branch_path = self._branch_path(branch_name)
        if not os.path.exists(branch_path):
            return None

        commit_hash = read_file(branch_path).decode().strip()
        return commit_hash or None

    def _get_head_commit(self) -> Optional[str]:
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
        branch_path = self._branch_path(ref_or_hash)
        if os.path.exists(branch_path):
            commit_hash = self._get_branch_commit(ref_or_hash)
            if not commit_hash:
                raise ValueError(f"Branch '{ref_or_hash}' has no commits yet.")
            return commit_hash

        self._read_commit_object(ref_or_hash)
        return ref_or_hash

    def _update_head(self, commit_hash: str) -> None:
        head = self._read_head()
        if head.startswith("ref: "):
            ref_path = head[5:].strip()
            abs_ref_path = os.path.join(self.tcs_dir, ref_path)
            os.makedirs(os.path.dirname(abs_ref_path), exist_ok=True)
            write_file(abs_ref_path, commit_hash.encode())
        else:
            self._set_detached_head(commit_hash)

    # ---------------------------------------------------------------------
    # Config
    # ---------------------------------------------------------------------

    def config(self, key: str, value: str) -> str:
        if key not in self.SUPPORTED_CONFIG_KEYS:
            raise ValueError("Unsupported config key. Use 'user.name' or 'user.email'.")

        config = self._load_config()
        config[key] = value
        self._save_config(config)
        return f"Set {key} to {value}"

    # ---------------------------------------------------------------------
    # Index / staging
    # ---------------------------------------------------------------------

    def _load_staged_files(self) -> Dict[str, str]:
        return self._load_index()

    def _get_staged_files(self) -> Dict[str, str]:
        return self._load_index()

    def _save_staged_files(self, staged_files: Dict[str, str]) -> None:
        self._save_index(staged_files)

    def _update_index(self, file_path: str, hash_value: str) -> None:
        rel_path = os.path.relpath(os.path.abspath(file_path), self.root_dir)
        index = self._load_index()
        index[rel_path] = hash_value
        self._save_index(index)

    def add(self, file_path: str) -> str:
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

    # ---------------------------------------------------------------------
    # Commit / object storage
    # ---------------------------------------------------------------------

    def _create_commit_object(self, message: str, parent_hash: Optional[str]) -> Dict[str, Any]:
        config = self._load_config()
        return {
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "author_name": config.get("user.name", ""),
            "author_email": config.get("user.email", ""),
            "files": self._get_staged_files(),
            "parent": parent_hash,
        }

    def _write_commit_object(self, commit_obj: Dict[str, Any]) -> str:
        commit_content = json.dumps(commit_obj, sort_keys=True).encode()
        commit_hash = calculate_hash(commit_content)
        commit_path = self._object_path(commit_hash)

        if not os.path.exists(commit_path):
            write_file(commit_path, commit_content)

        return commit_hash

    def _read_commit_object(self, commit_hash: str) -> Dict[str, Any]:
        commit_path = self._object_path(commit_hash)
        if not os.path.exists(commit_path):
            raise ValueError(f"Invalid commit hash: {commit_hash}")

        commit_content = read_file(commit_path)
        return json.loads(commit_content.decode())

    def commit(self, message: str) -> str:
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

    # ---------------------------------------------------------------------
    # Status / working tree inspection
    # ---------------------------------------------------------------------

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

    # ---------------------------------------------------------------------
    # History
    # ---------------------------------------------------------------------

    def log(self) -> Iterator[Tuple[str, Dict[str, Any]]]:
        commit_hash = self._get_head_commit()
        while commit_hash:
            commit_obj = self._read_commit_object(commit_hash)
            yield commit_hash, commit_obj
            commit_hash = commit_obj.get("parent")

    # ---------------------------------------------------------------------
    # Diff helpers
    # ---------------------------------------------------------------------

    def _get_last_commit_file_content(self, file_path: str) -> Optional[bytes]:
        commit_hash = self._get_head_commit()
        if not commit_hash:
            return None

        commit_obj = self._read_commit_object(commit_hash)
        staged_files = commit_obj.get("files", {})

        abs_path = os.path.abspath(file_path)
        rel_path = os.path.relpath(abs_path, self.root_dir)

        if rel_path in staged_files:
            file_hash = staged_files[rel_path]
            object_path = self._object_path(file_hash)
            if os.path.exists(object_path):
                return read_file(object_path)

        return None

    def _diff_one(self, file_path: str) -> str:
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return f"File not found: {file_path}"

        last_commit_content = self._get_last_commit_file_content(abs_path)
        if last_commit_content is None:
            return f"No previous commit for file {os.path.relpath(abs_path, self.root_dir)}"

        current_content = read_file(abs_path).decode(errors="replace").splitlines(keepends=True)
        previous_content = last_commit_content.decode(errors="replace").splitlines(keepends=True)

        diff_result = difflib.unified_diff(
            previous_content,
            current_content,
            fromfile=f"a/{os.path.relpath(abs_path, self.root_dir)}",
            tofile=f"b/{os.path.relpath(abs_path, self.root_dir)}",
            lineterm="",
        )

        output = "\n".join(diff_result)
        return output if output else "No differences found."

    def diff(self, file_path: Optional[str] = None) -> str:
        if file_path is None:
            staged_files = self._get_staged_files()
            if not staged_files:
                return "No tracked files to diff."

            diffs: List[str] = []
            for rel_path in staged_files:
                abs_path = os.path.join(self.root_dir, rel_path)
                if os.path.exists(abs_path):
                    diff_text = self._diff_one(abs_path)
                    if diff_text:
                        diffs.append(diff_text)
                else:
                    diffs.append(f"File deleted: {rel_path}")

            return "\n".join(diffs) if diffs else "No differences found."

        return self._diff_one(file_path)