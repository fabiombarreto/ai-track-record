# Phase 0 results

> **Status:** In progress · **Last updated:** 2026-10-23 · **Owner:** Fabio Martins Barreto

This report records what Phase 0 actually found, work package by work package, against the [Phase 0 plan](../plans/phase-0.md) and its [checks](phase-0-tooling.md#7-phase-0-checks). It is completed at milestone M0.

## Progress

| WP | Status | Date |
|---|---|---|
| 0. API credits, workspace and key | Done | 2026-10-21 |
| 1. WSL 2 environment | Done | 2026-10-21 |
| 2. Harbor and a first Agent SDK run | Done | 2026-10-21 |
| 3. Synthetic target and task | Done | 2026-10-22 |
| 4. Relay and vanilla adapters | Done | 2026-10-22 |
| 5. Telemetry and loader | Done | 2026-10-22 |
| 6. Pilot runs and checks | Done | 2026-10-23 |
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

## WP5: telemetry and loader

- **Collector:** [`infra/otel-collector/`](../../infra/otel-collector/) runs the contrib image, pinned at 0.162.0, the latest stable release. It listens for OTLP over HTTP on port 4318, published on the WSL host's loopback only, and writes `logs.jsonl` and `metrics.jsonl` to `~/atr/data/telemetry/`. Task containers reach it at `host.docker.internal:4318`.
- **Per-run settings:** with the `otel_endpoint` option set, the agent turns Claude Code's telemetry on:
  - OTLP over `http/protobuf`, with one-second export intervals;
  - ten-second flush and shutdown timeouts, so the last batch is sent when the run ends;
  - `OTEL_LOG_TOOL_DETAILS=1`, so plugin agents keep their names instead of `custom`;
  - resource attributes for the job, the trial, the configuration and the model.

  Prompt and response text stay out of the telemetry. Each run also gets a fixed session ID derived from its trial. The variable names were checked against the Claude Code binary bundled with the SDK.
- **Loader:** [`harness/src/atr/store/load.py`](../../harness/src/atr/store/load.py) rebuilds `~/atr/data/atr.duckdb` on every run.
  - Tables: `trials`, `model_usage`, `events` and `metric_points`. They come from Harbor's results, the runner's result and the Collector's files.
  - Views: `reconciliation` and `usage_by_agent`. Telemetry joins to its trial on the resource attributes.
  - The `reconciliation` view compares the `api_request` events, the token and cost metrics, and the SDK's `modelUsage`, per trial, model and token type.
- **First reconciled run:** vanilla on Haiku on task 01 again, with telemetry on. Reward 1.0, US$ 0.022.
  - The three sources agree exactly over 14 requests: 28 input, 16,245 output, 608,974 cache-read and 60,807 cache-write tokens, and the same cost to the last digit.
  - The run's events: 14 `api_request`, 16 `tool_decision`, 16 `tool_result`, 11 `assistant_response`, 2 `plugin_loaded` and one `user_prompt`.

### Clock jumps

The Windows clock is about two minutes behind; an internet time source agrees with WSL. During the run, the WSL clock jumped back to match Windows for a moment. The first events of the run carry timestamps two minutes before the run started, although their sequence numbers come after the session's first event. Two consequences:

- The loader orders events by `event.sequence`.
- Durations come from the SDK's `duration_ms` and the events' own `duration_ms`, never from wall-clock differences.

Syncing the Windows clock reduces the jumps. It is a system setting, so the operator does it.

The operator synced the Windows clock to NTP.br on 2026-10-22: the offset is now −0.004 s, down from +116 s.

## WP6: pilot runs and checks

### Pilot runs on task 01

The three pilots ran in parallel on 2026-10-22, each with telemetry on and a soft cap of US$ 5.

| Measure | Relay on Haiku | Relay on Sonnet | Vanilla on Sonnet |
|---|---|---|---|
| Reward | 1.0 | 1.0 | 1.0 |
| Criteria satisfied | 7 of 7 | 7 of 7 | 7 of 7 |
| Existing tests | Pass | Pass | Pass |
| Outcome | `completed` | `completed` | `completed` |
| Cost | US$ 1.041 | US$ 2.787 | US$ 0.178 |
| Agent time | 32.9 min | 9.2 min | 1.0 min |
| API requests | 144 | 88 | 6 |
| Turns in the main thread | 64 | 46, over 9 result messages | 7 |
| Sub-agents | 14 | 12 | 0 |
| Output tokens | 208,092 | 70,258 | 6,468 |
| Cache reads / writes | 10.4 M / 1.31 M | 5.1 M / 604 k | 156 k / 39 k |
| Uncached input tokens | 248,313 | 42,419 | 12 |
| Files changed | 33 | 19 | 6 |

Costs are the SDK's client-side estimate at list prices, and they match the telemetry exactly. Agent time is Harbor's agent phase.

What the pilots showed:

- **Task 01 still does not separate the configurations.** All three scored 1.0, as did the WP4 runs. Relay on Sonnet cost 16 times as much as vanilla on Sonnet.
- **Relay's process depends on the model.** On Haiku, relay ran the full pipeline: a worktree, docs sync, and every downstream command adopted inline. On Sonnet it shortened the protocol and reported each deviation in its summary:
  - it worked in `/app` instead of a worktree;
  - it skipped the docs sync;
  - it dispatched the agents directly instead of adopting `/relay-implement` and `/relay-test`.

  The grade does not see this. Protocol adherence needs a measure of its own, for example from relay's `orchestrator-run.json`.
- **Variance between repetitions is large.** Relay on Haiku took 18.5 min and US$ 1.195 in WP4 and 32.9 min and US$ 1.041 here, on the same task, model and pin. Comparisons need repetitions ([D-020](../decisions/decision-log.md#d-020)).
- **A session can end in several result messages.** Relay on Sonnet ran sub-agents in the background, and the SDK emitted one result message each time the session resumed. Each carries the cumulative cost and usage, but `duration_ms` and `num_turns` cover only its own segment. The pilot's last result reported 21 s and 5 turns for a 9-minute run. The runner now also records its own wall time (`atr_wall_ms`), the turns summed over all result messages (`atr_num_turns`) and their count, and the loader prefers those.

### Background model (check 2)

In the relay run on Sonnet, the two calls that summarise WebFetch pages (`query_source` `web_fetch_apply`) went to Claude Haiku: 2 requests, US$ 0.0022. They use the `haiku` alias, which `CLAUDE_CODE_SUBAGENT_MODEL` does not cover. Every sub-agent request was on Sonnet, as were the main thread's.

The agent now also sets `ANTHROPIC_DEFAULT_HAIKU_MODEL` to the model under test. In a check run on Sonnet that made one WebFetch call, the `web_fetch_apply` request went to Sonnet, and `modelUsage` listed only Sonnet. Runs on Haiku were never affected.

### Telemetry per agent (check 6)

- Every trial with telemetry that ended with a result reconciles exactly across the `api_request` events, the metrics and `modelUsage`: 12 trials, from 4 to 144 requests.
- The `usage_by_agent` view adds up to each run's total: 17 rows to US$ 1.0415 for relay on Haiku, and 15 rows to US$ 2.7875 for relay on Sonnet.
- Relay's agents appear by name, for example `relay:plan-writer` and `relay:code-reviewer`, with `query_source` `agent:custom`. Claude Code's own agents appear as, for example, `general-purpose` with `agent:builtin:general-purpose`. Web tool calls are counted under the main thread, with `query_source` `web_search_tool` and `web_fetch_apply`.

Relay's biggest costs on both models were the main thread (US$ 0.77 each), then plan-writer, code-reviewer and plan-reviewer.

### Killed run (check 7)

A relay run on Haiku with the agent timeout cut to 486 s (`--agent-timeout-multiplier 0.045`):

- Harbor stopped the agent at 486 s with `AgentTimeoutError`, then ran the verifier anyway. The trial scored 0.0 with the existing tests passing.
- There was no SDK result. The telemetry kept 63 `api_request` events, the last one 6 s before the kill. Their cost, US$ 0.605, matches the cost metric. They include the requests of three relay sub-agents.
- The loader now maps outcomes to [D-019](../decisions/decision-log.md#d-019)'s vocabulary and keeps the native one: this trial is `timed_out`, with `AgentTimeoutError`. A run on the SDK's budget or turn limit is `budget_exceeded`, and agents with no SDK result, such as `oracle`, have no outcome.
- **Gap:** the timeout kills the runner before it collects relay's worktree. The graded diff held relay's plan and reports in `/app`, but not the code being written in `.worktrees/event-registration`. A timed-out relay run is therefore graded without its partial code. Collecting worktrees has to move out of the runner, for example into a step Harbor runs after the agent phase.

### Stability (check 8)

Task 01 takes 1 to 33 minutes, so the hour-long runs used a stand-in workload, agreed with the operator. Three vanilla trials on Haiku ran in parallel in one job (`-k 3 -n 3`). Each was told to run `python3 -c "import time; time.sleep(540)"` seven times, one foreground Bash call at a time, and then to implement the task. A two-minute version was tried first.

| Trial | Agent time | Waits | Reward | Requests | Cost |
|---|---|---|---|---|---|
| 1 | 64.8 min | 7 of 7 | 1.0 | 19 | US$ 0.035 |
| 2 | 64.9 min | 7 of 7 | 1.0 | 24 | US$ 0.041 |
| 3 | 64.8 min | 7 of 7 | 1.0 | 23 | US$ 0.026 |

The job took 66 minutes. All three trials reconciled exactly, and no container was left behind. The relay timeout and resume tests ran alongside them for their first few minutes.

This shows that containers, Docker Desktop, WSL 2, Harbor, the Collector and the verifier hold up for more than an hour with three runs in parallel. It does not show an hour of steady API load: the agents were idle for most of it. The pilots were the heaviest parallel load, with three runs of up to 33 minutes and 144 requests.

**Resume.** A job of two vanilla trials on Haiku ran one trial at a time. Harbor was killed with SIGKILL 60 s into the second trial, then resumed with `harbor job resume`:

- The finished trial was kept, and the killed one was discarded and run again from scratch. Both scored 1.0.
- The killed trial's containers kept running, idle. Its agent process had died with Harbor, so it spent nothing more, but the containers had to be removed by hand.
- The killed trial's 15 requests stay in the telemetry, joined to a trial folder that no longer exists. Their cost counts towards the total even though no result records it.

**Timed-out run graded.** The killed relay run above was graded after its timeout.

**Restart.** The machine restarted on 2026-10-22, after the pilots had finished. The Collector did not come back by itself, despite `restart: unless-stopped`: it exited with code 127 and had to be started by hand. A run started while the Collector is down would lose its telemetry without notice, so the harness needs a check that the Collector is up before a run starts.

### Network (check 5)

**With an open network,** which every run so far used, the agents reached third parties during the run:

| Run | Outside the model API |
|---|---|
| Vanilla on Haiku (WP4, WP5 and the WP6 resume test) | PyPI, to add `email-validator` |
| Vanilla on Sonnet (WP6) | Nothing: it validated emails without a new package |
| Relay on Haiku (WP6) | PyPI; 2 web searches; 8 fetches from `www.rfc-editor.org`, `http.dev` and `apiguide.dev` |
| Relay on Sonnet (WP6) | 2 web searches; fetches from `docs.djangoproject.com` and `github.com` |
| Relay on Haiku, timed out (WP6) | 2 web searches; fetches from `www.rfc-editor.org` and `github.com` |

The searches and fetches come from relay's research sub-agent. Telemetry records the tool calls but not their URLs or queries, even with `OTEL_LOG_TOOL_DETAILS=1`. They are only in the session transcripts.

**With Harbor's network allowlist:** a copy of task 01 set the agent phase to `network_mode = "allowlist"` with only `api.anthropic.com` and `host.docker.internal`. A vanilla run on Haiku then tried four calls:

| Call | Result |
|---|---|
| `curl https://pypi.org/simple/` | Blocked (TLS error) |
| `curl https://us.i.posthog.com/` | Blocked (TLS error) |
| WebFetch `https://example.com` | Blocked ("Socket is closed") |
| WebSearch "django ninja" | **Worked**: the search runs on the provider's side, behind the model API |

The run itself worked, the Collector received its telemetry, and the agent install still had the network it needs. So the allowlist works on this machine with WSL's 6.18.54 kernel, which settles the plan's network risk.

Harbor's own PostHog telemetry is off according to its source (WP2), but it runs on the WSL host, outside the allowlist, and no network-level capture of it was made.

**Options for Target A, for the M0 decision:**

1. **Model API only:**
   - the allowlist with `api.anthropic.com` and the Collector;
   - `WebSearch` and `WebFetch` disabled, which needs a `disallowed_tools` option in the runner;
   - every dependency pre-installed in the task image.

   A task whose solution adds a package then fails unless the package is already there.
2. **Model API plus the package index:** as option 1, with `pypi.org` and `files.pythonhosted.org` (or Target A's own registries) allowed. The verifier then needs the same access, since it installs what the agent added.
3. **Open network:** web tools kept, with their queries and URLs extracted from the transcripts and recorded. This is the least private option, because search queries can reveal what Target A is building.

### Agent SDK and CLI parity (check 10)

No credits were spent on this check. In a container built from task 01's image, the same prompt went through the Agent SDK with the runner's options and through the CLI bundled with it, `claude -p` 2.1.306. The prompt was `/relay:relay-execute PRPs/prds/event-registration.prd.md`, with relay loaded, a fresh configuration folder and a placeholder key. Both sides pointed `ANTHROPIC_BASE_URL` at a local stand-in that recorded each request body and answered with an error.

- **Init messages:** identical except for a socket path. Both show the same 21 tools, 68 slash commands, 28 agents and 17 skills, the same three plugins (relay 0.47.0 and the two built-ins), `bypassPermissions` and an `ANTHROPIC_API_KEY` key source.
- **Requests:** four on each side, identical except for:
  - the session and device IDs;
  - the billing header's entry point, `sdk-py` against `sdk-cli`;
  - one default in the Bash tool's description: background commands may run 30 minutes through the SDK and 10 minutes through the CLI.

  The system prompt, the tool definitions, `CLAUDE.md` in the first message and the expanded relay command were all byte for byte the same.

This compares the SDK with the headless CLI. An interactive session on a subscription was not compared, because benchmark runs never use one.

### Cost against the provider (check 9)

The harness's own total covers every trial since 2026-10-21. It uses the SDK's cost where a run ended with a result, and the `api_request` events where it did not: the timed-out run and the killed trial of the resume test. That total is **US$ 6.110** over 22 trials, US$ 4.861 of it in WP6.

On 2026-10-23, after the last run, the operator read the Console's cost page for the dedicated workspace:

| Console | Amount |
|---|---|
| Total cost | **US$ 6.12** |
| Token cost | US$ 5.19 |
| Web search cost | US$ 0.07 |
| Code execution and session runtime cost | US$ 0.00 |

The totals differ by US$ 0.01, under 0.2%. The WP0 test call, which no trial records, and rounding to cents account for it. The comparison holds only for the total:

- The cards shown do not break down the remaining US$ 0.86.
- The daily chart splits the token cost between 2026-10-22 and 2026-10-23 differently from the trials' UTC start times, so a per-day comparison is not meaningful.

The SDK's estimate is therefore a sound cost record for these runs. The Console stays the reference for the D-028 budget.

## Checks

Every check now has a result. Harbor passed checks 1, 3 and 8, and the SDK passed check 10, so neither fallback is triggered. The M0 review records the decisions ([D-030](../decisions/decision-log.md#d-030), [D-049](../decisions/decision-log.md#d-049)).

| Check | Status | Evidence |
|---|---|---|
| 1. Plugin and version | Passed | Init message lists relay 0.47.0 with no `plugin_errors`, on Claude Code 2.1.306 |
| 2. Forced models | Passed, with the background model pinned since 2026-10-23. Sub-agents ran on the model under test on Haiku and Sonnet, including relay's agents that declare `model: sonnet`. WebFetch's summary calls used Haiku in a Sonnet run until `ANTHROPIC_DEFAULT_HAIKU_MODEL` was set | `modelUsage` and `api_request` events of the WP6 relay runs and the pin check run |
| 3. Hidden tests | Passed | The agent image has no hidden test file; the separate verifier scores; `oracle` 1.0 and `nop` 0.0 |
| 4. No history leakage | Passed | `git log --all` in the agent image shows only the base commit, with no remotes |
| 5. Privacy | Passed with the network allowlist; the open network the pilots used fails it. Under the allowlist, PyPI, PostHog and WebFetch were blocked and only the model API and the Collector were reached. WebSearch still works through the model API, so keeping queries private needs the tool disabled. Harbor's own telemetry is off by its source only | Allowlist check run; WP4–WP6 tool calls and transcripts |
| 6. Telemetry | Passed | `reconciliation` view: exact match for every trial with telemetry and a result; `usage_by_agent` sums to each run's total, with relay's agent names |
| 7. Killed run | Passed | The timed-out relay run is `timed_out`; 63 `api_request` events kept up to 6 s before the kill |
| 8. Stability | Passed, on a stand-in workload: three parallel trials of 65 minutes completed and scored 1.0; a job killed mid-trial resumed and reran only that trial; a timed-out run was graded. Gaps: orphaned containers after a kill, and relay's worktree not collected on a timeout | `wp6-stability-3x60`, resume and timeout jobs |
| 9. Cost | Passed: US$ 6.110 from the harness against US$ 6.12 in the Console | Console cost page on 2026-10-23 |
| 10. SDK parity and billing | Passed: billing from the included credits; init messages and request bodies identical to the headless CLI's except for IDs, the entry-point label and one Bash timeout default | Console billing page; local request capture |

### Follow-ups

- **Workflow fidelity:** measure relay's protocol adherence, since relay on Sonnet skipped steps that the grade cannot see.
- **Timeouts:** collect relay's worktrees outside the runner, so a timed-out run is graded with its partial code.
- **Killed jobs:** remove a killed trial's containers before resuming.
- **Before a run:** check that the Collector is up.
- **Target A:** add a `disallowed_tools` option to the runner if M0 picks option 1 or 2 for the network.
- **Tasks:** the MVP's tasks must be hard enough to separate the configurations.
