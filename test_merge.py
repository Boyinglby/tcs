import os
from pathlib import Path

import pytest

from core import TinyControlSystem


def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def setup_repo(tmp_path: Path) -> TinyControlSystem:
    TinyControlSystem.init(str(tmp_path))
    vcs = TinyControlSystem(str(tmp_path))
    vcs.config("user.name", "Test User")
    vcs.config("user.email", "test@example.com")
    return vcs


def make_commit(vcs: TinyControlSystem, root: Path, filename: str, content: str, message: str) -> str:
    file_path = root / filename
    write_file(file_path, content)
    vcs.add(str(file_path))
    return vcs.commit(message)


def test_is_ancestor_on_linear_history(tmp_path):
    vcs = setup_repo(tmp_path)
    root = tmp_path

    c1 = make_commit(vcs, root, "a.txt", "one\n", "first")
    c2 = make_commit(vcs, root, "a.txt", "two\n", "second")

    assert vcs._is_ancestor(c1, c2) is True
    assert vcs._is_ancestor(c2, c1) is False


def test_fast_forward_merge(tmp_path):
    vcs = setup_repo(tmp_path)
    root = tmp_path

    c1 = make_commit(vcs, root, "a.txt", "one\n", "first")
    vcs.create_branch("feature")

    vcs.checkout_branch("feature")
    c2 = make_commit(vcs, root, "a.txt", "two\n", "feature update")

    vcs.checkout_branch("main")
    msg = vcs.merge("feature")

    assert "Fast-forward merged" in msg
    assert vcs._get_head_commit() == c2
    assert (root / "a.txt").read_text(encoding="utf-8") == "two\n"


def test_merge_when_source_already_contains_current(tmp_path):
    vcs = setup_repo(tmp_path)
    root = tmp_path

    c1 = make_commit(vcs, root, "a.txt", "one\n", "first")
    vcs.create_branch("feature")
    vcs.checkout_branch("feature")
    c2 = make_commit(vcs, root, "a.txt", "two\n", "second")

    vcs.checkout_branch("main")
    msg = vcs.merge("main")

    assert "already up to date" in msg or "already contains" in msg

    vcs.merge("feature")
    msg2 = vcs.merge("feature")
    assert "already up to date" in msg2 or "already contains" in msg2


def test_non_fast_forward_merge_is_refused(tmp_path):
    vcs = setup_repo(tmp_path)
    root = tmp_path

    make_commit(vcs, root, "a.txt", "base\n", "base")
    vcs.create_branch("feature")

    # Diverge main
    write_file(root / "a.txt", "main change\n")
    vcs.add(str(root / "a.txt"))
    main_commit = vcs.commit("main diverge")

    # Diverge feature
    vcs.checkout_branch("feature")
    write_file(root / "a.txt", "feature change\n")
    vcs.add(str(root / "a.txt"))
    feature_commit = vcs.commit("feature diverge")

    vcs.checkout_branch("main")

    with pytest.raises(RuntimeError, match="branches have diverged"):
        vcs.merge("feature")

    assert vcs._get_head_commit() == main_commit
    assert vcs.current_branch() == "main"