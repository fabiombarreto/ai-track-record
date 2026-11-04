# Architecture

AI Track Record is a local-first benchmark for AI coding agents. This repository holds its harness (the Python package `atr`), its infrastructure configuration, the public synthetic target's task manifest and its planning documentation. Runs, data and private targets live outside the repository, in the operator's private workspace.

The product, its decisions and its plans are documented in `documentation/`, which is the source of truth (D-011). This file describes the code.

## Stack

| Layer | Technology | Pinned at | Decision |
|---|---|---|---|
| Harness language | Python 3.12, managed with uv, built with hatchling | `requires-python >= 3.12` | D-047 |
| Runner | Harbor, a local checkout run with `uv run harbor` | 0.24.0 | D-030 |
| Agent under test | Claude Code through the Claude Agent SDK, installed in each task container | SDK 0.2.170 | D-017, D-049 |
| Workflows under test | relay (a Claude Code plugin, mounted read-only from a copy of its exact commit) and vanilla (no plugin) | relay 0.49.0 and 0.47.0 | D-016, D-054 |
| Containers | Docker Desktop on WSL 2; Harbor's network allowlist through its egress sidecar | — | D-050 |
| Telemetry | OpenTelemetry Collector (contrib image), OTLP over HTTP, JSON-lines files | 0.162.0 | D-032 |
| Store | DuckDB, rebuilt from the run folders on every load | duckdb 2.0.0 | D-033 |
| Local inference (in preparation) | llama.cpp's CUDA server image, open-weight GGUF models | build b12063 | D-031, D-057, D-058 |
| Synthetic target | Django and Django Ninja on PostgreSQL, graded with pytest | — | D-046 |

## Architectural pattern

A set of small command-line modules around Harbor, with run folders as the system of record.

- **Harbor plugin.** `atr.agents.claude_sdk` is a Harbor installed agent. It installs the Agent SDK in the task container and runs `claude_sdk_runner.py` there with the run's model, limits, plugin and telemetry settings.
- **Files first.** Every run leaves an immutable trial folder: Harbor's result, the runner's messages and result, the verifier's rewards and patch, the review and the checks. The store is derived from those folders and can be rebuilt at any time (D-033).
- **Graders outside the agent.** The grader runs in a separate verifier container on the run's diff applied to a clean base, with the hidden tests added only there (D-015). The independent review runs in its own container with a pinned reviewer (D-018).
- **Deny-by-default publication.** The exporter copies only allowlisted fields per visibility class and blocks on any leak-check finding.
- **Configuration, not code.** Models, workflow versions and limits are job-config values passed as agent kwargs, not code changes (D-005).

## Data flow of one run

1. A task manifest (a pull request: base ref and solution ref) is built into a Harbor task folder by `atr.tasks.build`.
2. A Harbor job config names the task, the agent `atr.agents.claude_sdk:ClaudeAgentSdk`, the model and the kwargs (cwd, telemetry endpoint, disallowed tools, cost cap, configuration label, and for relay a read-only mount of the plugin).
3. Harbor starts the task container; the agent installs the SDK and the runner executes Claude Code unattended. Telemetry goes to the Collector at `host.docker.internal:4318`.
4. Harbor's verifier runs `grade.py` and writes `reward.json` and `changes.patch`.
5. `atr.checks.skipped_steps` and `atr.review.run` add the protocol check and the independent review to the trial folder.
6. `atr.store.load` rebuilds `atr.duckdb`; `atr.store.export` writes a publication after the leak check.

## Folder structure

| Path | What lives there |
|---|---|
| `harness/src/atr/agents/` | Harbor agent (`claude_sdk.py`) and the in-container runner (`claude_sdk_runner.py`) |
| `harness/src/atr/tasks/` | Task builder (`build.py`) and the grader copied into every task (`grade.py`) |
| `harness/src/atr/checks/` | Protocol check of skipped workflow steps (`skipped_steps.py`) |
| `harness/src/atr/review/` | Independent review (`run.py`, `reviewer.py`) and blind human confirmation (`confirm.py`) |
| `harness/src/atr/store/` | Loader into DuckDB (`load.py`) and the allowlist exporter (`export.py`) |
| `harness/src/atr/ops/` | Spend against the ceiling (`budget.py`) and cleanup of killed jobs (`cleanup.py`) |
| `harness/src/atr/local/` | Local inference: pinned models, download, server start and stop, speed benchmark |
| `infra/otel-collector/` | Collector configuration and Compose file |
| `infra/local-inference/` | Pinned server image and model files (`models.toml`) |
| `targets/synthetic-events/` | The public synthetic target's task manifest and Docker and pytest templates |
| `documentation/` | Product, plans, research reports and the decision log (source of truth) |
| `PRPs/` | relay artifacts for work on this repository: PRDs, plans, reports |
| `docs/` | Agent context: this folder, domain notes, library notes, decision gate |
| `scripts/` | Per-worktree bootstrap scripts for relay |

## Outside the repository

The private workspace `~/atr` in WSL has no remote and is never committed:

| Path | Content |
|---|---|
| `~/atr/data/` | `jobs/` (trial folders), `tasks/` (built tasks), `telemetry/`, `atr.duckdb`, `exports/`, `confirmations/`, `leak-terms.txt`, `local-inference/` |
| `~/atr/manifests/` | Target A's task manifests |
| `~/atr/targets/` | Target repositories |
| `~/atr/relay/<commit>/` | Copies of relay at the exact commits under test |
| `~/atr/tools/` | The Harbor checkout and the harness virtual environment |
| `~/atr/.env` | Secrets |

Model weights for local inference live on D: (`/mnt/d/atr/models`), because C:, which holds the WSL and Docker disks, has little free space.

## Technical decisions visible in the code

- The runner fails instead of dropping any requested option that the installed SDK does not support, so a run never silently differs from its configuration.
- The runner records its own wall time and summed turns, because a session that waits on background sub-agents emits several result messages whose durations cover only their own segment.
- The grader copies files changed in relay's git worktrees over `/app` before diffing, so a run stopped by its time limit is still graded with its partial code.
- Telemetry events are ordered by `event.sequence`, not by time, because the WSL clock can jump during a run.
- Relay's working files under `PRPs/` are excluded from size metrics and from the reviewed diff, so relay and vanilla are compared on the same kind of change.
- Local inference runs one model per server start, with a new API key each time, published on the host's loopback only [INFERRED - VALIDATE: set by the local models plan, not yet exercised].
