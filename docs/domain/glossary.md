# Glossary

The authoritative vocabulary is in `documentation/product/02-concepts.md`. This glossary lists the terms as they appear in the code, with the code's own names where they differ.

| Term | In code | Definition |
|---|---|---|
| Target | `target`, `codename`, `visibility` | A software project used as a testbed: a repository, an environment that builds and tests it, and its tasks. Public or private; a private target appears publicly under a codename only (D-013) |
| Target A | `codename = "Target A"` | The first, private target. Never named otherwise in this repository |
| Synthetic target | `synthetic-events` | The public Django target of Phase 0 (D-046), used for checks and debugging |
| Task | task manifest (`.toml`), built task folder, `task_id` | A self-contained unit of work, authored as a pull request: a base ref the agent starts from and a solution ref with the feature and its hidden tests |
| Specification | `spec`, a PRD under `PRPs/prds/` in the target | The only instruction the agent receives |
| Hidden oracle | `hidden_tests`, tests named `test_ac<N>_...` | Acceptance tests added only at grading time; each maps to an acceptance criterion |
| Existing tests | `existing_tests` | The target's own tests at the base; they must keep passing |
| Harness | Claude Code through the Agent SDK | The agent runtime that executes a run, pinned by SDK version |
| Workflow | `workflow`: `relay` or `vanilla` | The prompt layer under test. Vanilla is Claude Code with no plugin and a fixed minimal instruction |
| Workflow version | `workflow_version`, `workflow_digest` | The exact plugin version and digest a run used; relay runs from a copy of its commit |
| Configuration | `config`, `config_label` (e.g. `relay049-sonnet`) | Workflow version plus model plus limits; the factor compared |
| Experiment | a set of jobs with one prefix (`m3-`, `lc-`) | The runs that answer one question, with declared hypotheses |
| Run | Harbor **trial** | One execution of one configuration on one task. "Run" in the documentation, "trial" in Harbor's folders and the store |
| Job | Harbor job, one config file | Harbor's unit of launch. In M3 each job holds one trial, so a job name identifies a run |
| Repetition | `r1`, `r2`, `r3` in job names | One pass over every configuration and task; runs are ordered by repetition |
| Cell | configuration × task | One combination; three repetitions per cell |
| Pilot | `m2-pilot-`, `m3-pilot-` | Runs made before a batch to check the harness and calibrate the budget; not part of the experiment's sample |
| Outcome | `outcome`, `native_outcome` | How a run ended before grading: completed, halted, budget_exceeded, timed_out or error (D-019). `native_outcome` keeps relay's HALT code |
| Grader | verifier `grade.py`, review, checks | A check that scores a run |
| Reward | `reward` | 1.0 when every hidden and existing test passes, else 0.0 |
| Criteria satisfied | `criteria_satisfied` | Share of acceptance criteria whose tests all pass |
| New static findings | `new_static_findings` | Findings of the task's static analysis that the run introduced, base against run |
| Independent review | `review/review.json`, `review_findings` | Claude Code's `/code-review` on the run's graded diff, pinned and outside the workflow (D-018) |
| Blind confirmation | `atr.review.confirm`, `confirmations/` | The operator grades a sample of review findings without knowing the configuration |
| Skipped step | `checks/skipped_steps.json`, `skipped_flagged` | A protocol step the workflow skipped; flagged when its summary does not mention it. Never a grade (D-051) |
| Deviation | `relay_deviations` | What relay 0.49.0 itself recorded as departures from its protocol |
| Route | `route.json` (planned) | How a model is reached: Anthropic's API directly, or a local inference server |
| Local model | `models.toml` entry: id, alias, role | An open-weight model served by llama.cpp on the operator's machine (D-057) |
| Role (local plan) | `L-MoE`, `L-Small`, `L-Alt` | The configurations of the local models plan |
| Stage (local plan) | `main`, `fallback`, `option`, `candidate` | Which model files `atr.local.fetch` downloads by default |
| Ceiling | `CEILING_USD = 800` | The MVP's total spend limit (D-028) |
| Cost cap | `max_budget_usd` | A run's soft cost limit, enforced by the SDK's estimate |
| Publication | `exports/`, `publications.jsonl` | A recorded export of allowlisted fields after the leak check |
| Leak check | `leak_check`, `leak-terms.txt` | Scan of an export for private terms, paths, file names, secrets, e-mail addresses and long text |

## Inconsistencies to watch

- "Run" and "trial" mean the same thing; "job" is Harbor's launch unit and only coincides with a run when a job holds one trial.
- "Role" means a workflow function in the concepts document (planner, implementer) and a local-plan configuration (L-MoE) in `models.toml`.
- "Stage" is a relay pipeline stage in relay's records and a download group in `models.toml`.
