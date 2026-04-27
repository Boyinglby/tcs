import os
import json
import difflib
from datetime import datetime
from typing import Any, Dict, Iterator, Optional, Tuple, List

from .utils import read_file, write_file, list_files, calculate_hash

from collections import deque


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

    def _create_commit_object(
        self,
        message: str,
        parent_hash: Optional[str],
        merge_parent_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
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

    # ---------------------------------------------------------------------
    # Checkout / restore
    # ---------------------------------------------------------------------

    def _would_overwrite_untracked(self, target_files: Dict[str, str]) -> List[str]:
        staged = self._load_index()
        _, untracked, _ = self._get_working_tree_changes(staged)
        return [p for p in untracked if p in target_files]

    def _has_dirty_worktree_or_index(self) -> bool:
        staged = self._load_index()
        modified, _, deleted = self._get_working_tree_changes(staged)

        head_commit = self._get_head_commit()
        head_snapshot = self._read_commit_object(head_commit).get("files", {}) if head_commit else {}

        index_dirty = staged != head_snapshot
        return index_dirty or bool(modified) or bool(deleted)

    def _restore_commit_snapshot(self, target_files: Dict[str, str]) -> None:
        current_index = self._load_index()

        for rel_path in list(current_index.keys()):
            if rel_path not in target_files:
                abs_path = os.path.join(self.root_dir, rel_path)
                if os.path.exists(abs_path):
                    os.remove(abs_path)

        for rel_path, file_hash in target_files.items():
            object_path = self._object_path(file_hash)
            if not os.path.exists(object_path):
                raise ValueError(f"Missing object for file hash: {file_hash}")

            abs_path = os.path.join(self.root_dir, rel_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            write_file(abs_path, read_file(object_path))

        self._save_index(dict(target_files))

    def _checkout_commit_internal(
        self,
        commit_hash: Optional[str],
        *,
        attach_ref: Optional[str] = None,
        force: bool = False,
    ) -> str:
        target_files: Dict[str, str] = {}
        if commit_hash:
            target_files = self._read_commit_object(commit_hash).get("files", {})

        if not force:
            if self._has_dirty_worktree_or_index():
                raise RuntimeError("Uncommitted changes present. Commit or discard them first.")

            overwrite = self._would_overwrite_untracked(target_files)
            if overwrite:
                raise RuntimeError(
                    "Untracked files would be overwritten: " + ", ".join(sorted(overwrite))
                )

        self._restore_commit_snapshot(target_files)

        if attach_ref is not None:
            self._set_head_ref(attach_ref)
            return f"Switched to branch '{attach_ref.split('/')[-1]}'"

        if commit_hash is not None:
            self._set_detached_head(commit_hash)
            return f"HEAD is now detached at {commit_hash}"

        return "Checked out empty state"

    def checkout_commit(self, commit_hash: str, force: bool = False) -> str:
        commit_hash = self._resolve_commit_hash(commit_hash)
        return self._checkout_commit_internal(commit_hash, attach_ref=None, force=force)

    def checkout_branch(self, name: str, force: bool = False) -> str:
        branch_path = self._branch_path(name)
        if not os.path.exists(branch_path):
            raise ValueError(f"Branch '{name}' does not exist.")

        commit_hash = self._get_branch_commit(name)
        return self._checkout_commit_internal(
            commit_hash,
            attach_ref=f"refs/heads/{name}",
            force=force,
        )

    # ---------------------------------------------------------------------
    # Branch management
    # ---------------------------------------------------------------------

    def create_branch(self, name: str, start_point: Optional[str] = None, force: bool = False) -> str:
        if not name or name.strip() != name or "/" in name or ".." in name:
            raise ValueError("Invalid branch name.")

        os.makedirs(self.refs_heads_dir, exist_ok=True)
        branch_path = self._branch_path(name)

        if os.path.exists(branch_path) and not force:
            raise ValueError(f"Branch '{name}' already exists.")

        if start_point is None:
            start_point = self._get_head_commit()

        if start_point is not None:
            self._read_commit_object(start_point)

        write_file(branch_path, (start_point or "").encode())
        return f"Created branch '{name}'"

    def delete_branch(self, name: str) -> str:
        if not name or name.strip() != name:
            raise ValueError("Invalid branch name.")

        current_ref = self._get_head_ref()
        if current_ref == f"refs/heads/{name}":
            raise RuntimeError("Cannot delete the currently checked out branch.")

        branch_path = self._branch_path(name)
        if not os.path.exists(branch_path):
            raise ValueError(f"Branch '{name}' does not exist.")

        os.remove(branch_path)
        return f"Deleted branch '{name}'"

    def rename_branch(self, old_name: str, new_name: str) -> str:
        if not old_name or old_name.strip() != old_name:
            raise ValueError("Invalid branch name.")
        if not new_name or new_name.strip() != new_name or "/" in new_name or ".." in new_name:
            raise ValueError("Invalid branch name.")

        old_path = self._branch_path(old_name)
        if not os.path.exists(old_path):
            raise ValueError(f"Branch '{old_name}' does not exist.")

        new_path = self._branch_path(new_name)
        if os.path.exists(new_path):
            raise ValueError(f"Branch '{new_name}' already exists.")

        os.rename(old_path, new_path)

        current_ref = self._get_head_ref()
        if current_ref == f"refs/heads/{old_name}":
            self._set_head_ref(f"refs/heads/{new_name}")

        return f"Renamed branch '{old_name}' to '{new_name}'"

    def current_branch(self) -> Optional[str]:
        ref = self._get_head_ref()
        if not ref:
            return None
        return ref.split("/")[-1]

    def list_branches(self) -> List[str]:
        if not os.path.exists(self.refs_heads_dir):
            return []

        return sorted(
            name
            for name in os.listdir(self.refs_heads_dir)
            if os.path.isfile(os.path.join(self.refs_heads_dir, name))
        )


    # ---------------------------------------------------------------------
    # Fast forward merge
    # ---------------------------------------------------------------------    
    def _get_commit_parents(self, commit_hash: str) -> List[str]:
        """
        Return all known parents for a commit.
    
        Current commits have one parent, but this also supports a future
        merge_parent field.
        """
        commit_obj = self._read_commit_object(commit_hash)
    
        parents: List[str] = []
        parent = commit_obj.get("parent")
        merge_parent = commit_obj.get("merge_parent")
    
        if parent:
            parents.append(parent)
        if merge_parent:
            parents.append(merge_parent)
    
        return parents
    
    def _is_ancestor(self, ancestor_hash: str, descendant_hash: str) -> bool:
        """
        True if ancestor_hash is reachable from descendant_hash.
        This walks the commit graph using parent links.
        """
        if not ancestor_hash or not descendant_hash:
            return False
    
        if ancestor_hash == descendant_hash:
            return True
    
        visited = set()
        queue = deque([descendant_hash])
    
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
    
            if current == ancestor_hash:
                return True
    
            for parent in self._get_commit_parents(current):
                if parent not in visited:
                    queue.append(parent)
    
        return False
    
    def _fast_forward_branch(self, branch_name: str, target_commit: str) -> str:
        """
        Move branch_name to target_commit and update the working tree to match.
        Assumes the merge is safe and fast-forwardable.
        """
        branch_ref = f"refs/heads/{branch_name}"
    
        # Update the branch pointer first
        self._set_head_ref(branch_ref)
        branch_path = self._branch_path(branch_name)
        write_file(branch_path, target_commit.encode())
    
        # Restore the working tree/index to the target snapshot
        target_files = self._read_commit_object(target_commit).get("files", {})
        self._restore_commit_snapshot(target_files)
    
        return f"Fast-forwarded '{branch_name}' to {target_commit}"
    
    def merge(self, source: str) -> str:
        """
        Merge source into the currently checked out branch.

        Supported behavior:
        - already up to date: no-op
        - fast-forward merge: move current branch to source
        - diverged branches: refuse for now, since this system does not yet
          implement a 3-way content merge/conflict resolver
        """
        if self._is_detached_head():
            raise RuntimeError("Cannot merge in detached HEAD state.")

        current_branch = self.current_branch()
        if not current_branch:
            raise RuntimeError("No current branch is checked out.")

        current_commit = self._get_head_commit()
        source_commit = self._resolve_commit_hash(source)

        if not current_commit:
            # Empty current branch: this is effectively a fast-forward to source.
            self._fast_forward_branch(current_branch, source_commit)
            return f"Fast-forwarded '{current_branch}' to {source_commit}"

        if source_commit == current_commit:
            return f"Branch '{current_branch}' is already up to date with '{source}'."

        # Source is already contained in current branch history.
        if self._is_ancestor(source_commit, current_commit):
            return f"Branch '{current_branch}' already contains '{source}'."

        # Current branch is behind source, so fast-forward is possible.
        if self._is_ancestor(current_commit, source_commit):
            if self._has_dirty_worktree_or_index():
                raise RuntimeError("Uncommitted changes present. Commit or discard them first.")

            overwrite = self._would_overwrite_untracked(
                self._read_commit_object(source_commit).get("files", {})
            )
            if overwrite:
                raise RuntimeError(
                    "Untracked files would be overwritten: " + ", ".join(sorted(overwrite))
                )

            self._fast_forward_branch(current_branch, source_commit)
            return f"Fast-forward merged '{source}' into '{current_branch}'."

        # Diverged history: not supported without a real merge algorithm.
        raise RuntimeError(
            f"Cannot fast-forward merge '{source}' into '{current_branch}': "
            "branches have diverged."
        )
