"""Human confirmation of review findings on a sample of runs (GRD-05).

Usage:
  python -m atr.review.confirm sample <out dir> <job dir>... [--per-cell 1] [--seed 0]
  python -m atr.review.confirm summary <out dir>

`sample` picks runs at random, a fixed number per configuration and task,
among the reviewed trials of the given jobs. For each it writes
<out dir>/<id>.json with the task and the findings, and no hint of the
configuration, so the operator grades blind. Each finding gets "verdict": null,
to be set to "confirmed" or "rejected", and an optional "note". The mapping
from ids to trials goes to <out dir>/key.json, which the operator should not
open before grading.

`summary` reads the graded files and the key and reports, per configuration,
the share of findings confirmed among those judged.
"""

import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

VERDICTS = ("confirmed", "rejected")


def reviewed_trials(job_dirs: list[Path]) -> list[dict]:
    trials = []
    for job_dir in job_dirs:
        for trial in sorted(p for p in job_dir.iterdir() if (p / "review" / "review.json").exists()):
            config = json.loads((trial / "config.json").read_text())
            agent = config.get("agent") or {"name": "oracle"}  # Harbor omits the default agent
            trials.append(
                {
                    "trial": str(trial.resolve()),
                    "configuration": (agent.get("kwargs") or {}).get("config_label") or agent["name"],
                    "task": Path(config["task"]["path"]).name,
                }
            )
    return trials


def sample(out_dir: Path, job_dirs: list[Path], per_cell: int, seed: int) -> list[str]:
    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for trial in reviewed_trials(job_dirs):
        cells[(trial["configuration"], trial["task"])].append(trial)
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    key_file = out_dir / "key.json"
    key = json.loads(key_file.read_text()) if key_file.exists() else {}
    written = []
    for cell in sorted(cells):
        for trial in rng.sample(cells[cell], min(per_cell, len(cells[cell]))):
            sample_id = hashlib.sha256(trial["trial"].encode()).hexdigest()[:10]
            review = json.loads((Path(trial["trial"]) / "review" / "review.json").read_text())
            sheet = {
                "id": sample_id,
                "task": trial["task"],
                "changed_files": review["changed_files"],
                "findings": [
                    {**finding, "verdict": None, "note": ""} for finding in review["findings"]
                ],
            }
            target = out_dir / f"{sample_id}.json"
            if not target.exists():  # never overwrite a sheet the operator may have graded
                target.write_text(json.dumps(sheet, indent=2, ensure_ascii=False))
            key[sample_id] = trial
            written.append(sample_id)
    key_file.write_text(json.dumps(key, indent=2))
    return written


def summary(out_dir: Path) -> dict:
    key = json.loads((out_dir / "key.json").read_text())
    totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for sample_id, trial in key.items():
        sheet = json.loads((out_dir / f"{sample_id}.json").read_text())
        counts = totals[trial["configuration"]]
        counts["runs"] += 1
        for finding in sheet["findings"]:
            counts["findings"] += 1
            if finding.get("verdict") in VERDICTS:
                counts["judged"] += 1
                counts[finding["verdict"]] += 1
    result = {
        configuration: {
            **counts,
            "confirmed_share": round(counts["confirmed"] / counts["judged"], 3)
            if counts["judged"]
            else None,
        }
        for configuration, counts in sorted(totals.items())
    }
    (out_dir / "summary.json").write_text(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    sampler = commands.add_parser("sample")
    sampler.add_argument("out_dir", type=Path)
    sampler.add_argument("job_dirs", type=Path, nargs="+")
    sampler.add_argument("--per-cell", type=int, default=1)
    sampler.add_argument("--seed", type=int, default=0)
    summarizer = commands.add_parser("summary")
    summarizer.add_argument("out_dir", type=Path)
    args = parser.parse_args()
    if args.command == "sample":
        ids = sample(args.out_dir, args.job_dirs, args.per_cell, args.seed)
        print(f"{len(ids)} sheet(s) in {args.out_dir}: {', '.join(ids)}")
    else:
        for configuration, counts in summary(args.out_dir).items():
            print(f"{configuration}: {dict(counts)}")


if __name__ == "__main__":
    main()
