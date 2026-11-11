# Methodology

This page explains what AI Track Record measures, how runs are graded and how to read every number on the site. Each metric below has its own anchor, and every table and chart on the site links its metric names here.

## What is measured

Each run gives an AI coding agent the same task: turn a specification into a pull request. The same task is run under different models and workflows. Every run is then graded by checks that the agent never sees: a hidden oracle written from the specification, the target's existing tests, static analysis of the change and a pinned independent review. The workflow that produced the change never grades itself, and steps it skipped are flagged, never scored.

## Questions and hypotheses

The experiment declares five questions. Is a workflow worth it? Did a new workflow version help? How much does the model tier matter? How often do agents claim false success? What does a working feature cost? A question stays marked "not yet answered" until the analysis is written, and the home page then shows "analysis pending" instead of an answer.

The experiment also states hypotheses in advance: that the newer release of the workflow no longer halts on the smaller model, that the workflow costs many times as much as the baseline for the same result, that the newer release records fewer deviations from its protocol, that the larger model does not improve on the reference model, and that the quality graders differ less between configurations than cost and time do.

## Rigor rules

- One run per cell is preliminary. Every aggregate shows its sample size and the label "preliminary" until every cell has the planned number of runs.
- An interval is shown only when every task cell of a group has at least 3 runs. Below that, the sample size stands alone.
- No pass@k or pass^k is computed from a single run.
- A cost is always shown next to its quality, and always with its source.
- A configuration or question declared in the experiment is never omitted: a configuration with no runs shows "not run".

## Known limits

- A small task set supports decisions about the tasks measured. It does not prove general superiority.
- Oracles check what was specified. Qualities the specification does not state are covered only by review and static analysis.
- Durations depend on the environment, so they are compared only within an experiment.
- A review model may favor output from its own family, so it is fixed across an experiment.
- Workflows are tuned for some models, so results with other models measure workflow portability, not model capability.

## Glossary

<h3 id="task-success">Task success</h3>

A run succeeds only when its reward is exactly 1.0. The reward is awarded only when every hidden test and every existing test passes.

<h3 id="success-rate">Success rate</h3>

The share of runs that reached task success, over the runs in the group shown. It is always shown with its sample size.

<h3 id="false-completion">False completion</h3>

The share of completed runs without task success: the agent said it was done and the checks disagree. It is counted over completed runs only, so a halted run is not a false completion.

<h3 id="criteria-satisfied">Criteria satisfied</h3>

The share of the specification's acceptance criteria that the hidden checks confirm. It gives partial credit where task success is all or nothing.

<h3 id="cost-per-run">Cost per run</h3>

The mean cost of the runs in the group, in US dollars. When any run in the group lacks a recorded cost, no mean is shown. A missing cost is never treated as zero.

<h3 id="cost-per-successful-task">Cost per successful task</h3>

The total cost of all runs in the group, failed ones included, divided by the number of successful runs. A group with no successful run reads "no successful run".

<h3 id="cost-source">Cost source</h3>

Where a cost figure comes from, for example the agent's own report. Every published cost names its source, because sources are not equally exact.

<h3 id="wall-clock-time">Wall-clock time</h3>

The elapsed time of a run from start to end. It depends on hardware and provider latency, so compare it only within one experiment.

<h3 id="outcome">Outcome</h3>

How the run ended: completed, halted or another normalized reason. The native reason reported by the tool is kept beside the normalized one on each run's page.

<h3 id="review-status">Review status</h3>

The state of the independent review of a run: how many findings it raised and how many were confirmed when judged. A run with findings not yet judged says so.

<h3 id="sample-size">Sample size</h3>

The number of runs behind a number. Small samples are noisy, so the size is stated beside every aggregate.

<h3 id="preliminary">Preliminary</h3>

A result is preliminary while the experiment is marked so, or while a cell has fewer runs than planned. Preliminary numbers describe what was measured, not a settled ranking.

<h3 id="wilson-interval">Wilson interval</h3>

A 95 percent confidence interval for a success rate, shown only when every task cell of the group has at least 3 runs. A wide interval means the sample cannot separate the configurations.

<h3 id="pareto-frontier">Pareto frontier</h3>

The configurations that no other configuration beats on both mean cost per run and success rate. A configuration is beaten when another costs no more and succeeds at least as often, and is strictly better on one of the two.
