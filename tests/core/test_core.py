import json
from pathlib import Path

import pytest


from src.tcs.core.core import (
    TinyControlSystem,
    calculate_hash,
    list_files,
    read_file,
    write_file,
)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Create an isolated temporary repository root for each test."""
    return tmp_path / "repo"


@pytest.fixture()
def initialized_vcs(repo: Path) -> TinyControlSystem:
    """Initialize a repository and return a ready-to-use TCS instance."""
    repo.mkdir()
    ok, msg = TinyControlSystem.init(str(repo))
    assert ok is True
    assert "Initialized" in msg
    return TinyControlSystem(str(repo))


# -----------------------
# Unit tests
# -----------------------

def test_calculate_hash_is_deterministic() -> None:
    data = b"hello world"
    assert calculate_hash(data) == calculate_hash(data)
    assert calculate_hash(data) != calculate_hash(b"hello world!")


def test_read_write_file_round_trip(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    write_file(str(file_path), b"abc123")
    assert file_path.exists()
    assert read_file(str(file_path)) == b"abc123"


def test_list_files_recursively(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "one.txt").write_text("1", encoding="utf-8")
    (tmp_path / "b.txt").write_text("2", encoding="utf-8")

    files = sorted(Path(p).relative_to(tmp_path).as_posix() for p in list_files(str(tmp_path)))
    assert files == ["a/one.txt", "b.txt"]


def test_init_creates_repository_structure(repo: Path) -> None:
    ok, msg = TinyControlSystem.init(str(repo))
    assert ok is True
    assert "Initialized empty TCS repository" in msg

    assert (repo / ".tcs").is_dir()
    assert (repo / ".tcs" / "objects").is_dir()
    assert (repo / ".tcs" / "refs").is_dir()
    assert (repo / ".tcs" / "index").is_file()
    assert (repo / ".tcs" / "config.json").is_file()

    config = json.loads((repo / ".tcs" / "config.json").read_text(encoding="utf-8"))
    assert config == {"user.name": "", "user.email": ""}


def test_config_updates_repository_settings(initialized_vcs: TinyControlSystem) -> None:
    assert initialized_vcs.config("user.name", "Alice") == "Set user.name to Alice"
    assert initialized_vcs.config("user.email", "alice@example.com") == "Set user.email to alice@example.com"

    config = json.loads((Path(initialized_vcs.config_path)).read_text(encoding="utf-8"))
    assert config["user.name"] == "Alice"
    assert config["user.email"] == "alice@example.com"


def test_add_stages_file_and_stores_object(initialized_vcs: TinyControlSystem, repo: Path) -> None:
    repo_file = repo / "hello.txt"
    repo_file.write_text("hello\n", encoding="utf-8")

    file_hash = initialized_vcs.add(str(repo_file))
    assert len(file_hash) == 64

    index = json.loads((repo / ".tcs" / "index").read_text(encoding="utf-8"))
    assert index["hello.txt"] == file_hash
    assert (repo / ".tcs" / "objects" / file_hash).is_file()


def test_commit_requires_staged_changes(initialized_vcs: TinyControlSystem) -> None:
    with pytest.raises(ValueError, match="No staged changes to commit"):
        initialized_vcs.commit("Initial commit")


def test_commit_rejects_empty_message(initialized_vcs: TinyControlSystem, repo: Path) -> None:
    file_path = repo / "hello.txt"
    file_path.write_text("content\n", encoding="utf-8")
    initialized_vcs.add(str(file_path))

    with pytest.raises(ValueError, match="Commit message cannot be empty"):
        initialized_vcs.commit("   ")


# -----------------------
# Integration tests
# -----------------------

def test_init_add_commit_verify_workflow(repo: Path) -> None:
    ok, _ = TinyControlSystem.init(str(repo))
    assert ok is True
    vcs = TinyControlSystem(str(repo))

    vcs.config("user.name", "Boying")
    vcs.config("user.email", "boying@example.com")

    file_path = repo / "notes.txt"
    file_path.write_text("line one\nline two\n", encoding="utf-8")

    staged_hash = vcs.add(str(file_path))
    commit_hash = vcs.commit("Add notes")

    assert len(staged_hash) == 64
    assert len(commit_hash) == 64
    assert vcs._get_head_commit() == commit_hash

    commits = list(vcs.log())
    assert len(commits) == 1
    head_hash, head_commit = commits[0]
    assert head_hash == commit_hash
    assert head_commit["message"] == "Add notes"
    assert head_commit["author_name"] == "Boying"
    assert head_commit["author_email"] == "boying@example.com"
    assert head_commit["files"]["notes.txt"] == staged_hash

    status = vcs.status()
    assert "notes.txt" in status["staged"]
    assert status["modified"] == []
    assert status["untracked"] == []
    assert status["deleted"] == []

    diff_output = vcs.diff(str(file_path))
    assert diff_output == "No differences found."


def test_modify_after_commit_shows_status_and_diff(repo: Path) -> None:
    ok, _ = TinyControlSystem.init(str(repo))
    assert ok is True
    vcs = TinyControlSystem(str(repo))

    file_path = repo / "story.txt"
    file_path.write_text("alpha\nbeta\n", encoding="utf-8")
    vcs.add(str(file_path))
    vcs.commit("Add story")

    file_path.write_text("alpha\ngamma\n", encoding="utf-8")

    status = vcs.status()
    assert "story.txt" in status["modified"]

    diff_output = vcs.diff(str(file_path))
    assert "-beta" in diff_output
    assert "+gamma" in diff_output
