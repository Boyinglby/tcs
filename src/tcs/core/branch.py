import os
from typing import List, Optional

from .utils import write_file


class BranchOperations:
    """
    Branch creation, deletion, rename, and listing commands.
    """

    def create_branch(self, name: str, start_point: Optional[str] = None, force: bool = False) -> str:
        """
        Create a branch at the given start point or at the current HEAD.
        """
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
        """
        Delete an existing branch that is not currently checked out.
        """
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
        """
        Rename a branch and update HEAD if that branch is checked out.
        """
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
        """
        Return the checked-out branch name, or None for detached HEAD.
        """
        ref = self._get_head_ref()
        if not ref:
            return None
        return ref.split("/")[-1]

    def list_branches(self) -> List[str]:
        """
        Return all local branch names in sorted order.
        """
        if not os.path.exists(self.refs_heads_dir):
            return []

        return sorted(
            name
            for name in os.listdir(self.refs_heads_dir)
            if os.path.isfile(os.path.join(self.refs_heads_dir, name))
        )
