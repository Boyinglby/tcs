"""Console script entry point for Tiny Control System."""

from .cli import run


def main() -> None:
    """
    Run the CLI and exit with its returned status code.
    """
    raise SystemExit(run())
