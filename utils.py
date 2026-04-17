import os
import hashlib
from typing import Any, Dict, Iterator, Optional, Tuple, List

def read_file(file_path: str) -> bytes:
    """
    Read a file as raw bytes.

    Parameters:
        file_path (str): Path to the file to read.

    Returns:
        bytes: File content as bytes.

    """
    with open(file_path, "rb") as f:
        return f.read()


def write_file(file_path: str, content: bytes) -> None:
    """
    Write raw bytes to a file.

    Parameters:
        file_path (str): Path to the file to write.
        content (bytes): Content to write.

    Returns:
        None

    """
    with open(file_path, "wb") as f:
        f.write(content)


def calculate_hash(content: bytes) -> str:
    """
    Calculate a SHA-256 hash for the given content.

    Parameters:
        content (bytes): Input bytes to hash.

    Returns:
        str: Hexadecimal SHA-256 hash string.
    """
    return hashlib.sha256(content).hexdigest()


def list_files(directory: str) -> Iterator[str]:
    """
    Recursively yield all file paths inside a directory.

    Parameters:
        directory (str): Root directory to scan.

    Returns:
        Iterator[str]: Iterator over absolute file paths.

    Raises:
        OSError: If the directory cannot be traversed.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            yield os.path.join(root, file)
