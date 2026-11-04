# Interfaces reference

AI Track Record has no HTTP API. Its interfaces are command-line modules, a Harbor agent, and file formats.

## Harbor agent

`atr.agents.claude_sdk:ClaudeAgentSdk`, configured in a job's `agents` entry:

| Kwarg | Meaning |
|---|---|
| `model_name` (agent field) | Model id, e.g. `claude-sonnet-5-5` |
| `cwd` | Working directory in the container, `/app` |
| `otel_endpoint` | Collector URL, `http://host.docker.internal:4318` |
| `disallowed_tools` | Tools to disable, `["WebSearch", "WebFetch"]` on Target A |
| `max_budget_usd`, `max_turns` | Run limits |
| `plugin_dir` | Plugin path in the container, for relay |
| `config_label` | Configuration name recorded with telemetry |
| `install_node`, `python_version`, `prompt` | Container setup and an instruction override |

## Command-line modules

| Module | Reads | Writes |
|---|---|---|
| `atr.tasks.build` | A task manifest and the target's templates | A Harbor task folder with `atr-task.json` |
| `atr.checks.skipped_steps` | A trial's workflow records and summary | `<trial>/checks/skipped_steps.json` |
| `atr.review.run` | A graded trial and its built task | `<trial>/review/review.json` and the transcript |
| `atr.review.confirm` | Reviewed trials; graded sheets | Blind sheets and `key.json`; a summary |
| `atr.store.load` | `~/atr/data`: jobs, tasks, confirmations, telemetry | `atr.duckdb` |
| `atr.store.export` | `atr.duckdb`, `leak-terms.txt` | An export folder and a line in `publications.jsonl` |
| `atr.ops.budget` | Trial results and reviews | A spend report; exit 1 with `--next` past the ceiling |
| `atr.ops.cleanup` | A job folder | Removes leftover Compose containers and networks |
| `atr.local.fetch` | `models.toml` | Verified weights and markers in `ATR_MODELS_DIR` |
| `atr.local.serve` | `models.toml`, verified weights | The `atr-llm` container, `server.json`, `server.key` |
| `atr.local.bench` | `server.json`, `server.key` | `local-inference/bench/<model id>-<time>.json` |

## Trial folder

| Path | Written by | Content |
|---|---|---|
| `result.json` | Harbor | Exception info, timings |
| `agent/result.json`, `agent/messages.jsonl` | Runner | SDK result with `atr_wall_ms`, `atr_num_turns`; every SDK message |
| `agent/workflow.json` | Agent | Plugin version and digest |
| `verifier/reward.json`, `verifier/changes.patch` | `grade.py` | Rewards; the graded diff |
| `review/review.json` | `atr.review.run` | Findings and review cost |
| `checks/skipped_steps.json` | `atr.checks.skipped_steps` | Protocol steps and flags |

## Local inference configuration

`infra/local-inference/models.toml`: a `[server]` table (image, build, commit, CUDA, `api_key_env`, shared `args`) and one `[models."<id>"]` table per file (alias, role, stage, repo, revision, file, size, sha256, context, args).
