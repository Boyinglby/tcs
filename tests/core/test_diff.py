from pathlib import Path
from typing import Callable

from src.tcs.core.core import TinyControlSystem


def test_diff_reports_no_differences_for_clean_file(
    configured_vcs: TinyControlSystem,
    repo: Path,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    make_commit(configured_vcs, "notes.txt", "line one\nline two\n", "Add notes")

    diff_output = configured_vcs.diff(str(repo / "notes.txt"))
    assert diff_output == "No differences found."


def test_diff_reports_changed_lines(
    configured_vcs: TinyControlSystem,
    repo: Path,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    make_commit(configured_vcs, "story.txt", "alpha\nbeta\n", "Add story")

    file_path = repo / "story.txt"
    file_path.write_text("alpha\ngamma\n", encoding="utf-8")

    diff_output = configured_vcs.diff(str(file_path))
    assert "-beta" in diff_output
    assert "+gamma" in diff_output
