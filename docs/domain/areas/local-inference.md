# Local inference

## Primary responsibility

Serve open-weight models on the operator's machine, so Claude Code can run Target A's tasks on them without sending anything to a provider (local models plan, D-057, D-058). Code: `atr.local.config`, `atr.local.fetch`, `atr.local.serve`, `atr.local.bench`, `atr.local.probe`, `atr.local.launch`; configuration: `infra/local-inference/models.toml`; tool fixture for check L1: `infra/local-inference/claude-code-tools.json`.

## Entities

Server image, model entry (id, alias, role, stage, repository, revision, file, size, SHA-256, context, flags), verified marker, server record, server key, benchmark result.

## Rules

- Weights are downloaded once from the publisher's or a named quantizer's repository at a pinned revision, and kept only when their size and SHA-256 match `models.toml` (D-057). A verified marker next to the file records the digest.
- The server image is pinned by digest and its build recorded.
- One model per server start. Each start makes a new API key and refuses to continue unless the server rejects a request without the key and accepts one with it.
- A start also fails closed (and stops the container) unless `docker inspect` shows the port published on `127.0.0.1` only, and unless the key is absent from the serialized server record.
- A weights file whose size or digest does not match is renamed `<file>.bad`, so the next fetch downloads afresh; the fetch result line says "present, verified" for an already complete file and "downloaded and verified" only after a download.
- The server is published on the host's loopback only and runs in offline mode; task containers reach it at `host.docker.internal:<port>`, as they reach the Collector.
- The server's record (`server.json`) holds the model, file digest, image, flags, load time and memory use, never the key. The key lives in `server.key`, readable by its owner only.
- Weights live on D: (`/mnt/d/atr/models`), because C: has little free space.
- The server's record also holds the image id, the published address and the machine (GPU, VM memory, processors).
- The benchmark prompt is random words from a fixed seed, never content from any target. It is tokenized and rescaled to within 0.5% of the target and never above it. Energy integrates GPU power over the sample times; container memory is recorded as a peak during the request. The result file is rewritten after every prompt size; a size that fails is recorded with an error, the others still run, and the exit status is non-zero.
- Each main-stage model's `baseline` in `models.toml` names the benchmark file behind its flags; the measurements are in `documentation/research/local-route.md`.
- A start refuses, before any container starts, flags that lack `--offline` or that contain a download flag (`-hf`, `--hf-repo`, `--model-url`, `--docker-repo` and the like). The key check covers `count_tokens`, `/slots` and `/metrics`; the record states `offline` and the endpoints checked.
- Final server flags include `--no-webui`, `--slots`, `--metrics`, `--parallel 1` and a per-model `--cache-ram` (4096 MiB for L-Small, 2048 MiB for L-MoE), a first value that check L5 revisits.
- `serve record <folder>` writes `server.json`, `slots.json`, `metrics.prom` and `server.log` for the running server. `/slots` returns each slot's prompt and generated text, so the copy drops both fields; nothing is written if the key appears in any file.
- Check L1 (`atr.local.probe`) sends one synthetic streamed Messages API request (thinking, two system blocks, tools, a tool call and result, cache markers, a random marker) and passes on a complete event stream without an error event, sampling shown in `/slots`, and the marker absent from the server log. Its result file holds block types and lengths only, never the key or the response text. Results are in `documentation/research/local-route.md`.
- Local runs never start while an MVP job is running; the MVP keeps priority over the machine (D-058). `atr.local.launch` refuses while any other `harbor run` process exists (it sees processes only, not a batch script waiting between runs), refuses a job that is not local (name not `lc-`, agent not on route `local` with a `local/<alias>` model, or an agent network that is not an allowlist without `api.anthropic.com`), an alias that is not one main-stage model (unless `--model-id` has that alias), and an existing job folder.
- The launcher runs Harbor with no `ANTHROPIC_` variable, samples GPU power every second, writes `server/` and the power files into each trial and `launch.json` into the job folder, scans what it wrote for the server key (exit non-zero if found) and always stops the server. Power is the GPU's; with more than one trial it is shared and `trials_sharing_samples` says so.
- `atr.tasks.build --route local` builds `<task id>-local` with the agent allowlist `network.agent_allowed_hosts_local`, or `agent_allowed_hosts` without `api.anthropic.com` and with `host.docker.internal`; a manifest with neither key, or a list naming `api.anthropic.com` or lacking `host.docker.internal`, is not built. `atr-task.json` adds `"route": "local"`; the default build is unchanged.
- The server mounts `infra/local-inference/templates` read-only at `/templates`. L-Small runs with `--chat-template-file /templates/qwen3.5-9b-q4_k_m.jinja`, its embedded template changed so that a system message after the first user message is rendered in place as a system turn instead of raising (Claude Code appends such turns mid-conversation); the file header names source, revision, license and the change. `check_args` refuses a `--chat-template-file` outside `/templates/` or whose SHA-256 differs from the entry's `chat_template_sha256`, and `server.json` records the digest.
- L-MoE has no template override: its embedded template does not raise but silently skips a system message after the first user message, so L-MoE runs lack Claude Code's environment section. Read its results with that limitation.
- The local pre-flight in `atr.agents.claude_sdk` also probes `api.anthropic.com` and `pypi.org` with bare curl (no route environment) and records the result as `network` in `agent/route.json`; a probe failure never fails the run.
- Results are labeled as workflow portability on a quantized model on consumer hardware, never as a model ranking.

## Relationships

Feeds runs through the `route: "local"` option in `atr.agents.claude_sdk`, which reads `server.json` and `server.key` and writes `agent/route.json`; `atr.local.launch` starts the server and runs the job; the store loads route, energy and server token records (see store-and-publication), and the budget reports `lc-` jobs apart from the ceiling.

## Main flow

`atr.local.fetch` → `atr.local.serve start <id>` → `atr.local.bench` / `atr.local.probe` → `atr.local.serve record <folder>` → `atr.local.serve stop`. A whole job: `atr.tasks.build --route local` → `atr.local.launch <job config>`.

## Open Questions

- `--n-cpu-moe` (34 for L-MoE) and context (131072) were measured in WP0; the final flags and `--cache-ram` were set in Phase 2 and check L1 passed for both main models. Whether the cache budget holds under real prefix reuse is check L5.
- Loading from D: worked (L-Small 60 s, L-MoE 255 s); whether L-MoE needs a warm-up request, because its first request is slower while experts enter the page cache, is open.
- L-Small has about 0.2 GB of VRAM free at a full 128k prompt; whether runs sharing the desktop need a lower context is open.
- Whether llama.cpp reuses the prompt prefix of hybrid-attention models between Claude Code's requests is check L5 of the plan.
