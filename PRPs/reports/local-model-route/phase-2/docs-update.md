# Docs Update — local-model-route

**PR:** n/a (Phase 2 patch diff, not merged)
**Merged at:** 2026-11-04
**Source PRD:** PRPs/prds/local-model-route.prd.md
**Effective configuration:** diff_source=patch, non_interactive=true, docs_sync=true

All paths below are under the worktree `.worktrees/local-model-route/`. The Phase 1 manifest is kept at `phase-1/docs-update.md`.

## Files Edited

### `docs/domain/areas/local-inference.md`

**Change type:** additive
**Rationale:** The diff adds `atr.local.probe` (check L1) and the tool fixture, `check_args` (offline guard), the key check on `/slots` and `/metrics`, `serve record`, and the final flags. Rules were appended for each, the code and main-flow lines name `probe` and `serve record`, and the Open Question on the final flags and `--cache-ram` was narrowed (decided; only check L5 remains). Phase 1 edits were kept.

---

### `docs/libs/llama-cpp.md`

**Change type:** additive
**Rationale:** The diff shows that `/slots` returns prompt and generated text and is dropped in `serve record` and the probe, that `/slots` and `/metrics` need the key, and the `--no-webui`, `--slots` and `--cache-ram` choices (4096 and 2048). Added to Gotchas.

---

### `docs/development.md`

**Change type:** additive
**Rationale:** The Local models command row now lists `atr.local.probe` and `atr.local.serve record <folder>`, both new in the diff.

---

## Candidate Decisions (for operator review)

- Prompt-cache RAM budgets of 4096 MiB (L-Small) and 2048 MiB (L-MoE), derived from measured container peaks; the research report calls them a first value that check L5 revisits. Decide later whether it needs a D-0xx entry.
- The server fails closed on any start without `--offline` or with a download flag. This is stated in code and the research report but not as a decision; decide whether it belongs in `documentation/` decisions (it relates to D-020).
- `/slots` copies must drop prompt and generated text before they are stored. Candidate anti-pattern: storing `/slots` output verbatim.

## Deferred Questions

- Should `docs/api-reference.md` mention the `baseline` key of `[models."<id>"]` in `models.toml` (carried over from Phase 1)? Suggested default: add `baseline` to the key list on line 49.
- Should `docs/context/constraints.md` record the machine limits measured in WP0 (8 GB VRAM, 18 GB VM, no headroom for L-Small at 128k)? Suggested default: add one line pointing to `documentation/research/local-route.md` (carried over from Phase 1).
- `docs/libs/llama-cpp.md` and `docs/development.md` are not in the explicit write scope table; they were edited because the orchestrator named them as relevant. Suggested default: accept the edits.
- Should `docs/api-reference.md` document the `serve record` and `probe` command-line interfaces, or the `claude-code-tools.json` fixture? Suggested default: no, `docs/development.md` and the module docstrings cover them.

## Files Scanned — No Edit Required

- `docs/KNOWLEDGE_BASE.md` — no new `docs/` file was added.
- `docs/decisions.md`, `docs/anti-patterns.md`, `CLAUDE.md` — no explicit decision or pattern is stated in the diff; see Candidate Decisions.
- `docs/context/*` — PRESERVE rule; machine limits are a deferred question.
- `documentation/research/local-route.md` — changed by the diff; `documentation/` is read-only for this agent.
- `infra/local-inference/models.toml`, `harness/src/atr/local/*` — code and configuration, read-only.
- Step 3.5 (component-map) — skipped: `figma_track` is not a Figma phase of this feature and the diff carries no Figma-sourced phase.

---
*Generated: 2026-11-04*
*Approved: 2026-11-04*
*Status: APPROVED*
