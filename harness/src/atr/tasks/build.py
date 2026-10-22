"""Build a Harbor task folder from a task authored as a pull request.

Usage: python -m atr.tasks.build <task manifest .toml> [--out <directory>]

The manifest names a target repository, a base ref and a solution ref. The
base ref becomes the agent's starting point, as a snapshot with no other git
history. The hidden tests come from the solution ref, and the rest of the
solution's changes become the reference solution that Harbor's oracle agent
applies. Templates come from the "templates" folder next to the manifest.
"""

import argparse
import io
import json
import os
import shutil
import subprocess
import tarfile
import tomllib
from pathlib import Path

GRADER = Path(__file__).with_name("grade.py")

INSTRUCTION = (
    "Implement the feature specified in `{spec}`. "
    "Keep the existing tests passing. "
    "Stop when the feature is complete.\n"
)

TEST_SH = """#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
python3 /grading/grade.py
"""

SOLVE_SH = """#!/bin/bash
set -euo pipefail
git -C /app apply --whitespace=nowarn "$(dirname "$0")/reference.patch"
"""

TASK_TOML = """schema_version = "1.4"

artifacts = [{{ source = "/app", exclude = [".venv", "__pycache__", ".pytest_cache"] }}]

[task]
name = "atr/{target}-{task_id}"
description = "{title}"
authors = []
keywords = []

[metadata]
difficulty = "{difficulty}"
category = "{category}"
tags = []

[verifier]
timeout_sec = {verifier_timeout}.0
environment_mode = "separate"

[agent]
timeout_sec = {agent_timeout}.0

[environment]
build_timeout_sec = 1200.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
gpus = 0
"""


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True
    ).stdout


def export_tree(repo: Path, ref: str, destination: Path) -> None:
    """Write the files of `ref` to `destination`, without any git metadata."""
    archive = git(repo, "archive", "--format=tar", ref)
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(destination, filter="data")


def write(path: Path, content: str | bytes, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content)
    if executable:
        path.chmod(0o755)


def build(manifest_path: Path, out_root: Path) -> Path:
    manifest = tomllib.loads(manifest_path.read_text())
    target, task = manifest["target"], manifest["task"]
    repo = Path(os.path.expanduser(target["repository"]))
    templates = manifest_path.parent / "templates"
    base, solution = task["base_ref"], task["solution_ref"]

    out = out_root / target["name"] / task["id"]
    if out.exists():
        shutil.rmtree(out)

    environment = out / "environment"
    export_tree(repo, base, environment / "app")
    shutil.copy(templates / "agent.Dockerfile", environment / "Dockerfile")
    shutil.copy(templates / "agent-compose.yaml", environment / "docker-compose.yaml")

    tests = out / "tests"
    export_tree(repo, base, tests / "pristine")
    shutil.copy(templates / "verifier.Dockerfile", tests / "Dockerfile")
    shutil.copy(templates / "verifier-compose.yaml", tests / "docker-compose.yaml")
    write(tests / "test.sh", TEST_SH, executable=True)
    grading = tests / "grading"
    grading.mkdir()
    shutil.copy(GRADER, grading / "grade.py")
    shutil.copy(templates / "grading-pytest.ini", grading / "pytest.ini")
    for path in task["hidden_tests"]:
        write(grading / "hidden" / Path(path).name, git(repo, "show", f"{solution}:{path}"))
    for path in task["existing_tests"]:
        write(grading / "existing" / Path(path).name, git(repo, "show", f"{base}:{path}"))
    write(grading / "task.json", json.dumps({"criteria": task["criteria"]}, indent=2))

    excluded = [f":(exclude){path}" for path in task["hidden_tests"]]
    patch = git(repo, "diff", "--binary", base, solution, "--", ".", *excluded)
    write(out / "solution" / "reference.patch", patch)
    write(out / "solution" / "solve.sh", SOLVE_SH, executable=True)

    write(out / "instruction.md", INSTRUCTION.format(spec=task["spec"]))
    write(
        out / "task.toml",
        TASK_TOML.format(
            target=target["name"],
            task_id=task["id"],
            title=task["title"],
            difficulty=task["difficulty"],
            category=task["category"],
            agent_timeout=task["agent_timeout_sec"],
            verifier_timeout=task["verifier_timeout_sec"],
        ),
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(os.environ.get("ATR_DATA_DIR", "~/atr/data")).expanduser() / "tasks",
    )
    args = parser.parse_args()
    print(build(args.manifest.resolve(), args.out))


if __name__ == "__main__":
    main()
