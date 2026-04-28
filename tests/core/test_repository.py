import json
from pathlib import Path

from src.tcs.core.core import TinyControlSystem


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
