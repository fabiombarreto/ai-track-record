# Docs Update — local-model-route

**PR:** n/a (Phase 1 worktree diff, not merged)
**Merged at:** 2026-11-04
**Source PRD:** PRPs/prds/local-model-route.prd.md
**Effective configuration:** diff_source=patch, non_interactive=true, docs_sync=true

## Files Edited

### `docs/domain/areas/local-inference.md` (under the worktree `.worktrees/local-model-route/`)

**Change type:** additive
**Rationale:** The diff adds fail-closed checks to `serve` (loopback-only publication via `docker inspect`, key absent from the record), image id and machine in the server record, `.bad` renaming and result wording in `fetch`, and tokenize-and-rescale, energy integration, peak container memory and partial results in `bench`. It also adds `baseline` to `models.toml`. Rules were appended and the Open Questions were narrowed to what WP0 measured (n-cpu-moe 34, context 131072) versus what remains for Phase 2.

---

## Candidate Decisions (for operator review)

- L-MoE runs with `--n-cpu-moe 34` and both models use context 131072 and one slot, as measured in WP0. The measurement lives in `documentation/research/local-route.md`; decide whether it needs a D-0xx entry in `documentation/`.
- L-MoE uses UD-Q3_K_XL because the 4-bit variant needs a larger WSL memory profile.

## Deferred Questions

- Should `docs/api-reference.md` mention the new `baseline` key of `[models."<id>"]` in `models.toml`? It is outside this agent's write scope — suggested default: add `baseline` to the key list on line 49.
- Should `docs/context/constraints.md` record the machine limits measured in WP0 (8 GB VRAM, 18 GB VM, no headroom for L-Small at 128k)? Suggested default: add one line pointing to `documentation/research/local-route.md`.

## Files Scanned — No Edit Required

- `docs/KNOWLEDGE_BASE.md` — no new `docs/` file was added; the local-inference entry still holds.
- `docs/development.md` — the command list for `fetch`, `serve` and `bench` is unchanged.
- `docs/api-reference.md` — outside the write scope; see Deferred Questions.
- `docs/decisions.md`, `docs/anti-patterns.md`, `CLAUDE.md` — no explicit decision or pattern stated in the diff.
- `documentation/research/local-route.md` — new file in the `documentation/` site, read-only for this agent.

---
*Generated: 2026-11-04*
*Approved: 2026-11-04*
*Status: APPROVED*
