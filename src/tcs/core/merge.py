from collections import deque
from typing import List

from .utils import write_file


class MergeOperations:
    """
    Fast-forward merge support.
    """

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

        self._set_head_ref(branch_ref)
        branch_path = self._branch_path(branch_name)
        write_file(branch_path, target_commit.encode())

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
            self._fast_forward_branch(current_branch, source_commit)
            return f"Fast-forwarded '{current_branch}' to {source_commit}"

        if source_commit == current_commit:
            return f"Branch '{current_branch}' is already up to date with '{source}'."

        if self._is_ancestor(source_commit, current_commit):
            return f"Branch '{current_branch}' already contains '{source}'."

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

        raise RuntimeError(
            f"Cannot fast-forward merge '{source}' into '{current_branch}': "
            "branches have diverged."
        )
