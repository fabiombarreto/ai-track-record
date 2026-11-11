"""Export the publishable results of selected jobs (PUB-01 to PUB-03, PRV-04).

Usage: python -m atr.store.export <out dir> <job>... [--data-dir <dir>] [--db <file>]
       [--experiment <file>]

With --experiment, the experiment file is validated, copied into experiment.json,
leak-checked and recorded like the other files.

Deny by default: each run, task and target is copied through an allowlist of
fields for its target's visibility class, and anything not listed is withheld.
For a private target that leaves the codename and generic description, the
task's category and difficulty, per-run metrics, the size of each run's changes
and the review findings as counts by category, never their text. Each run
carries its route, provider, quantization, cost source and GPU energy; a local
run also carries a label naming it workflow portability on a quantized model,
and its model is published as the alias (version 3 of the allowlist).

Before anything is written, a leak check scans the whole export for the
private terms listed in <data dir>/leak-terms.txt (one per line, kept outside
the repository and required when a private target is exported), absolute
paths, file names, secrets, e-mail addresses and, in private runs, any long
text. Any finding blocks the export. The site check (atr.store.check_site) reuses
the patterns and the helpers read_leak_terms and text_findings. Each export is recorded in
<data dir>/publications.jsonl with its date, jobs, runs and allowlist version.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import duckdb

ALLOWLIST_VERSION = "3"

RUN_FIELDS = (
    "job", "trial", "codename", "task_id", "config", "model", "agent_version",
    "outcome", "native_outcome", "num_turns", "wall_ms", "duration_api_ms", "cost_usd",
    "reward", "criteria_satisfied", "existing_tests_pass",
    "files_changed", "lines_added", "lines_removed", "docs_files_changed", "docs_lines_added",
    "new_static_findings", "review_findings", "skipped_steps", "skipped_flagged",
    "relay_deviations", "workflow", "workflow_version", "workflow_source", "started_at",
    "route", "provider", "quantization", "cost_source", "energy_wh",
)
LOCAL_LABEL = "workflow portability, quantized local model"
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
        local = trial["route"] == "local"
        run["label"] = LOCAL_LABEL if local else None
        if local:
            # The alias, not the route's `local/<alias>` id, which the leak check reads as a path.
            run["model"] = str(trial["model"]).removeprefix("local/")
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


def read_leak_terms(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.startswith("#")]


def text_findings(name: str, text: str, terms: list[str],
                  labels: tuple[str, ...] = tuple(PATTERNS)) -> list[str]:
    findings = []
    lowered = text.lower()
    for term in terms:
        if re.search(rf"(?<!\w){re.escape(term.lower())}(?!\w)", lowered):
            findings.append(f"{name}: private term {term!r}")
    for label, pattern in PATTERNS.items():
        if label not in labels:
            continue
        for match in sorted(set(pattern.findall(text)))[:5]:
            findings.append(f"{name}: {label} {match!r}")
    return findings


def leak_check(export: dict[str, object], private_terms: list[str], private: set[str]) -> list[str]:
    findings = []
    for name, content in export.items():
        findings += text_findings(name, json.dumps(content, ensure_ascii=False), private_terms)
    for run in export["runs.json"]:
        if run.get("codename") in private:
            for field, value in run.items():
                if isinstance(value, str) and len(value) > LONG_TEXT:
                    findings.append(f"runs.json: long text in {field} of {run['trial']}")
    return findings


def _table(value: object, where: str, required: tuple, optional: tuple = ()) -> dict:
    if not isinstance(value, dict):
        raise SystemExit(f"experiment file: {where} must be a table")
    unknown = sorted(set(value) - set(required) - set(optional))
    if unknown:
        raise SystemExit(f"experiment file: unknown key {unknown[0]!r} in {where}")
    for key in required:
        if key not in value:
            raise SystemExit(f"experiment file: {where} lacks the key {key!r}")
    for key, item in value.items():
        if key != "status" and not isinstance(item, str):
            raise SystemExit(f"experiment file: {key!r} in {where} must be a string")
    return value


def _entries(data: dict, key: str) -> list:
    items = data[key]
    if not isinstance(items, list) or not items:
        raise SystemExit(f"experiment file: {key!r} must be a non-empty list of tables")
    return items


def load_experiment(path: Path) -> dict:
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise SystemExit(f"cannot read the experiment file {path}: {error}") from None
    top = ("preliminary", "planned_repetitions", "configurations", "questions", "hypotheses")
    unknown = sorted(set(data) - set(top))
    if unknown:
        raise SystemExit(f"experiment file: unknown key {unknown[0]!r}")
    for key in top:
        if key not in data:
            raise SystemExit(f"experiment file lacks the key {key!r}")
    if not isinstance(data["preliminary"], bool):
        raise SystemExit("experiment file: 'preliminary' must be true or false")
    repetitions = data["planned_repetitions"]
    if isinstance(repetitions, bool) or not isinstance(repetitions, int):
        raise SystemExit("experiment file: 'planned_repetitions' must be an integer")

    questions = []
    for i, q in enumerate(_entries(data, "questions")):
        q = _table(q, f"questions[{i}]", ("id", "text", "status"), ("reason", "answer"))
        if q["status"] not in ("answered", "not_yet_answered"):
            raise SystemExit(f"experiment file: question {q['id']!r} has the unknown status {q['status']!r}")
        questions.append({"id": q["id"], "text": q["text"], "status": q["status"],
                          "reason": q.get("reason"), "answer": q.get("answer")})
    ids = [q["id"] for q in questions]
    for question_id in ids:
        if ids.count(question_id) > 1:
            raise SystemExit(f"experiment file: duplicate question id {question_id!r}")

    configurations = []
    for i, c in enumerate(_entries(data, "configurations")):
        c = _table(c, f"configurations[{i}]", ("label", "name", "workflow", "model", "question"),
                   ("workflow_version",))
        if c["question"] not in ids:
            raise SystemExit(f"experiment file: configuration {c['label']!r} names the undeclared question {c['question']!r}")
        configurations.append({"label": c["label"], "name": c["name"], "workflow": c["workflow"],
                               "workflow_version": c.get("workflow_version"), "model": c["model"],
                               "question": c["question"]})
    labels = [c["label"] for c in configurations]
    for label in labels:
        if labels.count(label) > 1:
            raise SystemExit(f"experiment file: duplicate configuration label {label!r}")

    hypotheses = []
    for i, h in enumerate(_entries(data, "hypotheses")):
        h = _table(h, f"hypotheses[{i}]", ("id", "text"))
        hypotheses.append({"id": h["id"], "text": h["text"]})
    return {"preliminary": data["preliminary"], "planned_repetitions": repetitions,
            "configurations": configurations, "questions": questions, "hypotheses": hypotheses}


def check_configurations(experiment: dict, runs: list[dict]) -> None:
    declared = {c["label"] for c in experiment["configurations"]}
    for run in runs:
        if run["config"] not in declared:
            raise SystemExit(f"run config {run['config']!r} is not declared in the experiment file")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("jobs", nargs="+")
    default_data = Path(os.environ.get("ATR_DATA_DIR", "~/atr/data")).expanduser()
    parser.add_argument("--data-dir", type=Path, default=default_data)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--experiment", type=Path)
    args = parser.parse_args()

    con = duckdb.connect(str(args.db or args.data_dir / "atr.duckdb"), read_only=True)
    export = build_export(con, args.jobs)
    if not export["runs.json"]:
        raise SystemExit("no runs found for these jobs")
    if args.experiment:
        export["experiment.json"] = load_experiment(args.experiment)
        check_configurations(export["experiment.json"], export["runs.json"])
    private = {t["codename"] for t in export["targets.json"] if t["visibility"] != "public"}
    terms_file = args.data_dir / "leak-terms.txt"
    terms = read_leak_terms(terms_file)
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
