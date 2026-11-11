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
| Export a publication | `python -m atr.store.export <out dir> <job>... [--experiment <file>]` (the experiment file, `experiments/mvp.toml` for the MVP, is copied into `experiment.json`) |
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

The harness has a pytest suite in `harness/tests/`, with pytest pinned in the `dev` dependency group. Run it with `make test-pytest` from the repository root on Windows, or with `uv run pytest` from `harness/` in WSL. Changes that need Docker, Harbor or a model are still verified with check runs on the synthetic task and recorded in the research reports. See docs/context/testing.md.

## Dashboard

The site is a separate component in `dashboard/`, built with Observable Framework 1.13.4 and pinned with its lockfile. It builds in WSL with Node 24.22.2, the version in `dashboard/.nvmrc`; `engine-strict` makes the install fail on any other version. From WSL:

```bash
cd /mnt/c/repos/ai-track-record/dashboard
npm ci
ATR_EXPORT_DIR=<export dir> npm run build
```

The result is in `dashboard/dist/`. The export comes from `python -m atr.store.export <out dir> <job>... --experiment experiments/mvp.toml`. The build script sets `OBSERVABLE_TELEMETRY_DISABLE=1` itself, fails with a message naming the missing variable or export file, uses no sample data, and clears the loader cache and `dist/` on every run. Git ignores `node_modules/`, `dist/` and the cache, and no export or built site is committed. If `npm ci` fails with a permission or symlink error on the Windows drive, run the same commands from a copy of `dashboard/` on the WSL filesystem. The site's pytest tests live in `harness/tests/`.

### Publication checks

Before any deploy, an operator builds the site from the real export and checks it. This procedure reads private data, so agents never run it; they validate with synthetic exports and a synthetic terms file.

1. Export the 12 jobs from `harness/`: `uv run python -m atr.store.export <out dir> <job>... --experiment experiments/mvp.toml`.
2. Build from `dashboard/`: `ATR_EXPORT_DIR=<out dir> npm run build`.
3. Check the build from `harness/`: `uv run python -m atr.store.check_site ../dashboard/dist`. It reads the private terms from `<data dir>/leak-terms.txt` (`ATR_DATA_DIR`, default `~/atr/data`) or from `--leak-terms <file>`.
4. Read the exit code: 0 means the check passed, 2 means findings (each line names its file, the rule and the match), and 1 means a precondition is not met: a missing `dist/`, a missing or ambiguous data file, an unreadable terms file, or a private target with no terms.

The check scans every file of `dist/` for the private terms, secrets, e-mail addresses and absolute paths, so vendored bundles are included; the only tolerated matches are the exact package specifiers listed in `VENDORED_ALLOWED`. The data files the pages read go through the exporter's own leak check, and the visible text of each page is checked for file names and relative paths. It then requires a page for every run, the evidence markers each page's code must carry, links that resolve, and methodology links that land on an existing anchor.

Cards, tables and charts render in the browser, so the check cannot see them. The manual audit before any deploy opens the home page, one question's runs link, one grid cell and one run page, and confirms that the numbers reach their runs within two clicks; the note of the audit is the operator's to keep. A clean `dist/` is deploy-ready; hosting waits for D-034.

