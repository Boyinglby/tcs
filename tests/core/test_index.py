import json
from pathlib import Path

from src.tcs.core.core import TinyControlSystem


def test_add_stages_file_and_stores_object(initialized_vcs: TinyControlSystem, repo: Path) -> None:
    repo_file = repo / "hello.txt"
    repo_file.write_text("hello\n", encoding="utf-8")

    file_hash = initialized_vcs.add(str(repo_file))
    assert len(file_hash) == 64

    index = json.loads((repo / ".tcs" / "index").read_text(encoding="utf-8"))
    assert index["hello.txt"] == file_hash
    assert (repo / ".tcs" / "objects" / file_hash).is_file()
