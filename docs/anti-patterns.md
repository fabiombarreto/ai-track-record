# Anti-Patterns

Forbidden patterns, disabled features and intentional restrictions.
The AI must NOT implement anything listed here, even if it seems right.
Updated by the Docs Updater after each approved implementation.

---

## Private-target material in the repository

**What it is:** Writing Target A's real name, specifications, code, data, prompts or run transcripts into any committed file, including `docs/`, `PRPs/` and commit messages.
**Why it's forbidden:** The repository is public; private targets appear under a codename only (D-013, public-safety rule in `documentation/README.md`).
**What to do instead:** Refer to "Target A"; keep private material in `~/atr`; run the exporter's leak check before publishing.
**Areas affected:** store-and-publication, runs, local-inference

---

## Sending Target A's content to a provider that is not allowed

**What it is:** Running Target A on any model route other than Anthropic's API or a local open-weight model, or pasting its material into a web interface.
**Why it's forbidden:** D-026, D-029, D-057; D-055 (Gemini) is open.
**What to do instead:** Run other providers on the public synthetic task until a decision allows them.
**Areas affected:** runs, local-inference

---

## Web tools or an open network on Target A runs

**What it is:** Enabling `WebSearch` or `WebFetch`, or dropping the network allowlist, on a Target A run.
**Why it's forbidden:** Search queries and fetched URLs could reveal what the product builds (D-050).
**What to do instead:** Keep the allowlist (model API or local server, Collector, package index) and pass the web tools in `disallowed_tools`.
**Areas affected:** runs

---

## Grading a workflow by its own records

**What it is:** Using relay's own reports, deviations or claims of success as a grade.
**Why it's forbidden:** A workflow is not graded by its own records alone; the outcome records what the agent claims, the grades what is true (D-018, D-051).
**What to do instead:** Grade with the hidden oracle, existing tests, static analysis and the independent review; keep the workflow's records next to them.
**Areas affected:** grading, review

---

## Letting the agent see or influence the grader

**What it is:** Putting hidden tests in the agent's image, giving the agent later git history, or loading a `conftest.py` the agent wrote during grading.
**Why it's forbidden:** It breaks the hidden oracle (D-015).
**What to do instead:** Only the run's diff crosses to the verifier; the pristine tests run from `/grading` on a clean base.
**Areas affected:** grading

---

## Silently dropping a configuration option

**What it is:** Ignoring a requested SDK or server option that the installed version does not support.
**Why it's forbidden:** The run would differ from its configuration without a trace (D-020).
**What to do instead:** Fail with an error, as `claude_sdk_runner.py` does.
**Areas affected:** runs, local-inference

---

## Unpinned versions

**What it is:** "latest" tags, floating image tags, unpinned model files or unrecorded relay versions.
**Why it's forbidden:** Results stop being comparable (D-020, R10).
**What to do instead:** Pin by version, commit, digest or SHA-256, and record what each run used.
**Areas affected:** runs, review, local-inference

---

## Excluding or retrying a run because it hit a limit

**What it is:** Dropping a run that timed out or hit its cap, or rerunning it until it passes.
**Why it's forbidden:** Hitting a limit is a measured outcome (rigor rule 6, D-020). Only `error` runs are retried.
**What to do instead:** Grade the run with what it left and record its outcome.
**Areas affected:** runs, grading

---

## Running two benchmark runs at the same time

**What it is:** Running MVP runs in parallel, or a local run while an MVP job runs.
**Why it's forbidden:** Time is a grader and parallel runs compete for the machine and the API (M3 results, D-058).
**What to do instead:** One run at a time; the launcher waits for a run in progress.
**Areas affected:** runs, local-inference

---

## Secrets in the repository

**What it is:** Committing API keys, tokens, server keys or `.env` files.
**Why it's forbidden:** Public repository; supply-chain risk (R11).
**What to do instead:** Keep secrets in `~/atr/.env`; the local server's key is written outside the repository with owner-only permissions.
**Areas affected:** all

---

## Large files on C: or inside the WSL and Docker disks

**What it is:** Downloading model weights or other multi-gigabyte files to the WSL filesystem or Docker volumes.
**Why it's forbidden:** Those disks live on C:, which has little free space [INFERRED - VALIDATE: a machine constraint, not a decision].
**What to do instead:** Keep weights on D: (`/mnt/d/atr/models`).
**Areas affected:** local-inference

---

<!-- Template for future entries:

## [pattern name]

**What it is:** Brief description.
**Why it's forbidden:** The reason this was explicitly prohibited.
**What to do instead:** The approved alternative.
**Areas affected:** [list domain areas]

-->
