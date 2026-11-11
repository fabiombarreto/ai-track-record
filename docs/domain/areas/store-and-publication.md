# Store and publication

## Primary responsibility

Load every run into a local analytical store that can be rebuilt from files, reconcile tokens and cost across sources, and publish only what each target's visibility allows. Code: `atr.store.load`, `atr.store.export`, `atr.store.check_site`.

## Entities

Trials, model usage, events, metric points, review findings, protocol steps, the reconciliation and spend views, exports, the publication log.

## Rules

- The store is rebuilt from scratch on every load, from the run folders, the built tasks, the confirmation sheets and the telemetry files (D-033). Run folders are the system of record.
- A trial regraded with `harbor job regrade` keeps one row: agent data from the original trial, grades and review from the latest regrade.
- Events are ordered by `event.sequence`, not by time, because the WSL clock can jump during a run.
- Cost is computed from tokens and a dated price table, and every published cost states its source (D-022). The reconciliation compares Claude Code's events, its metrics and the SDK's usage per trial and model.
- A local run is stored with route `local`, `cost_usd` zero and `cost_source` `local`; the SDK's own total is kept apart as `sdk_cost_estimate_usd` (an estimate for a model it cannot price, not money spent). Route, provider, quantization and server build come from `agent/route.json`, energy and mean power (GPU only) from `server/power.json`, and the server's prompt, cached prompt and output token counts from `server/metrics.prom`. An API run keeps the SDK's cost with source `sdk`.
- A run that failed before an SDK result names its cause in `native_outcome` (the exception type and the agent's own first message line, or the last assistant message's error); `outcome` stays `error`. This applies only to local-route trials.
- Reconciliation of a local run compares tokens only, across the SDK, events and metrics, plus the server's prompt total (processed plus reused) against the SDK's total input and the server's output against the SDK's output. No cost is compared. The view gains `route`, `server_prompt`, `server_output` and `sdk_total_input`.
- Size metrics count product files only; relay's `PRPs/` files are left out, and `docs/` changes are counted separately.
- Export is deny by default: each run, task and target is copied through an allowlist of fields for its visibility class (allowlist version 3). For a private target only the codename, a generic description, the task's category and difficulty, per-run metrics, change sizes and review findings as counts by category leave the store. Version 3 adds `route`, `provider`, `quantization`, `cost_source`, `energy_wh` and a `label` (`workflow portability, quantized local model` for local runs, null otherwise); a local run's model is published as its alias, without the `local/` prefix, which the leak check would read as a path.
- Before anything is written, a leak check scans the whole export for private terms (from `leak-terms.txt`, kept outside the repository and required when a private target is exported), absolute and relative paths, source file names, secrets, e-mail addresses and, in private runs, any text longer than 64 characters. Any finding blocks the export.
- Before any deploy, `python -m atr.store.check_site <dist dir>` checks the built site. It scans every file of `dist/` for private terms, secrets, e-mail addresses and absolute paths (only the exact package specifiers in `VENDORED_ALLOWED` are tolerated), runs the exporter's own leak check over the data files, checks the visible text of each page for file names and relative paths, and requires a page for every run, evidence markers, resolving links and existing methodology anchors. It fails closed (exit 1) on a missing `dist/`, data file or terms file, or a private target with no terms; findings exit 2. It reuses the exporter's `read_leak_terms` and `text_findings`.
- Each export is recorded in `publications.jsonl` with its date, jobs, runs, allowlist version and file digests.
- Private targets appear publicly under a codename only (D-013); publication waits for the operator's command.

## Relationships

Reads runs, grading, review and telemetry; feeds the dashboard (M4) and the budget's `spend` view.

## Main flow

`python -m atr.store.load` → `atr.duckdb` → analysis queries → `python -m atr.store.export <out dir> <job>... [--experiment <file>]` → leak check → files and a publication record. With `--experiment`, the public experiment file is validated and written as `experiment.json`; the export fails if a run's `config` is not declared in it.

## Open Questions

- Matching on a completed local run is untested: no local run has completed a request yet; it waits for check L7 (Phase 6).
