# AI Track Record — documentation

> Benchmarking AI coding agents from spec to pull request: cost, time and quality across models and prompt versions.

AI Track Record is a local-first benchmarking system for AI coding agents. It runs the same specification-to-pull-request task under different models and prompt workflows, grades every run with checks the agent never sees, and publishes cost, time and quality on a public dashboard without exposing private code.

**Current stage:** planning. No code has been written yet.

This folder is the source of truth for what the product is, why it exists and what has been decided. Technical documentation will be added here as the design progresses.

## Reading order

| # | Document | What it answers |
|---|---|---|
| 1 | [Vision and scope](product/01-vision-and-scope.md) | What AI Track Record is and is not, who it is for, what it does and does not do, its objectives, constraints and principles |
| 2 | [Concepts and run lifecycle](product/02-concepts.md) | The project vocabulary (target, task, workflow, configuration, run) and how one run flows end to end |
| 3 | [Capabilities](product/03-capabilities.md) | What the product must do, grouped by area and tagged by phase |
| 4 | [Measurement model](product/04-measurement.md) | What is measured, how each metric is defined and which rules keep comparisons fair |
| 5 | [Visibility and privacy](product/05-visibility-and-privacy.md) | The three visibility layers and what may be published |
| 6 | [Scope, roadmap and risks](product/06-scope-and-roadmap.md) | Phases, MVP scope, success criteria, estimates, risks and mitigations |
| — | [Decision log](decisions/decision-log.md) | Every decision and its status: Accepted, Proposed or Open |

## Research

Evidence gathered to support specific decisions.

| Document | What it supports |
|---|---|
| [Phase 0 tooling](research/phase-0-tooling.md) | The runner, the observability stack and the local store ([D-030](decisions/decision-log.md#d-030), [D-032](decisions/decision-log.md#d-032), [D-033](decisions/decision-log.md#d-033)) |

## Conventions

### Document status

Every document starts with a status line:

- **Draft** — being written; structure and content may change.
- **In review** — complete and waiting for the owner's review.
- **Stable** — reviewed; changes go through the decision log.

### Decision status

- **Accepted** — decided by the project owner.
- **Proposed** — recommended and already reflected in these documents, but not yet accepted by the owner.
- **Open** — needs a decision; the options are listed.

Anything that depends on a decision that is not Accepted is a proposal. Documents link to the decision they depend on, for example [D-015](decisions/decision-log.md#d-015).

### Language

Everything in this project is written in English: documentation, code, comments, commit messages and the dashboard ([D-010](decisions/decision-log.md#d-010)).

### Public-safety rule

This folder is published with the repository. It must never contain:

- material from private targets: real product names, specifications, source code, data, prompts or run transcripts;
- personal data beyond the author's public identity;
- secrets of any kind: API keys, tokens, credentials.

Private targets are referred to by codename only. See [Visibility and privacy](product/05-visibility-and-privacy.md).
