import argparse
import os
import sys
from typing import Optional, Sequence

from .core.core import TinyControlSystem


def find_repository_root(start_dir: str) -> Optional[str]:
    current = os.path.abspath(start_dir)

    while True:
        if os.path.isdir(os.path.join(current, TinyControlSystem.REPO_DIR_NAME)):
            return current

        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def get_vcs() -> TinyControlSystem:
    root = find_repository_root(os.getcwd())
    if root is None:
        raise RuntimeError("Not a TCS repository. Run 'tcs init' first.")
    return TinyControlSystem(root)


def print_paths(title: str, paths: Sequence[str]) -> None:
    if not paths:
        return

    print(f"{title}:")
    for path in sorted(paths):
        print(f"  {path}")


def init_repo(args: argparse.Namespace) -> None:
    ok, message = TinyControlSystem.init(os.getcwd(), args.directory)
    if not ok:
        raise RuntimeError(message)
    print(message)


def status(args: argparse.Namespace) -> None:
    vcs = get_vcs()
    repo_status = vcs.status()
    current_branch = vcs.current_branch()
    head_commit = vcs._get_head_commit()

    if current_branch:
        print(f"On branch {current_branch}")
    elif head_commit:
        print(f"HEAD detached at {head_commit}")
    else:
        print("No commits yet")

    tracked = repo_status["staged"]
    if tracked:
        print("Tracked files:")
        for path, file_hash in sorted(tracked.items()):
            print(f"  {path} {file_hash}")

    print_paths("Modified files", repo_status["modified"])
    print_paths("Deleted files", repo_status["deleted"])
    print_paths("Untracked files", repo_status["untracked"])

    if not any(
        [
            repo_status["modified"],
            repo_status["deleted"],
            repo_status["untracked"],
        ]
    ):
        print("Working tree clean")


def add(args: argparse.Namespace) -> None:
    vcs = get_vcs()
    file_hash = vcs.add(args.file)
    print(f"Staged {args.file} {file_hash}")


def commit(args: argparse.Namespace) -> None:
    vcs = get_vcs()
    commit_hash = vcs.commit(args.message)
    branch_name = vcs.current_branch() or "detached HEAD"
    print(f"[{branch_name} {commit_hash}] {args.message.strip()}")


def log(args: argparse.Namespace) -> None:
    vcs = get_vcs()
    commits = list(vcs.log())

    if not commits:
        print("No commits yet.")
        return

    for index, (commit_hash, commit_obj) in enumerate(commits):
        if index:
            print()

        author_name = commit_obj.get("author_name") or "Unknown"
        author_email = commit_obj.get("author_email") or "unknown"

        print(f"commit {commit_hash}")
        print(f"Author: {author_name} <{author_email}>")
        print(f"Date:   {commit_obj.get('timestamp', '')}")
        print()
        print(f"    {commit_obj.get('message', '')}")


def diff(args: argparse.Namespace) -> None:
    vcs = get_vcs()
    print(vcs.diff(args.file))


def config(args: argparse.Namespace) -> None:
    vcs = get_vcs()
    print(vcs.config(args.key, args.value))


def branch(args: argparse.Namespace) -> None:
    vcs = get_vcs()

    if not any([args.name, args.delete, args.force_delete, args.rename]):
        current_branch = vcs.current_branch()
        for branch_name in vcs.list_branches():
            marker = "*" if branch_name == current_branch else " "
            print(f"{marker} {branch_name}")
        return

    if args.delete:
        print(vcs.delete_branch(args.delete))
        return

    if args.force_delete:
        print(vcs.delete_branch(args.force_delete))
        return

    if args.rename:
        old_name, new_name = args.rename
        print(vcs.rename_branch(old_name, new_name))
        return

    print(vcs.create_branch(args.name, args.commit))


def switch(args: argparse.Namespace) -> None:
    vcs = get_vcs()

    if args.create:
        print(vcs.create_branch(args.create))
        print(vcs.checkout_branch(args.create, force=args.force))
        return

    if not args.target:
        raise ValueError("switch requires a branch name or commit hash.")

    branch_path = os.path.join(vcs.refs_heads_dir, args.target)
    if os.path.exists(branch_path):
        print(vcs.checkout_branch(args.target, force=args.force))
    else:
        print(vcs.checkout_commit(args.target, force=args.force))


def merge(args: argparse.Namespace) -> None:
    vcs = get_vcs()
    print(vcs.merge(args.source))


# -------------------------
# Parser Builder
# -------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tcs",
        description="Tiny Control System CLI",
    )

    subparsers = parser.add_subparsers(dest="command")

    # --- Repository ---
    p_init = subparsers.add_parser("init")
    p_init.add_argument("directory", nargs="?")
    p_init.set_defaults(func=init_repo)

    p_status = subparsers.add_parser("status")
    p_status.set_defaults(func=status)

    # --- Version Control ---
    p_add = subparsers.add_parser("add")
    p_add.add_argument("file")
    p_add.set_defaults(func=add)

    p_commit = subparsers.add_parser("commit")
    p_commit.add_argument("-m", "--message", required=True)
    p_commit.set_defaults(func=commit)

    p_log = subparsers.add_parser("log")
    p_log.set_defaults(func=log)

    p_diff = subparsers.add_parser("diff")
    p_diff.add_argument("file", nargs="?")
    p_diff.set_defaults(func=diff)

    p_merge = subparsers.add_parser("merge")
    p_merge.add_argument("source")
    p_merge.set_defaults(func=merge)

    # --- Config ---
    p_config = subparsers.add_parser("config")
    p_config.add_argument("key")
    p_config.add_argument("value")
    p_config.set_defaults(func=config)

    # --- Branch ---
    p_branch = subparsers.add_parser("branch")

    p_branch.add_argument("name", nargs="?")
    p_branch.add_argument("commit", nargs="?")

    p_branch.add_argument("-d", dest="delete")
    p_branch.add_argument("-D", dest="force_delete")
    p_branch.add_argument("-m", dest="rename", nargs=2)

    p_branch.set_defaults(func=branch)

    # --- Switch ---
    p_switch = subparsers.add_parser("switch")

    p_switch.add_argument("target", nargs="?")
    p_switch.add_argument("-c", dest="create")
    p_switch.add_argument("-f", "--force", action="store_true")

    p_switch.set_defaults(func=switch)

    return parser


# -------------------------
# Runner
# -------------------------

def run(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    try:
        args.func(args)
    except SystemExit:
        raise
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0
