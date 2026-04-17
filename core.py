import os
import json
from datetime import datetime
import difflib
import hashlib
from typing import Any, Dict, Iterator, Optional, Tuple, List

from utils import *

class TinyControlSystem:
    """
    A tiny version control system.

    This class manages repository initialization, staging, committing,
    status inspection, history traversal, and unified diffs.

    Parameters:
        root_dir (str): Path to the repository root directory.

    Attributes:
        root_dir (str): repository root path.
        tcs_dir (str): Path to the internal repository metadata directory.
        objects_dir (str): Path to the object store directory.
        refs_dir (str): Path to the references directory.

    Raises:
        OSError: If repository paths cannot be created or accessed.
    """

    def __init__(self, root_dir: str) -> None:
        """
        Initialize a TinyControlSystem instance.

        Parameters:
            root_dir (str): Path to the repository root directory.

        Returns:
            None

        Raises:
            OSError: If the repository path cannot be resolved.
        """
        self.root_dir: str = os.path.abspath(root_dir)
        self.tcs_dir: str = os.path.join(self.root_dir, ".tcs")
        self.objects_dir: str = os.path.join(self.tcs_dir, "objects")
        self.refs_dir: str = os.path.join(self.tcs_dir, "refs")
        self.index_path: str = os.path.join(self.tcs_dir, "index")
        self.config_path: str = os.path.join(self.tcs_dir, "config.json")

    @classmethod
    def init(cls, root_dir: str, directory_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Initialize a new repository on disk.

        Parameters:
            root_dir (str): Base directory where the repository should be created.
            directory_name (Optional[str]): Optional subdirectory name for the repo.

        Returns:
            Tuple[bool, str]: A success flag and a message.

        Raises:
            OSError: If directories or files cannot be created.
        """
        root_dir = cls._create_repo_directory(root_dir, directory_name)
        vcs = cls(root_dir)

        if os.path.exists(vcs.tcs_dir):
            return False, "TCS directory already initialized."

        cls._create_tcs_structure(vcs.tcs_dir, vcs.objects_dir, vcs.refs_dir, vcs.config_path)
        return True, f"Initialized empty TCS repository in {vcs.tcs_dir}"

    @staticmethod
    def _create_repo_directory(root_dir: str, directory_name: Optional[str]) -> str:
        """
        Create a repository directory if a name is provided.

        Parameters:
            root_dir (str): Base directory.
            directory_name (Optional[str]): Optional new repository folder name.

        Returns:
            str: Final repository directory path.

        Raises:
            OSError: If the target directory cannot be created.
        """
        if directory_name:
            new_dir = os.path.join(root_dir, directory_name)
            os.makedirs(new_dir, exist_ok=True)
            root_dir = new_dir
        return root_dir

    @staticmethod
    def _create_tcs_structure(
        tcs_dir: str,
        objects_dir: str,
        refs_dir: str,
        config_path: str,
    ) -> None:
        """
        Create the internal repository structure.

        Parameters:
            tcs_dir (str): Metadata root directory.
            objects_dir (str): Object storage directory.
            refs_dir (str): Reference storage directory.
            config_path (str): Path to the configuration file.

        Returns:
            None

        Raises:
            OSError: If directories or files cannot be created.
        """
        os.makedirs(tcs_dir, exist_ok=True)
        os.makedirs(objects_dir, exist_ok=True)
        os.makedirs(refs_dir, exist_ok=True)

        index_path = os.path.join(tcs_dir, "index")
        
        # Stores staged files later. Starts empty: {}
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        # Stores user info. Starts with empty values
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"user.name": "", "user.email": ""}, f, indent=2)

    def _load_index(self) -> Dict[str, str]:
        """
        Load the staging index from disk.

        Parameters:
            None

        Returns:
            Dict[str, str]: Mapping of relative file paths to content hashes.

        Raises:
            json.JSONDecodeError: If the index file is corrupted.
            OSError: If the index file cannot be read.
        """
        if os.path.exists(self.index_path):
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_index(self, index: Dict[str, str]) -> None:
        """
        Save the staging index to disk.

        Parameters:
            index (Dict[str, str]): Mapping of relative file paths to hashes.

        Returns:
            None

        Raises:
            OSError: If the index file cannot be written.
        """
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    def _load_config(self) -> Dict[str, str]:
        """
        Load repository configuration from disk.

        Parameters:
            None

        Returns:
            Dict[str, str]: Repository config dictionary.

        Raises:
            json.JSONDecodeError: If the config file is corrupted.
            OSError: If the config file cannot be read.
        """
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"user.name": "", "user.email": ""}

    def _save_config(self, config: Dict[str, str]) -> None:
        """
        Save repository configuration to disk.

        Parameters:
            config (Dict[str, str]): Config dictionary to save.

        Returns:
            None

        Raises:
            OSError: If the config file cannot be written.
        """
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def config(self, key: str, value: str) -> str:
        """
        Set a repository configuration value.

        Parameters:
            key (str): Configuration key, such as 'user.name' or 'user.email'.
            value (str): Configuration value to store.

        Returns:
            str: Confirmation message.

        Raises:
            ValueError: If the key is not supported.
            OSError: If the config file cannot be written.
        """
        if key not in ("user.name", "user.email"):
            raise ValueError("Unsupported config key. Use 'user.name' or 'user.email'.")

        config = self._load_config()
        config[key] = value
        self._save_config(config)
        return f"Set {key} to {value}"

    def _update_index(self, file_path: str, hash_value: str) -> None:
        """
        Add or update a file in the staging index.

        Parameters:
            file_path (str): Absolute or relative file path to stage.
            hash_value (str): Content hash of the file.

        Returns:
            None

        Raises:
            OSError: If the index file cannot be written.
        """
        rel_path = os.path.relpath(os.path.abspath(file_path), self.root_dir)
        index = self._load_index()
        index[rel_path] = hash_value
        self._save_index(index)

    def add(self, file_path: str) -> str:
        """
        Stage a file by content hash.

        Parameters:
            file_path (str): Path to the file to stage.

        Returns:
            str: SHA-256 hash of the file content.

        Raises:
            FileNotFoundError: If the file does not exist.
            OSError: If the object file or index cannot be written.
        """
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        content = read_file(abs_path)
        hash_value = calculate_hash(content)

        object_path = os.path.join(self.objects_dir, hash_value)
        if not os.path.exists(object_path):
            write_file(object_path, content)

        self._update_index(abs_path, hash_value)
        return hash_value

    def _get_head_commit(self) -> Optional[str]:
        """
        Return the current HEAD commit hash.

        Parameters:
            None

        Returns:
            Optional[str]: Current HEAD hash, or None if not set.

        Raises:
            OSError: If HEAD cannot be read.
        """
        head_path = os.path.join(self.refs_dir, "HEAD")
        if os.path.exists(head_path):
            head = read_file(head_path).decode().strip()
            return head or None
        return None

    def _update_head(self, commit_hash: str) -> None:
        """
        Update HEAD to a new commit hash.

        Parameters:
            commit_hash (str): Commit hash to write to HEAD.

        Returns:
            None

        Raises:
            OSError: If HEAD cannot be written.
        """
        head_path = os.path.join(self.refs_dir, "HEAD")
        write_file(head_path, commit_hash.encode())

    def _get_staged_files(self) -> Dict[str, str]:
        """
        Return the current staging index.

        Parameters:
            None

        Returns:
            Dict[str, str]: Staged files as relative path to hash mapping.

        Raises:
            json.JSONDecodeError: If the index file is corrupted.
            OSError: If the index file cannot be read.
        """
        return self._load_index()

    def _create_commit_object(self, message: str, parent_hash: Optional[str]) -> Dict[str, Any]:
        """
        Build a commit object.

        Parameters:
            message (str): Commit message.
            parent_hash (Optional[str]): Parent commit hash, if any.

        Returns:
            Dict[str, Any]: Commit object containing metadata and staged files.

        Raises:
            OSError: If the configuration or index cannot be read.
        """
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
        """
        Store a commit object in the object database.

        Parameters:
            commit_obj (Dict[str, Any]): Commit object to write.

        Returns:
            str: SHA-256 hash of the stored commit object.

        Raises:
            OSError: If the commit object cannot be written.
        """
        commit_content = json.dumps(commit_obj, sort_keys=True).encode()
        commit_hash = calculate_hash(commit_content)
        commit_path = os.path.join(self.objects_dir, commit_hash)

        if not os.path.exists(commit_path):
            write_file(commit_path, commit_content)

        return commit_hash

    def commit(self, message: str) -> str:
        """
        Create a commit from staged files.

        Parameters:
            message (str): Commit message.

        Returns:
            str: Commit hash of the newly created commit.

        Raises:
            ValueError: If the message is empty or no files are staged.
            OSError: If commit metadata cannot be written.
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

    def _read_commit_object(self, commit_hash: str) -> Dict[str, Any]:
        """
        Load a commit object by hash.

        Parameters:
            commit_hash (str): Commit hash to read.

        Returns:
            Dict[str, Any]: Parsed commit object.

        Raises:
            ValueError: If the commit hash is invalid or missing.
            json.JSONDecodeError: If the commit object is corrupted.
            OSError: If the commit object cannot be read.
        """
        commit_path = os.path.join(self.objects_dir, commit_hash)
        if not os.path.exists(commit_path):
            raise ValueError(f"Invalid commit hash: {commit_hash}")

        commit_content = read_file(commit_path)
        return json.loads(commit_content.decode())

    def status(self) -> Dict[str, Any]:
        """
        Return repository status information.

        Parameters:
            None

        Returns:
            Dict[str, Any]: Dictionary containing staged, modified, untracked, and deleted files.

        Raises:
            OSError: If the working tree cannot be scanned.
            json.JSONDecodeError: If the index file is corrupted.
        """
        staged = self._get_staged_files()
        modified, untracked, deleted = self._get_working_tree_changes(staged)

        return {
            "staged": staged,
            "modified": modified,
            "untracked": untracked,
            "deleted": deleted,
        }

    def _get_working_tree_changes(self, staged_files: Dict[str, str]) -> Tuple[List[str], List[str], List[str]]:
        """
        Compare the working tree with the staged files.

        Parameters:
            staged_files (Dict[str, str]): Staged file mapping.

        Returns:
            Tuple[List[str], List[str], List[str]]: Modified, untracked, and deleted file lists.

        Raises:
            OSError: If the working tree cannot be traversed.
        """
        modified: List[str] = []
        untracked: List[str] = []
        deleted: List[str] = []

        tracked_paths = set(staged_files.keys())

        for file_path in list_files(self.root_dir):
            rel_path = os.path.relpath(file_path, self.root_dir)

            # Ignore internal repository metadata.
            if rel_path.startswith(".tcs"):
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

    def log(self) -> Iterator[Tuple[str, Dict[str, Any]]]:
        """
        Yield commit history from HEAD backward.

        Parameters:
            None

        Returns:
            Iterator[Tuple[str, Dict[str, Any]]]: Iterator of commit hash and commit object pairs.

        Raises:
            ValueError: If a stored commit hash is invalid.
            OSError: If a commit object cannot be read.
        """
        commit_hash = self._get_head_commit()
        while commit_hash:
            commit_obj = self._read_commit_object(commit_hash)
            yield commit_hash, commit_obj
            commit_hash = commit_obj.get("parent")

    def _get_last_commit_file_content(self, file_path: str) -> Optional[bytes]:
        """
        Return file content from the latest commit for a given path.

        Parameters:
            file_path (str): File path to inspect.

        Returns:
            Optional[bytes]: File content from the last commit, or None if unavailable.

        Raises:
            ValueError: If the head commit cannot be read.
            OSError: If the object content cannot be read.
        """
        commit_hash = self._get_head_commit()
        if not commit_hash:
            return None

        commit_obj = self._read_commit_object(commit_hash)
        staged_files = commit_obj.get("files", {})

        abs_path = os.path.abspath(file_path)
        rel_path = os.path.relpath(abs_path, self.root_dir)

        if rel_path in staged_files:
            file_hash = staged_files[rel_path]
            object_path = os.path.join(self.objects_dir, file_hash)
            if os.path.exists(object_path):
                return read_file(object_path)

        return None

    def diff(self, file_path: Optional[str] = None) -> str:
        """
        Show unified diff output for a file or for all tracked files.

        Parameters:
            file_path (Optional[str]): Optional file path to diff. If omitted,
                the method diffs all tracked files.

        Returns:
            str: Unified diff text, or a message if no differences exist.

        Raises:
            OSError: If files cannot be read.
            ValueError: If commit history is invalid.
        """
        if file_path is None:
            staged_files = self._get_staged_files()
            if not staged_files:
                return "No tracked files to diff."

            diffs: List[str] = []
            for rel_path in staged_files:
                abs_path = os.path.join(self.root_dir, rel_path)
                if os.path.exists(abs_path):
                    d = self._diff_one(abs_path)
                    if d:
                        diffs.append(d)
                else:
                    diffs.append(f"File deleted: {rel_path}")

            return "\n".join(diffs) if diffs else "No differences found."

        return self._diff_one(file_path)

    def _diff_one(self, file_path: str) -> str:
        """
        Diff one file against its last committed version.

        Parameters:
            file_path (str): Path to the file to diff.

        Returns:
            str: Unified diff text, or a message if no differences exist.

        Raises:
            FileNotFoundError: If the file does not exist.
            OSError: If the file cannot be read.
            ValueError: If the last committed version cannot be found.
        """
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