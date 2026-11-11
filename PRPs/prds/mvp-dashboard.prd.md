# MVP Dashboard

```
**Decision Gate**
- Active context: none
- Activated criteria: architectural decisions (a new component, the static site, with a Node toolchain); reuse or creation of components (the exporter gains an experiment description; a site check reuses the exporter's leak check); separation between public and administrative areas (only the leak-checked export reaches the public site); business rules for store and publication; business rules for grading (how task success, false completion and review status are shown)
- Decisions found: D-025 (static site generated from the publication export, no server-side code, no online database); D-034 (hosting and domain, Open — the deploy waits for it); D-059 (publish the first repetition's 12 runs, every result preliminary); D-024 (MVP scope frozen: PUB-04 to PUB-10); D-009/D-041 (designed for engineering leaders and tech leads short on time); D-045 (LangSmith and Langfuse are reference designs only, nothing is sent to them); D-002/D-013 (deny-by-default publication, private targets by codename); D-022 (every published cost states its source); D-019 (normalized outcomes, native reason kept); D-015/D-018/D-051 (graders outside the workflow; skipped steps flagged, never scored); D-033 (derived outputs rebuilt from the system of record); D-020 (pin everything, rigor rules); D-010 (English); D-011 (planning in documentation/); D-047 (Python 3.12 with uv for the harness — the site is a separate component; its Node toolchain is recorded as D-060 on approval of this PRD)
- Applicable anti-patterns: private-target material in the repository; grading a workflow by its own records (relay's deviations appear next to the grades, never as one); unpinned versions; secrets in the repository
- Applicable architectural rules: deny-by-default publication — the site reads only the export; files first, the site rebuilt from the export at any time; fail closed on checks that guard privacy or correctness; small command-line modules in the harness
- Result: PROCEED
```

## Problem Statement

Engineering leaders and tech leads who choose AI models and workflows for their teams cannot see what AI Track Record has measured. The 12 graded runs of the MVP's first repetition exist only in the operator's local store and in markdown tables of a research report, with no path from a number to the runs behind it and nothing designed for a reader who has five minutes. Until a public dashboard exists, the MVP misses its exit criterion (M4, target 2026-12-04) and the results reach nobody.

## Evidence

- The MVP's exit criterion is that "the success criteria are met and the dashboard is public" (`documentation/product/06-scope-and-roadmap.md`, section 1; objectives OI-2 and OI-5 in `documentation/product/01-vision-and-scope.md`).
- The 12 runs of the first repetition are graded, and D-059 publishes them now, marked preliminary (`documentation/research/m3-results.md`, "The first repetition").
- Public benchmarks such as SWE-bench, Terminal-Bench, the OpenHands Index and Vibe Code Bench rank models or agents; none treats the workflow and its versions as the variable, and few show the cost of failed runs (`documentation/product/01-vision-and-scope.md`, section 9).
- The exporter already writes `runs.json`, `tasks.json`, `targets.json` and `publication.json` through an allowlist and a leak check (`harness/src/atr/store/export.py:71-124`), but `publication.json` carries no experiment description: no configuration names, questions, hypotheses, planned repetitions or preliminary flag (`harness/src/atr/store/export.py:171-176`).
- The leak check scans only the export files; nothing scans a generated site (`harness/src/atr/store/export.py:125-142`).
- The only export written so far is the M2 pilots', on allowlist version 1.

## Proposed Solution

Build the public dashboard as a static site with Observable Framework 1.13.4, pinned with its lockfile and built with telemetry disabled, from the publication export alone. The exporter gains an `experiment.json`, copied from a public experiment file in the repository, so that the publication record covers everything the site shows. Python data loaders compute the aggregates at build time; the pages follow the dashboard design principles, with the layout patterns of Langfuse and LangSmith as a visual reference (D-045): a sidebar, KPI cards, a dense run table, a page per run and a side-by-side grid of tasks × configurations. Before any deploy, a site check in the harness scans the built `dist/` with the exporter's leak patterns and verifies that every aggregate links to its runs. Observable Framework was the owner's choice over a Python generator, a static React application and Evidence.dev; self-hosting Langfuse or LangSmith is ruled out by D-045 and D-025.

## Key Hypothesis

We believe a static dashboard that leads with the headline questions, shows cost next to quality with sample sizes and the preliminary label, and links every number to its runs will let engineering leaders answer the MVP's questions from the first repetition's 12 runs.
We'll know we're right when three qualified readers each answer the headline questions in under five minutes and each says, unprompted, that the results are preliminary.

## What We're NOT Building

- A server, an online database, logins, analytics or any tracking — D-025, and the site must leave little to attack.
- Any use of Langfuse or LangSmith, hosted or self-hosted — D-045; they are visual references only.
- Transcripts, diffs, specifications, prompts or task titles of Target A — D-013 and the export allowlist; the site shows only what the export carries.
- Intervals, pass@k or pass^k computed from one run per cell — rigor rules 3 and 9; they appear when repetitions 2 and 3 exist.
- The LLM judge, mergeability verdicts and workflow version history — Phase 2 (GRD-06, GRD-07, PUB-11).
- The deploy and the domain — D-034 is open; this PRD ends with a deploy-ready `dist/`.
- The answer sentences themselves — they come from the M3 analysis, which the operator writes into the experiment file.

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Time to answer (SC-5) | 3 of 3 qualified readers answer the MVP headline questions in under 5 minutes each, and all 3 mention that the results are preliminary | Informal moderated test with a stopwatch, after the answer sentences exist |
| Evidence within two clicks (SC-2) | 100% of aggregate numbers reach their runs in at most 2 clicks | The site check over `dist/`, plus a manual spot check |
| No leak (SC-6) | 0 findings from the export's leak check and from the site check, and a recorded manual audit | Exporter and site check exit codes; the audit note in the publication record |
| Site ready for M4 | A deploy-ready `dist/` built from the 12-run export before 2026-12-04, or the re-forecast date | Build date of the first clean `dist/` |

## Acceptance Criteria (test scenarios)

Mandatory. Each criterion is an observable scenario the resulting code must
satisfy. If `tdd: true` in `docs/context/methodology.md`, these are the
contract the test pair authors test-first (before the Implementer). If
`tdd: false` with a declared framework, they are the contract the test pair
authors test-after (after the Implementer + Code Review). With no framework
declared, no tests are authored.

- **AC-1 Experiment description in the export:** Given the public experiment file and the 12 jobs of the first repetition, when `python -m atr.store.export <out dir> <job>... --experiment <file>` runs, then `<out dir>/experiment.json` lists every configuration (label as stored in `config`, display name, workflow, workflow version, model, the question it answers), the MVP questions with their status and answer sentence or null, the hypotheses H1 to H5, the planned repetitions (3) and the preliminary flag; it passes the leak check; and its SHA-256 is recorded in `publications.jsonl` next to the other files. Given an exported run whose `config` is not declared in the experiment file, the export fails and names the label.
- **AC-2 Pinned build without telemetry:** Given a clean checkout and an export directory, when `npm ci` and `npm run build` run in the site's folder with `ATR_EXPORT_DIR` set, then Observable Framework 1.13.4 from the lockfile writes `dist/`, and the build script itself sets `OBSERVABLE_TELEMETRY_DISABLE=1`. Given `ATR_EXPORT_DIR` unset, or an export missing one of the five files, the build fails with a message naming what is missing; no sample data is used in its place.
- **AC-3 Every attempt in the run explorer:** Given the 12-run export, the run explorer lists exactly the 12 runs of `runs.json`, including the 6 halted ones, each with configuration, task, outcome, task success, criteria satisfied, cost with its source and wall-clock time, and each row links to that run's page. The run's page shows every exported field of the run, its native outcome, tokens by type and review findings by category.
- **AC-4 Two clicks to evidence:** Given the built site, when the site check runs over `dist/`, then every aggregate value carries the identifiers of the runs it was computed from and links to a view that lists exactly those runs, each linking to its page. An aggregate without run identifiers, or a link to a missing page, fails the check.
- **AC-5 Sample size and preliminary label:** Given an export with fewer than 3 runs per configuration and task, every aggregate shows its sample size and the label "preliminary", and no interval, pass@k or pass^k is shown. Given a fixture export with 3 runs per cell, success rates show Wilson 95% intervals.
- **AC-6 Not run and not yet answered:** Given an experiment file that declares the earlier-release configuration and an export with none of its runs, the tasks × configurations grid shows "not run" in its three cells, and the question "Did a new workflow version help?" shows "not yet answered" with the reason. No configuration or question declared in the experiment file is omitted.
- **AC-7 Cost with quality, and its source:** Given any page, every cost is shown in the same view as task success or criteria satisfied for the same runs, and every quality number is shown with its cost; every cost names its source from `cost_source` (for the 12 runs, the SDK's estimate).
- **AC-8 Task success, false completion and the frontier:** Given the 12-run export, task success is `reward == 1.0`; the false completion rate is the share of `completed` runs without task success (0 of 6 for these runs); cost per successful task reads "no successful run" for a configuration with none; and the cost-versus-quality chart marks the configurations no other configuration beats on both mean cost per run and success rate (for these runs, the vanilla baseline alone).
- **AC-9 Review status:** Given a run whose review findings have `judged` equal to 0, the dashboard shows the number of findings with "not yet judged"; given `judged` greater than 0, it shows confirmed of judged findings.
- **AC-10 Private task catalog:** Given Target A's tasks, the task catalog shows the codename, task id, category and difficulty, and the target's generic description, and nothing else.
- **AC-11 Site leak check:** Given the built `dist/` and `leak-terms.txt`, when `python -m atr.store.check_site <dist dir>` runs, then it applies the private-term, secret, e-mail and absolute-path patterns to every file, and the file-name, relative-path and long-text rules to the data files and to the visible text of each page; any finding exits non-zero and names the file. Given a page or data file with a planted private term, an absolute path or an e-mail address, the check fails; given the clean 12-run build, it passes.
- **AC-12 Definitions one click away:** Given any table or chart, every metric name links to its definition on the methodology page, and the site check fails on a link to a missing anchor.
- **AC-13 Headline answers:** Given `experiment.json`, the home page lists the MVP questions in the declared order, each with its chart, its answer sentence or "analysis pending" when the sentence is null, its sample size, the preliminary label and a link to its runs.

## Open Questions

- [ ] D-034: where the site is hosted and under which domain. Needed before the deploy, by M4.
- [ ] Does the repository adopt pytest as its first test suite, and declare it in `docs/context/methodology.md` (`test_frameworks`) so relay's test pair runs? This PRD assumes pytest tests for the aggregates and the site check, recorded in `docs/context/testing.md`.
- [ ] Do the relay 0.47.0 pilots of M2 appear as context next to the empty earlier-release row (D-059 allows context, never a configuration)?
- [ ] Which Node LTS version is pinned for the build in WSL (Windows has 24.15.0; WSL has none)?
- [ ] Who are the three qualified readers of the SC-5 test, and when does it run?

---

## Users & Context

**Primary User**
- **Who:** An engineering leader or tech lead who decides which AI models and workflows a team adopts; technically fluent and short on time (D-041).
- **Current behavior:** Reads model leaderboards, vendor announcements and anecdotal posts, none of which compare workflows or show the cost of failed runs.
- **Trigger:** A new model release, a plugin or workflow the team is evaluating, or a review of the team's AI spend.
- **Success state:** In under five minutes they can say, for example, "on these backend tasks vanilla Claude Code on Sonnet met the oracle on all three tasks at about US$ 0.50 each, relay cost 5 to 36 times as much per run and halted on 6 of 9 runs — preliminary, one run per cell", and they can click through to the runs to check.

**Job to Be Done**
When I have to decide which model and workflow my team uses to deliver features with AI, I want to see measured cost, time and quality side by side with the evidence behind them, so I can make and defend the choice without running my own benchmark.

**Non-Users**
Readers looking for a single "best model" ranking across all kinds of work; teams that want a tool to benchmark their own codebases (D-039); anyone looking for Target A's code or specifications, which are never published. The operator's own analysis uses the local store, not the dashboard.

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | `experiment.json` in the export, from a public experiment file (AC-1) | The site shows only what a recorded publication carries (PUB-01) |
| Must | Observable Framework 1.13.4 pinned with its lockfile, built with `npm ci` and telemetry disabled (AC-2) | D-020; no data leaves the build machine |
| Must | Home page with the headline answers (AC-13) | PUB-05; questions first |
| Must | Cost-versus-quality chart with the Pareto frontier (AC-8) | PUB-06; the dashboard's main chart |
| Must | Tasks × configurations grid, with "not run" cells (AC-6) | The side-by-side comparison readers expect from experiment views |
| Must | Run explorer and a page per run (AC-3) | PUB-07; failures are first-class |
| Must | Task catalog, category and difficulty only for Target A (AC-10) | PUB-10; D-013 |
| Must | Methodology and glossary, every metric linked to its definition (AC-12) | PUB-08; no unexplained jargon |
| Must | Sample size and preliminary label everywhere; intervals only with 3 or more runs (AC-5) | Rigor rules 3 and 9; D-059 |
| Must | Cost always with quality and its source (AC-7) | Design principle; D-022 |
| Must | Review findings shown as "not yet judged" until the blind confirmation (AC-9) | The confirmation of the 12 runs has not started |
| Must | Site check: leak scan of `dist/` and evidence links (AC-4, AC-11) | PUB-03, PUB-09, SC-2, SC-6 |
| Should | Layout patterns of Langfuse and LangSmith: sidebar, KPI cards, dense tables (D-045) | The owner's visual reference |
| Should | Light and dark themes | Readability |
| Should | Download of the export's JSON files from the site | Readers can check the numbers themselves |
| Should | pytest tests for the aggregates and the site check | The repository's first test suite; see Open Questions |
| Could | The relay 0.47.0 pilots of M2 as context, never as a configuration | D-059; owner to decide |
| Could | A page listing past publications | Traceability of updates as repetitions are added |
| Won't | Server, online database, logins, analytics or tracking | D-025 |
| Won't | Langfuse or LangSmith, hosted or self-hosted | D-045 |
| Won't | Target A's transcripts, diffs, specifications, prompts or task titles | D-013; export allowlist |
| Won't | LLM judge, mergeability verdicts, workflow version history | Phase 2 |
| Won't | Deploy and domain | D-034 is open; a separate step once decided |

### MVP Scope

The whole dashboard above: PUB-04 to PUB-10 are all part of the frozen MVP (D-024). The minimum that tests the hypothesis is a `dist/`, built from the 12-run export, that passes the site check and carries the operator's answer sentences.

### User Flow

Home → a question's card (answer, chart, sample size, preliminary label) → a point on the chart or a cell of the grid → the list of runs behind it, or the run's own page. At most two clicks from any number to a run.

---

## Technical Approach

**Feasibility:** HIGH — the data contract exists, the first publication has 12 runs, and Observable Framework is built for static data dashboards with Python data loaders. The least certain parts are the page per run (parameterized routes with `dynamicPaths`) and a leak scan that tells the site's own text apart from vendored JavaScript.

### TDD routing

Current value of `tdd` in `docs/context/methodology.md`: **false**. Test-after ordering — when a test framework is declared, the test pair (test-writer/test-reviewer) authors and maintains the suite from the Acceptance Criteria above, after the Implementer + Code Review; with no framework declared, no tests are authored.

### Architecture Notes

- **New component.** An Observable Framework project in its own top-level folder of this repository (`dashboard/` unless the plan finds a better name), with `package.json`, `package-lock.json` and the Framework config. `node_modules/`, `dist/` and `.observablehq/cache/` are ignored by git; no export or built site is committed.
- **Input.** The build reads one export directory, named by `ATR_EXPORT_DIR`, and nothing else from `~/atr`. The site is rebuilt from the export at any time (D-033).
- **Experiment description.** A public experiment file in the repository (for example `experiments/mvp.toml`) declares the configurations with their display names, the questions, the hypotheses, the planned repetitions, the preliminary flag and the answer sentences. The exporter copies it into `experiment.json`, so the leak check and the publication record cover it.
- **Aggregates.** Python data loaders compute success rates, false completion, cost and time per successful task, the Pareto frontier and, when there are 3 or more runs per cell, Wilson intervals, at build time. Task success is `reward == 1.0` (the grader sets it only when every hidden and existing test passes).
- **Site check.** A harness module (`atr.store.check_site`) reuses the exporter's patterns and `leak-terms.txt` on `dist/`, and checks evidence links and definition anchors. It fails closed.
- **Build environment.** The build runs in WSL, where the export, the leak terms and uv live, with a pinned Node LTS version. The commands go into `docs/development.md`.
- **Runs.** A run is identified by `<job>/<trial>`. Its page path is derived from both, in a form the leak check's path patterns accept.

### Technical Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Observable Framework is in maintenance mode (one release in 2025, one in 2026) and brings about 45 direct npm dependencies (R11) | M | Exact version and lockfile, `npm ci`, telemetry off. The built site keeps working without Framework, and the export contract does not depend on it, so the generator can be replaced later |
| Readers take one run per cell as settled (R2) | H | Sample size and the preliminary label on every number, no fabricated intervals, links to the methodology; the SC-5 test checks that readers mention it |
| A leak through the site's text or generated pages (R7) | L | The site reads only the export; the site check scans `dist/`; a manual audit before any deploy |

---

## Implementation Phases

| # | Phase | Description | Status | Repo | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|------|----------|---------|----------|
| 1 | Experiment description in the export | Public experiment file; the exporter's `--experiment` option writes `experiment.json`, leak-checked and recorded in `publications.jsonl`; undeclared configurations fail the export | pending | - | - | - | - |
| 2 | Site scaffold and build | Observable Framework 1.13.4 project with lockfile, telemetry off, Python loaders reading `ATR_EXPORT_DIR`, layout and navigation, build in WSL, git ignores and development docs | pending | - | - | 1 | - |
| 3 | Runs and tasks | Run explorer, a page per run and the task catalog | pending | - | - | 2 | - |
| 4 | Answers and methodology | Home page with the headline answers, cost-versus-quality chart with the frontier, tasks × configurations grid, methodology and glossary | pending | - | - | 3 | - |
| 5 | Publication checks | `atr.store.check_site`: leak scan of `dist/`, evidence links and definition anchors; a deploy-ready `dist/` from the 12-run export | pending | - | - | 4 | - |

### Phase Details

**Phase 1: Experiment description in the export**
- **Goal:** Everything the site shows comes from a recorded, leak-checked publication.
- **Scope:** The experiment file for the MVP experiment (five configurations, the MVP questions, H1 to H5, three planned repetitions, the preliminary flag, null answer sentences); the exporter's new option; its record in `publications.jsonl`; the failure on an undeclared configuration.
- **Success signal:** An export of the 12 jobs contains `experiment.json`, passes the leak check, and its digest is in `publications.jsonl` (AC-1).

**Phase 2: Site scaffold and build**
- **Goal:** One command builds the site from an export, pinned and without telemetry.
- **Scope:** The Framework project and lockfile; the build script with `OBSERVABLE_TELEMETRY_DISABLE=1`; loaders that read `ATR_EXPORT_DIR` and fail on missing files; the sidebar, theme and page skeletons; git ignores; build instructions in `docs/development.md`.
- **Success signal:** `npm ci` and `npm run build` produce `dist/` from the 12-run export, and fail with a clear message without one (AC-2).

**Phase 3: Runs and tasks**
- **Goal:** Every attempt is visible, failures included.
- **Scope:** The run explorer, a page per run with all exported fields, tokens by type and review findings with their judgment status; the task catalog.
- **Success signal:** The explorer lists the 12 runs, each with its page; the catalog shows only allowed fields (AC-3, AC-9, AC-10).

**Phase 4: Answers and methodology**
- **Goal:** A reader answers the headline questions in under five minutes.
- **Scope:** The home page with the questions, answers or "analysis pending", sample sizes and the preliminary label; the cost-versus-quality chart with the frontier; the tasks × configurations grid with "not run" cells; the methodology and glossary with metric anchors; the rules for intervals, cost sources and quality next to cost.
- **Success signal:** AC-5 to AC-8, AC-12 and AC-13 hold on the 12-run build and on a fixture with 3 runs per cell.

**Phase 5: Publication checks**
- **Goal:** No build reaches the public without a clean leak scan and complete evidence links.
- **Scope:** `atr.store.check_site` over `dist/`; the operator's audit step in the publication instructions; a clean, deploy-ready `dist/` from the 12-run export.
- **Success signal:** The check passes on the clean build and fails on planted findings and broken links (AC-4, AC-11).

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Site generator | Observable Framework 1.13.4, pinned | A Python generator in the harness (Jinja2 and a vendored chart library); a static React application (Vite, React, Tailwind, shadcn/ui-style components, TanStack Table), closest to Langfuse's look; Evidence.dev; self-hosted Langfuse or LangSmith | The owner's choice on 2026-11-11: built for static data dashboards, with Python data loaders, Observable Plot and Inputs. Self-hosting Langfuse or LangSmith is ruled out by D-045 and D-025. Recorded as D-060 when this PRD is approved |
| Visual reference | Langfuse and LangSmith patterns: sidebar, KPI cards, dense run table, page per run, side-by-side grid | Report-style pages | D-045 names them as reference designs; the owner wants that experience |
| Source of the experiment description | A public experiment file, copied by the exporter into `experiment.json` | Data written by hand inside the site; a new table in the store | The publication record then covers everything the site shows (PUB-01), and the leak check scans it |
| Answer sentences | Written by the operator after the M3 analysis, in the experiment file; "analysis pending" until then | Sentences generated from the data | Measure, don't assert; the analysis is M3's work |
| Where aggregates are computed | Python data loaders at build time | JavaScript in the browser | Testable with pytest, the harness's language, and the data is small |
| Site check | A harness module reusing the exporter's patterns and leak terms | A JavaScript script in the site | One leak-check implementation; the leak terms live in `~/atr/data` |
| Build environment | WSL with a pinned Node LTS | Windows' Node 24 reading the export from WSL | The export, leak terms and uv live in WSL |
| Intervals and pass@k | Only with 3 or more runs per cell | Intervals from one run | Rigor rules 3 and 9; D-059 |
| Deploy and domain | Out of this PRD; it ends with a deploy-ready `dist/` | Choosing GitHub Pages or Cloudflare Pages now | D-034 is open and is the owner's decision |

---

## Research Summary

**Market Context**
- Observable Framework 1.13.4 is the latest release (npm, 2026-03-02), licensed ISC, requiring Node 18 or later; the release before it is from 2025-04-16, and 1.13.4 only upgrades dependencies, so the project is in maintenance mode (https://github.com/observablehq/framework/releases; npm registry).
- Hosting on Observable Cloud was deprecated on 2025-04-15, and the `deploy` command carries a deprecation notice; the built site goes to any static host, including GitHub Pages and Cloudflare Pages (https://observablehq.com/release-notes/2025-04-15-deprecating-observable-cloud).
- Framework collects telemetry by default; `OBSERVABLE_TELEMETRY_DISABLE` turns it off, a name taken from the project's own `package.json` test scripts, since the official telemetry page could not be fetched (https://raw.githubusercontent.com/observablehq/framework/main/package.json).
- Python data loaders print their output to stdout, are cached in `.observablehq/cache`, and fail the build when they fail (https://raw.githubusercontent.com/observablehq/framework/main/docs/data-loaders.md). Parameterized routes are generated from the `dynamicPaths` config option (https://github.com/observablehq/framework/blob/main/docs/params.md).
- Princeton's HAL leaderboard marks Pareto-optimal entries on an accuracy-versus-cost chart, shows a runs column and draws error bars only where repeated runs exist — the closest public example to a one-run-per-cell publication (https://hal.cs.princeton.edu/swebench_verified_mini).
- Langfuse's web application is built with Next.js, React, Tailwind, Radix components and TanStack Table (its `web/package.json`); these were weighed as an alternative for a Langfuse-like look and not chosen.

**Technical Context**
- The export's fields per file, the token sums and `review_by_category` with `findings`, `confirmed` and `judged` per category (`harness/src/atr/store/export.py:36-49`, `harness/src/atr/store/export.py:71-124`).
- `publication.json` holds only the date, allowlist version, jobs and runs; file digests go to `publications.jsonl` (`harness/src/atr/store/export.py:171-190`).
- The leak check's patterns and the 64-character limit for private runs (`harness/src/atr/store/export.py:51-58`, `harness/src/atr/store/export.py:125-142`).
- Outcomes and cost sources set by the loader, including `halted` with the native reason and `cost_source` `sdk` for API runs (`harness/src/atr/store/load.py:368-418`).
- Task success is `reward == 1.0`, set only when every hidden and existing test passes (`harness/src/atr/tasks/grade.py:16`, `harness/src/atr/tasks/grade.py:201`).
- The stored configuration labels of the 12 runs are `relay049-sonnet`, `relay049-haiku`, `relay049-opus` and `vanilla-sonnet`; the earlier release is planned as `relay047-sonnet`.
- Metric definitions, rigor rules and known limitations (`documentation/product/04-measurement.md`, sections 2 to 9); the questions (`documentation/product/01-vision-and-scope.md`, section 8); the glossary (`documentation/product/02-concepts.md`).
- The repository has no test suite and no Node tooling (`docs/context/testing.md`); Node 24.15.0 is installed on Windows and none in WSL.

---

*Generated: 2026-11-11*
*Approved: 2026-11-11*
*Status: APPROVED*
