from pathlib import Path
from typing import Callable

import pytest

from src.tcs.core.core import TinyControlSystem


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


@pytest.fixture()
def configured_vcs(initialized_vcs: TinyControlSystem) -> TinyControlSystem:
    initialized_vcs.config("user.name", "Test User")
    initialized_vcs.config("user.email", "test@example.com")
    return initialized_vcs


@pytest.fixture()
def make_commit(repo: Path) -> Callable[[TinyControlSystem, str, str, str], str]:
    def _make_commit(vcs: TinyControlSystem, filename: str, content: str, message: str) -> str:
        file_path = repo / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        vcs.add(str(file_path))
        return vcs.commit(message)

    return _make_commit
