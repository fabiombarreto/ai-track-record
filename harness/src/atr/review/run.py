"""Independent code review of one graded run (GRD-04, D-018).

Usage: python -m atr.review.run <trial dir> --task <built task dir> [--force]

The reviewer is pinned and is not part of any workflow under test: Claude
Code's built-in `/code-review` at a fixed effort and model, run through a
pinned Agent SDK in its own container, with web tools disabled. It reviews the
run's graded changes (the verifier's changes.patch) applied to a clean copy of
the base commit, so every configuration is reviewed the same way. Workflow
working files are left out of the diff, though the base's specification stays
readable as context.

Needs ANTHROPIC_API_KEY in the environment. Writes <trial>/review/review.json,
with the findings, and the reviewer's transcript next to it.
"""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

SDK_VERSION = "0.2.170"  # the same Agent SDK, and so Claude Code, as the runs
MODEL = "claude-sonnet-5-5"
EFFORT = "high"
IMAGE = f"atr-reviewer:{SDK_VERSION}"
# Relay's plans, reports and specification status updates: workflow working
# files, not product changes. Vanilla writes none of them.
WORKFLOW_FILES = ("PRPs/*",)


def git(workspace: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(workspace), *args], check=True, capture_output=True, text=True
    ).stdout


def build_workspace(task_dir: Path, patch: Path, workspace: Path) -> list[str]:
    """Base commit as HEAD and the run's product changes in the working tree."""
    shutil.copytree(task_dir / "tests" / "pristine", workspace, symlinks=True)
    git(workspace, "init", "-q", "-b", "main")
    git(workspace, "add", "-A")
    git(workspace, "-c", "user.name=atr", "-c", "user.email=atr@localhost", "commit", "-q", "-m", "Base commit")
    if patch.stat().st_size:
        excludes = [f"--exclude={pattern}" for pattern in WORKFLOW_FILES]
        git(workspace, "apply", "--whitespace=nowarn", *excludes, str(patch))
    status = git(workspace, "status", "--porcelain", "--untracked-files=all")
    return [line[3:] for line in status.splitlines()]


def ensure_image() -> None:
    present = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True)
    if present.returncode:
        subprocess.run(
            ["docker", "build", "-q", "--build-arg", f"SDK_VERSION={SDK_VERSION}", "-t", IMAGE,
             str(Path(__file__).parent)],
            check=True,
        )


def run_reviewer(workspace: Path, out_dir: Path) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY must be set")
    ensure_image()
    subprocess.run(
        [
            "docker", "run", "--rm",
            "-e", "ANTHROPIC_API_KEY",
            "-e", "IS_SANDBOX=1",
            "-e", "DISABLE_AUTOUPDATER=1",
            "-e", "DISABLE_ERROR_REPORTING=1",
            "-e", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1",
            "-v", f"{workspace}:/review",
            "-v", f"{out_dir}:/out",
            IMAGE,
            "python", "/opt/atr/reviewer.py", "--model", MODEL, "--effort", EFFORT,
        ],
        check=False,
    )
    findings_file = out_dir / "findings.json"
    if not findings_file.exists():
        raise RuntimeError("the reviewer produced no findings file; see messages.jsonl")
    return json.loads(findings_file.read_text())


def review(trial_dir: Path, task_dir: Path, force: bool = False) -> Path:
    out_dir = trial_dir / "review"
    target = out_dir / "review.json"
    if target.exists() and not force:
        return target
    patch = trial_dir / "verifier" / "changes.patch"
    if not patch.exists():
        raise SystemExit(f"no graded changes at {patch}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    with tempfile.TemporaryDirectory(prefix="atr-review-") as temp:
        workspace = Path(temp) / "workspace"
        changed = build_workspace(task_dir, patch, workspace)
        if changed:
            result = run_reviewer(workspace, out_dir)
        else:
            result = {"findings": [], "turns": []}

    findings = result["findings"]
    data = {
        "reviewer": {"tool": "claude-code /code-review", "sdk": SDK_VERSION, "model": MODEL, "effort": EFFORT},
        "reviewed_at": datetime.now(UTC).isoformat(),
        "excluded": list(WORKFLOW_FILES),
        "changed_files": changed,
        "completed": findings is not None,
        "n_findings": None if findings is None else len(findings),
        "findings": findings or [],
        "cost_usd_per_turn": [turn.get("total_cost_usd") for turn in result["turns"]],
    }
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("trial_dir", type=Path)
    parser.add_argument("--task", type=Path, required=True, help="the built Harbor task folder")
    parser.add_argument("--force", action="store_true", help="review again even if done")
    args = parser.parse_args()
    target = review(args.trial_dir.resolve(), args.task.resolve(), force=args.force)
    data = json.loads(target.read_text())
    print(f"{target}: {data['n_findings']} findings, cost per turn {data['cost_usd_per_turn']}")


if __name__ == "__main__":
    main()
