import json
from pathlib import Path

from src.tcs.core.core import TinyControlSystem


def test_config_updates_repository_settings(initialized_vcs: TinyControlSystem) -> None:
    assert initialized_vcs.config("user.name", "Alice") == "Set user.name to Alice"
    assert initialized_vcs.config("user.email", "alice@example.com") == "Set user.email to alice@example.com"

    config = json.loads(Path(initialized_vcs.config_path).read_text(encoding="utf-8"))
    assert config["user.name"] == "Alice"
    assert config["user.email"] == "alice@example.com"
