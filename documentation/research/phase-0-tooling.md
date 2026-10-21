# Phase 0 tooling: runner, observability and local store

> **Status:** Draft · **Last updated:** 2026-10-21 · **Owner:** Fabio Martins Barreto

This document holds the evidence behind three Phase 0 decisions: the runner ([D-030](../decisions/decision-log.md#d-030)), the observability stack ([D-032](../decisions/decision-log.md#d-032)) and the local store ([D-033](../decisions/decision-log.md#d-033)).

The facts were collected on 2026-10-20 from primary sources: official documentation, release notes, package metadata and source code at tagged versions. Nothing third-party has been installed or run yet. Anything that only a real run can confirm is marked *unverified* and becomes a Phase 0 check ([section 7](#7-phase-0-checks)).

## 1. Summary

All three recommendations were accepted on 2026-10-20.

| Decision | Recommendation | Main reason |
|---|---|---|
| D-030 Runner | Adopt **Harbor**, pinned, with a thin in-house layer. If it fails the Phase 0 checks, build a minimal container runner around the same task folders. | It runs the real Claude Code CLI on the real API path, and it already handles containers, hidden tests, timeouts, parallel runs, retries and resume. Its task format is one other people can run, which helps verification. |
| D-032 Observability | **Claude Code's native OpenTelemetry**, sent to a local Collector, together with each run's result event and transcripts, as the system of record. **MLflow**, run locally, as an optional and disposable trace viewer. | Per-request tokens, cost and duration, attributed to sub-agents, all on the operator's machine, without depending on transcript formats or hosted services. |
| D-033 Local store | **DuckDB** over immutable raw run folders. | Writes are append-only and reads are analytical. Keeping the raw files makes every load repeatable. |

## 2. Operator environment

Checked on 2026-10-20, with the Claude Code version rechecked on 2026-10-21:

- Windows 11 with Docker Desktop 29.6 on WSL 2 (Ubuntu). The Docker VM has 12 CPUs and 13.6 GiB of memory.
- Claude Code 2.1.306 on the host (updated from 2.1.257 on 2026-10-21), Python 3.11 and Node 24; `uv` is not installed.

Consequences:

- The harness runs inside WSL 2. Harbor and Inspect test their runtime only on Linux, and both have open bugs on native Windows.
- Harbor needs Python 3.12 or later, installed inside WSL 2.
- Three parallel runs with PostgreSQL and Next.js need more memory for WSL 2, set in `.wslconfig`.
- Runs do not use the host's Claude Code. Each run's image carries its own pinned version ([section 3](#3-what-the-harness-needs-from-claude-code)).

## 3. What the harness needs from Claude Code

| Need | Mechanism | Caveat |
|---|---|---|
| Load relay at a pinned commit | `--plugin-dir <checkout>`, or the `CLAUDE_CODE_PLUGIN_DIRS` variable (v2.1.280+) | Load failures are quiet: check `plugins` and `plugin_errors` in the `system/init` event |
| Run unattended | `claude -p "/relay:relay-execute <prd>"` inside a container, with an explicit `--permission-mode` | Since v2.1.302, `-p` without a permission mode denies every call that needs approval |
| Force every sub-agent onto the model under test | `CLAUDE_CODE_SUBAGENT_MODEL=<full model id>` with `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` (v2.1.257+) | Without FORCE, relay's `model: sonnet` frontmatter wins. Background calls use the `haiku` alias unless `ANTHROPIC_DEFAULT_HAIKU_MODEL` is pinned. Aliases move between releases, so the harness uses full model IDs |
| A different model per role (Phase 2) | A generated copy of the plugin with per-agent `model:` values | No setting does this without editing a copy |
| Cost cap | `--max-budget-usd` | A soft cap, checked after each response. It includes sub-agents and can overshoot by one response |
| Turn cap | `--max-turns` | v2.1.304 fixed plugin sub-agents running past it in headless runs |
| Time limit | None in the CLI | The runner enforces it from outside |
| Tokens and cost per model | `modelUsage` in the final `result` event | A client-side estimate. It covers sub-agents but leaves out permission-classifier and token-counting calls. `usage` covers the main loop only |
| Tokens and cost per sub-agent | OpenTelemetry `api_request` events and the cost and token metrics, with `agent.name` and `query_source` | Relay's agents appear as `custom` unless `OTEL_LOG_TOOL_DETAILS=1` (real names from v2.1.273). That flag also logs commands and tool parameters, so its output is private data |
| Transcripts | Session JSONL plus a `subagents/` folder, under a per-run `CLAUDE_CONFIG_DIR` | The format is internal and changes between versions |
| Long test commands | `BASH_MAX_TIMEOUT_MS` | Foreground commands time out after 2 minutes by default, with a 10-minute ceiling unless raised |
| A stable version | The pinned CLI baked into the image, plus `DISABLE_AUTOUPDATER=1` | Record `claude --version` with every run |

**Version to pin:** the latest release when Phase 0 starts, and no older than 2.1.304.

**Paying for runs:** an API key, as [D-027](../decisions/decision-log.md#d-027) requires. A dedicated key in its own workspace, with a spend limit equal to the MVP ceiling of US$ 800 ([D-028](../decisions/decision-log.md#d-028)), turns the soft per-run caps into a hard stop at the provider.

## 4. Runner options (D-030)

### 4.1 Harbor

[Harbor](https://github.com/harbor-framework/harbor) is the official harness of Terminal-Bench. Version 0.24.0 was released on 2026-10-05. It is licensed Apache-2.0, needs Python 3.12 or later, and ships a release every two to four weeks. It is pre-1.0, and its changelog often lists breaking changes.

**How it maps to AI Track Record**

| AI Track Record | Harbor |
|---|---|
| Task specification | `instruction.md` |
| Environment, including PostgreSQL | `environment/` with a Dockerfile or `docker-compose.yaml`; the agent runs in the `main` service |
| Hidden oracle | `tests/`, copied in only when verification starts; with the separate verifier, the tests run in a fresh container |
| Reference solution and task validation (TGT-04) | `solution/` plus the `oracle` agent, which should pass, and the `nop` agent, which should fail |
| Limits | `task.toml`: agent and verifier timeouts, CPU, memory, and a network policy per phase |
| Repetitions, parallel runs, retries, resume | `-k`, `-n`, `-r` and `harbor job resume` |
| Run record | `result.json` (timings, plus tokens and cost per model including sub-agents), the raw stream-json output, session transcripts including sub-agents, a trajectory file, and a local viewer |

Task folders do not depend on Harbor's code, so moving away from Harbor later is cheap.

**The built-in Claude Code agent** runs the real CLI inside the task container and sends it the instruction through `claude --print --output-format=stream-json --verbose`. It exposes typed options for turns, budget, effort, fallback model, an appended system prompt and tool lists, and it defaults to `bypassPermissions`. Extra environment variables go through `--ae`. It has **no option for loading a plugin** (confirmed in the 0.24.0 source), so relay is loaded either through `CLAUDE_CODE_PLUGIN_DIRS` or through a small subclass that adds `--plugin-dir`. Both routes are unverified in a real run.

**Settings AI Track Record must change**

- **Telemetry off.** Harbor sends job statistics to PostHog by default (confirmed in source). They include model names, token counts, cost, durations and resource settings, but not prompts, code, task paths or environment variables. `HARBOR_TELEMETRY=off` disables it.
- **Local Docker only.** Cloud environments, Harbor Hub and `harbor upload` send tasks and code to third parties, which [D-003](../decisions/decision-log.md#d-003) forbids.
- **Separate verifier.** In 0.24.0 the default verifier runs in the agent's container (confirmed in source), and an open report shows that an agent can plant files there that change test results ([pull request #2553](https://github.com/harbor-framework/harbor/pull/2553)). Every task sets `[verifier] environment_mode = "separate"`.
- **Locked install.** Harbor depends on LiteLLM, which had compromised package versions in March 2026. Harbor is installed from its release lock file.
- **Pinned Claude Code in the image.** Otherwise the agent downloads Claude Code at the start of each run.

**Known limits:** the agent can rewrite its own transcript files ([issue #3477](https://github.com/harbor-framework/harbor/issues/3477)); the API key sits inside the agent container; native Windows is unsupported in practice; and the documentation on `main` runs ahead of the release.

**Estimated effort:** two to three days to a first real task.

### 4.2 Inspect AI with inspect_swe

[Inspect](https://inspect.aisi.org.uk/) 0.3.282 and [inspect_swe](https://meridianlabs-ai.github.io/inspect_swe/) 0.2.72 are MIT-licensed. inspect_swe's `claude_code()` agent runs the real CLI in a sandbox but **routes every model call through Inspect on the host**. Claude Code never talks to Anthropic directly, and the bridge drops generation settings and beta headers unless a transparent mode is enabled. The agent also has no plugin option, which its maintainers confirmed on 2026-10-04.

Its strengths are privacy and logging: there is no default telemetry, the API key stays on the host, sandboxes can run with no network, and its logs hold every model call with usage, attributed to sub-agents. Its weakness is decisive for this project: the bridge changes the system under test, while [D-017](../decisions/decision-log.md#d-017) and the MVP compare Claude Code as people actually run it. Estimated effort: three to five days.

### 4.3 Custom container runner

A minimal runner has to:

1. build a workspace from the base commit with no git history;
2. build or reuse the task image (Django, Node, PostgreSQL);
3. start a container with resource limits and a network policy;
4. run `claude -p` with the pinned CLI, the plugin and the limits, under an external wall-clock kill;
5. keep the stream-json output and the session files;
6. grade in a fresh container and record the outcome;
7. map outcomes to [D-019](../decisions/decision-log.md#d-019);
8. run two or three runs in parallel, resume, retry infrastructure errors and clean up containers.

It gives exact control and no third-party dependency, at an estimated four to seven days, plus the Windows and Docker problems that Harbor has already worked through. It is the fallback if Harbor fails the Phase 0 checks.

### 4.4 Ruled out

- **SWE-bench harness:** it grades patches; it does not run agents.
- **mini-swe-agent and OpenHands:** different agents, not Claude Code.
- **promptfoo with its Agent SDK provider:** it runs on the host and targets short tests.
- **`claude plugin eval`:** at most one hour per case, an empty workspace and no code-based graders. It remains useful for quick regression tests of relay itself.

### 4.5 Comparison

| | Harbor 0.24.0 | Inspect with inspect_swe | Custom runner |
|---|---|---|---|
| Real Claude Code API path | Yes | No: calls are bridged | Yes |
| Plugin pinning | Environment variable or subclass (unverified) | Workaround only (unverified) | Native `--plugin-dir` |
| Forced sub-agent models | Environment variables | Native | Environment variables |
| Hidden tests | Separate verifier | Custom scorer | Built by hand |
| Private data | Local Docker, telemetry off | Best defaults | Depends on the hardening |
| Logs | Rich; transcripts writable by the agent | Rich and kept on the host | Whatever is built |
| Other agents later | About 40 built in | Several built in | One adapter each |
| Windows | Through WSL 2 | Through WSL 2 | Through WSL 2 |
| Estimated effort | 2–3 days | 3–5 days | 4–7 days |
| Main risk | Pre-1.0 churn | Changes the system under test | Time |

## 5. Integrity requirements for any runner

These follow from [D-014](../decisions/decision-log.md#d-014) and [D-015](../decisions/decision-log.md#d-015), whichever runner is chosen.

1. **No history leakage.** The workspace is a single-commit copy of the base commit, with no remotes, other refs or reflog. Agents have been seen reading later commits to find solutions: [NIST's CAISI](https://www.nist.gov/caissi/2-examples-cheating-caisis-agent-evaluations) (2025) and [Superconductor](https://www.superconductor.com/blog/preventing-agent-cheating) (2026-07-24) both document it.
2. **Grade in a fresh environment.** The verifier runs in a new container built from a pristine image. Only the agent's changes cross over, and they are treated as untrusted (no symlinks, no setuid bits).
3. **One container per run, not git worktrees.** Worktrees share history, processes, ports and the host filesystem.
4. **Contain the agent.** Runs that skip permission prompts happen only inside containers, with no Docker socket, no host secrets, resource limits, and network access limited to the model API and the registries needed for setup.
5. **Protect the key.** A dedicated API key with a spend limit. A host-side proxy that holds the key is a later option.

These make three capabilities of the frozen MVP scope more precise without adding to it: RUN-01 (isolated workspace), TGT-03 (oracles kept out of reach) and GRD-01 (running the oracle).

## 6. Observability options (D-032)

### 6.1 What Claude Code emits

- **Metrics and events** (stable): token and cost counters, and an `api_request` event for every model call with the model, tokens by type, cost, duration, `query_source` (main, sub-agent or auxiliary) and `agent.name`. Also `tool_result`, `subagent_completed` and others.
- **Traces** (beta): a span tree per prompt, with sub-agent spans nested under the tool call that started them.
- **Content** (prompts, responses, tool parameters, raw API bodies) is logged only when explicitly enabled.
- Exporter settings in a target repository's `.claude/settings.json` are ignored, so a target cannot redirect or switch off telemetry.

### 6.2 Recommended design

1. Each run sets the OpenTelemetry variables, a fixed session ID, and resource attributes with the run, task and configuration IDs.
2. A local OpenTelemetry Collector receives the data and writes rotating JSON files.
3. The runner keeps each run's result event and copies its transcripts into the run folder.
4. A loader reads the run folders into DuckDB ([D-033](../decisions/decision-log.md#d-033)). On every run it reconciles the OpenTelemetry sums with `modelUsage` and flags any mismatch.
5. Optionally, the Collector also forwards traces to a local MLflow server for browsing.

The OpenTelemetry stream leaves the container while the run is in progress, so it survives a killed run and cannot be rewritten by the agent afterwards. A killed run has no result event, so its events are its only cost record.

Pitfalls to handle: export is best-effort, so intervals are set to one second and the shutdown timeout is raised; metrics are sent as deltas, so a lost final export loses counts; and hook processes do not receive the OpenTelemetry variables.

### 6.3 Platforms

| Option | Version and license | Fit with D-003 | Effort | Role |
|---|---|---|---|---|
| **OTel Collector and DuckDB** | Collector v0.163.1, Apache-2.0; DuckDB 1.5, MIT | Full: nothing leaves the machine | About half a day to wire up, two to three days for the loader | **System of record** |
| **MLflow** | 3.17.1, Apache-2.0 | Full when run locally on SQLite; its usage telemetry must be switched off | One to two hours | **Optional viewer and run tracker.** It accepts Claude Code's native traces (3.17.1+), records runs with parameters and metrics, and has LLM-judge evaluation for Phase 2 |
| **Langfuse** | 4.66, MIT except its enterprise folders | Full when self-hosted; its telemetry must be switched off | High: six services including ClickHouse, a 16 GiB memory guideline against the Docker VM's 13.6 GiB, and a fast-changing data model | Not used. Reference design only ([D-045](../decisions/decision-log.md#d-045)) |
| **LangSmith** | Proprietary server | **Fails.** It is hosted, and self-hosting is an Enterprise add-on that still needs outbound connections | — | Not used, because D-003 keeps every run local, public or private. Reference design only ([D-045](../decisions/decision-log.md#d-045)) |
| **Arize Phoenix** | Elastic License 2.0 | Full when run locally | Low | Skipped: source-available license and partial sub-agent support |
| **Opik** | Apache-2.0 | Full when self-hosted | Medium (six services) | Not needed |

Every one of these platforms integrates with Claude Code through hooks that rebuild traces from the transcript files. That format is internal and changes between versions, and hooks only see sessions that end normally. For these reasons the system of record is built on OpenTelemetry and the result event, and any platform sits on top of it.

**Practicing the stack** ([D-040](../decisions/decision-log.md#d-040)): MLflow is used for real as the viewer and, in Phase 2, for LLM-judge evaluation. LangChain fits best inside the LLM judge (GRD-06), traced locally. LangSmith and Langfuse serve as reference designs for the local store and the dashboard, for example their traces, scores, datasets and run comparisons ([D-045](../decisions/decision-log.md#d-045)).

## 7. Phase 0 checks

Each check passes or fails. If Harbor fails checks 1, 3 or 8, the custom runner replaces it.

1. **Plugin and version.** The `system/init` event lists relay with no `plugin_errors`, and the Claude Code version equals the pin.
2. **Forced models.** Every model in `modelUsage` and in the `api_request` events is the model under test, including on a sub-agent whose definition names another model. Background calls are either pinned too or recorded separately.
3. **Hidden tests.** No test files exist in the agent's container during the run. The separate verifier scores the run, the `oracle` agent scores 1.0 and the `nop` agent scores 0.0.
4. **No history leakage.** `git log --all` inside the workspace shows only the base commit.
5. **Privacy.** With telemetry switched off, nothing reaches PostHog or any other third party. During the run, network traffic goes only to the model API.
6. **Telemetry.** The `api_request` sums match `modelUsage` by model and token type, the per-agent totals add up to the whole, and relay's agent names are visible.
7. **Killed run.** Events up to the kill are kept, and the run is classified as `timed_out`.
8. **Stability.** Three parallel runs of an hour or more complete under WSL 2, a resumed job continues, and a timed-out run is still graded.
9. **Cost.** The summed cost is within tolerance of the provider's usage report for the dedicated key.

## 8. Unverified items

- Loading relay in Harbor through `CLAUDE_CODE_PLUGIN_DIRS` or through a subclass.
- Harbor on this machine's WSL 2 and Docker Desktop, including its network allowlist.
- How far Harbor's token totals differ from `modelUsage`.
- OpenTelemetry export from inside Harbor's containers to a Collector on the host.
- Whether DuckDB's OTLP extension reads Claude Code's counter metrics; plain JSON reading is the fallback.
- MLflow under WSL 2, and linking its traces to runs.
- Whether 5-minute and 1-hour cache writes can be told apart for exact pricing. Pinning the cache duration avoids the question.
- All effort estimates.

## 9. Sources

All accessed on 2026-10-20.

- **Harbor:** [repository](https://github.com/harbor-framework/harbor); [release v0.24.0](https://github.com/harbor-framework/harbor/releases/tag/v0.24.0); [Claude Code agent source at v0.24.0](https://github.com/harbor-framework/harbor/blob/v0.24.0/src/harbor/agents/installed/claude_code.py); [pull request #2553](https://github.com/harbor-framework/harbor/pull/2553); [issue #3477](https://github.com/harbor-framework/harbor/issues/3477).
- **Inspect:** [agent bridge](https://inspect.aisi.org.uk/agent-bridge.html); [inspect_swe Claude Code agent](https://meridianlabs-ai.github.io/inspect_swe/claude_code.html).
- **Claude Code:** [CLI reference](https://code.claude.com/docs/en/cli-reference.md); [headless mode](https://code.claude.com/docs/en/headless.md); [sub-agents](https://code.claude.com/docs/en/sub-agents.md); [environment variables](https://code.claude.com/docs/en/env-vars.md); [monitoring](https://code.claude.com/docs/en/monitoring-usage.md); [sessions](https://code.claude.com/docs/en/sessions.md); [cost tracking](https://code.claude.com/docs/en/agent-sdk/cost-tracking.md); [plugin evals](https://code.claude.com/docs/en/plugin-evals.md); [legal and compliance](https://code.claude.com/docs/en/legal-and-compliance.md).
- **Observability:** [MLflow and Claude Code OpenTelemetry tracing](https://mlflow.org/blog/claude-otel-tracing) (2026-10-14); [Langfuse self-hosting](https://langfuse.com/self-hosting); [LangSmith self-hosting](https://docs.langchain.com/langsmith/self-hosted); [OpenTelemetry Collector file exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/fileexporter); [DuckDB OTLP extension](https://duckdb.org/community_extensions/extensions/otlp).
- **Evaluation integrity:** [NIST CAISI, examples of cheating in agent evaluations](https://www.nist.gov/caissi/2-examples-cheating-caisis-agent-evaluations) (2025-11-28, updated 2025-12-02); [Superconductor, preventing agents from cheating on a custom SWE-bench](https://www.superconductor.com/blog/preventing-agent-cheating) (2026-07-24).
