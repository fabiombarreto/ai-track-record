# Store and publication

## Primary responsibility

Load every run into a local analytical store that can be rebuilt from files, reconcile tokens and cost across sources, and publish only what each target's visibility allows. Code: `atr.store.load`, `atr.store.export`.

## Entities

Trials, model usage, events, metric points, review findings, protocol steps, the reconciliation and spend views, exports, the publication log.

## Rules

- The store is rebuilt from scratch on every load, from the run folders, the built tasks, the confirmation sheets and the telemetry files (D-033). Run folders are the system of record.
- A trial regraded with `harbor job regrade` keeps one row: agent data from the original trial, grades and review from the latest regrade.
- Events are ordered by `event.sequence`, not by time, because the WSL clock can jump during a run.
- Cost is computed from tokens and a dated price table, and every published cost states its source (D-022). The reconciliation compares Claude Code's events, its metrics and the SDK's usage per trial and model.
- Size metrics count product files only; relay's `PRPs/` files are left out, and `docs/` changes are counted separately.
- Export is deny by default: each run, task and target is copied through an allowlist of fields for its visibility class (allowlist version 2). For a private target only the codename, a generic description, the task's category and difficulty, per-run metrics, change sizes and review findings as counts by category leave the store.
- Before anything is written, a leak check scans the whole export for private terms (from `leak-terms.txt`, kept outside the repository and required when a private target is exported), absolute and relative paths, source file names, secrets, e-mail addresses and, in private runs, any text longer than 64 characters. Any finding blocks the export.
- Each export is recorded in `publications.jsonl` with its date, jobs, runs, allowlist version and file digests.
- Private targets appear publicly under a codename only (D-013); publication waits for the operator's command.

## Relationships

Reads runs, grading, review and telemetry; feeds the dashboard (M4) and the budget's `spend` view.

## Main flow

`python -m atr.store.load` → `atr.duckdb` → analysis queries → `python -m atr.store.export <out dir> <job>...` → leak check → files and a publication record.

## Open Questions

- Local runs have no API cost; how their machine time and energy enter the store and the export is planned (local models plan, section 7) but not built.
