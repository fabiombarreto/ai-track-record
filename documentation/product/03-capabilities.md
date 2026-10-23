# Capabilities

> **Status:** Draft · **Last updated:** 2026-10-23 · **Owner:** Fabio Martins Barreto

This document lists what AI Track Record must be able to do, grouped by area. It describes behavior, not implementation; technology choices are tracked in the [decision log](../decisions/decision-log.md).

**Phase tags** follow the proposed roadmap in [Scope, roadmap and risks](06-scope-and-roadmap.md): **MVP**, **P2** (credibility and breadth) and **P3** (optional extensions, chosen after Phase 2). The capabilities tagged MVP are part of the accepted, frozen MVP scope ([D-024](../decisions/decision-log.md#d-024)); changing them needs a new decision. The P2 and P3 tags are still proposals, except where an accepted decision sets the phase, as [D-021](../decisions/decision-log.md#d-021) and [D-023](../decisions/decision-log.md#d-023) do. At M0, [D-050](../decisions/decision-log.md#d-050) moved RUN-08 into the MVP and [D-051](../decisions/decision-log.md#d-051) added GRD-09.

## 1. Targets and tasks

| ID | Capability | Phase |
|---|---|---|
| TGT-01 | Register a target: repository, visibility class (public or private), codename, environment, setup commands and allowed model providers. | MVP |
| TGT-02 | Define a task: specification, base commit, interface contract, hidden oracle, grading profile and metadata. | MVP |
| TGT-03 | Keep hidden oracles out of the agent's environment for the whole run. | MVP |
| TGT-04 | Validate a task before use: its oracle fails on the base commit and passes on a reference solution, when one exists. | MVP |
| TGT-05 | Map each oracle test to the acceptance criteria it checks. | MVP |
| TGT-06 | Split tasks into a development set and a held-out set, so that workflows are not tuned on the tasks used to judge them. | P2 |
| TGT-07 | Add targets and tasks through a documented task format, with no code changes. | P2 |

## 2. Workflows, models and configurations

| ID | Capability | Phase |
|---|---|---|
| CFG-01 | Run workflows through adapters that follow a documented contract (see [Concepts](02-concepts.md#workflow-adapter)). | MVP |
| CFG-02 | Ship two adapters: **relay** and the **vanilla** baseline. | MVP |
| CFG-03 | Pin workflow versions by immutable reference (git tag or commit SHA) and record them with every run. | MVP |
| CFG-04 | Apply a single-model assignment to every role of a workflow, including sub-agents whose prompts name a fixed model. | MVP |
| CFG-05 | Apply mixed model assignments, with a different model per role. | P2 |
| CFG-06 | Reach Anthropic models through the provider's API, with a pinned harness version. | MVP |
| CFG-07 | Reach models from other providers and open-weight models through compatible endpoints, a gateway or a local inference server. | P2 |
| CFG-08 | Add adapters for other workflows, for example other Claude Code plugins or in-house prompt sets. | P3 |
| CFG-09 | Add adapters for other harnesses, for example other coding-agent CLIs. | P3 |
| CFG-10 | Treat tools and context, such as MCP servers or retrieval over project documentation, as configuration dimensions. | P3 |
| CFG-11 | Derive a stable configuration identifier from the content of the configuration. | MVP |

## 3. Experiments

| ID | Capability | Phase |
|---|---|---|
| EXP-01 | Declare an experiment in a configuration file: question, hypothesis, reference configuration, compared configurations, tasks, repetitions and limits. | MVP |
| EXP-02 | Validate an experiment file before running it, for example unknown models, missing tasks or a provider not allowed for a target. | MVP |
| EXP-03 | Enforce a budget cap per run and per experiment. | MVP |
| EXP-04 | Resume an interrupted experiment without repeating finished runs. | MVP |
| EXP-05 | Record the hypothesis before the first run, so that results are read against what was expected. | MVP |
| EXP-06 | Estimate the cost and duration of an experiment before running it, from the price table and past runs. | P2 |
| EXP-07 | Add repetitions to selected configurations after a first pass, for example to finalists only. | P2 |
| EXP-08 | Re-run a published experiment from its recorded inputs to check reproducibility. | P2 |
| EXP-09 | Extend a reference experiment with one new configuration (a new model or workflow release) and run only the new runs. This is what a maintenance round needs ([D-039](../decisions/decision-log.md#d-039)). | P2 |

## 4. Execution

| ID | Capability | Phase |
|---|---|---|
| RUN-01 | Create a fresh, isolated container for each run, holding a single-commit copy of the task's base commit with no other git history or remotes ([D-030](../decisions/decision-log.md#d-030)). | MVP |
| RUN-02 | Run the workflow unattended; no run may wait for human input. | MVP |
| RUN-03 | Enforce budget, wall-clock and turn limits from outside the agent. | MVP |
| RUN-04 | Record an environment fingerprint: harness version, workflow version, model identifiers, provider routes, operating system and tool versions. | MVP |
| RUN-05 | Save the final diff, logs, transcripts and workflow artifacts. | MVP |
| RUN-06 | Classify the outcome (`completed`, `halted`, `budget_exceeded`, `timed_out`, `error`) and keep the workflow's native reason. | MVP |
| RUN-07 | Retry runs that ended in `error` without counting them as workflow failures, and report how many were retried. | MVP |
| RUN-08 | Restrict network access during a run to what the task allows, such as model endpoints and package registries. On Target A: the model API, the Collector and the package index, with web tools disabled ([D-050](../decisions/decision-log.md#d-050)). | MVP |
| RUN-09 | Execute several runs in parallel within the operator's limits. | P2 |

## 5. Telemetry

| ID | Capability | Phase |
|---|---|---|
| TEL-01 | Capture the tokens of every run by type (input, output, cache write, cache read) and by model. | MVP |
| TEL-02 | Capture the wall-clock duration and the model API time of every run. | MVP |
| TEL-03 | Compute cost from tokens and a dated price table, and keep the harness's own estimate next to it. | MVP |
| TEL-04 | Reconcile computed cost with provider billing or gateway records, and report the difference. | MVP |
| TEL-05 | Attribute tokens, cost and time to roles and stages when the workflow adapter provides a stage map. | P2 |
| TEL-06 | Count rework: retries and review loops inside the workflow before it finished. | MVP |

## 6. Grading

| ID | Capability | Phase |
|---|---|---|
| GRD-01 | Run the hidden oracle in a fresh environment, separate from the agent's, and record pass or fail per acceptance criterion. | MVP |
| GRD-02 | Run the target's existing test suite to detect regressions. | MVP |
| GRD-03 | Run the static analysis configured for the target and count the findings introduced by the run. | MVP |
| GRD-04 | Run an independent code review with a pinned reviewer that is not part of the workflow under test. | MVP |
| GRD-05 | Let the operator confirm or reject review findings on a sample of runs. | MVP |
| GRD-06 | Score each run with an LLM judge on a published rubric that includes a mergeability verdict. | P2 |
| GRD-07 | Calibrate the LLM judge against human grades and publish the agreement. | P2 |
| GRD-08 | Hide the configuration from human graders (blind review). | P2 |
| GRD-09 | Record which of the workflow's own protocol steps a run skipped and whether it said so, and flag silent skips for review, outside every grade ([D-051](../decisions/decision-log.md#d-051)). | MVP |

## 7. Storage and analysis

| ID | Capability | Phase |
|---|---|---|
| ANL-01 | Store runs, grades and telemetry in a local structured database, with raw artifacts on disk. | MVP |
| ANL-02 | Build a scorecard for each configuration, with uncertainty intervals. | MVP |
| ANL-03 | Compare a configuration with a reference and report the difference with its uncertainty. | MVP |
| ANL-04 | Compute pass@k and pass^k from repetitions. | MVP |
| ANL-05 | Identify the cost-versus-quality Pareto frontier. | MVP |
| ANL-06 | Track a workflow across versions over time. | P2 |
| ANL-07 | Export the raw results of public targets in an open format for independent analysis. | P2 |

## 8. Publication and dashboard

| ID | Capability | Phase |
|---|---|---|
| PUB-01 | Publish only through an explicit command that records what was exported and from which runs. | MVP |
| PUB-02 | Export through an allowlist of fields per visibility class; anything not listed is withheld. | MVP |
| PUB-03 | Run an automated leak check before every publication and block the publication on any finding. | MVP |
| PUB-04 | Generate a static dashboard with no server-side code and no exposed database. | MVP |
| PUB-05 | Show headline answers: each research question with its chart, a one-sentence answer and its uncertainty. | MVP |
| PUB-06 | Show a cost-versus-quality chart for the configurations of each experiment. | MVP |
| PUB-07 | Provide a run explorer with every attempt, including failures, halts and errors. | MVP |
| PUB-08 | Publish the methodology and a glossary in plain language. | MVP |
| PUB-09 | Link every aggregate number to the runs behind it. | MVP |
| PUB-10 | Show a task catalog: full detail for public targets; category and difficulty only for private ones. | MVP |
| PUB-11 | Show the history of a public workflow, with the prompt diff between versions next to the measured effect. | P2 |

### Dashboard design principles

- **Designed for the primary audience.** Engineering leaders and tech leads who decide which models and workflows to adopt ([D-041](../decisions/decision-log.md#d-041)): technically fluent and short on time.
- **Questions first.** Lead with the [questions the product answers](01-vision-and-scope.md#8-questions-ai-track-record-answers), not with tables.
- **Cost and quality together.** No quality number appears without its cost, and no cost without its quality.
- **Uncertainty always visible.** Intervals and sample sizes appear next to every comparison.
- **Two clicks to evidence.** From any chart, a reader reaches the individual runs in at most two steps.
- **Failures are first-class.** Halts, errors and false completions are shown, not filtered out.
- **No unexplained jargon.** Every metric links to its definition in the [measurement model](04-measurement.md).

## 9. Privacy and governance

| ID | Capability | Phase |
|---|---|---|
| PRV-01 | Refuse to run a configuration whose provider is not allowed for the target. | MVP |
| PRV-02 | Keep every artifact of a private target on the operator's machine. | MVP |
| PRV-03 | Refer to private targets by codename in everything that can be published. | MVP |
| PRV-04 | Keep an audit log of publications. | MVP |
