# Grading

## Primary responsibility

Turn a task authored as a pull request into a Harbor task, and score each run on correctness, regressions and static quality, with graders the agent never sees. Code: `atr.tasks.build`, `atr.tasks.grade`, `atr.checks.skipped_steps`.

## Entities

Task manifest, built task, hidden tests, existing tests, acceptance criteria, reward, static findings, protocol steps, skipped steps.

## Rules

- A task's base ref becomes the agent's starting point as a snapshot with no other git history; the hidden tests come from the solution ref and never enter the agent's image (D-014, D-015).
- Only the run's changes cross from the agent: the git diff of `/app` against its `base` tag. Files changed in relay's git worktrees under `/app/.worktrees` are first copied over `/app`, and the worktree wins, so a timed-out run is graded with its partial code.
- The diff is applied to a clean copy of the base; the pristine existing tests and the hidden tests run from `/grading`, outside the agent's code, so no `conftest.py` the agent wrote is loaded.
- `reward` is 1.0 only when every hidden and every existing test passes.
- `criteria_satisfied` is the share of acceptance criteria whose tests all pass; a test maps to criterion N through its name, `test_ac<N>_...`.
- `new_static_findings` counts findings of the task's declared tools (ruff today) on the run that are not on the base.
- Tasks stay frozen during an experiment; configurations are compared beyond the oracle when it does not separate them (D-053).
- A skipped protocol step is flagged for human review when the run's summary does not mention it; it never enters a grade (D-051). A halted phase is checked only up to the halt.
- A workflow is not graded by its own records alone: relay's `deviations` are kept next to the check's result, not in place of it.
- The protocol checked follows the plugin version the run recorded.

## Relationships

Reads the trial folders of runs; feeds the store and the review (the review uses the verifier's `changes.patch`).

## Main flow

Manifest → `atr.tasks.build` writes the task folder → run → verifier runs `grade.py` → `reward.json`, `details.json`, `changes.patch` → `atr.checks.skipped_steps` writes `checks/skipped_steps.json`.

## Open Questions

- "Mentioned" in the skipped-step check is a keyword match on the summary; how many flags turn out to be false positives is not yet measured [INFERRED - VALIDATE].
