import os

from .branch import BranchOperations
from .checkout import CheckoutOperations
from .commit import CommitOperations
from .config import ConfigOperations
from .diff import DiffOperations
from .index import IndexOperations
from .merge import MergeOperations
from .repository import RepositoryOperations
from .status import StatusOperations


class TinyControlSystem(
    RepositoryOperations,
    ConfigOperations,
    IndexOperations,
    CommitOperations,
    StatusOperations,
    DiffOperations,
    CheckoutOperations,
    BranchOperations,
    MergeOperations,
):
    """
    A tiny version control system.

    This facade keeps the existing CLI and test API intact while delegating
    repository behavior to focused operation classes.
    """

    REPO_DIR_NAME = ".tcs"
    OBJECTS_DIR_NAME = "objects"
    REFS_DIR_NAME = "refs"
    HEADS_DIR_NAME = "heads"
    INDEX_FILE_NAME = "index"
    CONFIG_FILE_NAME = "config.json"
    HEAD_FILE_NAME = "HEAD"
    DEFAULT_BRANCH = "main"

    def __init__(self, root_dir: str) -> None:
        """
        Create a TCS object bound to an existing or future repository root.
        """
        self.root_dir: str = os.path.abspath(root_dir)
        self.tcs_dir: str = os.path.join(self.root_dir, self.REPO_DIR_NAME)
        self.objects_dir: str = os.path.join(self.tcs_dir, self.OBJECTS_DIR_NAME)
        self.refs_dir: str = os.path.join(self.tcs_dir, self.REFS_DIR_NAME)
        self.index_path: str = os.path.join(self.tcs_dir, self.INDEX_FILE_NAME)
        self.config_path: str = os.path.join(self.tcs_dir, self.CONFIG_FILE_NAME)
        self.refs_heads_dir: str = os.path.join(self.refs_dir, self.HEADS_DIR_NAME)
        self.head_path: str = os.path.join(self.refs_dir, self.HEAD_FILE_NAME)


__all__ = [
    "TinyControlSystem",
]
