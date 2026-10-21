# Phase 0 plan: feasibility spike

> **Status:** Draft · **Last updated:** 2026-10-21 · **Owner:** Fabio Martins Barreto

Phase 0 proves that a task can run unattended end to end, with full telemetry and grading, before any work on the dashboard. It ends at milestone **M0 on 2026-11-03** ([schedule](../product/06-scope-and-roadmap.md#4-schedule-to-the-mvp)) with:

- one relay run and one vanilla run on the synthetic task, graded by its hidden oracle, with reconciled cost;
- the nine [Phase 0 checks](../research/phase-0-tooling.md#7-phase-0-checks) run, deciding whether Harbor stays ([D-030](../decisions/decision-log.md#d-030));
- the provider decision for Target A made ([D-029](../decisions/decision-log.md#d-029)) and the MVP budget re-evaluated ([D-028](../decisions/decision-log.md#d-028)).

## 1. Scope

**In:** the WSL 2 environment, Harbor, a synthetic target with one task in pull-request format, the relay and vanilla adapters, the telemetry Collector, a first loader into DuckDB, pilot runs, the Phase 0 checks and the M0 review.

**Out:** Target A's tasks (M1), the experiment-file format (M2), the dashboard (M4), the MLflow viewer (optional, later) and mixed model assignments (Phase 2).

## 2. Decisions this plan relies on

| Decision | What it fixes for Phase 0 |
|---|---|
| [D-030](../decisions/decision-log.md#d-030) | Harbor, pinned, in WSL 2, local Docker only, telemetry off, separate verifier |
| [D-032](../decisions/decision-log.md#d-032), [D-033](../decisions/decision-log.md#d-033) | Native OpenTelemetry to a local Collector; run folders loaded into DuckDB |
| [D-046](../decisions/decision-log.md#d-046) | A synthetic Django backend whose task is authored as a pull request |
| [D-047](../decisions/decision-log.md#d-047) | Harness code in Python 3.12 with uv |
| [D-048](../decisions/decision-log.md#d-048) | Built in interactive Claude Code sessions |
| [D-027](../decisions/decision-log.md#d-027), [D-028](../decisions/decision-log.md#d-028) | A dedicated API key; spend counted against the US$ 800 MVP ceiling |

## 3. Workspace layout

Everything that runs lives on the WSL 2 file system, which Docker builds read much faster than `/mnt/c`. This repository stays where it is, and the harness code in it is run from WSL.

```text
C:\repos\ai-track-record\          this repository (public)
├── documentation/
├── harness/                       Python package (uv project): task builder, adapters, loader
├── infra/otel-collector/          Collector configuration and compose file
└── targets/synthetic-events/      task manifests for the synthetic target (no generated files)

~/atr/                             operator workspace in WSL 2, never committed
├── .env                           API key and run settings (readable by the operator only)
├── tools/harbor/                  Harbor at a release tag, installed from its lock file
├── relay/<commit>/                pinned relay checkouts
├── targets/synthetic-events/      the synthetic target's own git repository
└── data/                          ATR_DATA_DIR: generated tasks, Harbor jobs, telemetry, DuckDB
```

Rules:

- Nothing under `~/atr/data` is ever committed. It holds raw run material, which for private targets is private ([D-002](../decisions/decision-log.md#d-002)).
- Target A will live under `~/atr/targets/` too, outside this repository, when M1 starts.
- The synthetic target can be published once it is reviewed, since it is public by design.

## 4. The synthetic target and its task

### 4.1 Target

A minimal Django 6 project with a JSON API (Django Ninja), PostgreSQL 16 and pytest, managed with uv, with its own Dockerfile and compose file (application and database). It already supports creating, reading and listing events, with tests for those endpoints. Those tests are the target's **existing suite**, used to detect regressions (GRD-02).

To be relay-ready, the base commit also holds `CLAUDE.md` and the context documents that relay expects (generated with relay's context-builder, including a methodology file that declares pytest), plus the approved specification. Both workflows see the same files.

### 4.2 Task 01: event registration with capacity and a waitlist

Proposed acceptance criteria, to be finalized in the specification:

| ID | Criterion |
|---|---|
| AC-1 | Registering an email for an event returns 201 with status `confirmed` while confirmed registrations are below capacity |
| AC-2 | When the event is full, the registration is created as `waitlisted`, with its 1-based position in the waitlist |
| AC-3 | The same email cannot register twice for the same event, ignoring case; the second attempt returns 409 |
| AC-4 | Cancelling a registration returns 204; cancelling a confirmed one promotes the earliest waitlisted registration |
| AC-5 | Listing an event's registrations returns confirmed ones in creation order, then waitlisted ones by position |
| AC-6 | Unknown events return 404 and invalid emails return 422 |

The specification includes the interface contract the tests rely on: paths, request and response fields, and status codes. Concurrency is out of scope for this task.

### 4.3 Pull-request format

The task is authored exactly like a change to a real project:

1. **Base commit:** the scaffold, the context documents and the approved specification, tagged `task-01-base`.
2. **Solution branch:** the feature plus the tests that check its acceptance criteria, tagged `task-01-solution`.

A **task builder** in `harness/` turns that pair into a Harbor task folder under `~/atr/data/tasks/`:

| Harbor task part | Built from |
|---|---|
| `environment/` | A single-commit snapshot of the base commit, with no other history or remotes, plus the target's Dockerfile and compose file |
| `tests/` | The tests added on the solution branch, a `test.sh` that also runs the existing suite and writes the reward, and the verifier's own environment |
| `solution/` | The solution branch's changes, minus its tests, as a patch |
| `instruction.md` | The vanilla instruction (section 5) |
| `task.toml` | Timeouts, resources, network policy, the separate verifier and the declared artifacts |

The same builder will turn Target A changes (M1) and, later, open-source pull requests ([D-035](../decisions/decision-log.md#d-035)) into tasks.

### 4.4 Validating the task

Before any agent runs it (TGT-04):

- the existing suite passes on the base commit;
- the oracle fails on the base commit and passes with the reference solution: Harbor's `oracle` agent scores 1.0 and its `nop` agent scores 0.0.

## 5. Workflow adapters

### 5.1 What both adapters share

- **Run product:** each adapter ends by writing the run's changes as one `changes.patch` against the base commit. The separate verifier applies that patch to a clean copy of the base and runs the tests. This works the same way for every workflow, and only the patch crosses from the agent's container to the verifier.
- **Pinned Claude Code:** the version is baked into the image: the latest release when Phase 0 starts, no older than 2.1.304 (2.1.306 on 2026-10-21).
- **Limits:** a 3-hour agent timeout, a 15-minute verifier timeout, a per-run cost cap (US$ 15 for the pilots) and an explicit `bypassPermissions` mode inside the container.

| Setting | Value |
|---|---|
| Model under test | `ANTHROPIC_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL` and `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, always with full model IDs (for example `claude-haiku-5-5`, `claude-sonnet-5-5`). Whether `ANTHROPIC_DEFAULT_HAIKU_MODEL` also pins background calls is settled by check 2 |
| Stability | `DISABLE_AUTOUPDATER=1`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, and `BASH_MAX_TIMEOUT_MS` raised for test commands |
| Privacy | `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` and `DISABLE_ERROR_REPORTING=1`; Harbor runs with `HARBOR_TELEMETRY=off` |
| Telemetry | Section 6 |

### 5.2 Relay

- The pinned relay checkout is mounted read-only into the container, and `--plugin-dir` points at its `plugins/relay` folder. This is done by a small subclass of Harbor's Claude Code agent, or through `CLAUDE_CODE_PLUGIN_DIRS`, whichever passes check 1.
- The prompt is `/relay:relay-execute PRPs/prds/<task>.prd.md`.
- Relay works in a git worktree under `.worktrees/<feature>`, so the adapter builds `changes.patch` from that worktree. Relay's plans and reports are kept as workflow artifacts.
- If relay's precondition checks wait for an answer, relay gets a non-interactive mode in its own repository, and the new commit is pinned (assumption AS-1).

### 5.3 Vanilla

Harbor's built-in Claude Code agent with the same settings and limits. Its instruction is a fixed template, the same for every task:

> Implement the feature specified in `PRPs/prds/<task>.prd.md`. Keep the existing tests passing. Stop when the feature is complete.

## 6. Telemetry and the local store

1. **Collector.** `infra/otel-collector/` runs the OpenTelemetry Collector (contrib image, pinned) in Docker. It receives OTLP over HTTP on port 4318 and writes rotating JSON files to `~/atr/data/telemetry/`.
2. **Per-run settings.** `CLAUDE_CODE_ENABLE_TELEMETRY=1`; metric and log exporters set to OTLP over `http/protobuf`; the endpoint the containers use to reach the host (`host.docker.internal:4318`); export intervals of one second; a longer shutdown timeout; `OTEL_LOG_TOOL_DETAILS=1`, so relay's agent names appear; and resource attributes carrying the run, task and configuration IDs. Each run also gets a fixed `--session-id`.
3. **Loader.** A first version reads Harbor's trial folders (result, final stream-json event, verifier reward, `changes.patch`) and the telemetry files into DuckDB. It then compares the telemetry sums with `modelUsage` and flags any mismatch.
4. **Not yet.** The MLflow viewer and the trace export are optional and wait until they are needed.

## 7. Work packages

| WP | Content | Who | Effort | Target date | Done when |
|---|---|---|---|---|---|
| **0** | Create a dedicated API key in its own workspace with a US$ 800 spend limit; store it in `~/atr/.env` | Operator | 0.5 h | 2026-10-22 | A test call with the key works from WSL |
| **1** | Update WSL (`wsl --update`) to 2.7.8 or later; set `.wslconfig` (about 18 GB of memory and 10 processors); install uv; create `~/atr/` | Operator, with a session | 1.5–2.5 h | 2026-10-23 | `wsl --version` shows the new kernel; Docker and uv work in Ubuntu |
| **2** | Clone Harbor at its latest release tag and install it from the lock file; run its sample task with the `oracle` agent, then with the Claude Code agent on Haiku | Session | 2–3 h | 2026-10-24 | Both sample runs finish with results and a transcript; no traffic to PostHog |
| **3** | Build the synthetic target (base commit and solution branch), write and approve the specification, write the task builder and validate the task | Session | 5–7 h | 2026-10-28 | `oracle` scores 1.0, `nop` scores 0.0 and the existing suite passes |
| **4** | Pin relay; write the relay adapter and configure vanilla; produce `changes.patch`; check that relay runs unattended | Session | 2–3 h | 2026-10-30 | A relay run on Haiku completes and is graded |
| **5** | Set up the Collector, the per-run telemetry settings and the first loader | Session | 3–4 h | 2026-10-31 | One run's telemetry and result are in DuckDB and reconciled |
| **6** | Pilot runs (relay on Haiku, relay on Sonnet, vanilla on Sonnet), three parallel runs for stability, a killed run and the cost comparison | Operator, with a session | 3–4 h, plus machine time | 2026-11-02 | All nine checks have a result |
| **7** | M0 review: Harbor stays or goes, D-029, the D-028 re-evaluation, and the results report | Operator | 1 h | 2026-11-03 | Decisions recorded; [schedule](../product/06-scope-and-roadmap.md#4-schedule-to-the-mvp) re-forecast |

**Total: about 18–25 hours.** That is more than the 15–20 hours the schedule gives M0, so at 10–15 hours a week M0 lands on time only at the top of that range. If it slips, the date moves and the scope stays ([D-043](../decisions/decision-log.md#d-043)). If time runs short, the loader's polish moves to M2; the checks stay, because they decide whether Harbor is kept.

## 8. Expected spend

| Item | Estimate |
|---|---|
| Debug runs on Haiku | US$ 5–20 |
| Three pilot runs | US$ 10–40 |
| Stability and kill tests | US$ 10–35 |
| **Phase 0 total** | **about US$ 30–90**, counted against the US$ 800 MVP ceiling |

## 9. Risks and fallbacks

| Risk | Fallback |
|---|---|
| Harbor fails checks 1, 3 or 8 | The minimal custom runner replaces it, using the same task folders ([D-030](../decisions/decision-log.md#d-030)) |
| The network allowlist does not work on this machine, even after the WSL update | Phase 0 runs with an open network on the public synthetic task; Target A cannot start until the allowlist works |
| Relay waits for input in unattended mode | Add a non-interactive mode to relay and pin the new commit |
| Telemetry does not reach the Collector from the containers | Phase 0 relies on the result event and transcripts; the telemetry path is fixed in M2 |
| Model forcing misses some calls | Pin the background model as well, or record those calls separately (check 2) |

## 10. Outputs at M0

- The harness skeleton in `harness/`: task builder, relay adapter, loader.
- The Collector configuration in `infra/otel-collector/`.
- The synthetic target repository and its task manifest.
- A results report, `documentation/research/phase-0-results.md`, with the outcome of every check, costs and durations.
- Updated decisions: Harbor kept or replaced, D-029, and the D-028 re-evaluation.
