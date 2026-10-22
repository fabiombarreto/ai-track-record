# Phase 0 results

> **Status:** In progress · **Last updated:** 2026-10-22 · **Owner:** Fabio Martins Barreto

This report records what Phase 0 actually found, work package by work package, against the [Phase 0 plan](../plans/phase-0.md) and its [checks](phase-0-tooling.md#7-phase-0-checks). It is completed at milestone M0.

## Progress

| WP | Status | Date |
|---|---|---|
| 0. API credits, workspace and key | Done | 2026-10-21 |
| 1. WSL 2 environment | Done | 2026-10-21 |
| 2. Harbor and a first Agent SDK run | Done | 2026-10-21 |
| 3. Synthetic target and task | In progress | |
| 4. Relay and vanilla adapters | Not started | |
| 5. Telemetry and loader | Not started | |
| 6. Pilot runs and checks | Not started | |
| 7. M0 review | Not started | |

## WP0 and WP1: environment

- **Model provider:** a Console organization linked to the Max 5x plan, a dedicated workspace with a monthly spend limit, and an API key stored in the operator's WSL workspace. A first Messages API call through the key returned HTTP 200 in the dedicated workspace.
- **WSL:** updated to 3.0.3 with kernel 6.18.54, newer than the 6.18.33 that Harbor's network allowlist needs. `.wslconfig` gives WSL 18 GB of memory, 10 processors and 8 GB of swap, and Docker Desktop sees the same.
- **Tools in Ubuntu:** Docker 29.6.1, uv 0.13.4 and the system Python 3.12.3.
- **Operational note:** commands sent into WSL from Windows must use `wsl.exe --exec`. With `--`, the default shell re-parses quotes and expands variables before the login shell sets `PATH`.

## WP2: Harbor and a first Agent SDK run

### Harbor

- Version 0.24.0 (commit `b53b813`), installed from its lock file with `uv sync --frozen`. It runs on its own Python 3.13 and pulls LiteLLM 1.93.0, well clear of the compromised 1.82.7 and 1.82.8.
- Telemetry: in the source, all three functions that send events return immediately when `HARBOR_TELEMETRY=off`, which the run environment sets. A network-level check is part of check 5.
- The `oracle` agent solved Harbor's `hello-world` task with a reward of 1.0 in 41 seconds, which confirms Docker, the task build and the verifier on this machine.

### Agent SDK agent

[`harness/src/atr/agents/claude_sdk.py`](../../harness/src/atr/agents/claude_sdk.py) is a Harbor agent that installs `claude-agent-sdk` 0.2.170 in the task container and runs [`claude_sdk_runner.py`](../../harness/src/atr/agents/claude_sdk_runner.py) there ([D-049](../decisions/decision-log.md#d-049)). The runner sets Claude Code's system prompt, the project's settings, `bypassPermissions` and the limits, and it stops with an error if the installed SDK does not support a requested option.

First run, on `hello-world` with Claude Haiku 5.5:

| Measure | Value |
|---|---|
| Reward | 1.0 |
| Outcome | `success`, 2 turns |
| Cost | US$ 0.0022 (client-side estimate, list prices) |
| Tokens | 4 input, 140 output, 15,615 cache reads, 15,786 cache writes |
| Agent time | 3.2 seconds, 2.9 of them waiting for the API |
| Whole trial | 62 seconds, including the container build and the SDK install |

What the run showed:

- **Engine version:** SDK 0.2.170 bundles Claude Code **2.1.306**, above the 2.1.304 floor.
- **Model forcing:** `modelUsage` lists only `claude-haiku-5-5`, so no other model was called. The run started no sub-agent, so check 2 is still open.
- **Credentials:** the init message reports the key's source as `ANTHROPIC_API_KEY` and the permission mode as `bypassPermissions`.
- **Records:** Harbor stored tokens, cost and per-model usage from the runner's result. Every SDK message is in `messages.jsonl`, and the session transcript is in the synced logs folder.
- **Built-in plugins:** the SDK loads two of them by default, `cc-plugin-agents-md` and `cc-plugin-plugin-authoring`. They are present in every run, so comparisons stay fair, but check 10 has to confirm that a CLI run loads the same ones.

### Billing

Confirmed on 2026-10-22 in the Console: the purchased balance is US$ 0.00 and the promotional balance went from US$ 100.00 to US$ 99.99, so the spend came from the Max plan's included credits. The current credits apply to the Agent SDK, the API, the Batch API, the Playground and Managed Agents, and they **expire on 2026-11-03**, the M0 date. With no purchased balance, requests stop when the credits run out, which works as a hard spending stop.

## WP3: synthetic target (in progress)

- **Base project:** an events API with create, read and list endpoints, on Django 6.1, Django Ninja 1.7 and PostgreSQL 16, managed with uv. Its five existing tests pass, even with deprecation warnings treated as errors.
- **Relay context:** `CLAUDE.md` and the `docs/` knowledge base were generated with relay's context-builder (`*init`). They describe only the base project, never the task's feature. `methodology.md` declares `tdd: false` and pytest.
- **Still to do:** the task's specification in relay's PRD format, the solution branch with the hidden tests, the task builder, and validation with the `oracle` and `nop` agents.

The target lives in its own local repository in the operator's WSL workspace and will be published once reviewed ([D-046](../decisions/decision-log.md#d-046)).

## Checks so far

| Check | Status | Evidence |
|---|---|---|
| 1. Plugin and version | Partly: version confirmed, plugin loading not yet tested | Init message shows Claude Code 2.1.306 |
| 2. Forced models | Partly: one model only, no sub-agent yet | `modelUsage` keys |
| 5. Privacy | Partly: telemetry disabled in code and configuration | Harbor source |
| 9. Cost | Not yet | |
| 10. SDK parity and billing | Partly: billing confirmed from the included credits; parity with the CLI not yet tested | Console billing page; runner options |
| 3, 4, 6, 7, 8 | Not yet | |
