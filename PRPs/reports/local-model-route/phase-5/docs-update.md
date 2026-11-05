# Docs Update — local-model-route

**PR:** n/a (Phase 5 patch diff, not merged)
**Merged at:** 2026-11-04
**Source PRD:** PRPs/prds/local-model-route.prd.md
**Effective configuration:** diff_source=patch, non_interactive=true, docs_sync=true

All paths below are under the worktree `.worktrees/local-model-route/`. The Phase 4 APPROVED manifest is kept at `phase-4/docs-update.md`; earlier ones at `phase-3/`, `phase-2/` and `phase-1/`.

## Files Edited

### `docs/domain/areas/store-and-publication.md`

**Change type:** additive
**Rationale:** The diff adds trial columns for local runs, the local reconciliation rule, the `native_outcome` failure cause and allowlist version 3 with its new fields and label. Allowlist version 2 became 3; the open question about local cost and energy was replaced by the remaining untested item (check L7).

---

### `docs/domain/areas/budget.md`

**Change type:** additive
**Rationale:** `atr.ops.budget` now leaves `lc-` jobs out of the ceiling total and prints them on their own line.

---

### `docs/domain/areas/local-inference.md`

**Change type:** additive
**Rationale:** The Relationships line said store records were planned; they are now built.

---

## Candidate Decisions (for operator review)

- A local run's `cost_usd` is stored as 0 with `cost_source` `local`, and the SDK's figure is kept as `sdk_cost_estimate_usd`. Relates to D-022 and D-058. Decide whether it needs its own D-0xx entry.
- Local runs are published under the model alias without the `local/` prefix because of the leak check's path pattern; the leak check itself is unchanged.
- Budget exclusion is by the `lc-` job-name prefix, hard-coded (`LOCAL_PREFIX`). The budget Open Question about a per-experiment ceiling was left as is.

## Deferred Questions

- Should the budget Open Question on a per-experiment ceiling be closed now that `lc-` jobs are reported apart? Suggested default: keep it, since only a prefix exclusion exists and no separate ceiling.
- Should `docs/context/testing.md` list tests for the new store, budget and export behavior? The diff carries no test files. Suggested default: yes, once the tests exist.
- Earlier deferred questions (Phases 1 to 4) remain the operator's.

## Files Scanned — No Edit Required

- `docs/api-reference.md`, `docs/domain/glossary.md` — no store column list or cost source term is defined there.
- `docs/libs/duckdb.md`, `docs/KNOWLEDGE_BASE.md` — generic descriptions still accurate; no new `docs/` file.
- `docs/decisions.md`, `docs/anti-patterns.md`, `CLAUDE.md` — no explicit decision or pattern stated in the diff; see Candidate Decisions.
- `docs/context/*` — PRESERVE rule; no concrete need.
- `documentation/research/local-route.md` — changed by the diff; `documentation/` is read-only for this agent.
- `harness/src/atr/store/load.py`, `harness/src/atr/store/export.py`, `harness/src/atr/ops/budget.py` — code, read-only.
- Step 3.5 (component-map) — skipped: no Figma-sourced phase.

---
*Generated: 2026-11-04*
*Approved: 2026-11-04*
*Status: APPROVED*
