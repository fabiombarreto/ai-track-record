# Claude Agent SDK (Python)

- **Version used:** 0.2.170, installed in each task and reviewer container in a uv venv (`/opt/atr-sdk-venv`). It bundles the Claude Code engine, so the SDK version fixes the engine (D-049).
- **Docs:** https://github.com/anthropics/claude-agent-sdk-python (Context7 id `/anthropics/claude-agent-sdk-python`); Claude Code's settings and environment variables at https://code.claude.com/docs.

## Use in this project

- `claude_sdk_runner.py` runs one task: `query()` with `ClaudeAgentOptions` and writes every message to `messages.jsonl` and the last result to `result.json`.
- Options set: `system_prompt = {"type": "preset", "preset": "claude_code"}`, `setting_sources = ["project"]`, `permission_mode = "bypassPermissions"`, `max_turns`, `max_budget_usd`, `plugins = [{"type": "local", "path": ...}]` for relay, `disallowed_tools` (web tools off on Target A), a fixed session id.
- `reviewer.py` runs `/code-review` the same way and collects findings through a second turn.

## Patterns from the docs

- `setting_sources` decides which filesystem settings load; `"project"` is required to load `CLAUDE.md`. `None` loads all, `[]` none.
- Only local plugins are supported (`SdkPluginConfig` with `type: "local"`).
- `ResultMessage` carries `subtype`, `duration_ms`, `duration_api_ms`, `num_turns`, `total_cost_usd`, `usage` and `model_usage`.

## Gotchas

- A session that waits on background sub-agents emits one result message per resumption. Each carries cumulative cost and usage, but `duration_ms` and `num_turns` cover only its segment; the runner records `atr_wall_ms` and `atr_num_turns` itself.
- `ResultMessage.is_error` can be true with `subtype == "success"` when an API call failed; the HTTP status is then reported.
- `total_cost_usd` and `max_budget_usd` use a client-side price table. For a model Claude Code does not know (a local model), the cost basis is unknown and the USD cap cannot be relied on.
- Behind a custom base URL, Claude Code assumes a 200K context for an unknown model id and stops waiting on a stream idle for five minutes; set `CLAUDE_CODE_MAX_CONTEXT_TOKENS`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW` and the idle timeouts for local routes.
