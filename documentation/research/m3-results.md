# M3 results: the MVP runs

> **Status:** In progress · **Last updated:** 2026-11-11 · **Owner:** Fabio Martins Barreto

This report records milestone M3: the 45 runs of the MVP experiment, 3 tasks on Target A × 5 configurations × 3 repetitions, with their grades and analysis ([schedule](../product/06-scope-and-roadmap.md#4-schedule-to-the-mvp)). The API credits ran out after the first repetition. Under [D-059](../decisions/decision-log.md#d-059), M3 closes on that repetition's 12 runs, and the other 33 follow after M4. Target A and its tasks are described in the [M1 results](m1-results.md), and the harness and graders in the [M2 results](m2-results.md).

## Progress

| Item | Status | Date |
|---|---|---|
| Relay releases chosen ([D-054](../decisions/decision-log.md#d-054)) | Done | 2026-10-31 |
| Harness updates for relay 0.49.0 | Done | 2026-10-31 |
| Hypotheses declared ([D-020](../decisions/decision-log.md#d-020)) | Done | 2026-10-31 |
| Pilot runs of relay 0.49.0 on Target A | Done | 2026-11-01 |
| The 45 runs, in three batches | Stopped at 12 of 45: the first repetition, without the earlier release ([D-059](../decisions/decision-log.md#d-059)); the other 33 follow after M4 | 2026-11-10 |
| Grading: oracle, existing tests, static analysis, independent review, protocol check | Done for the 12 runs | 2026-11-10 |
| Blind confirmation of review findings, one run per configuration and task: 12 runs | Not started | |
| Telemetry metrics short of the events | Done | 2026-11-01 |
| Analysis | Not started | |

## Configurations

| Configuration | Workflow | Model | Question it answers |
|---|---|---|---|
| **Reference** | relay 0.49.0 | Sonnet 5.5 | — |
| Smaller model | relay 0.49.0 | Haiku 5.5 | How much quality is lost, and how much money saved, with a smaller model? |
| Larger model | relay 0.49.0 | Opus 5.5 | Does a larger model pay for itself? |
| Earlier release | relay 0.47.0 | Sonnet 5.5 | Did the 0.49.0 fixes help? |
| Baseline | vanilla | Sonnet 5.5 | Is the workflow worth its cost? |

Every run uses the Agent SDK 0.2.170, Target A's network allowlist, no web tools ([D-050](../decisions/decision-log.md#d-050)), a time limit of three hours and a cost cap of US$ 60, the same for every configuration. Each relay release runs from a copy of its exact commit ([D-054](../decisions/decision-log.md#d-054)).

## Harness updates

Relay 0.49.0 changes what the harness reads from a relay run, so the harness gained four things before the runs.

- **Plugin version per run.** Before its first API call, the agent writes `agent/workflow.json` with the plugin's name, version and a digest of its files. The store keeps them per trial, with the copy's commit, and the export carries the name and version. Runs made before this record take the version from the copy their job mounted.
- **Skipped-step check for both releases.** Relay 0.49.0 adds two steps to each phase of `/relay-execute`, the D8 mutations after the implementation and a snapshot at the end, and names the outcome each step may log. The check ([D-051](../decisions/decision-log.md#d-051)) now follows the protocol of the release the run used. It also stores the deviations relay 0.49.0 records about itself, next to its own result, since a workflow is not graded by its own records alone. On the 0.47.0 runs of Phase 0 and M2 the check gives the same results as before.
- **Project docs counted apart.** The size of a run's changes now leaves out the project's knowledge base under `docs/`, which relay's docs sync always updates and vanilla sometimes does, and counts it separately. Product sizes in the store are therefore a little smaller than in the M2 tables.
- **Spend.** The store has a `spend` view of run and review costs, and `python -m atr.ops.budget --next <cap>` stops a batch before a run whose cap could pass the US$ 800 ceiling ([D-028](../decisions/decision-log.md#d-028)). Both are lower bounds of what was billed, so the operator checks the credit balance before each batch.

Relay 0.49.0 keeps all its `PRPs/` files at the project root and leaves only code, tests and docs in the worktree. The grader already collects the worktree's changes and the check already reads both trees, so neither needed a change for that.

## Hypotheses

Declared on 2026-10-31, before the pilots and the batches.

| # | Hypothesis | Measured by |
|---|---|---|
| H1 | Relay 0.49.0 on Haiku no longer halts in its test-first track on Target A, where 0.47.0 halted on both M2 pilots, and meets the oracle on most of its runs | Outcomes and rewards of the smaller-model runs |
| H2 | Relay on Sonnet costs at least ten times as much as vanilla on Sonnet for the same oracle result | Cost and reward of the reference and baseline runs |
| H3 | Relay 0.49.0 on Sonnet records fewer deviations from its protocol than 0.47.0, at a similar or higher cost | Skipped-step check and cost of the reference and earlier-release runs |
| H4 | Opus does not improve on Sonnet's oracle result, and costs more | Rewards and cost of the larger-model and reference runs |
| H5 | The quality graders (new static findings, confirmed review findings) differ less between configurations than cost and time do | Graders across the five configurations |

With three repetitions per cell, every comparison is labeled as a small sample ([D-020](../decisions/decision-log.md#d-020)). Until repetitions 2 and 3 exist, M3 has one run per cell, so every result is marked preliminary ([D-059](../decisions/decision-log.md#d-059)). H3 needs the earlier-release runs, so it is answered once they run.

## Pilots

Two runs of relay 0.49.0 on Target A checked the release and the harness updates before the batches, on the two cells where 0.47.0 had trouble or cost the most in M2. They are not part of the 45 runs.

| Run | Oracle | Steps of the protocol | Cost (US$) | Time (min) | 0.47.0 in M2 |
|---|---|---|---|---|---|
| Haiku, task 01 | Met (1.0) | All 27 done; relay recorded no deviation | 5.54 | 121 | Halted in its test-first track, oracle not met, US$ 1.07, 20 min |
| Sonnet, task 03 | Met (1.0) | All 27 done; relay recorded no deviation | 17.05 | 55 | Oracle met, US$ 15.26, 51 min |

Both runs kept the existing tests passing and added no static analysis finding. On Haiku the test review asked for changes twice before approving, and the docs sync of the first phase ran out of its review budget, an outcome the release accepts. Haiku took two of the three hours of the time limit on the smallest task, so a Haiku run on a larger task may reach it; a run that does is graded with what it left, like any other.

The pilots cost US$ 22.59, and the MVP had spent US$ 42.05 before them. With their costs, a run is projected at US$ 15–18 for the reference, US$ 5.5–7 on Haiku, US$ 25–30 on Opus (the reference at the Opus-to-Sonnet ratio of Phase 0), about US$ 13.7 for the earlier release (its M2 pilots) and US$ 0.46 for the baseline. The 45 runs then cost US$ 525–640, or about US$ 580–705 with one retry in ten. With the spend so far and about US$ 18 of reviews, the MVP totals US$ 610–725, or up to about US$ 790 with retries: under the US$ 800 ceiling, with little room at the top. The launcher stops before any run whose cap could pass the ceiling, and the runs go by repetition, so a shortfall would cut runs of the third repetition, not a configuration.

## Running the batches

The runs go one at a time, in sessions of about four hours, as the machine cannot stay on overnight. Running two at a time would halve the calendar time, but time is one of the graders, and two runs would compete for the machine and the API. The launcher does not start a run that may not finish before the session ends, and it allows 150 minutes for relay on Haiku, 75 for relay on Sonnet or Opus and 15 for vanilla. The runs keep the order drawn for their repetition.

A run that fails before its agent makes any API call, such as when Docker Desktop loses its network, is an infrastructure error. The launcher sets it aside and runs it again, up to three attempts. A run interrupted after its agent started is also set aside and run again from the start. Each attempt set aside is recorded below with its cost, which the telemetry gives and the spend view does not include.

| Run | Attempt | What happened | Cost (US$) |
|---|---|---|---|
| Opus, task 02, repetition 1 | 1 | Stopped after 7 minutes, when the session ended | 4.65 |
| Haiku, task 02, repetition 1 | 1 | Agent setup timed out: Docker Desktop could not resolve the package hosts | 0 |
| Vanilla, task 01, repetition 1 | 1 | Environment build failed, for the same reason | 0 |
| Vanilla, task 03, repetition 1 | 1 | Agent setup timed out, for the same reason | 0 |
| Sonnet, task 03, repetition 1 | 1 | Stopped after 16 minutes, when the operator restarted the launcher | 4.64 |
| Earlier release, task 01, repetition 1 | 1 | Stopped after 43 minutes, when the API workspace reached its monthly usage limit | 14.24 |

The last attempt met the oracle with the code it left, but it ended before relay's protocol finished, so it is set aside like the others.

Since then the launcher starts a run only if it fits in what is left of the month's API allowance at the highest cost seen for its configuration, and it stops the batch when a run ends without a result. With US$ 56 left for November, the next session fills the empty cells that most comparisons depend on: the baseline on task 02, the reference on tasks 01 and 02, then the larger model on task 01 if it still fits, with the independent reviews of the finished runs. The three runs of the earlier release wait for the next allowance, since one alone would not complete its row.

That session ran all four runs and the reviews of the finished ones. The month's included credits were then used up, and the owner decided on 2026-11-10 not to buy credits for now. The batches stop there. The earlier release and repetitions 2 and 3 run after M4, from the included credits of later billing cycles, in the order drawn for each ([D-059](../decisions/decision-log.md#d-059)).

## The first repetition

Twelve runs of relay 0.49.0 and vanilla on Target A, one per configuration and task. Each cell gives the oracle result (criteria satisfied), the run's cost in US$ and its wall-clock time.

| Configuration | Task 01 | Task 02 | Task 03 |
|---|---|---|---|
| Reference: relay, Sonnet | Met (1.0) · 11.41 · 30 min | Met (1.0) · 8.92 · 27 min | Halted, not met (0.1) · 9.66 · 35 min |
| Smaller model: relay, Haiku | Met (1.0) · 4.05 · 60 min | Halted, not met (0.0) · 0.72 · 9 min | Halted, not met (0.1) · 3.52 · 48 min |
| Larger model: relay, Opus | Halted, not met (0.9) · 21.68 · 48 min | Halted, not met (0.0) · 13.35 · 35 min | Halted, not met (0.1) · 21.06 · 44 min |
| Earlier release: relay 0.47.0, Sonnet | not run | not run | not run |
| Baseline: vanilla, Sonnet | Met (1.0) · 0.45 · 2 min | Met (1.0) · 0.55 · 3 min | Met (1.0) · 0.57 · 4 min |

- Every run kept the existing tests passing, and none added a static analysis finding. All 12 were reviewed, at US$ 2.56 in total. The runs themselves cost US$ 95.93.
- Six of the nine relay runs halted, each with relay's own code, and each is graded with the code it left. The three relay runs that met the oracle are the three that finished their protocol. The protocol check found no skipped step in the phases each run reached.

  | Run | Phase | Halt |
  |---|---|---|
  | Haiku, task 02 | 1 | `FAILED_PLAN_REVIEW_STUCK`: the plan review failed the same item twice |
  | Haiku, task 03 | 3 | `HALT_PHASE_3_PLAN_REVIEW_STRUCTURAL`: the plan was never approved |
  | Opus, task 01 | 2 | `FAILED_IMPLEMENT_DISPUTE_UPHELD_TEST_WRONG`: the code reviewer upheld a dispute against a test |
  | Opus, task 02 | 1 | `FAILED_IMPLEMENT_FAILED_AFTER_N_RETRIES` |
  | Opus, task 03 | 2 | `FAILED_IMPLEMENT_DISPUTE_UPHELD_PRD_AMBIGUOUS`: the code reviewer upheld a dispute that the specification contradicts itself |
  | Sonnet, task 03 | 2 | The same as Opus on task 03, on the same point |

- Five of these halts were first stored as completed runs. Relay 0.49.0 writes some halts only to `orchestrator-halt.json` and leaves the outcome in `orchestrator-run.json` empty, or writes no run record at all, and the protocol check read only the run record. Since 2026-11-11 the check reads both, and the store was rebuilt. No grade changed, only the outcomes.
- On task 03, the three relay runs halted before the phase that the failing hidden tests cover, so each satisfied one criterion. The 0.49.0 pilot on Sonnet finished all three phases ([Pilots](#pilots)). Sonnet and Opus stopped on the same point, where two rules of the specification give different error responses to a request from another tenant. Vanilla and the pilot followed the reading the hidden tests expect, without raising it. Whether the specification really contradicts itself is for the owner to judge. The tasks stay frozen ([D-053](../decisions/decision-log.md#d-053)), so this is a finding for the analysis, not a change to the task.
- The results are preliminary: one run per cell ([D-059](../decisions/decision-log.md#d-059)).

## Telemetry metrics short of the events

M2 left open why the telemetry metrics fall 3–7% short of the events on some runs ([M2 results](m2-results.md#telemetry-metrics-short-of-the-events)). The stored telemetry shows a pattern:

- on every M2 run with a shortfall, the missing output tokens are those of API requests that took longer than about 60 seconds; on the Haiku runs, the shortfall equals their output tokens exactly;
- all of these runs ran behind Target A's network allowlist, where traffic to the Collector passes through Harbor's egress proxy. Runs without the allowlist kept their long requests, and the runs on Target A with no request over 60 seconds match.

The likely cause is that Claude Code exports metrics as deltas only when they change, so during a long request its connection to the Collector stays idle, the proxy drops it, and the next export, which carries that request's metrics, is lost. Events and the SDK's usage are unaffected, and cost comes from them ([D-022](../decisions/decision-log.md#d-022)).

The pilots, still on deltas, showed the same pattern. The Haiku pilot had no request over 60 seconds, and its metrics match the events. The Sonnet pilot had four, of 68 to 139 seconds, and its metrics lack exactly their 72,836 output tokens.

The fix makes each export carry running totals, so an export that is lost is made up by the next one:

- the agent sets `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=cumulative`;
- the loader keeps the last point of each cumulative series and still sums the deltas of earlier runs, whose results do not change.

Two short check runs on Haiku behind Target A's allowlist, one with a request of 61 seconds and one with a request of 111 seconds, then matched the events and the SDK in tokens and cost. The 45 runs all use the fix. Runs before M3 keep their shortfall, which is recorded, not corrected.
