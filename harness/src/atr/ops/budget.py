"""Report the MVP's model API spend so far and check it against the ceiling (D-028).

Usage: python -m atr.ops.budget [--data-dir <dir>] [--next <usd>] [--prefix <job prefix>]

Sums, over every trial folder under <data dir>/jobs, the run's cost from the
runner's agent/result.json and the independent review's cost from
review/review.json. A regrade adds only its review's cost, since its run is
the trial it regraded. The store's `spend` view reads the same files; this
command reads them without rebuilding the store, so a batch can check it
before each run.

The sum is a lower bound of what was billed: runs lost before writing a
result, and spend outside the harness, are not in it. The operator's credit
balance stays the check against billing.

Jobs whose name starts with `lc-` belong to the local models experiment (D-058)
and never count against the ceiling. They are reported on their own line: the
SDK's cost of such a run is an estimate for a model it cannot price, not money
spent, and their reviews' cost is Anthropic credit counted with that experiment.

With --next, exits 1 when the spend so far plus <usd> would pass the ceiling,
so a batch stops before a run that could cross it.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

CEILING_USD = 800.0
TARGET_USD = 400.0
LOCAL_PREFIX = "lc-"


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def spend_by_job(jobs_dir: Path) -> dict[str, float]:
    spend: dict[str, float] = defaultdict(float)
    for trial in sorted(p.parent for p in jobs_dir.glob("*/*/config.json")):
        # A regrade copies the agent folder of the trial it regraded.
        regrade = (read_json(trial / "config.json").get("source_trial") or {}).get("action") == "regrade"
        run = None if regrade else read_json(trial / "agent" / "result.json").get("total_cost_usd")
        # The SDK reports a session's cost cumulatively, so the last turn has it all.
        review = [c for c in read_json(trial / "review" / "review.json").get("cost_usd_per_turn") or []
                  if c is not None]
        spend[trial.parent.name] += (run or 0.0) + (review[-1] if review else 0.0)
    return dict(spend)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_data = Path(os.environ.get("ATR_DATA_DIR", "~/atr/data")).expanduser()
    parser.add_argument("--data-dir", type=Path, default=default_data)
    parser.add_argument("--next", type=float, help="cost cap of the next run, in USD")
    parser.add_argument("--prefix", default="m3-", help="job prefix reported on its own")
    args = parser.parse_args()

    jobs_dir = args.data_dir / "jobs"
    all_spend = spend_by_job(jobs_dir)
    spend = {job: cost for job, cost in all_spend.items() if not job.startswith(LOCAL_PREFIX)}
    total = sum(spend.values())
    batch = sum(cost for job, cost in spend.items() if job.startswith(args.prefix))
    print(f"spent: US$ {total:.2f} (jobs {args.prefix}*: US$ {batch:.2f}); "
          f"target US$ {TARGET_USD:.0f}, ceiling US$ {CEILING_USD:.0f}, "
          f"left US$ {CEILING_USD - total:.2f}")
    local = sorted(job for job in all_spend if job.startswith(LOCAL_PREFIX))
    if local:
        estimate = review = 0.0
        for trial in (p.parent for p in jobs_dir.glob("*/*/config.json") if p.parent.parent.name in local):
            if (read_json(trial / "config.json").get("source_trial") or {}).get("action") != "regrade":
                estimate += read_json(trial / "agent" / "result.json").get("total_cost_usd") or 0.0
            costs = [c for c in read_json(trial / "review" / "review.json").get("cost_usd_per_turn") or []
                     if c is not None]
            review += costs[-1] if costs else 0.0
        print(f"local jobs {LOCAL_PREFIX}* ({len(local)}), not counted above: "
              f"SDK estimate US$ {estimate:.2f} (not money spent), "
              f"reviews US$ {review:.2f} (Anthropic credit, local models experiment)")
    if args.next is not None and total + args.next > CEILING_USD:
        print(f"stop: the next run (up to US$ {args.next:.2f}) could pass the ceiling")
        sys.exit(1)


if __name__ == "__main__":
    main()
