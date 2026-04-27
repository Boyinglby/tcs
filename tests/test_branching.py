import os
import pytest
from src.core import TinyControlSystem


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_create_branch_and_switch_updates_files(tmp_path):
    repo = tmp_path / "repo"
    TinyControlSystem.init(str(tmp_path), "repo")
    vcs = TinyControlSystem(str(repo))
    vcs.config("user.name", "Alice")
    vcs.config("user.email", "alice@example.com")

    file_path = repo / "a.txt"
    write_text(str(file_path), "v1\n")
    vcs.add(str(file_path))
    c1 = vcs.commit("initial")

    vcs.create_branch("feature")

    write_text(str(file_path), "main-change\n")
    vcs.add(str(file_path))
    c2 = vcs.commit("main change")

    assert vcs._get_head_commit() == c2
    assert vcs.current_branch() == "main"

    msg = vcs.checkout_branch("feature")
    assert "feature" in msg
    assert read_text(str(file_path)) == "v1\n"
    assert vcs._get_head_commit() == c1
    assert vcs.current_branch() == "feature"


def test_checkout_refuses_dirty_worktree(tmp_path):
    repo = tmp_path / "repo"
    TinyControlSystem.init(str(tmp_path), "repo")
    vcs = TinyControlSystem(str(repo))
    vcs.config("user.name", "Alice")
    vcs.config("user.email", "alice@example.com")

    file_path = repo / "a.txt"
    write_text(str(file_path), "v1\n")
    vcs.add(str(file_path))
    vcs.commit("initial")
    vcs.create_branch("feature")

    write_text(str(file_path), "dirty\n")

    with pytest.raises(RuntimeError, match="Uncommitted changes"):
        vcs.checkout_branch("feature")


def test_checkout_branch_refuses_untracked_overwrite(tmp_path):
    repo = tmp_path / "repo"
    TinyControlSystem.init(str(tmp_path), "repo")
    vcs = TinyControlSystem(str(repo))
    vcs.config("user.name", "Alice")
    vcs.config("user.email", "alice@example.com")

    a = repo / "a.txt"
    write_text(str(a), "one\n")
    vcs.add(str(a))
    vcs.commit("initial")
    vcs.create_branch("feature")

    # Make the feature branch track b.txt
    vcs.checkout_branch("feature", force=True)
    write_text(str(repo / "b.txt"), "branch file\n")
    vcs.add(str(repo / "b.txt"))
    vcs.commit("add b")

    # Go back to main
    vcs.checkout_branch("main", force=True)

    # Create an untracked file that would be overwritten by feature
    write_text(str(repo / "b.txt"), "local untracked\n")

    with pytest.raises(RuntimeError, match="Untracked files would be overwritten"):
        vcs.checkout_branch("feature")


def test_delete_branch_safety(tmp_path):
    repo = tmp_path / "repo"
    TinyControlSystem.init(str(tmp_path), "repo")
    vcs = TinyControlSystem(str(repo))
    vcs.config("user.name", "Alice")
    vcs.config("user.email", "alice@example.com")

    a = repo / "a.txt"
    write_text(str(a), "v1\n")
    vcs.add(str(a))
    vcs.commit("initial")
    vcs.create_branch("feature")

    with pytest.raises(RuntimeError, match="currently checked out branch"):
        vcs.delete_branch("main")

    vcs.checkout_branch("feature")
    msg = vcs.delete_branch("main")
    assert "Deleted branch 'main'" in msg
    assert "main" not in vcs.list_branches()


def test_detached_head_commit_does_not_move_branch(tmp_path):
    repo = tmp_path / "repo"
    TinyControlSystem.init(str(tmp_path), "repo")
    vcs = TinyControlSystem(str(repo))
    vcs.config("user.name", "Alice")
    vcs.config("user.email", "alice@example.com")

    a = repo / "a.txt"
    write_text(str(a), "v1\n")
    vcs.add(str(a))
    c1 = vcs.commit("initial")

    vcs.create_branch("feature")
    vcs.checkout_commit(c1)
    assert vcs._is_detached_head() is True

    write_text(str(a), "detached commit\n")
    vcs.add(str(a))
    c2 = vcs.commit("detached work")
    assert c2 != c1

    main_ref = repo / ".tcs" / "refs" / "heads" / "main"
    assert read_text(str(main_ref)).strip() == c1