# Vision and scope

> **Status:** Draft · **Last updated:** 2026-10-20 · **Owner:** Fabio Martins Barreto

This document defines what AI Track Record is and is not, who it is for, what it does and does not do, and what it aims to achieve. Items backed by an **Accepted** decision come from the owner; everything else is a proposal until it is accepted in the [decision log](../decisions/decision-log.md).

## 1. Vision

AI Track Record produces public, verifiable evidence of how AI coding agents perform on real product work. It measures how well a prompt workflow and a model turn a written specification into a change ready for a pull request, what that costs in money and time, and how the answer changes as models and prompts evolve.

### Positioning statement

> **For** engineering leaders and tech leads who decide which AI models and workflows their teams adopt,\
> **who** need to know what quality, cost and time to expect on realistic work,\
> **AI Track Record** is a local-first benchmark with a public record of results\
> **that** runs prompt workflows end to end on real codebases, grades every run with checks the agent never sees, and reports quality, cost and time together.\
> **Unlike** public leaderboards that rank models on standardized open-source issues,\
> **it** treats the workflow and its version as the variable, measures delivery from specification to pull request, and shows every attempt, failures included.

### Primary purpose

AI Track Record exists first to produce public, verifiable evidence ([D-038](../decisions/decision-log.md#d-038)). When priorities conflict, whatever makes the public record more trustworthy and easier to read wins over breadth, convenience or internal tooling.

### End state

AI Track Record is a bounded study that becomes a maintained benchmark ([D-039](../decisions/decision-log.md#d-039)). A planned set of experiment rounds produces its findings. After that, feature development stops, and the project stays current by re-running its reference experiments when relevant new models or workflow versions appear.

## 2. The problem

AI coding agents are increasingly driven by **workflows**: layers of prompts, commands, sub-agents and skills that orchestrate planning, implementation, testing and review. Teams adopt and change these workflows mostly on intuition.

1. **Public benchmarks answer a different question.** They rank model-and-agent pairs on standardized tasks, usually turning an issue into a patch in an open-source repository. They do not tell a team whether its own workflow got better after the last prompt change, or which model should play which role.
2. **Quality is rarely shown next to cost and time.** A configuration that scores 3% higher at four times the cost is a different decision than its headline score suggests.
3. **Workflows grade themselves.** Many workflows include their own reviewers, and their approval is not evidence of correctness. In an evaluation recorded in the [relay repository](https://github.com/fabiombarreto/PRPs-agentic-eng), an independent review found at least five confirmed defects in three deliveries that relay's own reviewers had approved.
4. **Prompt changes ship without end-to-end regression evidence.** Existing evaluation tools test short, isolated behaviors well. Few show whether a change to a workflow made complete feature deliveries better or worse.
5. **Private evidence cannot be checked.** The most realistic tasks live in private codebases, and numbers that nobody can inspect are hard to trust.

## 3. What it is and what it is not

| AI Track Record is | AI Track Record is not |
|---|---|
| A benchmark that runs coding-agent workflows unattended on real tasks and grades the results | A coding agent, a prompt workflow or a prompt library |
| A method: frozen specifications, hidden tests, independent grading, repetitions and uncertainty | A universal model leaderboard |
| A public record of every run, failures included | A showcase of the best runs |
| Agnostic about workflows, models and target projects, with relay as the first workflow ([D-006](../decisions/decision-log.md#d-006)) | A tool built only for relay |
| Local software run by its author, plus a static public dashboard ([D-003](../decisions/decision-log.md#d-003)) | A hosted service or a commercial product ([D-039](../decisions/decision-log.md#d-039)) |
| A public repository that anyone can read and understand ([D-002](../decisions/decision-log.md#d-002)) | A framework packaged and supported for other teams to adopt ([D-039](../decisions/decision-log.md#d-039)) |
| A bounded study that then continues as a maintained benchmark | A platform under open-ended feature development |
| An evaluator of AI-driven delivery | An observability platform, a CI system or a replacement for code review |

## 4. Who it is for

### Primary audience

**Engineering leaders and tech leads who decide which AI models and workflows their teams adopt** ([D-041](../decisions/decision-log.md#d-041)). They are technically fluent and short on time. They want to know what quality, cost and time to expect, to see trade-offs side by side, and to check that the evidence holds up.

The dashboard is designed for them first: answers to concrete questions, cost next to quality, uncertainty always visible, and a short path from any number to the runs behind it.

### Secondary audiences

| Audience | What they look for |
|---|---|
| **Workflow and prompt authors**, starting with relay's author | Whether a change made a workflow better, and where it fails |
| **AI engineers and agent-evaluation practitioners** | The method, the raw evidence on public targets, reproducibility |

### Internal user

**The operator**, currently the author, prepares targets and tasks, declares experiments, runs them locally and publishes the results. The operator's needs (speed, budget control, trust in the numbers) shape the local tooling, never at the expense of the public record.

### Not the audience

- Readers looking for a single "best model" ranking across all kinds of work.
- Teams that want AI Track Record as a supported tool for their own codebases. The repository is public and readable, but adoption by other teams is not an objective ([D-039](../decisions/decision-log.md#d-039)).

## 5. What it does and what it does not do

### What it does

1. **Runs tasks unattended.** It takes a task (a frozen specification on a frozen base commit) and runs a configured workflow and model on it in an isolated workspace, with no human input and with fixed budget and time limits.
2. **Grades independently.** It checks each run with hidden acceptance tests, the target's existing tests, static analysis and a reviewer that is not part of the workflow under test.
3. **Measures cost and effort.** It records tokens, cost, duration and rework for every run.
4. **Compares configurations.** It changes one factor at a time (model, model per role, workflow version or workflow) and reports differences with their uncertainty.
5. **Keeps the full record.** It stores every run, its artifacts and its grades locally.
6. **Publishes safely.** It exports only allowed fields to a static public dashboard, after a leak check.
7. **Changes through configuration.** New models, workflow versions, tasks and experiments are added through configuration files, not code ([D-005](../decisions/decision-log.md#d-005)).

### What it does not do

| It does not… | Because |
|---|---|
| Write or refine specifications | Specifications are inputs, frozen before any run ([D-014](../decisions/decision-log.md#d-014)) |
| Help the agent during a run, or fix its work afterwards | Any human help would contaminate the measurement |
| Open pull requests or merge into targets | A run's product is a diff; merging the best output into a target is a separate, manual decision |
| Evaluate chat assistants, IDE autocomplete or interactive pair programming | It measures unattended delivery from a specification |
| Measure developer productivity | No human works during a run |
| Rank models in general | Results hold for the tasks and configurations measured |
| Certify that generated code is secure | Security scanners are graders, not guarantees |
| Send private code anywhere except to allowed model providers | Private targets stay on the operator's machine ([D-026](../decisions/decision-log.md#d-026)) |

## 6. Objectives

Objectives are grouped by horizon, and each has a measure that shows whether it was met.

### 6.1 Initial objectives: the MVP

These follow the MVP scope, which is accepted and frozen ([D-024](../decisions/decision-log.md#d-024)).

| ID | Objective | Measure of success | Status |
|---|---|---|---|
| OI-1 | Prove the method end to end: an unattended run on a small public or synthetic task, graded by a hidden oracle, with captured cost | The Phase 0 exit criterion is met (milestone M0) | Accepted |
| OI-2 | Publish the first trustworthy results on Target A: relay versus vanilla, three model tiers and two relay releases | MVP success criteria SC-1 to SC-6 are met and the dashboard is public | Accepted |
| OI-3 | Answer three questions with evidence: is relay worth its cost, how much does the model tier matter, and did recent relay changes help | Each question has a published answer with its uncertainty | Accepted |
| OI-4 | Publish the first write-up, in the form "measured X, found Y, changed Z" | The write-up is published and linked from the dashboard | Accepted |
| OI-5 | Ship the MVP by its target date | The dashboard is public in the first week of December 2026 ([D-042](../decisions/decision-log.md#d-042)). If a milestone slips, the date is re-forecast and the scope is kept ([D-043](../decisions/decision-log.md#d-043)). | Accepted |

### 6.2 Final objectives: the end state

The objectives are accepted ([D-039](../decisions/decision-log.md#d-039)); their measures are proposals.

| ID | Objective | Measure of success |
|---|---|---|
| OF-1 | **Complete the study.** Run the planned experiment rounds (the MVP, Phase 2 and any Phase 3 extensions chosen), publish their findings, then stop adding features. | Every planned round is published with a write-up, and feature development is closed |
| OF-2 | **Keep the record current.** In maintenance, re-run the reference experiments when a relevant new model or a new relay release appears, and publish the results. | Each relevant release is benchmarked and published within an agreed time, for example one month |

Maintenance means low, predictable effort: new runs with existing tasks and graders, not new capabilities.

### 6.3 Secondary objectives

The objectives are accepted ([D-040](../decisions/decision-log.md#d-040)); how they are pursued is a proposal. They are pursued only where they do not weaken the primary purpose.

| ID | Objective | How it is pursued | Guardrail |
|---|---|---|---|
| OS-1 | **Improve relay with data** | Results and failed runs guide changes to relay's prompts, and each change is measured in the next round | Held-out tasks keep relay from being tuned on the tasks that judge it ([D-023](../decisions/decision-log.md#d-023)) |
| OS-2 | **Advance Target A** | The best graded output of a task may be merged into Target A, so benchmark spend also builds the product | Tasks are chosen for benchmark value first; merging happens after grading and never changes recorded results |
| OS-3 | **Practice the AI engineering stack** | Gateways, tracing and observability, LLM judges and, later, retrieval (RAG) are used where the product needs them | Tool choices must still meet the local-first and privacy constraints ([D-003](../decisions/decision-log.md#d-003)) |
| OS-4 | **Share findings** | Articles, posts and talks built from published experiments | Content cites published runs only and claims nothing beyond the evidence |

### 6.4 When objectives conflict

1. The primary purpose wins: a trustworthy, readable public record.
2. Initial objectives come before final ones: nothing is broadened until the MVP is public.
3. Secondary objectives never justify weakening a measurement, exposing private material or delaying the MVP.
4. When the MVP runs late, the date moves and the accepted scope stays ([D-043](../decisions/decision-log.md#d-043)).

## 7. Constraints and assumptions

### Constraints

| ID | Constraint | Source |
|---|---|---|
| CN-1 | One operator, working part-time (10–15 hours per week planned until the MVP), builds and runs everything | Project reality |
| CN-2 | Model API spend for the MVP is capped at US$ 800, re-evaluated at M0 | [D-028](../decisions/decision-log.md#d-028) |
| CN-3 | Everything except the dashboard runs on the operator's machine | [D-003](../decisions/decision-log.md#d-003) |
| CN-4 | Material from private targets never appears in the public layers | [D-002](../decisions/decision-log.md#d-002) |
| CN-5 | Only providers allowed for a target may receive its content | [D-026](../decisions/decision-log.md#d-026) |
| CN-6 | Early phases depend on a single harness, Claude Code | [D-017](../decisions/decision-log.md#d-017) |
| CN-7 | Everything in the project is written in English | [D-010](../decisions/decision-log.md#d-010) |

### Assumptions

These are believed to be true but are not yet verified. Phase 0 tests the first four.

| ID | Assumption | If it is wrong |
|---|---|---|
| AS-1 | Relay can run its autonomous pipeline with no human input, with small changes at most | Relay needs a non-interactive mode before Phase 1 |
| AS-2 | Every sub-agent can be forced to use the model under test | Model comparisons need generated variants of the workflow |
| AS-3 | Tokens, cost and time can be captured for the orchestrator and for every sub-agent | Cost data has to come from a gateway or from billing |
| AS-4 | A medium-sized run costs roughly US$ 2–25, depending on the model | The MVP ceiling is revisited at M0 ([D-028](../decisions/decision-log.md#d-028)); the frozen scope changes only through a new decision |
| AS-5 | Target A's tasks can be specified with an interface contract precise enough for hidden tests | Tasks are redesigned or replaced |
| AS-6 | Three repetitions are enough to separate configurations that differ meaningfully | More repetitions, or fewer configurations |
| AS-7 | Model providers can receive Target A's content by milestone M0 ([D-029](../decisions/decision-log.md#d-029)); confirmed on 2026-10-22 for Anthropic models | The MVP waits, or runs on a public target instead |
| AS-8 | The Agent SDK reproduces the CLI's behavior for relay ([D-049](../decisions/decision-log.md#d-049)) | Runs go back to the CLI, paid with purchased credits |

## 8. Questions AI Track Record answers

| Question | Example | First answered in |
|---|---|---|
| Is a workflow worth it? | Does relay deliver more correct features than Claude Code without plugins, and at what extra cost? | MVP |
| Did a new workflow version help? | Did relay's latest release improve, regress or change nothing compared with an earlier release, on the same tasks? | MVP |
| How much does the model tier matter? | Under the same workflow, how much quality is gained, and how much money is spent, moving from a small model to a large one? | MVP |
| How often do agents claim false success? | In what share of runs does the workflow report "done" while the hidden tests fail? | MVP |
| What does a working feature cost? | What is the cost per successful task of each configuration? | MVP |
| Which model should play which role? | Is "a large model plans and reviews, a mid-size model implements, a small model runs the tests" better value than one mid-size model everywhere? | Phase 2 |
| How portable is a workflow? | How does the same workflow perform when driven by models from other providers or by open-weight models? | Phase 2 |

## 9. How it differs from existing benchmarks

Landscape as of October 2026.

| Project | What it evaluates | Difference |
|---|---|---|
| [SWE-bench](https://www.swebench.com/) (Verified, [Pro](https://labs.scale.com/leaderboard/swe_bench_pro), Live) and [SWE-rebench](https://swe-rebench.com/) | Model-and-agent pairs turning real issues into patches in open-source repositories; Pro adds a subset of proprietary code | Issue to patch on standardized tasks. AI Track Record measures specification to pull request and treats the workflow as the variable. |
| [Terminal-Bench](https://www.tbench.ai/leaderboard), run with the [Harbor](https://github.com/harbor-framework/harbor) harness | Agents completing tasks in a terminal; reports cost and tokens | Different task style. Harbor is a candidate runner ([D-030](../decisions/decision-log.md#d-030)). |
| [OpenHands Index](https://index.openhands.dev/home) | Agent skill, cost and time | Ranks agents; does not vary prompt workflows or their versions. |
| [Vals.ai Vibe Code Bench](https://www.vals.ai/benchmarks/vibe-code) | Building applications from a specification, with cost and duration | Closest task shape; focuses on models, not workflows. |
| PRDBench, SpecBench | Research benchmarks for PRD-to-code and specification-to-code | Similar input; fixed research datasets rather than a continuous record. |
| [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals), [promptfoo](https://www.promptfoo.dev/) | Short test cases for prompts, agents and plugins | Unit tests for prompts. AI Track Record is the end-to-end test of a full feature delivery. |

AI Track Record covers what these leave open:

1. **Workflows and their versions are first-class variables**, tracked over time, not only models.
2. **Model allocation per role** can be tested.
3. **Tasks come from real products**, including private ones, and are graded by hidden tests derived from the specification and by a mergeability review. Passing tests is not enough: many benchmark-passing patches [would not be merged](https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/).
4. **The cost and time of every run are published**, failures included.

## 10. Principles

1. **Measure, don't assert.** Every claim on the dashboard is backed by recorded runs.
2. **Keep the full record.** Every run is kept and shown, including failures, halts and errors. A track record is not a highlight reel.
3. **Grade independently.** The workflow under test never grades its own work, and the agent never sees the hidden tests.
4. **Reproducible by construction.** Every input that can change a result (harness version, workflow version, model identifiers, base commit, settings) is pinned and recorded with the run.
5. **Configuration over code.** New models, workflow versions, tasks and experiments are added through configuration files.
6. **Agnostic core.** Targets, workflows, models and harnesses plug in through adapters. Relay is the first workflow, not a special case.
7. **Local-first, private by default.** Nothing is published unless it is allowed for its visibility class.
8. **Fair comparisons.** All configurations in an experiment get the same tasks, specifications, limits and environment.
9. **Honest labels.** Unofficial setups, estimated costs and small samples are labeled as such.
10. **Disclosed conflict of interest.** The operator also writes the main workflow under test. Hidden tests, independent grading, the full record and a public methodology are the safeguards.
