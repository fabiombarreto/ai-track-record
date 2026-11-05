# Docs Update — local-model-route

**PR:** n/a (Phase 3 patch diff, not merged)
**Merged at:** 2026-11-04
**Source PRD:** PRPs/prds/local-model-route.prd.md
**Effective configuration:** diff_source=patch, non_interactive=true, docs_sync=true

All paths below are under the worktree `.worktrees/local-model-route/`. The Phase 2 APPROVED manifest is kept at `phase-2/docs-update.md`; Phase 1 at `phase-1/docs-update.md`.

## Files Edited

### `docs/domain/areas/runs.md`

**Change type:** additive
**Rationale:** The diff adds the `route`, `local_base_url` and `local_timeout_ms` options, the local server checks (record, key, alias, port), the container pre-flight check and `agent/route.json`. Two rules and one pre-flight rule were added, the Relationships line now says the local route exists, and the open question on `route.json` was replaced by what is built plus the chat template finding from the check run.

---

### `docs/domain/areas/local-inference.md`

**Change type:** additive
**Rationale:** The Relationships line said the route option was planned; the diff builds it, reading `server.json` and `server.key` and writing `agent/route.json`.

---

### `docs/api-reference.md`

**Change type:** additive
**Rationale:** Added the `agent/route.json` row to the Trial folder table, next to `agent/workflow.json`.

---

### `docs/domain/glossary.md`

**Change type:** additive
**Rationale:** The Route entry said `route.json (planned)`; it is now `agent/route.json`.

---

## Candidate Decisions (for operator review)

- The local route's container holds no `ANTHROPIC_API_KEY`, and the pre-flight fails the trial if it does. Stated in code and the research report, not as a decision; relates to D-020 and D-058.
- The local route has no `max_budget_usd` because Claude Code has no price for a local model (check L8 studies the cap). Decide whether it needs a D-0xx entry.
- Candidate anti-pattern: putting the server key in a command string or a run record (the diff passes it through the exec environment and refuses to write `route.json` if it appears).

## Deferred Questions

- Should `docs/libs/claude-agent-sdk.md` list the route variables (the context, timeout and attribution header settings)? Its existing gotcha already covers context and timeouts. Suggested default: no.
- Should `docs/context/integrations.md` line 21 ("Claude Code will call `POST /v1/messages` once the local route exists") be updated? Suggested default: yes, to "calls", at the next sync; it was left as is because it is not strictly changed by this diff (the chat template failure means no request has succeeded).
- Earlier deferred questions (Phase 1 and 2: `baseline` in `api-reference.md`, WP0 machine limits in `constraints.md`, acceptance of edits to `docs/libs/llama-cpp.md` and `docs/development.md`, CLI docs for `serve record` and `probe`) remain the operator's.

## Files Scanned — No Edit Required

- `docs/KNOWLEDGE_BASE.md` — no new `docs/` file was added.
- `docs/decisions.md`, `docs/anti-patterns.md`, `CLAUDE.md` — no explicit decision or pattern stated in the diff; see Candidate Decisions.
- `docs/context/*` — PRESERVE rule; no concrete need.
- `docs/libs/claude-agent-sdk.md` — existing gotcha already covers the context and timeout settings.
- `documentation/research/local-route.md` — changed by the diff; `documentation/` is read-only for this agent.
- `harness/src/atr/agents/claude_sdk.py` — code, read-only.
- Step 3.5 (component-map) — skipped: no Figma-sourced phase.

---
*Generated: 2026-11-04*
*Approved: 2026-11-04*
*Status: APPROVED*
