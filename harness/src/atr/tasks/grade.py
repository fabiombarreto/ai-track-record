"""Grade one run inside a task's separate verifier.

Copied into each generated task as tests/grading/grade.py and run by
tests/test.sh. Only the run's changes cross from the agent: the git diff of
/app against its "base" tag. Workflows such as relay work in git worktrees
under /app/.worktrees and leave their changes uncommitted there, so every
file a worktree changed against "base" is first copied over /app, and the
worktree wins. This happens here, not in the agent, so a run stopped by a
timeout is still graded with its partial code. Other files ignored by git,
such as caches, never reach the grader. The diff is applied to a clean copy
of the base commit, and the pristine existing tests plus the hidden tests run
from /grading, outside the agent's code, so no conftest.py the agent wrote is
loaded.

Writes /logs/verifier/reward.json:
- reward: 1.0 when every hidden and existing test passes, otherwise 0.0
- criteria_satisfied: share of acceptance criteria whose tests all pass
- existing_tests_pass: 1.0 when every existing test still passes
- new_static_findings: findings of the task's static analysis tools that the
  run introduced (only when the task declares tools); the list is in
  details.json
"""

import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

APP = Path("/app")
PRISTINE = Path("/pristine")
WORK = Path("/work")
GRADING = Path("/grading")
OUT = Path("/logs/verifier")
CRITERION = re.compile(r"^test_ac(\d+)_")


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, **kwargs)


def copy_worktree_changes(worktree: Path) -> dict:
    """Copy every file the worktree changed against "base" over /app."""
    staged = run(["git", "-C", str(worktree), "add", "-A"])
    if staged.returncode:
        raise RuntimeError(f"git add failed: {staged.stderr}")
    listed = run(
        ["git", "-C", str(worktree), "diff", "--cached", "--name-status", "--no-renames", "-z", "base"]
    )
    if listed.returncode:
        raise RuntimeError(f"git diff against base failed: {listed.stderr}")
    fields = listed.stdout.split("\0")
    copied, deleted = 0, 0
    for status, path in zip(fields[0::2], fields[1::2], strict=False):
        target = APP / path
        if status == "D":
            if target.is_file() or target.is_symlink():
                target.unlink()
                deleted += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file() or target.is_symlink():
            target.unlink()
        shutil.copy2(worktree / path, target, follow_symlinks=False)
        copied += 1
    return {"copied": copied, "deleted": deleted}


def collect_worktrees() -> list[dict]:
    root = APP / ".worktrees"
    worktrees = sorted(p for p in root.glob("*") if (p / ".git").exists()) if root.exists() else []
    report = []
    for worktree in worktrees:
        entry = {"worktree": str(worktree.relative_to(APP))}
        try:
            entry |= copy_worktree_changes(worktree) | {"collected": True, "error": ""}
        except (OSError, RuntimeError) as error:
            entry |= {"collected": False, "error": str(error)[-2000:]}
        report.append(entry)
    return report


def extract_changes() -> str:
    staged = run(["git", "-C", str(APP), "add", "-A"])
    if staged.returncode:
        raise RuntimeError(f"git add failed: {staged.stderr}")
    # Worktrees were collected above; they never cross as nested repositories.
    unstaged = run(
        ["git", "-C", str(APP), "rm", "-r", "-q", "--cached", "--ignore-unmatch", ".worktrees"]
    )
    if unstaged.returncode:
        raise RuntimeError(f"git rm of .worktrees failed: {unstaged.stderr}")
    diff = run(["git", "-C", str(APP), "diff", "--cached", "--binary", "base"])
    if diff.returncode:
        raise RuntimeError(f"git diff against base failed: {diff.stderr}")
    return diff.stdout


def prepare_workspace(changes: str, project: Path) -> None:
    shutil.copytree(PRISTINE, WORK, symlinks=True)
    patch = OUT / "changes.patch"
    patch.write_text(changes)
    if changes.strip():
        applied = run(["git", "apply", "--whitespace=nowarn", str(patch)], cwd=WORK)
        if applied.returncode:
            raise RuntimeError(f"the run's changes do not apply: {applied.stderr}")
    synced = run(["uv", "sync", "--frozen", "--no-install-project"], cwd=project)
    if synced.returncode:
        raise RuntimeError(f"dependencies do not install: {synced.stderr[-2000:]}")


def ruff_findings(project: Path) -> list[dict]:
    """Findings of ruff with the project's own configuration."""
    result = run(
        ["ruff", "check", "--output-format", "json", "--no-cache", "--exit-zero", "."], cwd=project
    )
    if result.returncode:
        raise RuntimeError(f"ruff failed: {result.stderr[-1000:]}")
    return [
        {
            "file": str(Path(finding["filename"]).relative_to(project)),
            "rule": finding["code"] or "syntax-error",
            "message": finding["message"],
            "line": finding["location"]["row"],
        }
        for finding in json.loads(result.stdout or "[]")
    ]


ANALYZERS = {"ruff": ruff_findings}


def new_static_findings(tools: list[str], base: Path, after: Path) -> list[dict]:
    """Findings present after the run and absent on the base commit.

    Findings are matched by file, rule and message, not by line, since the
    run's changes move lines around.
    """
    new = []
    for tool in tools:
        before = Counter((f["file"], f["rule"], f["message"]) for f in ANALYZERS[tool](base))
        for finding in ANALYZERS[tool](after):
            key = (finding["file"], finding["rule"], finding["message"])
            if before[key]:
                before[key] -= 1
            else:
                new.append({"tool": tool, **finding})
    return new


def run_tests(project: Path) -> list[dict]:
    junit = OUT / "junit.xml"
    result = run(
        [
            "pytest",
            "-c", str(GRADING / "pytest.ini"),
            "--rootdir", str(GRADING),
            "-p", "no:cacheprovider",
            "-q",
            f"--junitxml={junit}",
            str(GRADING / "existing"),
            str(GRADING / "hidden"),
        ],
        cwd=GRADING,
        env={**os.environ, "PYTHONPATH": str(project)},
    )
    (OUT / "pytest.txt").write_text(result.stdout + result.stderr)
    if not junit.exists():
        raise RuntimeError("pytest produced no report; see pytest.txt")

    tests = []
    for case in ET.parse(junit).getroot().iter("testcase"):
        outcome = "passed"
        for child in case:
            if child.tag in ("failure", "error", "skipped"):
                outcome = "skipped" if child.tag == "skipped" else "failed"
        suite = "hidden" if "hidden" in case.get("classname", "") else "existing"
        tests.append({"suite": suite, "name": case.get("name"), "outcome": outcome})
    return tests


def score(tests: list[dict], criteria: list[str]) -> dict:
    hidden = [test for test in tests if test["suite"] == "hidden"]
    existing = [test for test in tests if test["suite"] == "existing"]
    by_criterion: dict[str, list[str]] = {criterion: [] for criterion in criteria}
    for test in hidden:
        match = CRITERION.match(test["name"])
        if match and f"AC-{match.group(1)}" in by_criterion:
            by_criterion[f"AC-{match.group(1)}"].append(test["outcome"])
    satisfied = [
        criterion
        for criterion, outcomes in by_criterion.items()
        if outcomes and all(outcome == "passed" for outcome in outcomes)
    ]
    hidden_ok = bool(hidden) and all(test["outcome"] == "passed" for test in hidden)
    existing_ok = bool(existing) and all(test["outcome"] == "passed" for test in existing)
    return {
        "reward": 1.0 if hidden_ok and existing_ok else 0.0,
        "criteria_satisfied": round(len(satisfied) / len(criteria), 4),
        "existing_tests_pass": 1.0 if existing_ok else 0.0,
        "_satisfied": satisfied,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    config = json.loads((GRADING / "task.json").read_text())
    criteria = config["criteria"]
    project = WORK / config.get("project_dir", ".")
    details: dict = {"criteria": criteria}
    rewards = {"reward": 0.0, "criteria_satisfied": 0.0, "existing_tests_pass": 0.0}
    try:
        if not (APP / ".git").exists():
            raise RuntimeError("the agent's /app repository was not transferred")
        run(["git", "config", "--global", "--add", "safe.directory", "*"])
        details["worktrees"] = collect_worktrees()
        prepare_workspace(extract_changes(), project)
        tests = run_tests(project)
        result = score(tests, criteria)
        details["tests"] = tests
        details["criteria_satisfied"] = result.pop("_satisfied")
        rewards = result
    except Exception as error:  # every failure still produces a reward
        details["error"] = str(error)
    tools = config.get("static_analysis") or []
    if tools and "error" not in details:
        try:
            base = PRISTINE / config.get("project_dir", ".")
            findings = new_static_findings(tools, base, project)
            details["new_static_findings"] = findings
            rewards["new_static_findings"] = float(len(findings))
        except Exception as error:  # static analysis never changes the reward
            details["static_analysis_error"] = str(error)
    (OUT / "reward.json").write_text(json.dumps(rewards, indent=2))
    (OUT / "details.json").write_text(json.dumps(details, indent=2))
    print(json.dumps(rewards))
    if "error" in details:
        print(f"grading error: {details['error']}")


if __name__ == "__main__":
    main()
