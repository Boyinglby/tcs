from pathlib import Path
from typing import Callable

import pytest

from src.tcs.core.core import TinyControlSystem


def test_commit_requires_staged_changes(initialized_vcs: TinyControlSystem) -> None:
    with pytest.raises(ValueError, match="No staged changes to commit"):
        initialized_vcs.commit("Initial commit")


def test_commit_rejects_empty_message(initialized_vcs: TinyControlSystem, repo: Path) -> None:
    file_path = repo / "hello.txt"
    file_path.write_text("content\n", encoding="utf-8")
    initialized_vcs.add(str(file_path))

    with pytest.raises(ValueError, match="Commit message cannot be empty"):
        initialized_vcs.commit("   ")


def test_commit_records_snapshot_and_author(
    configured_vcs: TinyControlSystem,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    commit_hash = make_commit(configured_vcs, "notes.txt", "line one\nline two\n", "Add notes")

    assert len(commit_hash) == 64
    assert configured_vcs._get_head_commit() == commit_hash

    commits = list(configured_vcs.log())
    assert len(commits) == 1
    head_hash, head_commit = commits[0]
    assert head_hash == commit_hash
    assert head_commit["message"] == "Add notes"
    assert head_commit["author_name"] == "Test User"
    assert head_commit["author_email"] == "test@example.com"
    assert "notes.txt" in head_commit["files"]
