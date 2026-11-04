# Local inference

## Primary responsibility

Serve open-weight models on the operator's machine, so Claude Code can run Target A's tasks on them without sending anything to a provider (local models plan, D-057, D-058). Code: `atr.local.config`, `atr.local.fetch`, `atr.local.serve`, `atr.local.bench`; configuration: `infra/local-inference/models.toml`.

## Entities

Server image, model entry (id, alias, role, stage, repository, revision, file, size, SHA-256, context, flags), verified marker, server record, server key, benchmark result.

## Rules

- Weights are downloaded once from the publisher's or a named quantizer's repository at a pinned revision, and kept only when their size and SHA-256 match `models.toml` (D-057). A verified marker next to the file records the digest.
- The server image is pinned by digest and its build recorded.
- One model per server start. Each start makes a new API key and refuses to continue unless the server rejects a request without the key and accepts one with it.
- The server is published on the host's loopback only and runs in offline mode; task containers reach it at `host.docker.internal:<port>`, as they reach the Collector.
- The server's record (`server.json`) holds the model, file digest, image, flags, load time and memory use, never the key. The key lives in `server.key`, readable by its owner only.
- Weights live on D: (`/mnt/d/atr/models`), because C: has little free space.
- The benchmark prompt is random words from a fixed seed, never content from any target.
- Local runs never start while an MVP job is running; the MVP keeps priority over the machine (D-058).
- Results are labeled as workflow portability on a quantized model on consumer hardware, never as a model ranking.

## Relationships

Will feed runs through a route option in `atr.agents.claude_sdk` (planned), and the store through route and energy records (planned).

## Main flow

`atr.local.fetch` → `atr.local.serve start <id>` → `atr.local.bench` → `atr.local.serve stop`.

## Open Questions

- Flag values (`--n-cpu-moe`, context, prompt-cache RAM) are first guesses until the WP0 measurements [INFERRED - VALIDATE].
- Whether loading weights from D: through Docker Desktop's file sharing is fast enough, or whether the server should lock them in memory, is untested.
- Whether llama.cpp reuses the prompt prefix of hybrid-attention models between Claude Code's requests is check L5 of the plan.
