"""Flag protocol steps a workflow skipped without notice (GRD-09, D-051).

Usage: python -m atr.checks.skipped_steps <trial dir>...

Skipping a step is not a metric: a run may skip what it judges unnecessary,
and the grades show whether that was right. This check records which steps of
relay's own protocol each phase skipped and whether the run's final summary
mentions them. A step skipped without mention is flagged for human review. The
flag never enters a grade.

Relay 0.47.0's protocol, per phase, as /relay-execute runs it:
plan (with its review), worktree, tests first (when the project declares
tdd: true), implementation (with its code review), docs sync (when docs_sync:
true), tests after (when tdd: false), test run and test review. A step counts
as done when relay's orchestrator-run.json logs it with a passing outcome or
when the step's own record exists, such as the docs sync manifest. A phase that
halted is checked only up to the halt, since a halt is an outcome, not a skip.
"Mentioned" is a keyword match on the summary, which is why the result is a
flag for review and not a verdict.

Writes <trial>/checks/skipped_steps.json. Runs of other workflows have no
protocol to check.
"""

import argparse
import json
import re
from pathlib import Path

PASSING = re.compile(r"^(APPROVED|CREATED|GREEN|IMPLEMENTATION_COMPLETE|OK|COMPLETE)", re.I)

# step -> (orchestrator stages that record it, artifact under the feature's
# reports folder that proves it, words that mention it in the summary)
STEPS: dict[str, tuple[tuple[str, ...], str | None, tuple[str, ...]]] = {
    "plan": (("plan",), None, ("plan",)),
    "worktree": (("worktree",), None, ("worktree",)),
    "tests_first": (("tdd",), None, ("test-first", "tdd", "test pair", "test-writer", "test writer")),
    "implementation": (("implement", "code_review"), None, ("implement",)),
    "docs_sync": (("docs_sync",), "docs-update.md", ("docs-sync", "docs sync", "docs_sync", "docs-updater")),
    "tests_after": (("test_after",), None, ("test-after", "test after", "tests after")),
    "test_run": (("test",), "run.json", ("test run", "pytest", "suite")),
    "test_review": (("test_review",), "test-review.json", ("test review", "test-review", "post-green")),
}


def frontmatter_flags(methodology: Path) -> dict[str, bool]:
    text = methodology.read_text() if methodology.exists() else ""
    flags = {}
    for key in ("tdd", "docs_sync"):
        match = re.search(rf"^{key}:\s*(true|false)", text, re.M)
        flags[key] = bool(match) and match.group(1) == "true"
    return flags


def expected_steps(flags: dict[str, bool]) -> list[str]:
    steps = ["plan", "worktree"]
    steps += ["tests_first"] if flags["tdd"] else []
    steps += ["implementation"]
    steps += ["docs_sync"] if flags["docs_sync"] else []
    steps += [] if flags["tdd"] else ["tests_after"]
    return steps + ["test_run", "test_review"]


def report_dirs(app: Path) -> list[Path]:
    """Relay's report folders, in the main tree and in every worktree."""
    roots = [app] + sorted(p for p in (app / ".worktrees").glob("*") if p.is_dir())
    return [d for root in roots for d in sorted((root / "PRPs" / "reports").glob("*")) if d.is_dir()]


def orchestrator_log(dirs: list[Path]) -> tuple[list[dict], str | None]:
    """The fullest orchestrator log among the report folders, and its outcome."""
    best: tuple[list[dict], str | None] = ([], None)
    for folder in dirs:
        record = folder / "orchestrator-run.json"
        if record.exists():
            data = json.loads(record.read_text())
            log = data.get("phases") or data.get("orchestrator_run_log") or []
            if len(log) >= len(best[0]):
                best = (log, data.get("outcome"))
    return best


def check(trial: Path) -> dict:
    config = json.loads((trial / "config.json").read_text())
    prompt = ((config.get("agent") or {}).get("kwargs") or {}).get("prompt") or ""
    if not prompt.startswith("/relay:"):
        return {"workflow": None, "applies": False, "flagged": False, "skipped": []}

    app = trial / "artifacts" / "app"
    flags = frontmatter_flags(app / "docs" / "context" / "methodology.md")
    dirs = report_dirs(app)
    log, outcome = orchestrator_log(dirs)
    result_file = trial / "agent" / "result.json"
    summary = str(json.loads(result_file.read_text()).get("result") or "") if result_file.exists() else ""
    summary_lower = summary.lower()

    phases = sorted({e["phase"] for e in log if isinstance(e.get("phase"), int)})
    steps_report, skipped = [], []
    for phase in phases:
        entries = [e for e in log if e.get("phase") == phase]
        complete = any(e.get("status") == "complete" for e in entries)
        due = expected_steps(flags)
        if not complete:
            # A phase that halted: only the steps up to the last one it reached
            # were due, and that last one is where it stopped.
            reached = [i for i, step in enumerate(due)
                       if any(e.get("stage") in STEPS[step][0] for e in entries)]
            due = due[: max(reached) + 1] if reached else []
        for step in due:
            stages, artifact, words = STEPS[step]
            recorded = [e for e in entries if e.get("stage") in stages]
            # The last attempt decides: a retry may follow CHANGES_REQUESTED.
            passed = bool(recorded) and bool(PASSING.match(str(recorded[-1].get("outcome") or "")))
            by_artifact = artifact is not None and any((d / artifact).exists() for d in dirs)
            done = passed or (by_artifact and complete)
            if not done and not complete and step == due[-1]:
                steps_report.append({"phase": phase, "step": step, "status": "halted",
                                     "outcomes": [e.get("outcome") for e in recorded]})
                continue
            status = "done" if done else ("deviated" if recorded else "skipped")
            entry = {"phase": phase, "step": step, "status": status,
                     "outcomes": [e.get("outcome") for e in recorded]}
            if status != "done":
                entry["mentioned"] = any(word in summary_lower for word in words)
                skipped.append(entry)
            steps_report.append(entry)
    return {
        "workflow": "relay",
        "applies": True,
        "methodology": flags,
        "orchestrator_outcome": outcome,
        "phases": phases,
        "steps": steps_report,
        "skipped": skipped,
        "flagged": any(not entry["mentioned"] for entry in skipped),
        "no_record": not log,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("trial_dirs", type=Path, nargs="+")
    args = parser.parse_args()
    for trial in args.trial_dirs:
        result = check(trial)
        out = trial / "checks"
        out.mkdir(exist_ok=True)
        (out / "skipped_steps.json").write_text(json.dumps(result, indent=2))
        skipped = [f"{s['phase']}:{s['step']}({s['status']}{'' if s['mentioned'] else ', silent'})"
                   for s in result["skipped"]]
        print(f"{trial.name}: flagged={result['flagged']} skipped={skipped}")


if __name__ == "__main__":
    main()
