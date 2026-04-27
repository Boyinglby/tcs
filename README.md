# Tiny Control System

Tiny Control System, or `tcs`, is a small educational version control system written in Python. It stores repository metadata in a local `.tcs/` directory, stages file snapshots by SHA-256 hash, writes commit objects, tracks branches, supports checkout, and can perform fast-forward merges.

The core implementation is exposed through both a Python API and the packaged `tcs` console command.

## Features

- Initialize a repository with `.tcs/objects`, `.tcs/refs`, `.tcs/index`, `.tcs/config.json`, and a default `main` branch.
- Configure `user.name` and `user.email`.
- Stage files and store file contents as hashed objects.
- Create commits with parent links, author metadata, timestamps, and tracked file snapshots.
- Inspect repository status for staged, modified, untracked, and deleted files.
- Generate unified diffs against the latest committed version of a file.
- Walk commit history from `HEAD`.
- Create, list, delete, and checkout branches.
- Checkout specific commits in detached `HEAD` mode.
- Refuse unsafe checkout operations when uncommitted changes or conflicting untracked files are present.
- Fast-forward merge branches and refuse diverged histories.

## Project Layout

```text
.
|-- pyproject.toml
|-- README.md
|-- src/
|   |-- tcs/
|   |   |-- main.py
|   |   |-- cli.py
|   |   `-- core/
|   |       |-- core.py
|   |       `-- utils.py
`-- tests/
    `-- core/
        |-- test_core.py
        |-- test_branching.py
        `-- test_merge.py
```

## Requirements

- Python 3.8 or newer
- `pytest` for running the test suite

The project is packaged with `setuptools` and exposes the console script `tcs`.

## Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install pytest
```

If your PowerShell execution policy allows activation scripts, you can activate the environment first:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install pytest
```

## Core API Usage

```python
from tcs.core.core import TinyControlSystem

repo_path = "example-repo"

ok, message = TinyControlSystem.init(".", repo_path)
print(message)

vcs = TinyControlSystem(repo_path)
vcs.config("user.name", "Alice")
vcs.config("user.email", "alice@example.com")

with open(f"{repo_path}/notes.txt", "w", encoding="utf-8") as f:
    f.write("line one\nline two\n")

file_hash = vcs.add(f"{repo_path}/notes.txt")
commit_hash = vcs.commit("Add notes")

print(file_hash)
print(commit_hash)
print(vcs.status())
print(list(vcs.log()))
```

Branching example:

```python
vcs.create_branch("feature")
vcs.checkout_branch("feature")

with open(f"{repo_path}/notes.txt", "w", encoding="utf-8") as f:
    f.write("feature work\n")

vcs.add(f"{repo_path}/notes.txt")
vcs.commit("Update notes on feature")

vcs.checkout_branch("main")
vcs.merge("feature")
```

## CLI Usage

The package installs a `tcs` command. Commands operate on the current `.tcs` repository, and most commands discover the repository by walking up from the current directory.

```powershell
tcs init [directory]
tcs status
tcs add <file>
tcs commit -m <message>
tcs log
tcs diff [file]
tcs merge <source>
tcs config <key> <value>
tcs branch
tcs branch <name> [commit]
tcs branch -d <name>
tcs branch -D <name>
tcs branch -m <old> <new>
tcs switch <target>
tcs switch -c <name>
tcs switch [-f|--force] <target>
```

Example workflow:

```powershell
tcs init
tcs config user.name Alice
tcs config user.email alice@example.com
tcs add <file>
tcs commit -m <message>
tcs log
```

## Running Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The test suite covers repository initialization, config, staging, commits, status, diffs, branch checkout safety, detached `HEAD` behavior, ancestor detection, and fast-forward merge behavior.

## Notes

- Repository data is stored under `.tcs/` inside each initialized project.
- File and commit objects are addressed by SHA-256 hashes.
- Only fast-forward merges are supported today. Diverged branches are detected and refused.
- Supported config keys are `user.name` and `user.email`.
