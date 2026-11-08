# Development

## Setup

Everything runs in WSL 2 (Ubuntu) on the operator's machine, with Docker Desktop's WSL backend. From Windows, start commands with `wsl.exe -d Ubuntu --exec bash -lc '<command>'`.

1. Harness environment: `cd /mnt/c/repos/ai-track-record/harness && uv sync`. Batches use `~/atr/tools/harness-venv/bin/python`.
2. Harbor 0.24.0 is a checkout at `~/atr/tools/harbor`, run with `uv run harbor` from there.
3. Secrets in `~/atr/.env`, loaded with `set -a; . ~/atr/.env; set +a`.
4. Collector: `docker compose -f infra/otel-collector/docker-compose.yaml up -d`.

## Commands

All modules run from `harness/` with `uv run python -m <module>`, or with the harness venv's Python and `PYTHONPATH` pointing at `harness/src`.

| Task | Command |
|---|---|
| Build a task | `python -m atr.tasks.build <manifest>.toml [--out <dir>]` |
| Run a job | From `~/atr/tools/harbor`: `HARBOR_TELEMETRY=off PYTHONPATH=/mnt/c/repos/ai-track-record/harness/src uv run harbor run -c <job>.json -y` |
| Check skipped steps | `python -m atr.checks.skipped_steps <trial dir>...` |
| Review a run | `python -m atr.review.run <trial dir> --task <built task dir>` |
| Sample for blind confirmation | `python -m atr.review.confirm sample <out dir> <job dir>...` |
| Summarize confirmations | `python -m atr.review.confirm summary <out dir>` |
| Rebuild the store | `python -m atr.store.load` |
| Export a publication | `python -m atr.store.export <out dir> <job>...` |
| Check spend | `python -m atr.ops.budget [--next <usd>]` |
| Clean a killed job | `python -m atr.ops.cleanup <job dir>` |
| Local models | `python -m atr.local.fetch`, `python -m atr.local.serve start <id>`, `python -m atr.local.bench`, `python -m atr.local.probe` (check L1), `python -m atr.local.serve record <folder>`, `python -m atr.local.serve stop`, `python -m atr.local.launch <job config> [--model-id] [--port] [--dry-run]` (one local Harbor job with its server and power records), `python -m atr.tasks.build <manifest> --route local` (builds `<task id>-local`) |

## Adding a feature

1. Run the Decision Gate (docs/decision-gate.md) and read the domain area you change.
2. Record any new decision in `documentation/decisions/decision-log.md`, not only in `docs/`.
3. Verify on the public synthetic task first, so transcripts expose nothing private (D-046).
4. Record what was checked and found in the milestone's report in `documentation/research/`.
5. Commit with a conventional message (see docs/context/conventions.md).

## Tests

There is no automated test suite. Harness changes are verified with check runs on the synthetic task and recorded in the research reports; `python -m py_compile` catches syntax errors. See docs/context/testing.md.
