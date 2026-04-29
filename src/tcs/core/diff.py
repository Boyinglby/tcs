import difflib
import os
from typing import List, Optional

from .utils import read_file


class DiffOperations:
    """
    Diff commands and file content comparison helpers.
    """

    def _get_last_commit_file_content(self, file_path: str) -> Optional[bytes]:
        """
        Return a file's content from the current HEAD commit, if tracked.
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
            object_path = self._object_path(file_hash)
            if os.path.exists(object_path):
                return read_file(object_path)

        return None

    def _diff_one(self, file_path: str) -> str:
        """
        Return a unified diff for one working tree file.
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

    def diff(self, file_path: Optional[str] = None) -> str:
        """
        Return unified diffs for one tracked file or all tracked files.
        """
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
