# Phase 0 results

> **Status:** In progress · **Last updated:** 2026-10-22 · **Owner:** Fabio Martins Barreto

This report records what Phase 0 actually found, work package by work package, against the [Phase 0 plan](../plans/phase-0.md) and its [checks](phase-0-tooling.md#7-phase-0-checks). It is completed at milestone M0.

## Progress

| WP | Status | Date |
|---|---|---|
| 0. API credits, workspace and key | Done | 2026-10-21 |
| 1. WSL 2 environment | Done | 2026-10-21 |
| 2. Harbor and a first Agent SDK run | Done | 2026-10-21 |
| 3. Synthetic target and task | Done | 2026-10-22 |
| 4. Relay and vanilla adapters | Done | 2026-10-22 |
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

## WP3: synthetic target and task

- **Base project:** an events API with create, read and list endpoints, on Django 6.1, Django Ninja 1.7 and PostgreSQL 16, managed with uv. Its five existing tests pass, even with deprecation warnings treated as errors.
- **Relay context:** `CLAUDE.md` and the `docs/` knowledge base were generated with relay's context-builder (`*init`). They describe only the base project, never the task's feature. `methodology.md` declares `tdd: false` and pytest.
- **Specification:** written and approved with `/relay:relay-prd` on 2026-10-22, in an interactive session outside the measured run ([D-014](../decisions/decision-log.md#d-014)). It has seven acceptance criteria, one more than the plan proposed: re-registering after a cancellation. It also has an interface contract for the three registration endpoints and eight behavioral rules. Concurrency stays out of scope.
- **Base commit:** the base project, the relay context and the approved specification, tagged `task-01-base`.
- **Solution branch:** a reference implementation that derives each registration's status and waitlist position from creation order and capacity. With it comes `tests/test_registrations.py`, 16 hidden tests named after the criteria they check. Tagged `task-01-solution`.
- **Oracle validity (TGT-04), checked by hand:** on the solution all 21 tests pass (16 hidden and 5 existing) with deprecation warnings treated as errors. On the base commit all 16 hidden tests fail. One test first passed on the base, because a missing route also returns 404. It now also checks the contract's JSON `detail` body, which a missing route does not return.
- **Task builder:** [`harness/src/atr/tasks/build.py`](../../harness/src/atr/tasks/build.py) reads a manifest ([`targets/synthetic-events/task-01.toml`](../../targets/synthetic-events/task-01.toml)) and the target's templates, and writes a Harbor task to `~/atr/data/tasks/`:
  - The agent's environment is the base commit as a repository with one commit, tagged `base`, next to its own PostgreSQL.
  - The separate verifier has a clean copy of the base commit, its own PostgreSQL, and the tests in `/grading`, outside the agent's code.
  - The reference solution is the solution branch's changes without the hidden tests.
- **Grading:** [`grade.py`](../../harness/src/atr/tasks/grade.py) runs in the verifier and takes only the git diff of the agent's `/app` against `base`, so files ignored by git never cross. It applies that diff to the clean copy, runs the pristine existing tests and the hidden tests from `/grading`, where no `conftest.py` written by the agent is loaded, and writes `reward.json` with three metrics: `reward`, `criteria_satisfied` and `existing_tests_pass`.
- **Validation through Harbor:**

  | Agent | Reward | Criteria satisfied | Existing tests | Hidden tests | Time |
  |---|---|---|---|---|---|
  | `oracle` | 1.0 | 1.0 (7 of 7) | 1.0 | 16 of 16 | 64 s |
  | `nop` | 0.0 | 0.0 | 1.0 | 0 of 16 | ~60 s |

  The `oracle` run's diff, extracted from the agent's `/app`, held the four solution files; the `nop` run's diff was empty.
- **Agent image:** a build of the agent's environment shows one commit (`Base commit`, tag `base`), no remotes and no hidden test file.

The target lives in its own local repository in the operator's WSL workspace and will be published once reviewed ([D-046](../decisions/decision-log.md#d-046)).

## WP4: relay and vanilla adapters

### Adapters

Both configurations use the same Agent SDK agent. The relay configuration adds four options:

- **`prompt`** replaces the task instruction with the workflow's entry command, `/relay:relay-execute PRPs/prds/event-registration.prd.md`.
- **`plugin_dir`** loads relay from a read-only mount of the pinned checkout, commit `e1844b6` (version 0.47.0).
- **`install_node`** installs Node.js 20 in the agent's container. Relay's helper scripts need it. It is a dependency of the workflow, not of the target.
- **`collect_worktrees`** copies relay's changes back for grading. Relay leaves its changes uncommitted in `.worktrees/<feature>`, which git ignores, so after the run the runner applies each worktree's diff against `base` to `/app`. The outcome is recorded in `worktrees.json`.

Two fixes apply to both configurations:

- **Workspace trust.** The runner marks the workspace as trusted, as an operator does once in the CLI. Without it, Claude Code ignored the project's 53 allow rules.
- **Python downloads.** The SDK install allows Python downloads, because the task image forbids them for its own project.

A smoke test cost US$ 0.005. It showed that relay loads with no `plugin_errors`, that Node.js runs, and that a file written in a worktree reaches the grader's diff.

### Runs on task 01 with Claude Haiku 5.5

Each run had a soft cap of US$ 5. The two ran in parallel.

| Measure | Relay | Vanilla |
|---|---|---|
| Reward | 1.0 | 1.0 |
| Criteria satisfied | 7 of 7 | 7 of 7 |
| Existing tests | Pass | Pass |
| Cost | US$ 1.195 | US$ 0.029 |
| Agent time | 18.5 min | 1.8 min |
| Whole trial | 20.2 min | 2.9 min |
| Turns in the main thread | 74 | 20 |
| Sub-agents | 14 | 0 |
| Output tokens (thinking) | 259,703 (148,594) | 22,855 (8,673) |
| Cache reads / writes | 15.7 M / 922 k | 1.0 M / 60 k |
| Uncached input tokens | 196,804 | 38 |
| Files changed | 33, of which 12 are code, tests and docs | 10 |

Costs are the SDK's client-side estimate at list prices.

What the runs showed:

- **Relay runs unattended.** `/relay:relay-execute` ran the whole pipeline with no prompt: plan, plan review, test writing and review, implementation, code review, test run, post-green review and docs sync. It finished with the PRD row at `complete` and its changes uncommitted, as designed. Along the way it reopened an approved plan to fix a wrong route prefix in a validation command, then had it reviewed again. Its own summary flags this as a deviation from the strict flow.
- **Worktree collection works.** Relay wrote its PRD row and the completed plan in `/app`, and the code, tests, docs and most reports in the worktree. The worktree's 55 kB diff applied to `/app` with no conflict.
- **Forced model, with sub-agents.** All 14 sub-agent definitions that relay dispatched declare `model: sonnet`. Even so, `modelUsage` lists only `claude-haiku-5-5`, so the forced model reaches sub-agents too.
- **Project rules hold under `bypassPermissions`.** The project's deny rules blocked two `rm -rf` cleanups of relay's scratch folders in `/tmp`. The run carried on and reported the leftovers.
- **Task 01 does not separate the two configurations.** Both scored 1.0. Relay cost 41 times as much and took 10 times as long. The synthetic task tests the pipeline, not the workflows. The MVP's tasks must be hard enough for quality to differ, and the cost of relay's process must be weighed against what it adds: 24 tests of its own, docs updates, and review records.

### Findings for later work packages

- **Network use by the agent (check 5).** Each configuration reached the internet beyond the model API:
  - Vanilla added the `email-validator` package, downloaded from PyPI. The verifier then installed it, so the verifier also needs network access.
  - Relay's research sub-agent ran three web searches and six page fetches about the feature's design, such as waitlist promotion and 409 versus 422. The fetches went from the container to external sites.

  For the public synthetic target this is harmless. For Target A, search queries and fetched URLs could reveal what the product is building. Before Target A runs, WP6 or M0 must decide one of two options:
  - disable `WebSearch` and `WebFetch` for Target A runs and restrict the container's network;
  - accept them and record the queries.

## Checks so far

| Check | Status | Evidence |
|---|---|---|
| 2. Forced models | Partly: `modelUsage` passes, including 14 sub-agents pinned to Sonnet; the `api_request` events wait for WP5 | `modelUsage` keys of the relay run |
| 5. Privacy | Partly: Harbor's telemetry is off, but the agents reached PyPI and, in relay's run, external websites | Harbor source; WP4 tool calls |
| 9. Cost | Not yet | |
| 10. SDK parity and billing | Partly: billing confirmed from the included credits; the SDK loads relay, the project settings and Claude Code's system prompt, but no CLI run has been compared | Console billing page; init message; runner options |
| 1. Plugin and version | Passed | Init message lists relay 0.47.0 with no `plugin_errors`, on Claude Code 2.1.306 |
| 3. Hidden tests | Passed | The agent image has no hidden test file; the separate verifier scores; `oracle` 1.0 and `nop` 0.0 |
| 4. No history leakage | Passed | `git log --all` in the agent image shows only the base commit, with no remotes |
| 6, 7, 8 | Not yet | |
