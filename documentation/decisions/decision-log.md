# Decision log

> **Status:** Draft · **Last updated:** 2026-10-21 · **Owner:** Fabio Martins Barreto

Every product decision and its status:

- **Accepted**: decided by the project owner.
- **Proposed**: recommended and already reflected in the documentation, waiting for the owner's acceptance.
- **Open**: needs a decision; the options are listed.

Entries are listed in ID order and keep their ID when their status changes. To change a decision, update its entry, add a dated note explaining the change, and update the documents that link to it.

## Summary

| ID | Decision | Status |
|---|---|---|
| [D-001](#d-001) | Name "AI Track Record", with a fixed subtitle | Accepted |
| [D-002](#d-002) | Three visibility layers | Accepted |
| [D-003](#d-003) | Local-first operation | Accepted |
| [D-004](#d-004) | Target-agnostic; the first target is a private product | Accepted |
| [D-005](#d-005) | Models and workflow versions change through configuration, not code | Accepted |
| [D-006](#d-006) | Workflow-agnostic evaluation, with relay as the primary workflow | Accepted |
| [D-007](#d-007) | Measure time, tokens, bugs, code quality and specification compliance | Accepted |
| [D-008](#d-008) | Compare models across providers, including open-weight models | Accepted |
| [D-009](#d-009) | Dashboard designed for qualified readers | Accepted |
| [D-010](#d-010) | English for everything in the project | Accepted |
| [D-011](#d-011) | Planning documentation lives in `documentation/` | Accepted |
| [D-012](#d-012) | Add a public reference target | Accepted |
| [D-013](#d-013) | Private targets appear publicly under a codename only | Accepted |
| [D-014](#d-014) | Tasks start from frozen specifications and base commits | Accepted |
| [D-015](#d-015) | Hidden oracle as the primary correctness check | Accepted |
| [D-016](#d-016) | Vanilla baseline as a second workflow adapter in the MVP | Accepted |
| [D-017](#d-017) | Claude Code as the only harness in early phases | Accepted |
| [D-018](#d-018) | Independent code review outside the workflow under test | Accepted |
| [D-019](#d-019) | Normalized run outcomes | Accepted |
| [D-020](#d-020) | Measurement rigor rules | Accepted |
| [D-021](#d-021) | LLM judge calibrated against human grades | Accepted |
| [D-022](#d-022) | Cost computed from tokens and dated price tables | Accepted |
| [D-023](#d-023) | Held-out task set | Accepted |
| [D-024](#d-024) | MVP scope, frozen | Accepted |
| [D-025](#d-025) | Static public dashboard | Accepted |
| [D-026](#d-026) | Allowed model providers per target | Accepted |
| [D-027](#d-027) | Benchmark runs use API access, not consumer subscriptions | Accepted |
| [D-028](#d-028) | MVP budget ceiling: US$ 800 | Accepted |
| [D-029](#d-029) | Allowed providers for Target A | Open |
| [D-030](#d-030) | Runner: adopt Harbor | Accepted |
| [D-031](#d-031) | Route to non-Anthropic and open-weight models | Open |
| [D-032](#d-032) | Observability: native OpenTelemetry into a local store, MLflow as optional viewer | Accepted |
| [D-033](#d-033) | Local store: DuckDB over immutable run folders | Accepted |
| [D-034](#d-034) | Dashboard hosting and domain | Open |
| [D-035](#d-035) | Which public reference target | Open |
| [D-036](#d-036) | Repository license: MIT | Accepted |
| [D-037](#d-037) | Where retrieval-augmented generation (RAG) fits | Open |
| [D-038](#d-038) | Primary purpose: public, verifiable evidence | Accepted |
| [D-039](#d-039) | End state: a bounded study that becomes a maintained benchmark | Accepted |
| [D-040](#d-040) | Secondary objectives | Accepted |
| [D-041](#d-041) | Primary audience: people who decide which models and workflows to adopt | Accepted |
| [D-042](#d-042) | MVP target date: first week of December 2026 | Accepted |
| [D-043](#d-043) | When the MVP runs late, the date moves, not the scope | Accepted |
| [D-044](#d-044) | Budget ceiling for Phase 2 | Open |
| [D-045](#d-045) | LangSmith and Langfuse as reference designs only | Accepted |

## Decisions

### D-001

**Name "AI Track Record", with a fixed subtitle**

- **Status:** Accepted, 2026-10-19
- **Decision:** The product is called AI Track Record and always appears with the subtitle "benchmarking AI coding agents from spec to pull request: cost, time and quality across models and prompt versions". The repository is named `ai-track-record`.
- **Why:** "Track record" means both a record of results and a history of proven delivery. The subtitle removes the vagueness of the short name. Names already used by evaluation tools and benchmarks, such as Arena, Harbor, Inspect, PRDBench and SpecBench, were avoided.
- **Notes:** `aitrackrecord.dev` was available on 2026-10-19; `aitrackrecord.com` is registered by a third party. See [D-034](#d-034).

### D-002

**Three visibility layers**

- **Status:** Accepted, 2026-10-19
- **Decision:** (1) A public repository that anyone can read and understand. (2) A public online dashboard with results, metrics and attempts. (3) Artifacts from private targets, such as generated code, prompts used and documentation, stay on the operator's machine, and nobody else has access to them.
- **Consequences:** [Visibility and privacy](../product/05-visibility-and-privacy.md) defines what goes in each layer.

### D-003

**Local-first operation**

- **Status:** Accepted, 2026-10-19
- **Decision:** Except for the public dashboard, everything runs on the operator's machine: execution, storage, grading and analysis.
- **Consequences:** Hosted services that require sending traces or artifacts to a third party cannot be used for private targets. This constrains [D-032](#d-032).

### D-004

**Target-agnostic; the first target is a private product**

- **Status:** Accepted, 2026-10-19
- **Decision:** The first target is a private product owned by the project owner (Target A). AI Track Record must work with any other project.
- **Consequences:** Targets plug in through a documented task format. Nothing in the core may assume Target A's stack.

### D-005

**Configuration over code**

- **Status:** Accepted, 2026-10-19
- **Decision:** Switching models or prompt workflow versions must not require code changes.
- **Consequences:** Declarative experiment files ([EXP-01](../product/03-capabilities.md#3-experiments)) and configuration identifiers derived from content ([CFG-11](../product/03-capabilities.md#2-workflows-models-and-configurations)).

### D-006

**Workflow-agnostic evaluation, with relay as the primary workflow**

- **Status:** Accepted, 2026-10-20
- **Decision:** AI Track Record evaluates prompt workflows in general, not only relay. Relay is the workflow used most. Evaluating other workflows does not have to be part of the MVP, but the MVP must not prevent it.
- **Consequences:** Workflows plug in through [adapters](../product/02-concepts.md#workflow-adapter). Results are attributed to workflow versions. Relay gets no special treatment in the core. See also [D-016](#d-016).

### D-007

**Measured dimensions**

- **Status:** Accepted, 2026-10-19
- **Decision:** Measure at least time spent, tokens used, bugs found, code quality and specification compliance, plus other measures of how good the final result is.
- **Consequences:** The [measurement model](../product/04-measurement.md) maps each dimension to defined metrics.

### D-008

**Models across providers, including open-weight models**

- **Status:** Accepted, 2026-10-19
- **Decision:** Compare different models, including models from different providers. The owner intends to include open-weight models and to use an LLM proxy where needed.
- **Consequences:** Provider routes are part of a configuration. How models are reached is [D-031](#d-031); which providers may receive private code is [D-026](#d-026).

### D-009

**Dashboard designed for qualified readers**

- **Status:** Accepted, 2026-10-19
- **Decision:** The public interface shows results, metrics and attempts, organized so that any qualified reader can interpret them easily.
- **Consequences:** See the [dashboard design principles](../product/03-capabilities.md#dashboard-design-principles). The primary audience is defined in [D-041](#d-041).

### D-010

**English for everything in the project**

- **Status:** Accepted, 2026-10-20
- **Decision:** Everything in the project is in English: documentation, code, comments, commit messages and the dashboard.
- **Why:** The repository and the dashboard are public and aimed at an international audience.

### D-011

**Planning documentation in `documentation/`**

- **Status:** Accepted, 2026-10-20
- **Decision:** Planning and product documentation lives in `documentation/` and is the source of truth. Working notes from the initial analysis are superseded by it.

### D-012

**Public reference target**

- **Status:** Accepted, 2026-10-20. Proposed 2026-10-19.
- **Decision:** Add at least one public target whose tasks, oracles and runs are fully inspectable, and apply the same method to it as to private targets.
- **Why:** Numbers from code nobody can see are hard to verify. A public target lets readers check the method end to end, which makes private results credible. SWE-bench Pro uses a similar public/private split.
- **Depends on:** [D-035](#d-035), which project to use.

### D-013

**Codenames for private targets**

- **Status:** Accepted, 2026-10-20, with the MVP scope ([D-024](#d-024)). Proposed 2026-10-19.
- **Decision:** In anything that can be published, private targets appear only under a codename with a generic description, for example "Target A, a private B2B SaaS built with Django and Next.js".
- **Why:** Protects the target owner while still telling readers what kind of project was measured.

### D-014

**Frozen specifications and base commits**

- **Status:** Accepted, 2026-10-20, with the MVP scope ([D-024](#d-024)). Proposed 2026-10-19.
- **Decision:** Each task starts from an approved specification and a base commit that do not change during an experiment. Writing the specification, including relay's interactive PRD flow, is outside the measured run. When a target has no suitable code for a task yet, a minimal scaffold is created and frozen as the base commit.
- **Why:** Interactive steps cannot be repeated identically; frozen inputs make runs comparable.

### D-015

**Hidden oracle as the primary correctness check**

- **Status:** Accepted, 2026-10-20, with the MVP scope ([D-024](#d-024)). Proposed 2026-10-19.
- **Decision:** Correctness is judged mainly by acceptance tests derived from the specification. The agent never sees them: they are added to the workspace only at grading time. The specification includes the interface contract the tests rely on.
- **Why:** A workflow's own claim of success, and approval by its own reviewers, are not reliable evidence.

### D-016

**Vanilla baseline as a second adapter in the MVP**

- **Status:** Accepted, 2026-10-20, with the MVP scope ([D-024](#d-024)). Proposed 2026-10-19.
- **Decision:** The MVP includes a "vanilla" workflow, the harness with no plugin, given the specification with a fixed minimal instruction. It is built as its own adapter.
- **Why:** It answers whether a workflow is worth its cost, and it exercises the workflow abstraction ([D-006](#d-006)) from the start. Vanilla runs are expected to cost a fraction of workflow runs.

### D-017

**Claude Code as the only harness in early phases**

- **Status:** Accepted, 2026-10-20. Proposed 2026-10-19.
- **Decision:** Use Claude Code, at a pinned version, as the only harness until Phase 3.
- **Why:** Relay is a Claude Code plugin. Commands and sub-agents are not portable across coding-agent tools; current cross-tool standards cover only skills and MCP servers. A fixed harness also isolates the effect of models and workflows.
- **Note:** For the MVP, the harness is already settled by [D-024](#d-024).

### D-018

**Independent code review**

- **Status:** Accepted, 2026-10-20, with the MVP scope ([D-024](#d-024)). Proposed 2026-10-19.
- **Decision:** Every run is reviewed by a pinned code reviewer that is not part of the workflow under test, for example Claude Code's built-in code review at a fixed effort level and model. The reviewer is the same for every configuration of an experiment, and a human confirms findings on a sample of runs.
- **Why:** In relay's recorded evaluation, an independent review found confirmed defects in deliveries that relay's own reviewers had approved.

### D-019

**Normalized run outcomes**

- **Status:** Accepted, 2026-10-20, with the MVP scope ([D-024](#d-024)). Proposed 2026-10-20.
- **Decision:** Every run ends as `completed`, `halted`, `budget_exceeded`, `timed_out` or `error`, and keeps the workflow's native reason, for example a relay HALT code.
- **Why:** Workflows stop for different native reasons. A shared vocabulary makes them comparable and keeps infrastructure failures out of workflow scores.

### D-020

**Measurement rigor rules**

- **Status:** Accepted, 2026-10-20. Proposed 2026-10-19.
- **Decision:** Apply the [rigor rules](../product/04-measurement.md#8-rigor-rules) to every experiment that feeds the dashboard: pinned inputs, at least 3 repetitions, uncertainty intervals, one factor at a time, hypotheses declared before running, the same limits for all, infrastructure failures kept apart, blind human grading and small samples labeled.
- **Why:** Small samples of non-deterministic agents easily produce differences that are not real.
- **Note:** For the MVP, three repetitions per configuration and task are already settled by [D-024](#d-024).

### D-021

**LLM judge calibrated against human grades**

- **Status:** Accepted, 2026-10-20. Proposed 2026-10-19.
- **Decision:** From Phase 2, an LLM judge scores each run on a published rubric that ends in a mergeability verdict. The judge is calibrated against human grades on a sample, and the agreement is published.
- **Why:** "Would I merge this?" is what teams care about, and uncalibrated judges are unreliable.

### D-022

**Cost from tokens and dated price tables**

- **Status:** Accepted, 2026-10-20, with the MVP scope ([D-024](#d-024)). Proposed 2026-10-20.
- **Decision:** Store the tokens of every run per model, compute cost from a dated price table, keep the harness's own estimate next to it, reconcile with provider billing or gateway logs, and label the source of every published cost.
- **Why:** Harness-reported cost is a client-side estimate that may not know models from other providers, and prices change often.

### D-023

**Held-out task set**

- **Status:** Accepted, 2026-10-20. Proposed 2026-10-20.
- **Decision:** From Phase 2, keep a set of tasks that is never used while developing workflows. Results on it are reported separately, and its oracles are never published.
- **Why:** The operator also develops relay. Tuning a workflow on the tasks that judge it inflates its results.

### D-024

**MVP scope, frozen**

- **Status:** Accepted, 2026-10-20
- **Decision:** The MVP is the scope in [Scope, roadmap and risks](../product/06-scope-and-roadmap.md#3-phase-1-mvp): relay (current release and an earlier release) and vanilla on Claude Code; single-model assignments with Claude Haiku, Sonnet and Opus; three backend tasks on Target A; three repetitions, for 45 runs; the MVP graders; and a static dashboard. The capabilities tagged MVP in [Capabilities](../product/03-capabilities.md) are part of it.
- **Consequences:** The scope is frozen: additions go to a later phase, and any change needs a new entry in this log. When the MVP runs late, the date moves instead ([D-043](#d-043)). Accepting this scope also accepted the proposals it contains: [D-013](#d-013), [D-014](#d-014), [D-015](#d-015), [D-016](#d-016), [D-018](#d-018), [D-019](#d-019), [D-022](#d-022), [D-025](#d-025) and [D-026](#d-026). The MVP budget is capped at US$ 800 ([D-028](#d-028)).

### D-025

**Static public dashboard**

- **Status:** Accepted, 2026-10-20, with the MVP scope ([D-024](#d-024)). Proposed 2026-10-19.
- **Decision:** The dashboard is a static site generated from the publication export, with no server-side code and no database online.
- **Why:** It fits local-first operation, costs almost nothing to host and leaves little to attack.

### D-026

**Allowed model providers per target**

- **Status:** Accepted, 2026-10-20, with the MVP scope ([D-024](#d-024)). Proposed 2026-10-19.
- **Decision:** Each target lists the providers allowed to receive its content, and runs that would break the list are refused. Providers that may train on submitted content are not allowed on private targets.
- **Why:** Running an agent sends the target's code and specifications to the model provider.

### D-027

**API access for benchmark runs**

- **Status:** Accepted, 2026-10-20. Proposed 2026-10-19.
- **Decision:** Benchmark runs use API keys or credits meant for programmatic use, never consumer subscriptions or free tiers.
- **Why:** Consumer terms restrict automated use and their limits assume individual use. Free tiers often allow training on submitted content.

### D-028

**MVP budget ceiling: US$ 800**

- **Status:** Accepted, 2026-10-20
- **Decision:** Model API spend for the MVP is capped at US$ 800, including pilot runs and retries. The ceiling is re-evaluated at M0 with the actual cost of the Phase 0 pilot runs.
- **Why:** It covers the central estimate for the frozen scope ([D-024](#d-024)), about US$ 600, with a margin of about a third. It does not cover the heavy-run scenario, up to about US$ 1,340; the pilot runs show which scenario applies. See the [estimates](../product/06-scope-and-roadmap.md#8-effort-and-cost-estimates).
- **Consequences:** The per-experiment cap ([EXP-03](../product/03-capabilities.md#3-experiments)) is set from this ceiling. If the pilot runs show that the 45 runs will not fit, the ceiling is revisited at M0; reducing the frozen scope would need a new decision. The Phase 2 budget is [D-044](#d-044).

### D-029

**Allowed providers for Target A**

- **Status:** Open
- **Question:** Which model providers may receive Target A's code and specifications?
- **Considerations:** Depends on the target owner's data-protection requirements, which were not yet confirmed on 2026-10-20. The candidates are providers whose paid API terms exclude training on submitted content. The MVP uses only Anthropic models, so allowing the Anthropic API is enough to unblock it. Phase 0 uses a public or synthetic task and does not depend on this decision.
- **If still open at M0:** the owner chooses between waiting, which moves the MVP date ([D-043](#d-043)), and running the MVP on a public target, which changes the frozen scope ([D-024](#d-024)) and brings [D-012](#d-012) forward.
- **Needed by:** M0 (2026-11-03), before any Target A content is sent to a model provider, including during task preparation.

### D-030

**Runner: adopt Harbor**

- **Status:** Accepted, 2026-10-20
- **Decision:** AI Track Record runs on [Harbor](https://github.com/harbor-framework/harbor), pinned to a release and installed from its lock file, inside WSL 2 with local Docker only. Harbor's telemetry is switched off, every task uses the separate verifier, and relay is loaded from a pinned plugin directory. A thin in-house layer adds what Harbor lacks: single-commit workspaces, experiment files, outcome mapping and cost computation.
- **Why:** Harbor runs the real Claude Code CLI on the real API path and already handles containers, hidden tests, timeouts, parallel runs, retries and resume. Its tasks are plain folders that other people can run. Inspect AI with inspect_swe routes model calls through a proxy, which changes the system under test, and a custom runner would take an estimated four to seven days.
- **Consequences:**
  - If Harbor fails the [Phase 0 checks](../research/phase-0-tooling.md#7-phase-0-checks) on plugin loading, hidden tests or stability, a minimal custom container runner replaces it, using the same task folders.
  - The [integrity requirements](../research/phase-0-tooling.md#5-integrity-requirements-for-any-runner) apply: single-commit workspaces with no history, grading in a fresh container, one container per run, contained agents, and a dedicated API key with a spend limit. They make capabilities RUN-01, TGT-03 and GRD-01 more precise without adding to the frozen scope ([D-024](#d-024)).
  - Each run image pins Claude Code at the latest release when Phase 0 starts, and no older than 2.1.304.
- **Evidence:** [Phase 0 tooling](../research/phase-0-tooling.md#4-runner-options-d-030). Alternatives considered: Inspect AI with inspect_swe, and a custom runner.

### D-031

**Route to non-Anthropic and open-weight models**

- **Status:** Open
- **Question:** How does the harness reach models from other providers and open-weight models?
- **Options:** the providers' Anthropic-compatible endpoints, used directly; [LiteLLM](https://docs.litellm.ai/); [claude-code-router](https://github.com/musistudio/claude-code-router); local inference servers such as Ollama or LM Studio.
- **Considerations:** A gateway also provides per-agent cost logs. Compromised LiteLLM packages were published in March 2026, so any gateway must be pinned and verified. Local servers do not cache prompts, which changes cost and latency comparisons. Anthropic does not officially support routing Claude Code to non-Claude models.
- **Needed by:** Phase 2.

### D-032

**Observability: native OpenTelemetry into a local store, MLflow as optional viewer**

- **Status:** Accepted, 2026-10-20
- **Decision:** Claude Code's native OpenTelemetry metrics and events go to a local OpenTelemetry Collector that writes files. Together with each run's result event and transcripts, they form the system of record, which is loaded into DuckDB ([D-033](#d-033)). A local MLflow server, with its usage telemetry switched off, is an optional and disposable trace viewer and run tracker.
- **Why:** Native telemetry gives per-request tokens, cost and duration, attributed to sub-agents, without anything leaving the machine ([D-003](#d-003)). Platform integrations rebuild traces from an internal transcript format that changes between versions, and they only see sessions that end normally.
- **Consequences:**
  - LangSmith, the owner's initial preference, is not used: it is hosted, and self-hosting requires an Enterprise plan. Langfuse is not used either. Both serve only as reference designs ([D-045](#d-045)).
  - LangChain fits best inside the Phase 2 LLM judge, traced locally ([D-040](#d-040)).
  - Every run reconciles the OpenTelemetry sums with its result event and flags any mismatch.
- **Evidence:** [Phase 0 tooling](../research/phase-0-tooling.md#6-observability-options-d-032). Alternatives considered: LangSmith, Langfuse, Arize Phoenix and Opik.

### D-033

**Local store: DuckDB over immutable run folders**

- **Status:** Accepted, 2026-10-20
- **Decision:** Every run writes a folder with its raw outputs (result event, transcripts, telemetry files and grades) that is never changed afterwards. A loader reads the folders into DuckDB for analysis, and the database can be rebuilt from them at any time.
- **Why:** Writes are append-only, one run at a time, and reads are analytical. Keeping the raw files makes every load repeatable, and it keeps private raw material apart from the aggregates that may be published.
- **Evidence:** [Phase 0 tooling](../research/phase-0-tooling.md#1-summary). Alternative considered: SQLite.

### D-034

**Dashboard hosting and domain**

- **Status:** Open
- **Question:** Where is the dashboard hosted, and under which domain?
- **Options:** GitHub Pages or Cloudflare Pages; the domain `aitrackrecord.dev`, available on 2026-10-19.
- **Needed by:** the first publication (M4).

### D-035

**Which public reference target**

- **Status:** Open
- **Question:** Which project becomes the public reference target?
- **Options:** an existing open-source project with a good test suite, or a small project built for the benchmark with a stack similar to Target A's.
- **Considerations:** Well-known open-source projects may be part of model training data. A similar stack makes results comparable with Target A. The project's license must allow publishing derived tasks.
- **Needed by:** Phase 2. Depends on [D-012](#d-012).

### D-036

**Repository license: MIT**

- **Status:** Accepted, 2026-10-21
- **Decision:** The AI Track Record repository is licensed under the [MIT License](../../LICENSE), with copyright held by Fabio Martins Barreto.
- **Why:** It lets readers inspect and reuse the work with attribution, which is what verification needs. Adoption by other teams is not an objective ([D-039](#d-039)), so a simple permissive license is enough. MIT is also the license of the project relay was forked from.
- **Consequences:** The license covers the code and the documentation in this repository. Relay's own repository, which the dashboard will link to, still needs a license file; that work happens outside this repository.

### D-037

**Where retrieval-augmented generation (RAG) fits**

- **Status:** Open
- **Question:** How should RAG, which the owner wants to use, appear in the product?
- **Options:** (a) as a configuration dimension: agents with or without retrieval over project documentation or code ([CFG-10](../product/03-capabilities.md#2-workflows-models-and-configurations)); (b) as a separate track that applies the same method to LLM-powered features inside a product; (c) both, one after the other.
- **Considerations:** Option (b) takes the product beyond coding agents. Practicing RAG is a secondary objective ([D-040](#d-040)), but it must not delay the MVP.
- **Needed by:** Phase 3 planning.

### D-038

**Primary purpose: public, verifiable evidence**

- **Status:** Accepted, 2026-10-20
- **Decision:** AI Track Record exists first to produce public, verifiable evidence of how AI-driven delivery performs on real products. When priorities conflict, whatever makes the public record more trustworthy and easier to read wins over breadth, convenience or internal tooling.
- **Consequences:** The MVP comes before any broadening. Dashboard clarity and write-ups are first-class deliverables. See the [conflict rules](../product/01-vision-and-scope.md#64-when-objectives-conflict).

### D-039

**End state: a bounded study that becomes a maintained benchmark**

- **Status:** Accepted, 2026-10-20
- **Decision:** The project is a study with an end: the MVP, a planned set of experiment rounds and their write-ups. After that, feature development stops and the project continues in maintenance as a continuous benchmark, re-run when relevant new models or workflow versions appear. Adoption by other teams and a commercial product are not objectives.
- **Consequences:** Phase 3 becomes a set of optional extensions chosen after Phase 2. Guides and support for external operators are out of scope. The repository stays public and readable ([D-002](#d-002)). See the [roadmap](../product/06-scope-and-roadmap.md).

### D-040

**Secondary objectives**

- **Status:** Accepted, 2026-10-20
- **Decision:** Four secondary objectives: improve relay with data; advance Target A by merging the best graded outputs into it; practice the AI engineering stack (gateways, tracing, LLM judges, RAG); and share findings through articles, posts and talks.
- **Consequences:** They are pursued only where they do not weaken the primary purpose ([D-038](#d-038)). The guardrails for each are in the [vision and scope](../product/01-vision-and-scope.md#63-secondary-objectives).

### D-041

**Primary audience: people who decide which models and workflows to adopt**

- **Status:** Accepted, 2026-10-20
- **Decision:** The primary audience of the public dashboard and documentation is engineering leaders and tech leads who decide which AI models and workflows their teams adopt.
- **Consequences:** The dashboard is designed for technically fluent readers who are short on time. Secondary audiences (workflow authors, AI engineers and evaluation practitioners) are described in the [vision and scope](../product/01-vision-and-scope.md#4-who-it-is-for). Refines [D-009](#d-009).

### D-042

**MVP target date: first week of December 2026**

- **Status:** Accepted, 2026-10-20
- **Decision:** The MVP dashboard should be public in the first week of December 2026. Planning uses 2026-12-04 as the target date.
- **Consequences:** The [schedule to the MVP](../product/06-scope-and-roadmap.md#4-schedule-to-the-mvp) sets milestones backwards from this date. At the planned pace of 10–15 hours per week, the date is reachable only near the top of that range; the expected finish is mid-December. See [D-043](#d-043).

### D-043

**When the MVP runs late, the date moves, not the scope**

- **Status:** Accepted, 2026-10-20
- **Decision:** If the MVP is at risk of missing its target date, the date is re-forecast. The MVP scope is not cut to protect the date.
- **Consequences:** Each milestone is a checkpoint where the remaining work is re-estimated and the date is re-forecast. Since the date is no longer the main defense against scope creep, the MVP scope is frozen ([D-024](#d-024)), and anything new goes to a later phase.

### D-044

**Budget ceiling for Phase 2**

- **Status:** Open
- **Question:** What is the maximum model API spend for Phase 2?
- **Considerations:** The current estimate for Phase 2 is about US$ 1,700 on top of the MVP (about US$ 2,300 in total). The actual MVP costs will recalibrate it, and Phase 2 itself is still a proposal.
- **Needed by:** the end of the MVP.

### D-045

**LangSmith and Langfuse as reference designs only**

- **Status:** Accepted, 2026-10-21
- **Decision:** LangSmith and Langfuse are not used in AI Track Record. They serve only as guidance and as examples to follow.
- **Consequences:** Their concepts, such as traces and spans, scores attached to runs, datasets, experiments and side-by-side comparison of runs, guide the design of the local store and the dashboard where they fit. They are implemented on the local stack ([D-032](#d-032), [D-033](#d-033)), and nothing is sent to either product.
