# M2 results: harness and pilot runs

> **Status:** Draft · **Last updated:** 2026-10-26 · **Owner:** Fabio Martins Barreto

This report records milestone M2 as it progresses: the harness items carried from M0 and M1, and the pilot runs on Target A's three tasks ([schedule](../product/06-scope-and-roadmap.md#4-schedule-to-the-mvp)). Target A is a private B2B SaaS built with Django and Next.js ([D-013](../decisions/decision-log.md#d-013)), and its tasks are described in the [M1 results](m1-results.md).

## Progress

| Item | Status | Date |
|---|---|---|
| Web tools disabled per run ([D-050](../decisions/decision-log.md#d-050)) | Done | 2026-10-25 |
| Worktree collection that survives files the workflow also writes in the main tree | Done | 2026-10-25 |
| Pilot runs on Target A | Done | 2026-10-26 |
| Budget check with the pilot costs ([D-028](../decisions/decision-log.md#d-028)) | Done | 2026-10-26 |
| Graders: static analysis and independent review | Not started | |
| Skipped-step flag ([D-051](../decisions/decision-log.md#d-051)) | Not started | |
| Phase 0 harness fixes: worktree collection on a timeout, cleanup after a killed job, Collector check before each run | Not started | |
| Local store and exporter end to end | Not started | |

## Web tools disabled

The Agent SDK agent takes a `disallowed_tools` option, which the runner passes to the SDK. On Target A every configuration runs with `WebSearch` and `WebFetch` removed, inside the network allowlist set by the task templates.

A check run on Target A with Haiku confirmed the result:

- the main session has neither tool and cannot load them through `ToolSearch`;
- relay's web research sub-agent declares only those two tools, so Claude Code refuses to start it, because it would have no tools left.

Relay's plan writer treats an unusable research result as partial research and continues, so the refusal costs relay its web grounding and nothing else. This is the limit [D-050](../decisions/decision-log.md#d-050) accepted, and it applies to every configuration. For [D-051](../decisions/decision-log.md#d-051), the skipped research step is forced by the environment, not a choice of the workflow.

## Worktree collection

Relay works in a git worktree and leaves its changes uncommitted there. The runner used to bring them into the main tree by applying the worktree's diff as a patch. Relay also writes some of its reports in the main tree. In the first relay pilot one of them already existed there, so `git apply` refused the whole patch: a run that relay completed with 161 passing tests of its own was graded 0.0.

The runner now copies every file the worktree changed against `base` over the main tree, so the worktree wins. The failed run was graded again from its saved artifacts through Harbor's verifier and scored 1.0. The pilot table below shows the corrected grade.

## Pilot runs on Target A

All pilots ran one at a time, with the network allowlist, without web tools, with telemetry, and with a cost cap per run.

| Configuration | Task 01 | Task 02 | Task 03 |
|---|---|---|---|
| Vanilla, Sonnet | 1.0 · US$ 0.43 · 2 min | 1.0 · US$ 0.44 · 2 min | 1.0 · US$ 0.50 · 3 min |
| Vanilla, Haiku | 1.0 · US$ 0.25 · 5 min | 1.0 · US$ 0.36 · 8 min | 1.0 · US$ 0.35 · 8 min |
| Relay, Sonnet (reference) | 1.0 · US$ 12.18 · 41 min | — | 1.0 · US$ 15.26 · 51 min |
| Relay, Haiku | 0.0 · US$ 1.07 · 20 min (halted; 1 of 10 criteria) | — | 0.0 · US$ 0.44 · 26 min (halted) |

Each cell gives the reward, the cost computed by the SDK and the wall time. "1.0" means every hidden and existing test passed, so all ten acceptance criteria were met. The pilots, the check run and a run lost to a Docker stop cost about US$ 32 in all, paid with the plan's included credits.

## Findings

### Precise specifications make the tasks easy for a strong model

Vanilla on Sonnet met every criterion of all three tasks in two to three minutes, writing 40–50 KB of changes per task, its own tests included. The transcripts show it read only the specification, relay's context files and the code at the base; the hidden tests were not in its image. The likely cause is the specifications themselves. Each has an interface contract with exact error bodies, numeric examples and the order of checks, which leaves a strong model little to get wrong.

Vanilla on Haiku did the same in five to eight minutes. The hidden oracle therefore separates neither relay from vanilla nor Sonnet from Haiku on vanilla. Cost and time do: relay on Sonnet cost about 28 times as much as vanilla on Sonnet on task 01 for the same grade.

### Relay's test-first track halts on Haiku

Target A's relay context declares test-driven development (`tdd: true`), so relay runs its test-first track. Relay on Haiku halted on both tasks it tried, at two different points of that track:

- **Task 03, `FAILED_TDD_WRITER_HALTED`.** Relay's plan reviewer approved a phase plan that listed production files. Relay's test writer, in test-first mode, refuses a plan with rows that are not tests. The orchestrator halted and asked for a human decision, which an unattended run cannot give.
- **Task 01, `FAILED_IMPLEMENT_R-X`.** The test-first suite was approved and the implementation applied, but the code reviewer's test-modification guard (R-X) saw the approved test file as newly created in the implementation's diff. The implementer may not touch tests, so no retry could clear it, and the orchestrator halted.

With Sonnet, relay hit the same guard and got past it by improvising: it passed the approved test files as part of the diff base and dispatched the agents directly, and its final summary announced each deviation. Haiku followed the protocol and stopped.

Vanilla on Haiku met every criterion of the same tasks, so the halts come from relay's protocol, not from the model's ability. This is a conflict inside relay 0.47.0, measured as it is. A fix belongs to a later relay release, which the benchmark can then compare.

### Docker Desktop can stop during unattended runs

Overnight, Docker Desktop stopped while a pilot was running. The run was lost with no result, its containers exited, and the telemetry Collector stopped with them. The trial was set aside and run again. This adds weight to the Phase 0 items on cleanup after a killed job and on checking the Collector before each run.

## Budget check

The pilots replace the synthetic-task costs in the [M0 projection](phase-0-results.md#cost-projection-for-the-mvp). Two configurations were not piloted on Target A, so their costs are estimates.

| Configuration | Cost per run on Target A | Basis |
|---|---|---|
| Reference: relay on Sonnet | about US$ 13.7 | Pilots on tasks 01 and 03: US$ 12.18 and US$ 15.26 |
| Smaller model: relay on Haiku | about US$ 0.8 | Pilots on tasks 01 and 03, both halted early; a completed run would cost more |
| Larger model: relay on Opus | about US$ 23 | Estimate: the reference at the Opus-to-Sonnet cost ratio of the Phase 0 pilots |
| Earlier release: relay on Sonnet | about US$ 13.7 | Estimate: the same as the reference |
| Baseline: vanilla on Sonnet | about US$ 0.46 | Pilots on all three tasks |
| **Total per task and repetition** | **about US$ 52** | |

At that size the 45 runs cost about US$ 470, or about US$ 520 with retries. That passes the US$ 400 target and stays under the US$ 800 ceiling. [D-028](../decisions/decision-log.md#d-028) allows that, so the frozen scope stays as it is. The Opus and earlier-release figures are the least certain, and an earlier relay release may well cost less.

## Decisions

The pilots led to two decisions by the owner on 2026-10-25:

- Target A keeps relay's test-first methodology, and the halts are recorded as a finding ([D-052](../decisions/decision-log.md#d-052)).
- The tasks stay frozen. Configurations are compared on cost, time, workflow robustness and the quality graders, which become central in M2 ([D-053](../decisions/decision-log.md#d-053)).
