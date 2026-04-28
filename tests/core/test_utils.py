from pathlib import Path

from src.tcs.core.utils import calculate_hash, list_files, read_file, write_file


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
