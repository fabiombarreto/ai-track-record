# Measurement model

> **Status:** Draft · **Last updated:** 2026-10-20 · **Owner:** Fabio Martins Barreto

This document defines what AI Track Record measures and the rules that make comparisons meaningful. Statistical procedures will be detailed in a separate methodology document.

## 1. From requirements to metrics

The owner's requirements name five things to measure ([D-007](../decisions/decision-log.md#d-007)). Each maps to one or more metric families:

| Requirement | Metric family | Main metrics |
|---|---|---|
| Specification met | Correctness | Task success, criteria satisfied |
| Bugs found | Correctness, honesty | Oracle failures, regressions, escaped defects |
| Code quality | Quality | New static findings, review findings, mergeability |
| Time spent | Efficiency | Wall-clock duration, duration per stage |
| Tokens used | Efficiency | Tokens by type and model, cost |

Two families are added to make results trustworthy: **reliability** (does the configuration succeed consistently?) and **honesty** (does the workflow's claim of success match reality?).

## 2. Correctness

| Metric | Definition |
|---|---|
| **Task success** | The run passes every hidden oracle test and the target's existing test suite. Binary per run. |
| **Criteria satisfied** | The share of the specification's acceptance criteria whose oracle tests all pass. |
| **Regressions** | The number of tests in the target's existing suite that passed on the base commit and fail after the run. |
| **Success rate** | The share of runs with task success, per configuration and task, reported with a 95% interval. |

## 3. Reliability

Coding agents are non-deterministic: the same configuration can succeed and fail on the same task.

| Metric | Definition |
|---|---|
| **pass@k** | The estimated probability that at least one of *k* independent runs succeeds. Measures capability. |
| **pass^k** | The estimated probability that all *k* independent runs succeed. Measures consistency, which is what a team relying on the configuration experiences. |
| **Outcome distribution** | The share of runs ending `completed`, `halted` (by native reason), `budget_exceeded`, `timed_out` and `error`. |

## 4. Honesty

| Metric | Definition |
|---|---|
| **False completion rate** | The share of runs whose outcome is `completed` but that fail task success: the agent said "done" and it was not. |
| **Escaped defects** | Confirmed defects found by the independent review in runs that ended `completed`, that is, defects that got past the workflow's own checks. Reported per run. |

## 5. Quality

| Metric | Definition |
|---|---|
| **New static findings** | Findings from the target's configured linters, type checkers, architecture rules and security scanners that are present after the run and absent on the base commit, by severity. |
| **Review findings** | Findings from the independent code review, by severity, with the share confirmed by a human on sampled runs. |
| **Mergeability** | A verdict on a fixed rubric: *merge as is*, *merge after minor changes*, *needs rework* or *reject*. Produced by an LLM judge calibrated against human grades ([D-021](../decisions/decision-log.md#d-021)). |
| **Scope discipline** | Changes the specification did not ask for: files the task did not require, unrequested features, deleted or weakened tests. |

## 6. Efficiency

| Metric | Definition |
|---|---|
| **Cost (USD)** | Tokens multiplied by the dated price of each model. Always labeled with its source (see below). |
| **Tokens** | Input, output, cache write and cache read, per model; per role and stage when the adapter provides a stage map. |
| **Wall-clock duration** | From the start of the agent to the end of the run, excluding grading. |
| **API time** | Time spent waiting for model responses. |
| **Turns and tool calls** | The volume of interaction with the model and the environment. |
| **Rework** | Retries and review loops inside the workflow before it finished. |

### Cost sources

Cost comes from three sources that rarely agree exactly. Every published cost states its source ([D-022](../decisions/decision-log.md#d-022)).

| Source | Strength | Weakness |
|---|---|---|
| **Computed**: tokens × dated price table | Comparable across time and providers; can be recomputed | Depends on complete token capture |
| **Harness estimate**: the cost reported by the harness itself | Available for every run | A client-side estimate; may not know models from other providers |
| **Billed**: provider invoice or gateway log | The ground truth for money spent | Aggregated, delayed, not always attributable to a single run |

Computed cost is the default for comparisons. Billed cost is used to check it.

## 7. Derived metrics

| Metric | Definition |
|---|---|
| **Cost per successful task** | The total cost of all runs of a configuration divided by its number of successful runs. Includes the price of failures and retries. |
| **Time per successful task** | The same, for wall-clock duration. |
| **Pareto frontier** | The configurations that no other configuration beats on both cost and success rate. This is the dashboard's main chart. |

## 8. Rigor rules

These rules apply to every experiment that feeds the public dashboard ([D-020](../decisions/decision-log.md#d-020)).

1. **Pin everything.** Harness version, workflow version, model identifiers, provider routes, base commit, grader versions and price table are recorded with every run.
2. **Repeat.** At least 3 runs per configuration and task; 5 or more for configurations that are close to each other or to a decision threshold.
3. **Show uncertainty.** Proportions get 95% intervals (for example, Wilson intervals); differences get bootstrap intervals. Sample sizes are always shown.
4. **Change one factor at a time.** Each experiment compares configurations that differ from a reference in a single dimension.
5. **Declare before running.** The question and the expected result are recorded before the first run, and results are published whatever their direction.
6. **Same limits for all.** Every configuration in an experiment gets the same budget, time and turn limits. Hitting a limit is a measured outcome, not a reason to exclude a run.
7. **Separate infrastructure failures.** Runs that end in `error` are retried and reported separately; they never count as workflow failures or successes.
8. **Grade blind where humans grade.** Human reviewers do not see which configuration produced a run.
9. **Label small samples.** Results with fewer runs than rule 2 requires are marked as preliminary.

## 9. Known limitations

- **Few tasks.** A small task set supports decisions about the tasks measured; it does not prove general superiority.
- **Oracles check what was specified.** Desirable qualities that the specification does not state are covered only by review and static analysis.
- **Durations depend on the environment.** Hardware and provider latency affect wall-clock time, so durations are compared only within an experiment.
- **LLM judges have biases.** A judge may favor output from its own model family. The judge is fixed across an experiment and calibrated against human grades.
- **Workflows are tuned for some models.** Relay's prompts were written for Claude models, so results with other models measure workflow portability, not model capability.
