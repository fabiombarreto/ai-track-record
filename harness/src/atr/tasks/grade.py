"""Grade one run inside a task's separate verifier.

Copied into each generated task as tests/grading/grade.py and run by
tests/test.sh. Only the run's changes cross from the agent: the git diff of
/app against its "base" tag. Files ignored by git, such as caches or relay's
worktrees, never reach the grader. The diff is applied to a clean copy of the
base commit, and the pristine existing tests plus the hidden tests run from
/grading, outside the agent's code, so no conftest.py the agent wrote is
loaded.

Writes /logs/verifier/reward.json:
- reward: 1.0 when every hidden and existing test passes, otherwise 0.0
- criteria_satisfied: share of acceptance criteria whose tests all pass
- existing_tests_pass: 1.0 when every existing test still passes
"""

import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

APP = Path("/app")
PRISTINE = Path("/pristine")
WORK = Path("/work")
GRADING = Path("/grading")
OUT = Path("/logs/verifier")
CRITERION = re.compile(r"^test_ac(\d+)_")


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, **kwargs)


def extract_changes() -> str:
    if not (APP / ".git").exists():
        raise RuntimeError("the agent's /app repository was not transferred")
    run(["git", "config", "--global", "--add", "safe.directory", "*"])
    staged = run(["git", "-C", str(APP), "add", "-A"])
    if staged.returncode:
        raise RuntimeError(f"git add failed: {staged.stderr}")
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
        prepare_workspace(extract_changes(), project)
        tests = run_tests(project)
        result = score(tests, criteria)
        details["tests"] = tests
        details["criteria_satisfied"] = result.pop("_satisfied")
        rewards = result
    except Exception as error:  # every failure still produces a reward
        details["error"] = str(error)
    (OUT / "reward.json").write_text(json.dumps(rewards, indent=2))
    (OUT / "details.json").write_text(json.dumps(details, indent=2))
    print(json.dumps(rewards))
    if "error" in details:
        print(f"grading error: {details['error']}")


if __name__ == "__main__":
    main()
