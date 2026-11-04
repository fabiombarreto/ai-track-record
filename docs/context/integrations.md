# Integrations

No secret values appear here. Secrets live in `~/atr/.env` in WSL and are loaded into the shell that starts a batch.

| Integration | Purpose | Auth | Used through |
|---|---|---|---|
| Anthropic API | Model calls of every Claude run and of the independent review | API key (`ANTHROPIC_API_KEY`), paid with the Max plan's included API credits (D-049) | Claude Agent SDK inside the task and reviewer containers |
| Harbor 0.24.0 | Runs tasks in containers, enforces limits and the network allowlist, runs the verifier | None; telemetry off (`HARBOR_TELEMETRY=off`) | `uv run harbor run -c <job>.json -y` from the Harbor checkout, with `PYTHONPATH` set to `harness/src` |
| Docker Desktop (WSL 2 backend) | Task, verifier, reviewer, Collector and inference containers | Local socket | `docker`, `docker compose`; Harbor's egress sidecar for allowlisted runs |
| OpenTelemetry Collector 0.162.0 | Receives Claude Code's metrics and events | None; published on the host's loopback only | OTLP over HTTP at `host.docker.internal:4318` from task containers |
| Package index (PyPI) | Installs a run's added dependencies; installs the SDK and uv in containers | None | Allowlisted hosts `pypi.org`, `files.pythonhosted.org` (D-050) |
| GitHub | Source of relay (`fabiombarreto/PRPs-agentic-eng`) and of this repository | SSH for git; `gh` CLI for pull requests | Copies of relay at exact commits under `~/atr/relay/` (D-054) |
| GitHub Container Registry | llama.cpp's CUDA server image | Anonymous pull | Pinned by digest in `infra/local-inference/models.toml` |
| Hugging Face | Open-weight model files for local inference | Anonymous download | `atr.local.fetch`, pinned by repository revision and SHA-256 (D-057) |
| llama.cpp server (local) | Serves one open-weight model to Claude Code over the Messages API | Bearer key, new per server start (`LLAMA_API_KEY` in the container) | `atr.local.serve`; reached at `host.docker.internal:<port>` |

## Endpoints the harness calls

- Anthropic: the Messages API, through the SDK only. The harness never calls it directly.
- Collector: `POST /v1/logs`, `POST /v1/metrics` (OTLP/HTTP), sent by Claude Code.
- llama.cpp server: `GET /health`, `POST /v1/messages/count_tokens` (key check), `POST /tokenize` and `POST /completion` (benchmark). Claude Code will call `POST /v1/messages` once the local route exists.

## Providers allowed per target

Running an agent sends the target's content to the model's provider. Target A's content may go only to Anthropic's API (D-029) and to open-weight models on the operator's machine (D-057). Other providers, such as Google's Gemini API, are not allowed on Target A (D-055 is open).
