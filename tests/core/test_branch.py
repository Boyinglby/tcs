from pathlib import Path
from typing import Callable

import pytest

from src.tcs.core.core import TinyControlSystem


def test_create_branch_and_switch_updates_files(
    configured_vcs: TinyControlSystem,
    repo: Path,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    vcs = configured_vcs
    file_path = repo / "a.txt"
    c1 = make_commit(vcs, "a.txt", "v1\n", "initial")

    vcs.create_branch("feature")

    file_path.write_text("main-change\n", encoding="utf-8")
    vcs.add(str(file_path))
    c2 = vcs.commit("main change")

    assert vcs._get_head_commit() == c2
    assert vcs.current_branch() == "main"

    msg = vcs.checkout_branch("feature")
    assert "feature" in msg
    assert file_path.read_text(encoding="utf-8") == "v1\n"
    assert vcs._get_head_commit() == c1
    assert vcs.current_branch() == "feature"


def test_checkout_refuses_dirty_worktree(
    configured_vcs: TinyControlSystem,
    repo: Path,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    vcs = configured_vcs
    file_path = repo / "a.txt"
    make_commit(vcs, "a.txt", "v1\n", "initial")
    vcs.create_branch("feature")

    file_path.write_text("dirty\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Uncommitted changes"):
        vcs.checkout_branch("feature")


def test_checkout_branch_refuses_untracked_overwrite(
    configured_vcs: TinyControlSystem,
    repo: Path,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    vcs = configured_vcs
    make_commit(vcs, "a.txt", "one\n", "initial")
    vcs.create_branch("feature")

    vcs.checkout_branch("feature", force=True)
    (repo / "b.txt").write_text("branch file\n", encoding="utf-8")
    vcs.add(str(repo / "b.txt"))
    vcs.commit("add b")

    vcs.checkout_branch("main", force=True)

    (repo / "b.txt").write_text("local untracked\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Untracked files would be overwritten"):
        vcs.checkout_branch("feature")


def test_delete_branch_safety(
    configured_vcs: TinyControlSystem,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    vcs = configured_vcs
    make_commit(vcs, "a.txt", "v1\n", "initial")
    vcs.create_branch("feature")

    with pytest.raises(RuntimeError, match="currently checked out branch"):
        vcs.delete_branch("main")

    vcs.checkout_branch("feature")
    msg = vcs.delete_branch("main")
    assert "Deleted branch 'main'" in msg
    assert "main" not in vcs.list_branches()


def test_detached_head_commit_does_not_move_branch(
    configured_vcs: TinyControlSystem,
    repo: Path,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    vcs = configured_vcs
    c1 = make_commit(vcs, "a.txt", "v1\n", "initial")

    vcs.create_branch("feature")
    vcs.checkout_commit(c1)
    assert vcs._is_detached_head() is True

    file_path = repo / "a.txt"
    file_path.write_text("detached commit\n", encoding="utf-8")
    vcs.add(str(file_path))
    c2 = vcs.commit("detached work")
    assert c2 != c1

    main_ref = repo / ".tcs" / "refs" / "heads" / "main"
    assert main_ref.read_text(encoding="utf-8").strip() == c1
