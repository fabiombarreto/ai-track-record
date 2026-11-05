# Local route results: the machine and the compatibility checks

> **Status:** In progress · **Last updated:** 2026-11-05 · **Owner:** Fabio Martins Barreto

This report records the local model route ([plan](../plans/local-models.md), D-031, D-057, D-058): what the operator's machine can serve, measured before the route is configured, and later the compatibility checks of the route. Target A, the codename of the private target, is not described here; the benchmark prompt is random words and holds no target content.

## Progress

| Item | Status | Date |
|---|---|---|
| WP0: weights downloaded and verified onto D:, speeds and power measured at 32k, 64k and 128k | Done | 2026-11-04 |
| WP0: choices recorded in `infra/local-inference/models.toml` (quantization, context, experts on the CPU, slots) | Done | 2026-11-04 |
| WP1: the server's checks (key, loopback, prompt cache, flags); check L1 passed for L-Small and L-MoE | Done | 2026-11-04 |
| WP2: the harness changes | Done: the agent's route option and its check run (the run failed at the server's chat template, see Agent route), the launcher and allowlists (see Launcher and allowlists), and the store, budget and export (see Store, budget and export) | 2026-11-04 |
| WP3: the compatibility checks on the synthetic task | Done: checks L1 to L10 have a result, with a fallback where one is not a pass (see Compatibility checks), and the relay probe ran (see The relay probe) | 2026-11-05 |

## Machine baseline

### The machine during the measurement

The machine is measured as it was in this session: the Windows desktop on the discrete GPU and the containers of other projects running. Neither was changed.

| Item | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 3060 Ti, 8192 MiB of VRAM |
| VRAM in use before the server started | 467 to 947 MiB (the desktop's share, varying between starts) |
| WSL 2 VM | 17987 MiB of memory (17.57 GiB for containers), 10 processors |
| VM memory available during the L-MoE runs | about 14.5 to 15.3 GiB, measured as MemAvailable inside the VM, including the page cache |
| Other containers running | 7 (counted before the server started, not named) |
| Server | llama.cpp build b12063, commit `2cbca389f515df455412dafa07e2b1359cc72a6d`, CUDA image `ghcr.io/ggml-org/llama.cpp:server-cuda-b12063` pinned by digest `sha256:d5ffba7d096ab0236c65dc147d797b4b7658a7e5425634593373635d661bccda`, image id `sha256:aaacf0f2346a3ae0b6ed509bb67d773b21d4bab2a9babf0139a5bd7abc3ef913` |
| Server flags | `--flash-attn on`, 8-bit key and value cache, `--parallel 1`, `--ctx-size 131072`, offline, loopback only |
| Method | One completion per prompt size, prompt cache off, 256 tokens generated, temperature 0, one slot, the prompt a fixed-seed list of random words rescaled to the target token count; GPU power read from `nvidia-smi` every second, energy integrated over the sample times; container memory sampled during the request |

Both main-stage files were verified by size and SHA-256 and sit on D: (`/mnt/d/atr/models`): `Qwen3.6-35B-A3B-UD-Q3_K_XL.gguf` (16.85 GB) and `Qwen3.5-9B-Q4_K_M.gguf` (5.68 GB).

### L-Small: qwen3.5-9b-q4_k_m

Entirely on the GPU, context 131072. Loaded in 60 s; 7920 MiB of VRAM in use after loading. Benchmark file: `qwen3.5-9b-q4_k_m-20261104T192021Z.json`.

| Prompt size | Prompt tokens | Prompt tokens/s | Generation tokens/s | Wall time (s) | GPU power mean / peak (W) | GPU energy (Wh) | Peak VRAM (MiB) | Container peak memory (MiB) |
|---|---|---|---|---|---|---|---|---|
| 32k | 32724 | 165.0 | 28.21 | 207.5 | 110.2 / 183.9 | 6.36 | 7989 | 5582 |
| 64k | 65417 | 108.7 | 26.10 | 611.9 | 106.1 / 196.6 | 18.02 | 7982 | 5602 |
| 128k | 130058 | 65.9 | 22.09 | 1985.0 | 102.7 / 213.8 | 56.64 | 7983 | 5624 |

An earlier run (`qwen3.5-9b-q4_k_m-20261104T190622Z.json`) measured 32k and 64k at similar speeds (192.8 and 124.6 prompt tokens/s) and recorded the 128k size as failed: the benchmark's first prompt-size estimate came out above the context and the server answered HTTP 400. The benchmark now tokenizes the prompt and rescales it to at most the target, and the table above is the run made after that fix. The speed differences between the two runs are the machine's variation with its other load.

At a full 128k the whole model, its cache and the compute buffers use 7983 of 8192 MiB, leaving about 0.2 GB beside the desktop's share. It ran without a failure, but there is no headroom on the card; the server is the only large user of the GPU while a run is going.

### L-MoE: qwen3.6-35b-a3b-ud-q3_k_xl

Context 131072, the experts of the first N layers on the CPU (`--n-cpu-moe N`), the rest on the GPU. Benchmark file for the chosen value: `qwen3.6-35b-a3b-ud-q3_k_xl-20261104T204406Z.json` (N = 34), loaded in 255 s, 7237 MiB of VRAM in use after loading.

| Prompt size | Prompt tokens | Prompt tokens/s | Generation tokens/s | Wall time (s) | GPU power mean / peak (W) | GPU energy (Wh) | Peak VRAM (MiB) | Container peak memory (MiB) |
|---|---|---|---|---|---|---|---|---|
| 32k | 32724 | 125.0 | 13.17 | 281.4 | 75.5 / 121.8 | 5.89 | 7327 | 13670 |
| 64k | 65417 | 352.9 | 13.32 | 204.7 | 120.6 / 132.3 | 6.85 | 7565 | 10040 |
| 128k | 130058 | 341.6 | 11.88 | 402.6 | 128.6 / 153.2 | 14.38 | 7429 | 10250 |

The first prompt of a fresh server is slower than the following ones (125 against about 350 prompt tokens/s): the experts on the CPU are read from the memory-mapped file and the first request pays for loading them into the page cache. A run's first request carries that cost.

#### `--n-cpu-moe` values tried

| `--n-cpu-moe` | Outcome | VRAM after loading (MiB) | Container memory after loading | Peak VRAM at the 128k prompt (MiB) | 128k prompt tokens/s | 128k generation tokens/s |
|---|---|---|---|---|---|---|
| 36 (first guess) | Loads at 128k context | 6297 | 11.88 GiB of 17.57 GiB | not measured | not measured | not measured |
| 34, set through `--arg` after the 36 in `models.toml` | Same as 36: the flag appends layers to the overrides, so a lower value after a higher one changes nothing; lowering needs the value in `models.toml` to change | 6296 | 11.83 GiB | not measured | not measured | not measured |
| 32 | Loads and completes 32k, 64k and 128k; the 128k prompt leaves 220 MiB of VRAM free | 7701 | 11.89 GiB | 7972 | 220.0 | 10.70 |
| 34 (chosen) | Loads and completes 32k, 64k and 128k; about 0.6 GB of VRAM free at the 128k prompt | 7237 | 13.15 GiB | 7565 (64k), 7429 (128k) | 341.6 | 11.88 |

The 36 and 34 loads on `--arg` were the same configuration, so 36 was not benchmarked. The 32 run (`qwen3.6-35b-a3b-ud-q3_k_xl-20261104T202111Z.json`) is the lowest value that loaded; it was rejected because 220 MiB of free VRAM at the largest prompt leaves no room for the desktop's share to grow. No value failed to load, so the UD-IQ3_XXS fallback and the other containers were not touched. The prompt speeds at 128k differ between 32 and 34 (220 and 342 tokens/s) by more than the layer count explains; the two runs were not made under the same load, so only the memory figures are compared here.

### Choices

| Choice | L-Small | L-MoE | Reason |
|---|---|---|---|
| Quantization | Q4_K_M (5.68 GB) | UD-Q3_K_XL (16.85 GB) | The largest main-stage files that load with a context of 128k beside the desktop and the other containers; the 4-bit L-MoE needs a larger WSL memory profile and was not tried |
| Context | 131072 | 131072 | Both load and complete a full 128k prompt; a larger context (the plan's aim of about 160k) was not tried, because L-Small has 0.2 GB of VRAM left at 128k |
| Experts on the CPU | none, all layers on the GPU | 34 | The lowest value that keeps about 0.6 GB of VRAM free at a full 128k prompt; 36 wastes VRAM and 32 leaves 220 MiB |
| Slots | 1 | 1 | The MVP runs one trial at a time (D-058); a second slot would split the context and the memory |

The choices are in `infra/local-inference/models.toml`, with the name of each benchmark file.

### Decided in Phase 2, and still open

Decided: the final server flags and the prompt-cache RAM budget (next section), with check L1 passing for both models.

Open for later phases:

- Whether the prompt-cache RAM budget holds under real prefix reuse (check L5).
- Whether the first-request cost of L-MoE (the experts read into the page cache) needs a warm-up request before a run.
- Whether L-Small's lack of VRAM headroom at 128k needs a lower context for runs that share the machine with the desktop.
- The limits of the measurement: GPU power only, with no whole-system meter; the desktop and the other containers varied between runs, so the speeds are for this machine in this state, not for the models.

## Hardened server

The flags are final for Phase 2 and live in `infra/local-inference/models.toml`.

| Flag | Models | Reason |
|---|---|---|
| `--offline` | all | The server never reaches the network; a start without it fails |
| `--no-webui` | all | The web UI is not used |
| `--slots` | all | `/slots` is enabled explicitly: check L1 and `serve record` read it |
| `--metrics` | all | The launcher reads `/metrics` |
| `--parallel 1` | all | One trial at a time (D-058) |
| loopback publish | all | Docker publishes the port on `127.0.0.1` only; a start fails otherwise |
| `--cache-ram 4096` | L-Small | The container peaked at about 5.6 GiB of the VM's 17.6 GiB; llama.cpp's default of 8192 MiB is too much |
| `--cache-ram 2048` | L-MoE (main and fallback) | The container peaked at 13.4 GiB, leaving about 4 GiB for the cache, the task container, the Collector and the other containers |

The prompt-cache budget is a first value; check L5 revisits it.

A start now makes these checks and fails closed on any of them: the weights are verified; `--offline` is among the flags and no download flag is (`-hf`, `--hf-repo`, `--model-url`, `--docker-repo` and the like), before any container starts; `count_tokens`, `/slots` and `/metrics` each answer 401 without the key and 200 with it; the port is published on `127.0.0.1` only; the key is absent from the record. The record states `offline` and the endpoints checked.

`serve record <folder>` writes `server.json`, `slots.json`, `metrics.prom` and `server.log` for the running server into a folder the launcher names. The server's `/slots` returns each slot's detokenized prompt and generated text, so the copy drops those two fields. Nothing is written if the key would appear in any of the four files.

## Agent route

The Harbor agent `atr.agents.claude_sdk` has a `route` option. Without it (`"anthropic"`) a run behaves as before. A job config for the local route sets `route: "local"`, a `model_name` of `local/<alias>` and, optionally, `local_base_url` (default `http://host.docker.internal:8090`; its port must equal the server record's) and `local_timeout_ms` (default 10800000, the run's three-hour limit). It has no `max_budget_usd`: Claude Code has no price for a local model (check L8 studies the cap).

The agent reads `server.json` and `server.key` from `$ATR_DATA_DIR/local-inference` and fails the trial if either is missing, if the job's model is not the server's alias, or if the base URL's port is not the record's.

| Variable | Value | Reason |
|---|---|---|
| `ANTHROPIC_API_KEY` | absent | The container holds nothing for Anthropic's API; in non-interactive mode a key, when present, is always used |
| `ANTHROPIC_BASE_URL` | the local server | Requests go to the server only |
| `ANTHROPIC_AUTH_TOKEN` | the server's key | Sent as a bearer token, which the server accepts; it reaches the container through the run's environment only |
| `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, `_SONNET_`, `_HAIKU_`, `_FABLE_`, `CLAUDE_CODE_SUBAGENT_MODEL` | the alias | Every alias names the model under test; no request names a Claude model |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | the server's context (131072) | Claude Code assumes 200K for an unknown model |
| `API_TIMEOUT_MS`, `CLAUDE_STREAM_IDLE_TIMEOUT_MS` | 10800000 | A long prefill on the local server can take far longer than the defaults wait |
| `CLAUDE_CODE_ATTRIBUTION_HEADER` | `0` | A header that changes between requests defeats the server's prompt cache |
| `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` | `1` | Removes beta headers and tool-schema fields a gateway may reject |

Before the runner starts, a check from inside the task container fails the trial, naming the cause, when: the container has `ANTHROPIC_API_KEY` ("the task container has ANTHROPIC_API_KEY set"); the server does not answer ("did not answer (HTTP none)"); the server rejects the key ("rejected the run's key (HTTP 401)"); the server answers another status; or `/v1/models` does not list the model ("serves X, not Y"). Against a real server the wrong-key and wrong-model cases failed as intended, and the messages hold no key.

`agent/route.json` records the provider, model, base URL, the server's image digest, build and commit, the model file, its size and SHA-256, the quantization, the flags, the sampling (temperature, top-p, top-k, min-p, presence penalty), the thinking setting, the context, the published ports, the machine and start time, and the route's variables with the token shown as `<set>`. It is not written if the key would appear in it.

### Check run

Job `lc-p3-vanilla-l-small-synthetic-task-01`, vanilla, L-Small (`qwen3.5-9b`, Q4_K_M), on the public synthetic task, no Anthropic key on the host or in the container.

| Item | Value |
|---|---|
| Outcome | Failed: `UnknownApiError`; the SDK result is an error after 10 retries of HTTP 500 |
| Cause | The server's chat template raises `System message must be at the beginning`: a request from Claude Code carries a system message after other messages, and the model's template rejects it. This is not a route fault: the pre-flight check passed, the request reached the server with the key, and the server answered |
| Reward from the verifier | 0.0 (`criteria_satisfied` 0.0, `existing_tests_pass` 1.0, the task's starting state) |
| Wall time | 4 m 35 s for the trial; 3 m 0 s in the agent |
| Turns, tokens | 1 turn; 0 input and 0 output tokens (no request succeeded) |
| Server log | Holds no `claude` or `anthropic` string; the only model name the agent used is the alias; the errors in the log are the template's |
| Repeat | One more run (`lc-p3-vanilla-l-small-synthetic-task-01-retry`) failed the same way in 3 m 50 s, and was used to check that no run record holds the key |
| Key | In the repeat, the key was grepped (fixed string) in `agent/route.json`, `agent/runner.txt`, the trial's `server/` snapshot, Harbor's job log, the trial folder and the run output before the server was stopped: it appears in none. In the first run the same check was lost to a truncated output and is not claimed |
| Independent review | Not run: it calls Anthropic's API and needs the operator's approval |

What it means for the route: the settings reach Claude Code and its requests reach the local server only. What blocks a finished run is the template of the model's chat format, to be decided in Phase 6 with the thinking setting and the fallbacks (for example a template that accepts a late system message, or the L-MoE model).

## Launcher and allowlists

`python -m atr.local.launch <job config> [--model-id <id>] [--port 8090] [--dry-run]` runs one local Harbor job the same way every time. It starts the model's server with a new key, samples the GPU every second, runs `uv run harbor run -c <config> -y` from the Harbor checkout with `HARBOR_TELEMETRY=off` and every `ANTHROPIC_` variable removed from the environment, and always stops the server in a `finally`.

### Refusals

Before anything starts, the launcher refuses:

| Refusal | Check |
|---|---|
| Another Harbor job is running (D-058) | Any `harbor run` process that is not the launcher, its ancestors or its descendants; the message names the job's config. It sees processes only: a batch script waiting between runs is not seen, and the budget's `lc-` filter (Phase 5) keeps the money apart either way |
| The job is not local | The name does not start with `lc-`, an agent is not on route `local` with a `local/<alias>` model, or a task's agent network is not an allowlist without `api.anthropic.com` |
| The model is not one pinned entry | The alias maps to other than one main-stage entry of `models.toml`, and no `--model-id` with that alias was given |
| The job folder exists | No job is resumed or mixed |

### What it writes

Into every trial folder, `server/` holds `server.json`, `slots.json`, `metrics.prom` and `server.log` (what `serve record` writes), `power.csv` (seconds from the sampler's start, power in W, VRAM in MiB, GPU use in %) and `power.json` (samples, mean and peak power, energy in Wh, peak VRAM, mean use, the wall-clock start and end, and the number of trials sharing the samples). Into the job folder it writes `launch.json` (the model id, the server image and the weights' SHA-256, Harbor's exit code, the trials recorded, the wall time); Harbor's output goes to `<jobs dir>/<job name>.launch.log`. The launcher scans what it wrote for the server key and exits non-zero if it appears. Power is the GPU's, as `nvidia-smi` reports it; with one trial per job it belongs to that trial, and with more it is shared and the count says so.

### Allowlist variants

`python -m atr.tasks.build <manifest> --route local` builds `<task id>-local`: the agent's allowlist is the manifest's `network.agent_allowed_hosts_local`, or, when that key is absent, `agent_allowed_hosts` without `api.anthropic.com` and with `host.docker.internal`. A manifest with neither key is not built, nor is a list that names `api.anthropic.com` or lacks `host.docker.internal`. The verifier's network is unchanged, `atr-task.json` keeps the task id and adds `"route": "local"`, and the default build is unchanged. The synthetic task's allowlist is the local server and the Collector on the host and the package index (`host.docker.internal`, `pypi.org`, `files.pythonhosted.org`); its default build keeps the open network. Target A's three variants were built in the private workspace, each with its allowlist checked for `host.docker.internal` and without Anthropic's API; none was run.

### Check run

| Item | Value |
|---|---|
| Job | `lc-p4-launcher-l-small-synthetic-task-01-local`, L-Small (qwen3.5-9b-q4_k_m), run through the launcher on the synthetic task's local variant |
| Outcome | Harbor exited 0 with one trial in error: `UnknownApiError`, the same chat template error as in Phase 3 (`System message must be at the beginning`, 11 times in the server log); reward 0.0. Expected, and left to Phase 6 |
| Records present | `server.json`, `slots.json`, `metrics.prom`, `server.log`, `power.csv` and `power.json` in the trial's `server/`, and `launch.json` in the job folder |
| Power | 248 samples over about 4 minutes, mean 32.9 W, peak 88.3 W, 2.269 Wh, peak VRAM 8003 MiB, mean use 29% |
| Refusal | With a stand-in process named like a Harbor job, a dry run refused, named the job and started no server; once the stand-in was killed, the same dry run passed |
| Cleanup | No `atr-llm` container and no `server.key` remained |
| Key | The launcher's own scan found the key in none of `launch.json`, the launch log and the trial's `server/` files |
| Independent review | Not run |

## Store, budget and export

### Trial columns

| Column | Source |
|---|---|
| `route` | `agent/route.json`'s `provider`, else the job config's `route`, else `anthropic` for a trial with an SDK result; null for agents without one |
| `provider`, `quantization`, `server_build` | `agent/route.json` (`provider`, `quantization`, `build`) |
| `cost_usd`, `cost_source` | A local run: zero with source `local`. An API run: the SDK's total with source `sdk` |
| `sdk_cost_estimate_usd` | A local run's SDK total, kept apart: Claude Code's estimate for a model it cannot price, not money spent |
| `energy_wh`, `power_mean_w` | `server/power.json`; the GPU's energy only, not the whole system's |
| `server_prompt_tokens`, `server_cached_prompt_tokens`, `server_output_tokens` | `server/metrics.prom`: llama.cpp's processed prompt, reused prompt and generated token counters |
| `native_outcome` of a run that failed before an SDK result | The exception type and the first line of Harbor's message when that line is the agent's own; for Harbor's "Command failed" line, the error of the last assistant message in `agent/messages.jsonl` (for example `server_error`), else the exception type. `outcome` is unchanged (`error`) |

### Rules

- Reconciliation: API runs keep today's rule (tokens and cost across the SDK, events and metrics). A local run compares the four token counts across the SDK, events and metrics, and the server's prompt total (processed plus reused) against the SDK's total input (input plus cache read plus cache creation) and its output against the SDK's output. No cost is compared, so a cost the route cannot have never reads as a mismatch. The view gains `route`, `server_prompt`, `server_output` and `sdk_total_input`.
- Budget: `atr.ops.budget` leaves `lc-` jobs out of the total checked against the ceiling and prints them on their own line (the SDK's estimate, and the reviews' cost as Anthropic credit of the local models experiment).
- Export: allowlist version 3 adds `route`, `provider`, `quantization`, `cost_source`, `energy_wh` and a `label` (`workflow portability, quantized local model` for local runs, null otherwise). A local run's model is published as its alias, without the `local/` prefix, which the leak check's relative-path pattern would otherwise read as a file path. The leak check is unchanged.

### Checks

| Item | Result |
|---|---|
| Synthetic check data (one API and one local trial, four sources agreeing, in a temporary folder) | Both trials `match`; the local trial loads with route `local`, cost 0.0 source `local`, SDK estimate 0.37, 1.5 Wh and 50 server output tokens; the API trial keeps 0.5 with source `sdk`; the budget reads `spent: US$ 0.50`, passes `--next 799.4` and stops `--next 799.6`; the export labels the local run and publishes its model as `qwen3.5-9b` under allowlist version 3 |
| Real local trials (3, Phases 3 and 4) | Loaded with route `local`, source `local`, cost 0, build `b12063`, quantization `q4_k_m`, outcome `error` with native reason `server_error` (the chat template's HTTP 500), server counts 0; the Phase 4 trial carries 2.269 Wh (the Phase 3 trials had no power record) |
| The MVP's numbers | Unchanged: 35 trials and US$ 149.80889974 over `m2-` and `m3-` jobs before and after; the budget's spent total US$ 163.81 is the same, with the `lc-` line added |
| Export of the two local jobs | Passed the leak check, with route and label, into a temporary folder and a temporary publication record; the real `publications.jsonl` stayed at 2 lines |
| Matching on a completed local run | Checked in Phase 6 (check L7): the two vanilla runs match; the relay probe differs by 3 input tokens |

## Compatibility checks

The check is run by `atr.local.probe` on a synthetic request: a streamed Messages API request with thinking, two system blocks, a tool set, a tool call and its result, and cache markers, and a random marker that must not appear in the server's log. The tool set is a fixture (`infra/local-inference/claude-code-tools.json`) with the names and input schemas of Claude Code's built-in tools and descriptions of our own; it approximates what Claude Code sends, and checks L2 and L3 use the real requests.

| Check | Model | Result | Date | Notes |
|---|---|---|---|---|
| L1 | L-Small (qwen3.5-9b-q4_k_m) | Pass | 2026-11-04 | HTTP 200, complete event stream, stop reason `end_turn`, blocks thinking (415 characters) and text (122), no error event; `/slots` shows temperature 0.6, top-p 0.95, top-k 20, min-p 0, presence penalty 0; marker not in the log. No thinking-off retry was needed |
| L1 | L-MoE (qwen3.6-35b-a3b-ud-q3_k_xl) | Pass | 2026-11-04 | Loaded with `--cache-ram 2048`; HTTP 200, complete event stream, stop reason `end_turn`, blocks thinking (1488 characters) and text (107), no error event; the same sampling applied; marker not in the log. No thinking-off retry was needed |
| L1 | L-Small on the override | Pass | 2026-11-05 | The same request on the server started with the pinned template override (digest checked at the start, recorded in `server.json`): HTTP 200, complete event stream, stop reason `end_turn`, blocks thinking (304 characters) and text (115), no error event, marker not in the log |
| L2 | L-Small, L-MoE, relay probe | Pass | 2026-11-05 | Every request event that names a model names the alias: 257 in the L-Small vanilla run (`qwen3.5-9b`), 39 in the L-MoE vanilla run and 36 in the relay probe (`qwen3.6-35b-a3b`); every assistant message of the three runs (395, 80 and 71) carries the alias, and `modelUsage` has one key per run. Claude Code logs one `unrecognized_model` notice per run and does not substitute another model. The relay probe's calls are in the same events, with no other model name |
| L3 | L-Small | Pass | 2026-11-05 | 143 tool calls (Read 34, Write 9, Edit 38, Bash 62), every input a JSON object, none leaked into text as a `<tool_call>` block, 143 results. 39 results are errors of the task's own commands (exit codes, a string not found), not malformed calls. No stalled stream and no server error (0 HTTP 500). It needs the template override: without it the first request fails (see The template finding) |
| L3 | L-MoE | Pass | 2026-11-05 | 41 tool calls (Read 21, Bash 15, Edit 5), all well formed, none leaked into text; 4 error results from commands. No stalled stream or server error. The run stopped with 5 of 7 criteria satisfied (reward 0), a quality result and not a tool-call defect |
| L4 | L-Small | Pass | 2026-11-05 | Claude Code compacted automatically twice, at 100428 and 103781 tokens (window 131072), down to 12093 and 10265; the largest context the server held was 126960 tokens; no context error. The first compaction took 1262 s (one summary request generated about 27000 tokens before it ended) and the second 181 s; the server did not time out |
| L4 | L-MoE | Pass | 2026-11-05 | No compaction was needed: the largest context was 40729 tokens, and no request failed with a context error. Compaction was seen on the relay probe |
| L4 | Relay probe (L-MoE) | Pass | 2026-11-05 | Three automatic compactions at 100412, 103160 and 98026 tokens, down to 55052, 67312 and 28638 (210.6 s, 46.0 s and 198.2 s); the largest context was 99020 tokens; no context error |
| L5 | L-Small | Pass | 2026-11-05 | 271760 prompt tokens processed against 6921070 cached (3.8 percent processed) over 139 requests. Consecutive turns select the slot with similarity 0.99 or more; only requests whose prompt differs (the compaction requests, 0.163 to 0.504) reprocess most of the context. No setting needs to change; if compaction time matters in the pilots, the next setting to try is a larger `--cache-ram` |
| L5 | L-MoE | Pass | 2026-11-05 | 37145 tokens processed against 833123 cached (4.3 percent) over 26 requests; slot similarity 0.537 or more throughout |
| L5 | Relay probe (L-MoE) | Partial | 2026-11-05 | 231985 tokens processed against 1011040 cached (18.7 percent) over 21 requests. Reuse between ordinary turns holds; the requests after a compaction have similarity down to 0.201 and reprocess most of the context (1501.6 s of prompt processing in all). Fallback (section 13 of the plan): no setting was changed; the next to try is more prompt-cache RAM, and the runs are slower meanwhile |
| L6 | L-Small, L-MoE, relay probe | Pass | 2026-11-05 | The unchanged verifier graded all three: L-Small reward 1.0 (7 of 7 criteria, existing tests pass), L-MoE reward 0.0 (5 of 7 criteria, 0.7143, existing tests pass), relay probe reward 0.0 (0 criteria, no changes, existing tests pass). The skipped-step check on the relay probe: not flagged, 0 skipped steps. The independent review ran on the L-Small trial (11 findings, US$ 0.206) and on the L-MoE trial (10 findings, US$ 0.173); the relay probe had no changes and was not reviewed, so two of the three approved reviews were used. Static analysis was not part of this phase and was not run: `new_static_findings` is null for these trials |
| L7 | L-Small | Pass | 2026-11-05 | Reconciliation `match` over 139 requests: the SDK's `modelUsage`, Claude Code's events and metrics and the server's counters agree on 271760 processed plus 6921070 cached input tokens and 113739 output tokens |
| L7 | L-MoE | Pass | 2026-11-05 | Reconciliation `match` over 26 requests: 37145 processed plus 833123 cached input tokens and 9105 output tokens |
| L7 | Relay probe (L-MoE) | Partial | 2026-11-05 | Reconciliation `mismatch` over 21 requests, recorded as it is. The SDK, the events and the metrics agree (231985 processed plus 1011043 cached input tokens, 9171 output tokens); the server's counters give 1243025 input tokens in all against 1243028, 3 tokens (0.0002 percent), and the same output. The cause is not isolated; the three compactions are the likely place. The comparison was not loosened. The operator can accept a tolerance of a few tokens or ask for the cause |
| L8 | L-Small, L-MoE, relay probe, limit runs | Partial | 2026-11-05 | The SDK's cost for a model it cannot price is recorded as an estimate and not as money (US$ 7.66, 0.83 and 1.89, loaded with source `local` and cost 0); no run used a USD cap. The time limit works as in the MVP: a 108 s agent limit ended the run as `timed_out` (`AgentTimeoutError`). The turn limit stops the run (`error_max_turns` at a limit of 2) but the SDK raises its result as an error, the runner writes no `agent/result.json`, and the store gives outcome `error` with native reason `NonZeroAgentExitCodeError` instead of `budget_exceeded`. Fallback: an operator decision, to let the runner write the result file for an `error_max_turns` result before it fails (a change outside this phase); until then a local turn-limit stop reads as `error` |
| L9 | L-Small, L-MoE, relay probe, limit runs | Pass | 2026-11-05 | The `network` record in `route.json` of every local run after the change: Anthropic's API unreachable (no HTTP status, curl exit code 35) and the package index reachable (HTTP 200); the server answered the run's own pre-flight check |
| L10 | L-Small | Partial | 2026-11-05 | The server stayed up through the 58 minute run (3502 s of agent time) with no error, at a VRAM peak of 8001 of 8192 MiB; the container held 5.3 GiB of the VM's 17.6 GiB at the start; GPU power 186.8 W mean, 184.6 Wh. The three-hour run was not reached: the longest run took 62 minutes |
| L10 | L-MoE and relay probe | Partial | 2026-11-05 | The server stayed up through a 17 minute and a 37 minute run, with a VRAM peak of 6763 and 7509 MiB and 12.3 and 12.9 GiB of the VM's 17.6 GiB at the start; no out-of-memory stop. The first request of a fresh L-MoE server spent about five minutes before its first token (the experts are read from the memory-mapped file). The three-hour run was not reached; the pilot on the largest task is that test (section 13 of the plan) |

After each request a `serve record` snapshot was taken and the key was found in none of its files or in the check results; the probe's own log check found no marker.

## The template finding

A debug run (L-Small, one turn, the server's verbose log on) found the cause of the HTTP 500 that ended every earlier local run. Every request Claude Code sends reaches the server as three messages after the server's conversion from the Messages API: a system message of 4153 characters (the `system` field), a user message of four text blocks, and a second system message of 8244 characters (the environment and working-directory section of the prompt) after it. The server's conversion puts the top-level `system` field first, so the second system message is a system-role turn that arrives inside the request's messages. All 11 requests of the run had this shape, with 18 tools, and all were rejected with HTTP 500 by the template of Qwen3.5-9B, which raises "System message must be at the beginning." for a system message that is not first (line 85 of the embedded template). The finding is recorded, structure only, in `l3-template-<stamp>.json` under `$ATR_DATA_DIR/local-inference/checks`; the verbose log, which holds the synthetic task's prompt text, stays in that trial's `server` folder. The raw Messages API request is not in the log, so the system-role turn is inferred from the order and the sizes.

The fix is within the plan's fallbacks: a pinned override of the model's own template. `infra/local-inference/templates/qwen3.5-9b-q4_k_m.jinja` is the template read from the server's `/props`, with one change: a system message that is not first is rendered in place as a system turn in the template's own format, instead of raising (deleting the raise alone would drop the message silently). The file starts with a comment naming its source (`unsloth/Qwen3.5-9B-GGUF` at revision `3885219b6810b007914f3a7950a8d1b469d598a5`), its license (Apache 2.0), the date (2026-11-04) and the change. Its SHA-256 is `a4080a6ecb3b1ed244e0a98d028f45c1634225363cb38998375b7d5402889921`, pinned as `chat_template_sha256` in `models.toml`. The launcher mounts the folder read-only at `/templates`; a start fails before any container starts if a `--chat-template-file` is not under `/templates/` or its digest differs from the entry's, and `server.json` records the digest.

L-MoE (Qwen3.6-35B-A3B) needs no override: its embedded template merges up to two leading system messages and does not raise. A system message that follows a user message is not rendered at all, so that model runs without the environment section of Claude Code's prompt (the working directory and the like) in its context. This is recorded here and not corrected; it is a difference between the two models' runs to keep in mind when comparing them.

## The relay probe

The relay probe ran relay 0.49.0 (the MVP's copy at digest `0a9da7c2afdc64d633974cd82fc38b3b260fc01ae1e7c844fd749d3724c81e77`) on L-MoE with `/relay:relay-execute PRPs/prds/event-registration.prd.md` on the synthetic task's local variant. Outcome: the SDK ended with `success` after 45 turns and 2198.7 s, and the workflow did not run. The model read the project's context and answered that it was ready, with no change to the tree (an empty patch), no relay phase started and no orchestrator record, so the store's protocol check has no halt code to report (`protocol_checked` true, 0 skipped steps, not flagged). The verifier gave reward 0 with 0 criteria. It is recorded as a completed run that did not execute the workflow, not as a halt: relay's slash command was recognized (the plugin loaded, with no error), and the model stopped before carrying out the orchestration.

Figures: 231985 processed and 1011040 cached input tokens, 9171 output tokens, 41 tool calls (Read 33, Bash 8), three automatic compactions, 52.4 Wh, peak VRAM 7509 MiB. A model of this size, at this quantization, does not follow relay's orchestration on its own in this run. Whether another prompt or a larger model does is not tested here.

## The runs

| Job | Model | Outcome (native) | Reward (criteria) | Turns | Wall time (s) | Input tokens (processed + cached) | Output tokens | Energy (Wh) |
|---|---|---|---|---|---|---|---|---|
| `lc-p6-debug-l-small-synthetic-task-01-local` | L-Small | error (`server_error`) | 0.0 (0 of 7) | 0 | about 230 | 0 | 0 | not recorded (run by hand) |
| `lc-p6-vanilla-l-small-synthetic-task-01-local` | L-Small | completed (`success`) | 1.0 (7 of 7) | 147 | 3502 | 7192830 (271760 + 6921070) | 113739 | 184.6 |
| `lc-p6-vanilla-l-moe-synthetic-task-01-local` | L-MoE | completed (`success`) | 0.0 (5 of 7) | 42 | 994 | 870268 (37145 + 833123) | 9105 | 15.5 |
| `lc-p6-relay049-l-moe-synthetic-task-01-local` | L-MoE | completed (`success`), workflow not run | 0.0 (0 of 7) | 45 | 2199 | 1243025 (231985 + 1011040) | 9171 | 52.4 |
| `lc-p6-limit-turns-l-small-synthetic-task-01-local` | L-Small | error (`NonZeroAgentExitCodeError`; the SDK's `error_max_turns`, limit 2) | 0.0 (0 of 7) | 2 (limit) | 219 | 37364 (21852 + 15512) | 292 | 5.6 |
| `lc-p6-limit-time-l-small-synthetic-task-01-local` | L-Small | timed_out (`AgentTimeoutError`, 108 s) | 0.0 (0 of 7) | 1 request | 160 | 36851 (21336 + 15515) | 60 | 3.9 |

Reviews: two, on the two vanilla runs, US$ 0.379 together, counted on the `lc-` line of the budget (`atr.ops.budget`), which also shows the SDK's estimate of US$ 10.39 for the local jobs as not money spent; the MVP's total of US$ 163.81 is unchanged. L-Small solved the task in one hour with two compactions; L-MoE at 3-bit stopped early with a partial solution; neither result ranks the models (one run each, different quantizations, the late system message rendered for one and dropped for the other).
