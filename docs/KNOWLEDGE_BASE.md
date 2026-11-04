# Knowledge Base

# Intro

## README
What AI Track Record measures and compares, and where the documentation starts. → README.md

## Product documentation
Source of truth for the product, plans, research and decisions (D-011). → documentation/README.md

# Architecture & Development

## Developer architecture
Which file to change for each kind of task, and where results go. → docs/architecture.md

## Development
Setup in WSL, the command for every module, and how to add a feature. → docs/development.md

## Interfaces reference
The Harbor agent's kwargs, every command-line module, the trial folder and models.toml. → docs/api-reference.md

## Troubleshooting
Known failures of runs, telemetry, WSL and local inference, with fixes. → docs/troubleshooting.md

# Governance

## Decision Gate
Mandatory check before planning, coding or reviewing, with its sources and evidence block. → docs/decision-gate.md

## Decisions
Summary of the decisions that constrain code, pointing to the decision log. → docs/decisions.md

## Anti-patterns
What must not be done: private material in the repo, disallowed providers, self-grading, unpinned versions. → docs/anti-patterns.md

# Context

## Architecture
Stack with pinned versions, the pattern, the data flow of a run and the folder map. → docs/context/architecture.md

## Conventions
Module entry points, naming, code style, error handling, pinning and commits. → docs/context/conventions.md

## Integrations
Anthropic API, Harbor, Docker, the Collector, PyPI, GitHub, GHCR, Hugging Face and the local server. → docs/context/integrations.md

## Constraints
Pinned versions, the machine's limits, experiment rules, privacy and network. → docs/context/constraints.md

## Methodology
TDD not declared; no test framework; docs sync on. → docs/context/methodology.md

## Testing
Mandatory test guardrail for every change; no suite detected yet. → docs/context/testing.md

# Domain

## Glossary
Terms as they appear in the code, and where the code's names differ. → docs/domain/glossary.md

## Flows
Prepare a task, run a batch, grade, review, publish, prepare local inference. → docs/domain/flows.md

## Runs
Harness, limits, model forcing, outcomes and retries. → docs/domain/areas/runs.md

## Grading
Task building, the hidden oracle, rewards, static findings and the skipped-step check. → docs/domain/areas/grading.md

## Review
The pinned independent review and blind confirmation. → docs/domain/areas/review.md

## Store and publication
Rebuildable store, reconciliation, allowlist export and leak check. → docs/domain/areas/store-and-publication.md

## Budget
The MVP's ceiling and the check before each run. → docs/domain/areas/budget.md

## Local inference
Pinned weights, one model per server start, key check, loopback only. → docs/domain/areas/local-inference.md

# Libraries

## Library notes
Harbor, Claude Agent SDK, DuckDB and llama.cpp: versions, use, patterns, gotchas. → docs/libs/
