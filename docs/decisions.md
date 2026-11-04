# Decisions

Stable project decisions that the AI must not re-evaluate.
Updated by the Docs Updater after each approved implementation.

The source of truth is the decision log, `documentation/decisions/decision-log.md` (D-011). This file summarizes only the decisions that constrain code, with their IDs; it does not copy the log's entries. When the two differ, the log wins, and a decision changes only through the log.

---

## [2026-10-20] Claude Code through the Agent SDK is the only harness

**Context:** Relay is a Claude Code plugin, and a fixed harness isolates the effect of models and workflows.
**Decision:** Every run and every review uses Claude Code through the Claude Agent SDK at a pinned version (D-017, D-049, accepted 2026-10-21). Other models are reached by changing the route, not the harness (D-031, proposed).
**Reason:** The included API credits cover the SDK, not the CLI, and the SDK bundles the same engine.
**Areas affected:** runs, review, local-inference

---

## [2026-10-20] Harbor is the runner

**Context:** Runs need containers, limits, a network allowlist and a separate verifier.
**Decision:** Harbor 0.24.0 runs every task; the harness extends it with its own installed agent (D-030).
**Reason:** It provides isolation, limits and grading hooks without a custom runner.
**Areas affected:** runs, grading

---

## [2026-10-20] Run folders are the system of record; DuckDB is derived

**Context:** Results must be reproducible and auditable.
**Decision:** Every run leaves an immutable trial folder; the DuckDB store is rebuilt from those folders and the telemetry files on every load (D-033). Telemetry is native OpenTelemetry into local files (D-032).
**Reason:** A store that can be rebuilt from files cannot drift from the evidence.
**Areas affected:** store-and-publication, runs

---

## [2026-10-20] Pin everything and follow the rigor rules

**Context:** Agent results are noisy and the ecosystem changes fast.
**Decision:** Pin harness, workflow, model identifiers, routes, base commits, graders and price tables; at least three repetitions; one factor at a time; hypotheses declared before running; the same limits for all (D-020). Relay runs from copies of exact commits (D-054).
**Reason:** Comparisons are only fair when everything but the factor under study is fixed.
**Areas affected:** runs, grading, review, local-inference

---

## [2026-10-20] Graders sit outside the workflow under test

**Context:** A workflow must not grade itself.
**Decision:** The hidden oracle is the primary correctness check (D-015); the target's existing tests and static analysis also run; the independent review is a pinned `/code-review` outside any workflow (D-018); skipped protocol steps are flagged, never scored (D-051); tasks stay frozen (D-014, D-053).
**Reason:** Independent graders make results credible.
**Areas affected:** grading, review

---

## [2026-10-20] Normalized outcomes

**Context:** Workflows and the harness end runs in different ways.
**Decision:** Every run ends as completed, halted, budget_exceeded, timed_out or error, with the native reason kept (D-019).
**Reason:** Outcomes must compare across workflows; infrastructure errors are kept apart and retried.
**Areas affected:** runs, store-and-publication

---

## [2026-10-20] Cost from tokens and dated prices

**Context:** Billing is aggregated and delayed.
**Decision:** Cost is computed from tokens and a dated price table, with the harness estimate kept next to it; every published cost states its source (D-022).
**Reason:** Computed cost is comparable across time and providers and can be recomputed.
**Areas affected:** store-and-publication, budget

---

## [2026-10-20] Spend ceiling for the MVP

**Context:** The MVP has a fixed budget.
**Decision:** MVP spend is capped at US$ 800 and checked before every run (D-028). Experiments outside the MVP never draw on it (D-058).
**Reason:** Experiments must not stop half-way.
**Areas affected:** budget

---

## [2026-10-22] Allowed providers for Target A

**Context:** Running an agent sends the target's content to the model provider.
**Decision:** Each target lists its allowed providers (D-026). Target A's content may go only to Anthropic's API (D-029) and to open-weight models on the operator's machine (D-057, accepted 2026-11-03).
**Reason:** Providers that may train on the content are not allowed on private targets; local models send nothing out.
**Areas affected:** runs, local-inference

---

## [2026-10-23] Network allowlist and no web tools on Target A

**Context:** Open network access let runs reveal what the product builds.
**Decision:** Target A runs allow only the model API, the Collector and the package index; `WebSearch` and `WebFetch` are disabled (D-050).
**Reason:** Search queries and fetched URLs could leak private information.
**Areas affected:** runs

---

## [2026-10-20] Deny-by-default publication; private targets by codename

**Context:** The project publishes results about a private product.
**Decision:** Exports copy only allowlisted fields per visibility class, after a leak check; private targets appear publicly under a codename only (D-002, D-013).
**Reason:** Private material must never leave the machine.
**Areas affected:** store-and-publication

---

## [2026-10-20] Python 3.12 with uv; English everywhere; planning in documentation/

**Context:** One operator, one language, one place for planning.
**Decision:** The harness is Python 3.12 managed with uv (D-047); everything is written in English (D-010); planning documentation lives in `documentation/` (D-011).
**Reason:** Consistency for readers and agents.
**Areas affected:** all

---

## [2026-11-03] Local models experiment outside the frozen MVP

**Context:** The owner asked to include tests with local models.
**Decision:** The local models plan runs vanilla on open-weight models served by llama.cpp on the operator's machine, plus one relay probe, outside the frozen MVP; the MVP keeps priority over the operator's time and the machine (D-058).
**Reason:** It costs almost no money, keeps Target A's content on the machine and shows whether the oracle separates configurations.
**Areas affected:** local-inference, runs, store-and-publication, budget

---

<!-- Template for future entries:

## [YYYY-MM-DD] Title of the decision

**Context:** Why this decision was needed.
**Decision:** What was decided.
**Reason:** Why this option was chosen over alternatives.
**Areas affected:** [list domain areas]

-->
