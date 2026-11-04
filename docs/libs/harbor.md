# Harbor

- **Version used:** 0.24.0, a local checkout at `~/atr/tools/harbor`, run with `uv run harbor` and `HARBOR_TELEMETRY=off`. Context7 indexes v0.22.0 and `main`; check differences against the checkout.
- **Docs:** https://github.com/harbor-framework/harbor (Context7 id `/harbor-framework/harbor`).

## Use in this project

- Runner for every run (D-030): task containers, time limits, the network allowlist, the verifier and the trial folders.
- `atr.agents.claude_sdk:ClaudeAgentSdk` is a custom **installed agent**: it extends `BaseInstalledAgent`, installs the Agent SDK in `install()`, runs the runner in `run()` (decorated with `with_prompt_template`) and fills `AgentContext` in `populate_context_post_run()`.
- Jobs run from a JSON config: `uv run harbor run -c <job>.json -y`. The config's `agents` list names the agent by import path (`name: "atr.agents.claude_sdk:ClaudeAgentSdk"`), its `model_name` and its `kwargs` (passed to the agent's options).
- `harbor job resume` continues a job; `harbor job regrade` grades a trial again.

## Patterns from the docs

- Use `exec_as_root` for system packages and `exec_as_agent` for user-level installation and execution.
- `AgentContext` carries `n_input_tokens` (cache included), `n_cache_tokens`, `n_output_tokens`, `cost_usd` and per-model `model_usage`; the agent sets them after the logs are synced.
- `AgentConfig` also supports `base_url`, `model_api_key_name`, `extra_allowed_hosts` and `env`; this project passes its route settings through the agent's own kwargs instead.

## Gotchas

- With a network allowlist in any phase, Harbor routes every Compose service without explicit networking through its egress sidecar: a service's name stops resolving and it answers on `127.0.0.1` (M1 results).
- A killed job leaves its trial's Compose projects behind; run `python -m atr.ops.cleanup <job dir>` before `harbor job resume`.
- The allowlist names hosts, not ports: `host.docker.internal` admits every port published on the host's loopback.
