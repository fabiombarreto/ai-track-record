# Docs Update — local-model-route

**PR:** n/a (Phase 4 patch diff, not merged)
**Merged at:** 2026-11-04
**Source PRD:** PRPs/prds/local-model-route.prd.md
**Effective configuration:** diff_source=patch, non_interactive=true, docs_sync=true

All paths below are under the worktree `.worktrees/local-model-route/`. The Phase 3 APPROVED manifest is kept at `phase-3/docs-update.md`; earlier ones at `phase-2/` and `phase-1/`.

## Files Edited

### `docs/development.md`

**Change type:** additive
**Rationale:** The diff adds `atr.local.launch` and `atr.tasks.build --route local`; both were added to the Local models command row.

---

### `docs/domain/areas/local-inference.md`

**Change type:** additive
**Rationale:** Added the launcher to the code list, the refusals (other Harbor job, non-local job, unmapped alias, existing job folder), the launcher's run and records rules, the local allowlist variant, the whole-job flow and the Relationships line.

---

### `docs/api-reference.md`

**Change type:** additive
**Rationale:** Added the `atr.local.launch` row to the commands table and the `server/` and power file rows to the Trial folder table. The job folder's `launch.json` is in the command row (the file has no job folder table).

---

## Candidate Decisions (for operator review)

- The local allowlist default (`agent_allowed_hosts` without `api.anthropic.com` plus `host.docker.internal`) and the refusal to build a local variant that names Anthropic's API or lacks the host. Stated in code and the research report; relates to D-050. Decide whether it needs its own D-0xx entry.
- The launcher fails closed when the server key appears in anything it wrote, and removes every `ANTHROPIC_` variable from Harbor's environment. Relates to D-020 and D-029.
- Candidate anti-pattern: starting a local job outside the launcher (no refusal check, no power records, server left running).

## Deferred Questions

- Should `docs/domain/areas/runs.md` mention that local jobs go through the launcher? Suggested default: no; the rules are in local-inference and runs only describes the agent.
- Should `docs/context/testing.md` list tests for the launcher and `local_hosts()`? The diff carries no test files. Suggested default: yes, once the tests exist.
- Earlier deferred questions (Phases 1 to 3) remain the operator's.

## Files Scanned — No Edit Required

- `docs/KNOWLEDGE_BASE.md` — no new `docs/` file was added.
- `docs/decisions.md`, `docs/anti-patterns.md`, `CLAUDE.md` — no explicit decision or pattern stated in the diff; see Candidate Decisions.
- `docs/context/*` — PRESERVE rule; no concrete need.
- `docs/domain/areas/runs.md`, `docs/domain/glossary.md` — unchanged by this diff.
- `documentation/research/local-route.md` — changed by the diff; `documentation/` is read-only for this agent.
- `harness/src/atr/local/launch.py`, `harness/src/atr/tasks/build.py`, `targets/synthetic-events/task-01.toml` — code and task manifest, read-only.
- Step 3.5 (component-map) — skipped: no Figma-sourced phase.

---
*Generated: 2026-11-04*
*Approved: 2026-11-04*
*Status: APPROVED*
