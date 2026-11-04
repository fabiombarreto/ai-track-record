# Decision Gate (AI Control Mechanism)

The Decision Gate is a mandatory cognitive control mechanism.
It prevents the AI from making silent decisions in areas where accumulated
knowledge or architectural risk already exists.

---

## Purpose

- Avoid re-solving already settled decisions
- Force conscious risk evaluation
- Ensure correct use of existing decisions
- Reduce silent architectural regressions

---

## When the Decision Gate is activated

The gate MUST be executed at the following points:

1. **Before any planning** — with or without the `plan-feature` command.
   Includes any moment where the AI needs to decide structure, layers, components, or data flow.

2. **Before any code generation or modification** — when the task involves
   creating files, changing existing components, or adding logic
   that impacts more than one module.

3. **During formal reviews** — when the `review-feature` command is executed,
   or when the AI is asked to evaluate already-implemented code.

The gate is NOT activated for exempt tasks defined in the "Decision Gate Scope" section.

---

## Mandatory consultation sources

Whenever the Decision Gate is activated, the AI MUST consult:

| Source | Content |
|--------|---------|
| `docs/decisions.md` | Already-made decisions that must not be re-evaluated |
| `documentation/decisions/decision-log.md` | The project's decision log, source of truth for every decision and its status; `docs/decisions.md` summarizes the ones that constrain code |
| `docs/anti-patterns.md` | Forbidden patterns, disabled features, and intentional restrictions |
| `docs/context/architecture.md` | Inviolable architectural rules (layers, dependencies, services) |
| `docs/context/constraints.md` | Hard limits and non-violable technical constraints |
| `docs/domain/areas/runs.md` | Business rules for runs |
| `docs/domain/areas/grading.md` | Business rules for grading |
| `docs/domain/areas/review.md` | Business rules for review |
| `docs/domain/areas/store-and-publication.md` | Business rules for store and publication |
| `docs/domain/areas/budget.md` | Business rules for budget |
| `docs/domain/areas/local-inference.md` | Business rules for local inference |

Consulting these sources is MANDATORY. The AI CANNOT proceed
without having verified them when the gate is active.

### Refinement by active context

If a `.context.md` file is active (provided by the user or referenced in the task):

- The AI MUST use it to **restrict the scope** of consultation to the mandatory sources.
- Only decisions, anti-patterns, and rules **relevant to the domains permitted**
  by the active context must be considered.
- Domains explicitly excluded by `.context.md` MUST NOT be evaluated.
- If there is no active context, consultation must cover all sources without restriction.

---

## Mandatory evidence

Every Decision Gate execution MUST produce a visible evidence block
to the user BEFORE proceeding with planning, code, or review.

The block MUST follow this format:

```
**Decision Gate**
- Active context: [path to .context.md or "none"]
- Activated criteria: [list of checklist items that apply]
- Decisions found: [list of relevant decisions or "none"]
- Applicable anti-patterns: [list or "none"]
- Applicable architectural rules: [list or "none"]
- Result: PROCEED | HALT (reason)
```

Evidence rules:
- The block MUST appear in the response to the user, not only in internal reasoning.
- If the result is HALT, the AI MUST stop and request clarification.
- If the result is PROCEED, the AI may continue with the task.
- The absence of the evidence block is a violation of the Decision Gate.

---

## Decision Gate — Planning

Before planning any feature, the AI MUST evaluate whether the task involves
one or more of the items below:

- architectural decisions
- cross-cutting patterns
- reuse or creation of components
- domain rules
- separation between public and administrative areas
- impact on shared UI
- impact on reusable services
- business rules for runs (see docs/domain/areas/runs.md)
- business rules for grading (see docs/domain/areas/grading.md)
- business rules for review (see docs/domain/areas/review.md)
- business rules for store and publication (see docs/domain/areas/store-and-publication.md)
- business rules for budget (see docs/domain/areas/budget.md)
- business rules for local inference (see docs/domain/areas/local-inference.md)

### Mandatory behavior

- If it does NOT involve any item above:
  - Proceed with planning normally.

- If it involves ANY item above:
  - Consult all sources listed in the "Mandatory consultation sources" section.
  - Treat the content of those sources as mandatory.
  - If there is doubt, conflict, or uncertainty:
    - Halt planning.
    - Request clarification before continuing.

---

## Decision Gate — Review

During a review of an implementation, the AI MUST consult all sources
listed in the "Mandatory consultation sources" section and verify:

- Whether each source was respected in the implementation
- Whether any rule or restriction was violated or ignored
- Whether new stable decisions emerged that should be recorded

### Review restrictions

- Do NOT propose new decisions
- Do NOT re-plan the feature
- Do NOT suggest cosmetic refactors

The purpose of the review is only to:
- validate conformance
- extract reusable learning

---

## Decision Gate Scope — Exemptions

The Decision Gate MUST NOT be applied when ALL criteria below are true:

1. The change is confined to a **single file** that is NOT shared by other modules.
2. The change does NOT create, remove, or rename exports consumed by other files.
3. The change does NOT modify data contracts (props, types, interfaces, service parameters).

### Examples of exempt tasks

- Fixing label text or error message inside a specific component
- Adjusting spacing, color, or CSS style confined to a single component
- Fixing a typo in a local variable (no export)
- Mechanical tasks: lint, formatting, import ordering

### Examples of non-exempt tasks (gate required)

- Renaming a prop that is passed by a parent component
- Changing the signature of a service function
- Moving a component from `components/` to `pages/` or vice-versa
- Adding a new field to a shared type

---

## Feedback loop with review

The `review-feature` template produces a "📋 Decisions to record" section.
This section is the formal feedback channel for the Decision Gate.

When a review identifies decisions to record:

1. Decisions about **what to do** (product, UX, domain choices)
   → Must be recorded in `docs/decisions.md`.

2. Decisions about **what NOT to do** (forbidden patterns, intentional limitations)
   → Must be recorded in `docs/anti-patterns.md`.

3. Gate failures (an existing decision was not consulted or did not prevent an error)
   → Must trigger an update to this file (`docs/decision-gate.md`).

The AI MUST, at the end of a review, explicitly indicate in which file
each identified decision should be recorded.

---

## Updating the Decision Gate

This file should only be updated when:

- a review identifies a gate failure (existing decision not consulted)
- a new type of error escapes the gate that should have been caught
- the project changes in scale or complexity, requiring new criteria

Updates must:
- add criteria (never inflate lists without need)
- maintain objective and prescriptive language
- avoid duplication with other governance files
