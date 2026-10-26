"""Export the publishable results of selected jobs (PUB-01 to PUB-03, PRV-04).

Usage: python -m atr.store.export <out dir> <job>... [--data-dir <dir>] [--db <file>]

Deny by default: each run, task and target is copied through an allowlist of
fields for its target's visibility class, and anything not listed is withheld.
For a private target that leaves the codename and generic description, the
task's category and difficulty, per-run metrics, the size of each run's
changes and the review findings as counts by category, never their text.

Before anything is written, a leak check scans the whole export for the
private terms listed in <data dir>/leak-terms.txt (one per line, kept outside
the repository and required when a private target is exported), absolute
paths, file names, secrets, e-mail addresses and, in private runs, any long
text. Any finding blocks the export. Each export is recorded in
<data dir>/publications.jsonl with its date, jobs, runs and allowlist version.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import duckdb

ALLOWLIST_VERSION = "1"

RUN_FIELDS = (
    "job", "trial", "codename", "task_id", "config", "model", "agent_version",
    "outcome", "native_outcome", "num_turns", "wall_ms", "duration_api_ms", "cost_usd",
    "reward", "criteria_satisfied", "existing_tests_pass",
    "files_changed", "lines_added", "lines_removed", "new_static_findings",
    "review_findings", "skipped_steps", "skipped_flagged", "started_at",
)
PUBLIC_RUN_FIELDS = ("task_title",)
TASK_FIELDS = ("codename", "task_id", "category", "difficulty")
PUBLIC_TASK_FIELDS = ("task_title",)
TARGET_FIELDS = ("codename", "visibility", "target_description")

PATTERNS = {
    "absolute path": re.compile(r"(/root/|/home/|/mnt/|/app/|/opt/|[A-Za-z]:\\\\)"),
    "source file name": re.compile(r"\b[\w-]+\.(py|tsx?|sql|toml|ya?ml|html)\b"),
    "relative path": re.compile(r"\b[\w.-]+/[\w./-]*\.\w+\b"),
    "secret": re.compile(r"(sk-ant-[\w-]+|ANTHROPIC_API_KEY|Bearer\s+\S+|api[_-]?key)", re.I),
    "e-mail address": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),
}
LONG_TEXT = 64


def rows(con: duckdb.DuckDBPyConnection, query: str, params: list) -> list[dict]:
    relation = con.execute(query, params)
    columns = [column[0] for column in relation.description]
    return [dict(zip(columns, row, strict=True)) for row in relation.fetchall()]


def jsonable(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def build_export(con: duckdb.DuckDBPyConnection, jobs: list[str]) -> dict[str, object]:
    placeholders = ", ".join("?" * len(jobs))
    trials = rows(con, f"SELECT * FROM trials WHERE job IN ({placeholders}) ORDER BY job, trial", jobs)
    tokens = {
        (r["job"], r["trial"]): r
        for r in rows(
            con,
            f"""SELECT job, trial, sum(input_tokens) AS input_tokens,
                       sum(output_tokens) AS output_tokens,
                       sum(cache_read_tokens) AS cache_read_tokens,
                       sum(cache_creation_tokens) AS cache_creation_tokens
                FROM model_usage WHERE job IN ({placeholders}) GROUP BY ALL""",
            jobs,
        )
    }
    categories: dict[tuple, dict] = {}
    for r in rows(
        con,
        f"""SELECT job, trial, coalesce(category, 'uncategorized') AS category,
                   count(*) AS findings,
                   count(*) FILTER (WHERE verdict = 'confirmed') AS confirmed,
                   count(*) FILTER (WHERE verdict IN ('confirmed', 'rejected')) AS judged
            FROM review_findings WHERE job IN ({placeholders}) GROUP BY ALL""",
        jobs,
    ):
        categories.setdefault((r["job"], r["trial"]), {})[r["category"]] = {
            key: r[key] for key in ("findings", "confirmed", "judged")
        }

    runs, tasks, targets = [], {}, {}
    for trial in trials:
        public = trial["visibility"] == "public"
        fields = RUN_FIELDS + (PUBLIC_RUN_FIELDS if public else ())
        run = {field: jsonable(trial[field]) for field in fields}
        usage = tokens.get((trial["job"], trial["trial"]), {})
        run |= {key: usage.get(key) for key in
                ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens")}
        run["review_by_category"] = categories.get((trial["job"], trial["trial"]), {})
        runs.append(run)
        task_fields = TASK_FIELDS + (PUBLIC_TASK_FIELDS if public else ())
        tasks[(trial["codename"], trial["task_id"])] = {f: trial[f] for f in task_fields}
        targets[trial["codename"]] = {f: trial[f] for f in TARGET_FIELDS}
    return {
        "runs.json": runs,
        "tasks.json": sorted(tasks.values(), key=lambda t: (str(t["codename"]), str(t["task_id"]))),
        "targets.json": sorted(targets.values(), key=lambda t: str(t["codename"])),
    }


def leak_check(export: dict[str, object], private_terms: list[str], private: set[str]) -> list[str]:
    findings = []
    for name, content in export.items():
        text = json.dumps(content, ensure_ascii=False)
        lowered = text.lower()
        for term in private_terms:
            if re.search(rf"(?<!\w){re.escape(term.lower())}(?!\w)", lowered):
                findings.append(f"{name}: private term {term!r}")
        for label, pattern in PATTERNS.items():
            for match in sorted(set(pattern.findall(text)))[:5]:
                findings.append(f"{name}: {label} {match!r}")
    for run in export["runs.json"]:
        if run.get("codename") in private:
            for field, value in run.items():
                if isinstance(value, str) and len(value) > LONG_TEXT:
                    findings.append(f"runs.json: long text in {field} of {run['trial']}")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("jobs", nargs="+")
    default_data = Path(os.environ.get("ATR_DATA_DIR", "~/atr/data")).expanduser()
    parser.add_argument("--data-dir", type=Path, default=default_data)
    parser.add_argument("--db", type=Path)
    args = parser.parse_args()

    con = duckdb.connect(str(args.db or args.data_dir / "atr.duckdb"), read_only=True)
    export = build_export(con, args.jobs)
    if not export["runs.json"]:
        raise SystemExit("no runs found for these jobs")
    private = {t["codename"] for t in export["targets.json"] if t["visibility"] != "public"}
    terms_file = args.data_dir / "leak-terms.txt"
    terms = [line.strip() for line in terms_file.read_text().splitlines()
             if line.strip() and not line.startswith("#")] if terms_file.exists() else []
    if private and not terms:
        raise SystemExit(f"blocked: a private target is exported but {terms_file} lists no terms")
    findings = leak_check(export, terms, private)
    if findings:
        print("blocked by the leak check:")
        for finding in findings:
            print(f"  {finding}")
        raise SystemExit(2)

    now = datetime.now(UTC).isoformat()
    export["publication.json"] = {
        "exported_at": now,
        "allowlist_version": ALLOWLIST_VERSION,
        "jobs": args.jobs,
        "runs": [f"{run['job']}/{run['trial']}" for run in export["runs.json"]],
    }
    with tempfile.TemporaryDirectory() as temp:
        staging = Path(temp)
        digests = {}
        for name, content in export.items():
            data = json.dumps(content, indent=2, ensure_ascii=False) + "\n"
            (staging / name).write_text(data)
            digests[name] = hashlib.sha256(data.encode()).hexdigest()
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for name in export:
            shutil.copy(staging / name, args.out_dir / name)
    with (args.data_dir / "publications.jsonl").open("a") as log:
        log.write(json.dumps({**export["publication.json"], "out_dir": str(args.out_dir.resolve()),
                              "sha256": digests}) + "\n")
    print(f"exported {len(export['runs.json'])} runs to {args.out_dir}")


if __name__ == "__main__":
    main()
