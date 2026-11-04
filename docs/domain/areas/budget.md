# Budget

## Primary responsibility

Keep the MVP's model API spend under its ceiling and stop a batch before a run that could cross it. Code: `atr.ops.budget`, the batch launcher.

## Entities

Spend per job, run cost, review cost, ceiling, target, cost cap.

## Rules

- The MVP's spend is capped at US$ 800, with a target of US$ 400 set at M0 (D-028).
- Spend is the sum, over every trial folder, of the run's cost from the runner's result and the independent review's cost. A regrade adds only its review's cost.
- The sum is a lower bound of what was billed: runs lost before writing a result, and spend outside the harness, are not in it. The credit balance stays the check against billing.
- With `--next <usd>`, the command exits 1 when the spend so far plus that amount would pass the ceiling; the launcher passes the job's cost cap or its highest cost seen.
- Runs are paid first with the Max plan's included API credits, which expire each billing cycle, then with purchased credits, always within the ceiling (D-049).
- Experiments outside the MVP never draw on its ceiling: local runs have no API cost and their reviews are counted with their own experiment (D-058).

## Relationships

Reads run and review results; gates the runs launcher.

## Main flow

Before each run: `python -m atr.ops.budget --next <cap>` → exit 0 starts the run, exit 1 stops the batch.

## Open Questions

- A per-experiment ceiling (so local or Gemini jobs are summed apart from the MVP's) is planned, not built [INFERRED - VALIDATE: the prefix filter `--prefix` may already cover it].
