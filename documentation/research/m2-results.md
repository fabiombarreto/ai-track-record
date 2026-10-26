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
| Graders: static analysis, independent review and human confirmation | Done | 2026-10-26 |
| Skipped-step flag ([D-051](../decisions/decision-log.md#d-051)) | Done | 2026-10-26 |
| Phase 0 harness fixes: worktree collection on a timeout, cleanup after a killed job, Collector check before each run | Done | 2026-10-26 |
| Local store and exporter end to end | Not started | |

## Web tools disabled

The Agent SDK agent takes a `disallowed_tools` option, which the runner passes to the SDK. On Target A every configuration runs with `WebSearch` and `WebFetch` removed, inside the network allowlist set by the task templates.

A check run on Target A with Haiku confirmed the result:

- the main session has neither tool and cannot load them through `ToolSearch`;
- relay's web research sub-agent declares only those two tools, so Claude Code refuses to start it, because it would have no tools left.

Relay's plan writer treats an unusable research result as partial research and continues, so the refusal costs relay its web grounding and nothing else. This is the limit [D-050](../decisions/decision-log.md#d-050) accepted, and it applies to every configuration. For [D-051](../decisions/decision-log.md#d-051), the skipped research step is forced by the environment, not a choice of the workflow.

## Worktree collection

Relay works in a git worktree and leaves its changes uncommitted there. The runner used to bring them into the main tree by applying the worktree's diff as a patch. Relay also writes some of its reports in the main tree. In the first relay pilot one of them already existed there, so `git apply` refused the whole patch: a run that relay completed with 161 passing tests of its own was graded 0.0.

Collection now copies every file the worktree changed against `base` over the main tree, so the worktree wins. The failed run was graded again from its saved artifacts through Harbor's verifier and scored 1.0. The pilot table below shows the corrected grade.

## Phase 0 harness fixes

Three gaps found in Phase 0 ([follow-ups](phase-0-results.md#follow-ups)) are closed. Each fix was tested on a copy of Target A's task 01 whose `oracle` imitates the failure.

| Gap | Fix | Test |
|---|---|---|
| A timeout kills the runner before it collects relay's worktree, so the run is graded without its partial code | Collection moved from the runner to the grader, which runs after the agent phase however it ended. The grader records each worktree in `details.json`, and `.worktrees/` never crosses as a nested repository | An `oracle` that writes the solution into an uncommitted worktree, puts a report in both trees and then hangs was stopped by the timeout (`AgentTimeoutError`). The grader collected 6 files, the worktree's copy of the report won, and the run scored 1.0 |
| A killed job leaves its trial's containers and networks running | `python -m atr.ops.cleanup <job dir>` removes the Compose projects of every trial without a result, matched by the trial name Harbor gives them. `--dry-run` lists them first | Harbor was killed with SIGKILL mid-trial. The command removed the trial's three containers and its network, and left the Collector and other containers alone |
| A run started while the Collector is down loses its telemetry without notice | Before the runner starts, the agent sends an empty OTLP request from the task container to the Collector. Anything but HTTP 200 fails the trial with a clear error, before any API call. An empty request records nothing | With the Collector stopped, the trial failed with "telemetry Collector … did not answer" and made no API call. With it running, the same trial passed |

The synthetic task and Target A's task 03 still score 1.0 with `oracle` after the change.

## Quality graders

[D-053](../decisions/decision-log.md#d-053) made these graders central, since the oracle alone does not separate the configurations.

### Static analysis (GRD-03)

The grader runs the static analysis tools a task declares (`task.static_analysis` in the manifest) on the base and on the run, inside the verifier. It counts the findings the run introduced as `new_static_findings` in `reward.json` and lists them in `details.json`. Findings are matched by file, rule and message, not by line, since the run moves lines around. Static analysis never changes the reward.

Target A's tasks declare `ruff`, with the project's own configuration. On task 01, the reference solution and the pilot changes of vanilla and relay on Sonnet each introduced no finding: both agents ran `ruff` themselves. A copy of the reference solution with an unused import and an unused variable added produced those two findings, plus the import-order findings the misplaced import causes.

### Independent review (GRD-04)

`python -m atr.review.run <trial> --task <task>` reviews one graded run with a pinned reviewer that belongs to no workflow ([D-018](../decisions/decision-log.md#d-018)):

- **Reviewer:** Claude Code's built-in `/code-review` at effort `high`, on Sonnet 5.5, through the same pinned Agent SDK as the runs (0.2.170), in its own container with web tools disabled.
- **What it reviews:** the run's graded changes (the verifier's `changes.patch`) applied to a clean copy of the base commit. Relay's working files under `PRPs/` are left out, so relay and vanilla are reviewed on the same kind of change. The specification in the base stays readable as context.
- **Output:** a second turn in the same session asks the reviewer to report the findings it listed through its `ReportFindings` tool, so each finding comes back as data: file, line, category, summary and failure scenario. They are written to `review/review.json` in the trial folder, with the reviewer's transcript. A run with no changes is not sent to the model.

On task 01 the reviewer listed ten findings for vanilla on Sonnet and ten for relay on Sonnet, several of them the same in both, which suggests a consistent reviewer. Some findings flag behavior that the specification requires, for example clearing the draft on submission. Such false positives are what the human confirmation filters out. A review costs up to about US$ 0.40, so about US$ 18 for the 45 MVP runs.

### Human confirmation (GRD-05)

`python -m atr.review.confirm sample <dir> <jobs>...` picks one reviewed run per configuration and task at random, 15 of the 45 MVP runs. For each it writes a sheet with the task and the findings, and no hint of the configuration, so the operator grades blind (part of GRD-08). The operator marks each finding `confirmed` or `rejected`. `python -m atr.review.confirm summary <dir>` then reports the confirmed share per configuration.

## Skipped-step flag (GRD-09)

`python -m atr.checks.skipped_steps <trial>...` records, for each relay run, which steps of relay's own protocol each phase skipped and whether the final summary mentions them ([D-051](../decisions/decision-log.md#d-051)). It writes `checks/skipped_steps.json` in the trial folder. A step skipped without mention raises a flag for human review. The flag never enters a grade, and vanilla has no protocol to check.

- **Steps checked, per phase:** the plan with its review, the worktree, tests first (when the project declares `tdd: true`), the implementation with its code review, the docs sync (when `docs_sync: true`), tests after (when `tdd: false`), the test run and the test review. The project's flags come from the methodology file in the base.
- **Evidence:** the step's entry in relay's `orchestrator-run.json`, where the last attempt decides, or the record the step leaves, such as the docs sync manifest. Relay does not log every step in every run, so both sources are needed. A worktree fallback counts as a deviation.
- **Halts:** a phase that halted is checked only up to the step where it stopped, which is marked as the halt, not as a skip.
- **"Mentioned"** is a keyword match on the summary, which is why the result is a flag to review and not a verdict.
- **Not checked:** steps inside a step, such as relay's web research, which [D-050](../decisions/decision-log.md#d-050) removes from every relay run on Target A.

On the relay runs so far:

| Run | Result |
|---|---|
| Phase 0, relay on Sonnet | Worktree deviated and docs sync skipped, both announced: no flag, as [D-051](../decisions/decision-log.md#d-051) describes |
| Phase 0, relay on Haiku (two runs) | No step skipped |
| M2 pilots, relay on Sonnet, tasks 01 and 03 | No step skipped |
| M2 pilots, relay on Haiku, tasks 01 and 03 | Halted at the implementation and at tests first; the steps before were done |
| The Phase 0 Sonnet run with its summary replaced by one that announces nothing | Flagged: both deviations silent |

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

Overnight, Docker Desktop stopped while a pilot was running. The run was lost with no result, its containers exited, and the telemetry Collector stopped with them. The trial was set aside and run again. The harness fixes above now cover the cleanup and the Collector. Long unattended batches, such as M3's, still need someone to restart Docker Desktop if it stops.

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
