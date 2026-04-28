from pathlib import Path
from typing import Callable

import pytest

from src.tcs.core.core import TinyControlSystem


def test_is_ancestor_on_linear_history(
    configured_vcs: TinyControlSystem,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    c1 = make_commit(configured_vcs, "a.txt", "one\n", "first")
    c2 = make_commit(configured_vcs, "a.txt", "two\n", "second")

    assert configured_vcs._is_ancestor(c1, c2) is True
    assert configured_vcs._is_ancestor(c2, c1) is False


def test_fast_forward_merge(
    configured_vcs: TinyControlSystem,
    repo: Path,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    vcs = configured_vcs
    make_commit(vcs, "a.txt", "one\n", "first")
    vcs.create_branch("feature")

    vcs.checkout_branch("feature")
    c2 = make_commit(vcs, "a.txt", "two\n", "feature update")

    vcs.checkout_branch("main")
    msg = vcs.merge("feature")

    assert "Fast-forward merged" in msg
    assert vcs._get_head_commit() == c2
    assert (repo / "a.txt").read_text(encoding="utf-8") == "two\n"


def test_merge_when_source_already_contains_current(
    configured_vcs: TinyControlSystem,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    vcs = configured_vcs
    make_commit(vcs, "a.txt", "one\n", "first")
    vcs.create_branch("feature")
    vcs.checkout_branch("feature")
    make_commit(vcs, "a.txt", "two\n", "second")

    vcs.checkout_branch("main")
    msg = vcs.merge("main")

    assert "already up to date" in msg or "already contains" in msg

    vcs.merge("feature")
    msg2 = vcs.merge("feature")
    assert "already up to date" in msg2 or "already contains" in msg2


def test_non_fast_forward_merge_is_refused(
    configured_vcs: TinyControlSystem,
    repo: Path,
    make_commit: Callable[[TinyControlSystem, str, str, str], str],
) -> None:
    vcs = configured_vcs
    make_commit(vcs, "a.txt", "base\n", "base")
    vcs.create_branch("feature")

    (repo / "a.txt").write_text("main change\n", encoding="utf-8")
    vcs.add(str(repo / "a.txt"))
    main_commit = vcs.commit("main diverge")

    vcs.checkout_branch("feature")
    (repo / "a.txt").write_text("feature change\n", encoding="utf-8")
    vcs.add(str(repo / "a.txt"))
    vcs.commit("feature diverge")

    vcs.checkout_branch("main")

    with pytest.raises(RuntimeError, match="branches have diverged"):
        vcs.merge("feature")

    assert vcs._get_head_commit() == main_commit
    assert vcs.current_branch() == "main"
