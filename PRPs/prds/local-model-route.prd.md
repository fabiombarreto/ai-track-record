# Local Model Route

```
**Decision Gate**
- Active context: none
- Activated criteria: architectural decisions (a second model route for runs); cross-cutting patterns (agent options, trial records, store, budget, export); creation of components (inference server, local launcher); business rules for runs, store and publication, budget and local inference
- Decisions found: D-017/D-049 (Claude Code through the Agent SDK is the only harness); D-031 (route to open-weight models, Proposed; this PRD implements the local route it records and leaves its acceptance to WP4 of the plan); D-057 (Target A may be processed by open-weight models on the operator's machine); D-058 (experiment outside the frozen MVP; the MVP keeps priority over the operator's time and the machine); D-020 (pin everything; same limits for all); D-050 (network allowlist, no web tools on Target A); D-022 (cost computed from tokens, source labeled); D-033 (run folders are the system of record); D-019 (normalized outcomes); D-028 (MVP ceiling of US$ 800, never drawn on by other experiments); D-011 (planning lives in documentation/)
- Applicable anti-patterns: private-target material in the repository (this PRD and its plans live in the public PRPs/ folder); sending Target A's content to a provider that is not allowed; web tools or an open network on Target A runs; silently dropping a configuration option; unpinned versions; running two benchmark runs at the same time; secrets in the repository; large files on C: or inside the WSL and Docker disks
- Applicable architectural rules: graders sit outside the workflow and stay unchanged; configuration, not code (D-005) — the route is a job-config value; container-side scripts use the standard library only; fail closed on checks that guard correctness or privacy; every run's records live in its trial folder
- Result: PROCEED
```

## Problem Statement

The operator of AI Track Record can only run its benchmark on Claude models through Anthropic's API. Open-weight models cannot be measured at all, every experiment waits on API credits (the MVP's batches stopped in November when the included credits ran out), and all nine vanilla runs on Claude so far met every criterion, so it is not yet known whether the hidden oracle can separate configurations. A second model route that keeps Target A's content on the operator's machine, with the same harness, limits and graders, removes all three blocks.

## Evidence

- All nine vanilla runs on Target A (the M2 pilots and the first M3 repetition, on Sonnet 5.5 and Haiku 5.5) scored reward 1.0 on every task, so the oracle has not yet separated any two configurations (`documentation/research/m2-results.md`, local store).
- The M3 batches stopped when the API workspace reached its monthly usage limit (`documentation/research/m3-results.md`, "Running the batches").
- The agent refuses to start without `ANTHROPIC_API_KEY` and has no option for another endpoint (`harness/src/atr/agents/claude_sdk.py:229-231`).
- The only other route planned so far, a gateway to Google's Gemini API, is deferred (D-056) and would send Target A's content to a new processor, which D-055 has not allowed.
- llama.cpp's server accepts Anthropic's Messages API since January 2026, so Claude Code can reach a local model with no gateway (https://huggingface.co/blog/ggml-org/anthropic-messages-api-in-llamacpp).

## Proposed Solution

Add a local route to the harness: a Harbor job names a local model alias instead of a Claude model, and the agent points Claude Code at a llama.cpp server running on the operator's machine, with no Anthropic key in the container, every model alias pinned to the model under test, and Claude Code's context, compaction, timeout and attribution settings adjusted for a local server. A local launcher starts one pinned server per run with a new key, samples GPU power and copies the server's records into the trial folder; the store, budget and export learn the route so local runs are reconciled, kept out of the MVP's ceiling and labeled as workflow portability. A direct route was chosen over a gateway because llama.cpp already speaks the Messages API, which keeps one fewer component between the run and the model, and a per-run server was chosen over a long-lived one so no run inherits another's cache.

## Key Hypothesis

We believe that pointing Claude Code at llama.cpp's Messages API, with every alias pinned to the local model, the attribution header off and the context window and timeouts adjusted, will let vanilla runs on open-weight models finish within the MVP's limits on this machine, graded by the unchanged graders.
We'll know we're right when the compatibility checks L1 to L10 all have a recorded result, the machine baseline is recorded for both main models, and one vanilla run on L-Small and one on L-MoE on the public synthetic task finish within three hours, are graded, loaded into the store and reconciled, with no request leaving the machine.

## What We're NOT Building

- The experiment's runs on Target A, its hypotheses and its analysis (WP4 to WP8 of the local models plan) — they need D-031 decided and the compatibility checks' results first.
- Hardware upgrades (more RAM, a larger GPU) — each needs its own decision (local models plan, section 14).
- A gateway or any route to another provider's API, including Gemini — deferred by D-056; D-055 is open.
- Other harnesses built for open-weight models — Phase 3 extension (CFG-09).
- Relay configurations on local models beyond one probe on the synthetic task — only if the probe finishes within the limits, through a new decision.
- Dashboard changes — M4 work; local results publish only after the MVP is public.

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Compatibility checks with a result | 10 of 10 (pass, or failure with a fallback recorded) | The checks report in `documentation/research/` |
| Complete vanilla runs on the synthetic task | At least one per main model (L-Small, L-MoE), with tokens matching across the SDK, Claude Code's events and the server's record | The store's reconciliation view |
| Requests leaving the machine from local runs | Zero requests to Anthropic's API or any other provider | Check L9 and the server's request log |
| Machine baseline | Prompt and generation speed, GPU power and memory at 32k, 64k and 128k tokens for each main model | `atr.local.bench` outputs |

## Acceptance Criteria (test scenarios)

Mandatory. Each criterion is an observable scenario the resulting code must
satisfy. If `tdd: true` in `docs/context/methodology.md`, these are the
contract the test pair authors test-first (before the Implementer). If
`tdd: false` with a declared framework, they are the contract the test pair
authors test-after (after the Implementer + Code Review). With no framework
declared, no tests are authored.

- **AC-1 Verified weights:** Given the main-stage entries in `infra/local-inference/models.toml`, when `python -m atr.local.fetch` runs, then each file is in `$ATR_MODELS_DIR` with the pinned size and SHA-256 and a marker next to it; and given a file whose digest does not match, the file is renamed to `<file>.bad` and the command exits non-zero.
- **AC-2 Server start:** Given a verified model, when `python -m atr.local.serve start <id>` runs, then the server answers `/health`; `POST /v1/messages/count_tokens` returns 401 without the key and 200 with it; the port is published on `127.0.0.1` only; and `server.json` records the image digest, build, file SHA-256, context and flags, and does not contain the key.
- **AC-3 Baseline measurement:** Given a running server, when `python -m atr.local.bench` runs, then it writes a JSON file with, for prompts of 32k, 64k and 128k tokens (or the largest that fits the context), the prompt and generation tokens per second, mean GPU power, GPU energy, peak VRAM and the container's memory.
- **AC-4 Route settings:** Given a job config that names the local route and a model alias, when the run starts, then the task container has no `ANTHROPIC_API_KEY`; `ANTHROPIC_BASE_URL` points to `http://host.docker.internal:<port>`; `ANTHROPIC_MODEL`, the Opus, Sonnet, Haiku and Fable aliases and the forced sub-agent model all name the model under test; `CLAUDE_CODE_ATTRIBUTION_HEADER=0`; the context and compaction window equal the server's context; and `agent/route.json` records the provider `local`, the server's image digest and build, the model file and its SHA-256, the quantization, the server flags, the sampling and the thinking setting.
- **AC-5 Fail before any model call:** Given the server is unreachable or rejects the run's key, when a local run starts, then it fails before Claude Code sends any model request, ends as an infrastructure error and names the cause.
- **AC-6 Graded, loaded, reconciled:** Given a vanilla run with L-Small on the synthetic task, when it ends, then it is graded by the unchanged verifier and review; the store loads it with route `local` and an API cost of zero labeled with its source; and the reconciliation view reports its input and output tokens matching across the SDK, Claude Code's events and the server's record, not a mismatch caused by a missing cost.
- **AC-7 MVP keeps priority:** Given an MVP job in progress, when the local launcher is asked to start a local run, then it refuses and starts nothing; and given `lc-` jobs in the data directory, when `python -m atr.ops.budget --next <usd>` runs, then the `lc-` jobs add nothing to the total checked against the MVP's ceiling.
- **AC-8 Network:** Given a local run behind the allowlist variant, when the task container tries to reach `api.anthropic.com` or any other host, then the request fails, while `host.docker.internal` (the server and the Collector) and the package index answer.
- **AC-9 Export:** Given a loaded local run, when `python -m atr.store.export` exports it, then the run carries its route and the workflow-portability label, the allowlist version is raised, and the leak check passes on the exported model identifiers.
- **AC-10 Checks recorded:** Given the compatibility checks L1 to L10 of the local models plan, when the last phase ends, then each has a recorded result — passed, or failed with the fallback chosen — in the checks report; and given the relay probe was run, its outcome is recorded in the same report.

## Open Questions

- [ ] Is thinking on or off by default for the Qwen models inside Claude Code? Decided by checks L1 and L3.
- [ ] How many server slots and how much prompt-cache RAM? Decided in WP0 and check L5.
- [ ] Does `CLAUDE_CODE_ATTRIBUTION_HEADER=0` take effect from the process environment, or must it go in a settings `env` block inside the container? Check L5.
- [ ] Should the SDK subtype `error_max_turns` map to `budget_exceeded`, as the store does today, or to `timed_out`, as D-019 lists the turn limit?
- [ ] Does the local launcher live in the harness or in the private workspace, next to the MVP's batch script?
- [ ] How is whole-system energy measured, beyond the GPU's own power samples?
- [ ] Is loading weights from D: through Docker Desktop's file sharing fast enough, or does the Docker disk need to move to D:?

---

## Users & Context

**Primary User**
- **Who:** The operator of AI Track Record, who builds and runs its experiments and answers for the published numbers.
- **Current behavior:** Runs the MVP's batches one at a time through the batch launcher, always on Anthropic's API, paid with the plan's API credits.
- **Trigger:** Wanting to measure an open-weight model without spending API credits and without sending Target A's content off the machine.
- **Success state:** A local run starts from the same kind of job config as an MVP run and ends graded, loaded and reconciled, with its route recorded and no effect on the MVP's ceiling.

**Job to Be Done**
When I want to evaluate Claude Code on an open-weight model without sending Target A's content off my machine, I want to run the same job with the same harness, limits and graders as the MVP, so I can compare its grades, time and energy with the runs on Claude.

**Non-Users**
Readers of the dashboard, who get results later through the export; other machines or operators, since the design assumes one machine; other harnesses; anyone looking for a production model server or a ranking of models — results measure workflow portability on a quantized model on consumer hardware.

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | Machine baseline: fetch and verify L-MoE and L-Small, serve each, benchmark, record the quantization, context and slot choices | The route cannot be configured without the machine's real limits |
| Must | Hardened server: pinned image, one model, new key per start, offline, loopback only, server record copied into each trial | Reproducibility (D-020) and privacy (D-057) |
| Must | Agent route option: base URL and token, no Anthropic key, all aliases pinned, context, compaction and timeouts, attribution header off, thinking recorded, pre-flight server check, `agent/route.json` | The core of the hypothesis |
| Must | Local launcher: server per run, power sampling, record copy, refusal while an MVP job runs | D-058's priority rule and per-run isolation |
| Must | Allowlist variants: Target A without Anthropic's API; the synthetic task with an allowlist | D-050; check L9 needs an allowlist on the synthetic task |
| Must | Store: route and energy loaded, server tokens as a third source, zero API cost labeled, no false mismatch | D-022, D-033 |
| Must | Budget: `lc-` jobs excluded from the MVP's ceiling | D-028, D-058 |
| Must | Export: route field, workflow-portability label, raised allowlist version, leak check on model identifiers | R9; publication must not mislabel local runs |
| Must | Compatibility checks L1 to L10 on the synthetic task, recorded in a report | The plan's exit criterion for WP3 |
| Should | Relay probe on the synthetic task | Answers whether relay can run locally at all, but not needed to validate the vanilla route |
| Could | L-Alt candidates (gpt-oss-20b, Gemma 4 26B-A4B) | Only if machine time allows |
| Could | The 4-bit L-MoE option with a larger WSL memory profile | Only if RAM allows |
| Could | Whole-system energy with a plug meter | GPU power is measured; the rest is an estimate |
| Won't | WP4 to WP8: D-031's decision, hypotheses, Target A pilots and batches, reviews, analysis | Need this PRD's results first |
| Won't | Hardware upgrades, gateways, other providers, other harnesses, dashboard changes | Outside the local models plan or behind other decisions |

### MVP Scope

The Must rows: a local route that runs a vanilla job on the synthetic task end to end on both main models, with the server pinned and isolated, the run's records complete, the store, budget and export aware of the route, and the ten compatibility checks recorded.

### User Flow

The operator fetches the weights → writes a job config that names the local route and a model alias → starts it through the local launcher, which starts the server, runs the Harbor job and stops the server → grades, reviews and loads the run as today → reads the run's route, tokens, time and energy in the store.

---

## Technical Approach

**Feasibility:** MEDIUM — every piece exists (llama.cpp's Messages API, Claude Code's environment variables for custom endpoints, the harness's agent and record patterns), but whether local models' tool calls work through Claude Code, and whether the server reuses the prompt prefix between Claude Code's requests, is unproven on this machine.

### TDD routing

Current value of `tdd` in `docs/context/methodology.md`: **false**. Test-after ordering — when a test framework is declared, the test pair (test-writer/test-reviewer) authors and maintains the suite from the Acceptance Criteria above, after the Implementer + Code Review; with no framework declared, no tests are authored.

### Architecture Notes

- The route is a job-config value (D-005): the agent's options gain the route and its settings, and the agent builds Claude Code's environment from them. Without the route, runs behave exactly as today.
- The pre-flight server check mirrors `_check_collector` (`harness/src/atr/agents/claude_sdk.py:171-191`): a request from inside the container before any model call, failing the trial early.
- `agent/route.json` follows the pattern of `agent/workflow.json` (`harness/src/atr/agents/claude_sdk.py:193-217`) and carries the server's record for that run, so every trial proves which model file and flags it used.
- The inference server runs in Docker like the Collector, published on the host's loopback; task containers reach it at `host.docker.internal:<port>`. Harbor's allowlist names hosts, not ports.
- Weights live on D: (`/mnt/d/atr/models`) and are bind-mounted read-only; C: has no room for them.
- The SDK's USD cap cannot bound a local run, because Claude Code has no price for a local model; the time and turn limits bound it, as for every run.
- Local jobs use the `lc-` prefix; the budget filters them out of the MVP's total, and the store marks their cost source.
- Container-side code stays standard-library only; host-side code follows `docs/context/conventions.md`.

### Technical Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Local models' tool calls break through the server's translation (tool calls inside thinking blocks, template mismatches reported for Qwen3.5/3.6) | H | Unsloth's fixed templates; a switch to turn thinking off; another candidate model; a newer pinned build; otherwise record the finding |
| The server does not reuse the prompt prefix, so every request is processed in full and runs reach the three-hour limit | M | Attribution header off; slot count and prompt-cache RAM tuned in WP0; the time limit is a measured outcome |
| Not enough RAM or VRAM for the server, the run containers and the desktop | M | 3-bit or IQ3 quantizations; other containers stopped during local sessions; the display on the integrated graphics; a larger WSL profile for local sessions |

---

## Implementation Phases

| # | Phase | Description | Status | Repo | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|------|----------|---------|----------|
| 1 | Machine baseline | Finish and run the fetch, serve and bench scripts on L-MoE and L-Small; record speeds, power, memory and the quantization, context and slot choices | complete | - | - | - | PRPs/plans/local-model-route-phase-1-machine-baseline.plan.md |
| 2 | Hardened server | Final server flags in `models.toml`; offline, loopback and key checks; the server record shaped for copying into trials | complete | - | - | 1 | PRPs/plans/local-model-route-phase-2-hardened-server.plan.md |
| 3 | Agent route option | Route option and settings in the agent, pre-flight server check, `agent/route.json` | complete | - | - | 2 | PRPs/plans/local-model-route-phase-3-agent-route-option.plan.md |
| 4 | Local launcher and allowlists | Launcher with a server per run, power sampling, record copy and the MVP-priority refusal; allowlist variants for Target A and the synthetic task | complete | - | - | 3 | PRPs/plans/local-model-route-phase-4-local-launcher-and-allowlists.plan.md |
| 5 | Store, budget and export | Route-aware loading and reconciliation, `lc-` jobs out of the MVP's ceiling, route and label in the export | complete | - | - | 4 | PRPs/plans/local-model-route-phase-5-store-budget-and-export.plan.md |
| 6 | Compatibility checks | Checks L1 to L10 and the relay probe on the synthetic task, with the results report | complete | - | - | 5 | PRPs/plans/local-model-route-phase-6-compatibility-checks.plan.md |

#### Phase-status lifecycle

Every row starts at `pending` and advances through `in-progress`, `implemented`, `tested` and `complete`, as defined by relay's PRD template. With no test framework declared, a row goes from `implemented` to `complete` directly.

### Phase Details

**Phase 1: Machine baseline**
- **Goal:** Know what this machine can serve before configuring the route.
- **Scope:** `atr.local.fetch`, `atr.local.serve` and `atr.local.bench` meet AC-1 to AC-3; the operator approves the downloads (about 22.5 GB on D: and a 2.6 GB image), stops unneeded containers and frees the GPU from the desktop; the measured speeds and choices are recorded.
- **Success signal:** Benchmark files for both main models, and the chosen quantization, context and slot count recorded in `models.toml`.

**Phase 2: Hardened server**
- **Goal:** A server that is pinned, isolated and accountable for each run.
- **Scope:** Flags tuned from Phase 1, including the prompt-cache RAM; the offline, loopback-only and key checks of AC-2; a server record that the launcher can copy into a trial.
- **Success signal:** Check L1 passes for both main models.

**Phase 3: Agent route option**
- **Goal:** Claude Code reaches the local model, and nothing else, with the settings recorded.
- **Scope:** The agent's route option and the settings of AC-4; the pre-flight check of AC-5; `agent/route.json`.
- **Success signal:** A vanilla run with L-Small on the synthetic task reaches the server and finishes.

**Phase 4: Local launcher and allowlists**
- **Goal:** Local runs are started the same way every time, never alongside an MVP job, and behind the right network.
- **Scope:** The launcher of AC-7 (server per run, power sampling, record copy, MVP-priority refusal); the allowlist variants of AC-8.
- **Success signal:** A local job run through the launcher leaves the server's records and power samples in its trial folder, and the launcher refuses while an MVP job runs.

**Phase 5: Store, budget and export**
- **Goal:** Local runs are counted, reconciled and published correctly.
- **Scope:** AC-6 (route-aware loading and reconciliation), the budget half of AC-7, AC-9 (export).
- **Success signal:** The synthetic local run is loaded with route `local`, reconciled across three sources, excluded from the MVP's ceiling and exported with its label.

**Phase 6: Compatibility checks**
- **Goal:** Every compatibility question of the plan has an answer before any Target A run.
- **Scope:** Checks L1 to L10 and the relay probe on the synthetic task (AC-10); fixes the checks call for, within this PRD's scope; the results report.
- **Success signal:** Ten check results recorded, each with its fallback where it failed, and the relay probe's outcome when it was run.

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| How runs reach a local model | Directly, through llama.cpp's Messages API | A LiteLLM gateway; claude-code-router | The server already speaks the protocol Claude Code uses; one fewer component to pin and secure |
| How the server is packaged | llama.cpp's CUDA image in Docker, pinned by digest | A native build in WSL; a Windows binary | Same pattern as the Collector; pinned and isolated |
| Server lifetime | One server per run, with a new key | A long-lived server | No run inherits another's cache; the key is per run |
| Where weights live | D:, bind-mounted read-only | The WSL disk; a Docker volume | C:, which holds both disks, has little free space |
| Attribution header | Off (`CLAUDE_CODE_ATTRIBUTION_HEADER=0`) | Left on | Reported to break prefix reuse on local servers |
| PRD scope | WP0 to WP3 of the local models plan | The whole plan | Target A runs need D-031 decided and the checks' results first |
| Relay probe priority | Should | Must | Not needed to validate the vanilla route |
| Export in scope | Must | Deferred to publication | Model identifiers may trip the leak check, and local runs must never publish unlabeled |
| Cost of local runs | Zero API cost with a labeled source, plus machine time and energy | A price-table entry for local models | D-022 requires every cost to state its source; energy is not an API price |

---

## Research Summary

**Market Context**
- llama.cpp's server accepts Anthropic's Messages API (`/v1/messages`, `/v1/messages/count_tokens`) with streaming, tool use and thinking since January 2026 (https://huggingface.co/blog/ggml-org/anthropic-messages-api-in-llamacpp).
- Claude Code puts an attribution block at the start of the system prompt; `CLAUDE_CODE_ATTRIBUTION_HEADER=0` removes it, and on custom base URLs older versions put a per-request token in it (https://code.claude.com/docs/en/env-vars.md). Measurements report the block breaking prefix caching (https://github.com/motiful/cc-cache-audit) and slowing local inference by about 90% (https://agentpatterns.ai/context-engineering/kv-cache-invalidation-local-inference/); the two sources disagree on whether a process environment variable is enough or a settings `env` block is needed.
- Claude Code's compatibility settings for gateways include `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, `CLAUDE_CODE_DISABLE_THINKING`, `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`, `API_TIMEOUT_MS` and `CLAUDE_STREAM_IDLE_TIMEOUT_MS`; for an unknown model id it assumes a 200K window (https://code.claude.com/docs/en/env-vars.md, https://code.claude.com/docs/en/model-config).
- Community reports from March to May 2026 describe Qwen3.5/3.6 tool calls inside thinking blocks and template mismatches on llama.cpp, with workarounds of fixed templates or thinking off; one links `--parallel 1` to full prompt reprocessing. Anecdotal (https://reddit.sentinel-team.org/posts/1rh6455/snapshots/2026-03-02T18%3A21%3A08.366403Z).
- On 8 GB cards with `--n-cpu-moe`, reports give 40+ tokens/s generation and 150 to 500 tokens/s prompt processing, on an RTX 3070 Ti and a 4060 laptop, not on a 3060 Ti (https://medium.com/coding-nexus/one-flag-tripled-my-tokens-per-second-on-an-8gb-gpu-238f55d1e3bd).
- Gap: no measured benchmark of these models' agentic task success inside Claude Code was found.

**Technical Context**
- The agent requires `ANTHROPIC_API_KEY` and has no endpoint option (`harness/src/atr/agents/claude_sdk.py:229-231`); it pins only the Haiku alias besides the session and sub-agent models (`harness/src/atr/agents/claude_sdk.py:234-249`).
- `_check_collector` is the pattern for a pre-flight check from inside the container (`harness/src/atr/agents/claude_sdk.py:171-191`), and `workflow.json` the pattern for a per-trial record (`harness/src/atr/agents/claude_sdk.py:193-217`).
- The runner forwards `max_budget_usd`, a client-side cost estimate that cannot bound a local run (`harness/src/atr/agents/claude_sdk_runner.py:43-63`).
- The reconciliation view requires costs to match within 1e-6, so a missing cost reads as a mismatch; the spend view and the trials table have no route column (`harness/src/atr/store/load.py:81-135`).
- The budget's `--prefix` only splits out a sub-total; the ceiling check uses the total of every job (`harness/src/atr/ops/budget.py:56-67`).
- The export allowlist (version 2) has no route field, and its relative-path pattern may match model identifiers that contain `/` (`harness/src/atr/store/export.py:31-50`).
- The synthetic task's manifest declares no network allowlist (`targets/synthetic-events/task-01.toml`), so check L9 needs a variant with one.
- The drafted local inference code starts a loopback-only server with a per-start key and checks it, but nothing yet connects it to the agent, and its record is per server, not per trial (`harness/src/atr/local/serve.py`); the config module finds `infra/` relative to the repository, which assumes the package runs from the repository (`harness/src/atr/local/config.py`).

---

*Generated: 2026-11-04*
*Approved: 2026-11-04*
*Status: APPROVED*
