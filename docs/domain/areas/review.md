# Review

## Primary responsibility

Review each graded run with a reviewer that is not part of any workflow under test, and confirm a blind sample of its findings by hand. Code: `atr.review.run`, `atr.review.reviewer`, `atr.review.confirm`.

## Entities

Review, findings (rank, category, file, line, summary, failure scenario), confirmation sheet, key, verdict.

## Rules

- The reviewer is pinned: Claude Code's built-in `/code-review` at high effort on Sonnet 5.5, through the same Agent SDK version as the runs, in its own container with web tools disabled (D-018).
- It reviews the verifier's `changes.patch` applied to a clean copy of the base, so every configuration is reviewed the same way. Workflow working files under `PRPs/` are left out of the diff; the base's specification stays readable as context.
- The findings come back as data through a second turn that asks for them with the ReportFindings tool.
- The reviewer stays the same for runs on other models and routes, including local models; it may favor its own model family, which the blind confirmation checks.
- Blind confirmation samples a fixed number of runs per configuration and task (default one), writes each without any hint of its configuration, and keeps the mapping in `key.json`, which the operator does not open before grading.
- Review findings are not evidence of defects until confirmed.
- Review cost is paid with Anthropic credits and counted in the spend.

## Relationships

Reads graded trials; feeds the store (`review_findings`, `review_cost_usd`) and the budget.

## Main flow

Graded trial → `atr.review.run` → `review/review.json` → `atr.review.confirm sample` → operator grades the sheets → `atr.review.confirm summary`.

## Open Questions

- Whether the reviewer judges code from non-Claude models differently is unknown until the local runs' confirmations are graded [INFERRED - VALIDATE].
