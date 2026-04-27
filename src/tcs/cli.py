# cli.py

import argparse


# -------------------------
# Command Handlers (stubs)
# -------------------------

def init_repo(args):
    print("Initializing repository...")


def status(args):
    print("Showing status...")


def add(args):
    print(f"Staging file: {args.file}")


def commit(args):
    print(f"Committing with message: {args.message}")


def log(args):
    print("Showing commit history...")


def diff(args):
    print("Showing diff...")


def config(args):
    print(f"Setting {args.key} to {args.value}")


def branch(args):
    if not any([args.name, args.delete, args.force_delete, args.rename]):
        print("Listing branches...")
    elif args.delete:
        print(f"Deleting branch: {args.delete}")
    elif args.force_delete:
        print(f"Force deleting branch: {args.force_delete}")
    elif args.rename:
        old, new = args.rename
        print(f"Renaming branch {old} -> {new}")
    elif args.name and args.commit:
        print(f"Creating branch {args.name} at commit {args.commit}")
    elif args.name:
        print(f"Creating branch {args.name}")


def switch(args):
    if args.create:
        print(f"Creating and switching to branch: {args.create}")
    else:
        print(f"Switching to: {args.target}")


# -------------------------
# Parser Builder
# -------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="tcs",
        description="Tiny Control System CLI"
    )

    subparsers = parser.add_subparsers(dest="command")

    # --- Repository ---
    p_init = subparsers.add_parser("init")
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
    p_diff.set_defaults(func=diff)

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

    p_switch.set_defaults(func=switch)

    return parser


# -------------------------
# Runner
# -------------------------

def run():
    parser = build_parser()
    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()