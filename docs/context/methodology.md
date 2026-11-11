---
tdd: false                # true | false — the only key consulted by the TDD track
tdd_evidence: null        # null | "<path-or-short-reason>" | "user-declared"
test_frameworks: [pytest] # array of frameworks detected in the scan (informative only)
docs_sync: true           # true | false — per-project master switch for automated docs/ sync (docs-updater/docs-reviewer)
figma_track: false        # true | false — opt-in switch for the Figma implementation track (design-to-code); default off, never heuristically flipped
visual_first_approval: auto  # auto | human — default approval mode for the Figma Visual-First Track's visual-first blocking gate; only meaningful when figma_track: true
lane_runtime_safe: false  # true | false — declares the project's test stage does not contend on shared runtime resources (ports, containers, databases); default off, never heuristically flipped
formatter_cmd: null   # null | "<command string>" — project formatter command; null means undeclared; never heuristically inferred
hybrid_code_review: false  # true | false — opt-in switch for the hybrid /code-review evidence pass inside code-reviewer's R-SEM row; default off, never heuristically flipped
hybrid_code_review_level: "medium"   # "medium" | "high" — configured /code-review effort level for the hybrid pass; any other value (xhigh, max, ultra, etc.) is refused by name inside code-reviewer, never heuristically inferred
---

# Methodology

## TDD (Test-Driven Development)

Current state: **not declared** (default).

The TDD track (agents B7 and B8) activates only when `tdd: true` in the
frontmatter above. Heuristics MUST NOT flip this value — only a human edit
or an explicit user declaration during `*init` can.

### Observed signals

- The harness has a pytest suite in `harness/tests/`, declared by the owner on 2026-11-11 for the MVP dashboard work; its commands are in `docs/context/testing.md`. With `tdd: false`, relay's test pair writes tests after the Implementer and Code Review.
- Target A, one of the targets the benchmark runs on, declares `tdd: true` in its own relay context (D-052). That is the target's methodology, not this repository's, and does not apply here.

### How to activate

1. Confirm with the team that TDD is the declared methodology.
2. Change `tdd: false` to `tdd: true` above.
3. Set `tdd_evidence` to `"user-declared"` or the path that records the
   decision.
4. Ensure `test_frameworks` lists frameworks the plugin should drive.
