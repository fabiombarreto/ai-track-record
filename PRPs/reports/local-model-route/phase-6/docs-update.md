# Docs Update — local-model-route

**PR:** n/a (Phase 6 patch diff, not merged)
**Merged at:** 2026-11-04
**Source PRD:** PRPs/prds/local-model-route.prd.md
**Effective configuration:** diff_source=patch, non_interactive=true, docs_sync=true

All paths below are under the worktree `.worktrees/local-model-route/`. The Phase 5 APPROVED manifest is kept at `phase-5/docs-update.md`; earlier ones at `phase-4/` to `phase-1/`.

## Files Edited

### `docs/domain/areas/local-inference.md`

**Change type:** additive
**Rationale:** The diff adds the L-Small template override, the `/templates` read-only mount, the `check_args` path and SHA-256 check with the digest in `server.json`, the L-MoE limitation (later system message silently not rendered) and the `network` probe in the local pre-flight.

---

### `docs/libs/llama-cpp.md`

**Change type:** additive
**Rationale:** Documents `--chat-template-file` as used here and the later-system-message behavior of the two embedded templates.

---

### `docs/domain/areas/runs.md`

**Change type:** additive
**Rationale:** Adds the `network` record in `agent/route.json`, the local-route turn-limit outcome (`error` with `NonZeroAgentExitCodeError`), the time limit as `timed_out` and the skipped-step blind spot; the chat-template Open Question now points to the Phase 6 fix.

---

### `docs/domain/areas/store-and-publication.md`

**Change type:** additive
**Rationale:** `failure_cause` (`native_outcome`) now applies only to local-route trials.

---

## Candidate Decisions (for operator review)

- Override the L-Small chat template (system turn rendered in place) and pin it by SHA-256, instead of patching the server or the client. Relates to D-020. Decide whether it needs its own D-0xx entry.
- Accept L-MoE running without Claude Code's environment section rather than overriding its template; results must carry that caveat.
- A network probe failure is recorded, never fatal.

## Deferred Questions

- The runs.md Open Question on `error_max_turns` mapped to `budget_exceeded` (Anthropic route) versus D-019 remains; the local route now ends as `error`. Suggested default: keep open until the two routes are reconciled.
- Should `docs/context/testing.md` list tests for `check_args` and the template digest check? Suggested default: yes, once tests exist (the diff was not checked for test files beyond the listed changes).
- Earlier deferred questions (Phases 1 to 5) remain the operator's.

## Files Scanned — No Edit Required

- `docs/api-reference.md` — lists `agent/route.json` generally; `check_args` is not listed.
- `docs/development.md`, `docs/KNOWLEDGE_BASE.md`, `docs/domain/glossary.md` — no serve flags or new `docs/` file concerned.
- `docs/decisions.md`, `docs/anti-patterns.md`, `CLAUDE.md` — no explicit decision or pattern stated; see Candidate Decisions.
- `docs/context/*` — PRESERVE rule; no concrete need.
- `documentation/research/local-route.md` — changed by the diff; `documentation/` is read-only for this agent.
- `infra/local-inference/*`, `harness/src/atr/**` — code and configuration, read-only.
- Step 3.5 (component-map) — skipped: no Figma-sourced phase.

---
*Generated: 2026-11-04*
*Approved: 2026-11-05*
*Status: APPROVED*
