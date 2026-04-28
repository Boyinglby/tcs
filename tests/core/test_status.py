from pathlib import Path
from typing import Callable

from src.tcs.core.core import TinyControlSystem


def test_status_reports_clean_tracked_working_tree(
    configured_vcs: TinyControlSystem,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    make_commit(configured_vcs, "notes.txt", "line one\nline two\n", "Add notes")

    status = configured_vcs.status()
    assert "notes.txt" in status["staged"]
    assert status["modified"] == []
    assert status["untracked"] == []
    assert status["deleted"] == []


def test_status_reports_modified_file(
    configured_vcs: TinyControlSystem,
    repo: Path,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    make_commit(configured_vcs, "story.txt", "alpha\nbeta\n", "Add story")

    (repo / "story.txt").write_text("alpha\ngamma\n", encoding="utf-8")

    status = configured_vcs.status()
    assert "story.txt" in status["modified"]
