import os
from typing import Dict, List, Optional

from .utils import read_file, write_file


class CheckoutOperations:
    """
    Checkout and working tree restore commands.
    """

    def _would_overwrite_untracked(self, target_files: Dict[str, str]) -> List[str]:
        """
        Return untracked paths that would be replaced by a target snapshot.
        """
        staged = self._load_index()
        _, untracked, _ = self._get_working_tree_changes(staged)
        return [p for p in untracked if p in target_files]

    def _has_dirty_worktree_or_index(self) -> bool:
        """
        Return True when the index or tracked working tree differs from HEAD.
        """
        staged = self._load_index()
        modified, _, deleted = self._get_working_tree_changes(staged)

        head_commit = self._get_head_commit()
        head_snapshot = self._read_commit_object(head_commit).get("files", {}) if head_commit else {}

        index_dirty = staged != head_snapshot
        return index_dirty or bool(modified) or bool(deleted)

    def _restore_commit_snapshot(self, target_files: Dict[str, str]) -> None:
        """
        Rewrite tracked working tree files and index to match a commit snapshot.
        """
        current_index = self._load_index()

        # Remove files tracked by the current index that are absent from the target snapshot.
        for rel_path in list(current_index.keys()):
            if rel_path not in target_files:
                abs_path = os.path.join(self.root_dir, rel_path)
                if os.path.exists(abs_path):
                    os.remove(abs_path)

        # Recreate every tracked file from object storage, including parent directories.
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
        """
        Shared checkout implementation for detached commits and attached branches.
        """
        target_files: Dict[str, str] = {}
        if commit_hash:
            target_files = self._read_commit_object(commit_hash).get("files", {})

        if not force:
            # Check tracked changes first, then untracked overwrite conflicts.
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
        """
        Restore a commit snapshot and leave HEAD detached at that commit.
        """
        commit_hash = self._resolve_commit_hash(commit_hash)
        return self._checkout_commit_internal(commit_hash, attach_ref=None, force=force)

    def checkout_branch(self, name: str, force: bool = False) -> str:
        """
        Switch to a branch and restore its current commit snapshot.
        """
        branch_path = self._branch_path(name)
        if not os.path.exists(branch_path):
            raise ValueError(f"Branch '{name}' does not exist.")

        commit_hash = self._get_branch_commit(name)
        return self._checkout_commit_internal(
            commit_hash,
            attach_ref=f"refs/heads/{name}",
            force=force,
        )
