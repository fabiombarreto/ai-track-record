// Pure rules for the home, grid and methodology pages, shared by the pages (browser) and Node.
// Task success is a reward of exactly 1.0 (the runs module's single rule); a missing cost is never
// zero and never a partial mean (D-022); an interval appears only when every cell of a group has
// enough runs (D-020); a run of an undeclared configuration fails the build instead of vanishing.
// One import, from the runs module; no file or network access.

import {isSuccess, runSlug} from "./runs.js";

export const METRICS = {
  "task-success": {name: "Task success"},
  "success-rate": {name: "Success rate"},
  "false-completion": {name: "False completion"},
  "criteria-satisfied": {name: "Criteria satisfied"},
  "cost-per-run": {name: "Cost per run"},
  "cost-per-successful-task": {name: "Cost per successful task"},
  "cost-source": {name: "Cost source"},
  "wall-clock-time": {name: "Wall-clock time"},
  "outcome": {name: "Outcome"},
  "review-status": {name: "Review status"},
  "sample-size": {name: "Sample size"},
  "preliminary": {name: "Preliminary"},
  "wilson-interval": {name: "Wilson interval"},
  "pareto-frontier": {name: "Pareto frontier"}
};

export function wilson(successes, n) {
  if (!n) return null;
  const z = 1.96;
  const p = successes / n;
  const centre = p + (z * z) / (2 * n);
  const spread = z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));
  const scale = 1 + (z * z) / n;
  return {low: (centre - spread) / scale, high: (centre + spread) / scale};
}

function hasCost(run) {
  const cost = run?.cost_usd;
  return cost !== null && cost !== undefined && Number.isFinite(Number(cost));
}

const money = (value) => `US$ ${Number(value).toFixed(2)}`;

function distinctSources(runs) {
  const seen = [];
  for (const run of runs) {
    const source = run.cost_source;
    if (source !== null && source !== undefined && !seen.includes(source)) seen.push(source);
  }
  return seen;
}

function declaredConfigurations(experiment) {
  return experiment?.configurations ?? [];
}

export function configStats(runs, experiment, minRuns = 3) {
  const configs = declaredConfigurations(experiment);
  for (const run of runs) {
    if (!configs.some((c) => c.label === run.config)) {
      throw new Error(`run config ${JSON.stringify(run.config)} is not declared in the experiment`);
    }
  }
  return configs.map((config) => {
    const own = runs.filter((run) => run.config === config.label);
    const n = own.length;
    let successes = 0;
    let completed = 0;
    let falseCompletions = 0;
    let totalCost = 0;
    let allCosted = true;
    const perTask = new Map();
    for (const run of own) {
      const ok = isSuccess(run);
      if (ok) successes += 1;
      if (run.outcome === "completed") {
        completed += 1;
        if (!ok) falseCompletions += 1;
      }
      if (hasCost(run)) totalCost += Number(run.cost_usd);
      else allCosted = false;
      perTask.set(run.task_id, (perTask.get(run.task_id) ?? 0) + 1);
    }
    let cellMin = 0;
    for (const count of perTask.values()) {
      if (cellMin === 0 || count < cellMin) cellMin = count;
    }
    let costPerSuccessText;
    if (successes === 0) costPerSuccessText = "no successful run";
    else if (!allCosted) costPerSuccessText = "no cost recorded";
    else costPerSuccessText = money(totalCost / successes);
    const planned = Number(experiment?.planned_repetitions);
    return {
      label: config.label,
      name: config.name,
      question: config.question,
      n,
      successes,
      successRate: n === 0 ? null : successes / n,
      meanCost: n === 0 || !allCosted ? null : totalCost / n,
      totalCost,
      costPerSuccessText,
      completed,
      falseCompletions,
      falseCompletionText: `${falseCompletions} of ${completed} completed runs`,
      cellMin,
      interval: cellMin >= minRuns ? wilson(successes, n) : null,
      costSources: distinctSources(own),
      slugs: own.map((run) => runSlug(run)),
      preliminary: experiment?.preliminary === true || (Number.isFinite(planned) && cellMin < planned)
    };
  });
}

export function paretoLabels(stats) {
  const eligible = stats.filter((s) => s.n > 0 && s.meanCost !== null);
  const labels = [];
  for (const s of eligible) {
    let beaten = false;
    for (const o of eligible) {
      if (o === s) continue;
      const noWorse = o.meanCost <= s.meanCost && o.successRate >= s.successRate;
      const better = o.meanCost < s.meanCost || o.successRate > s.successRate;
      if (noWorse && better) {
        beaten = true;
        break;
      }
    }
    if (!beaten) labels.push(s.label);
  }
  return labels;
}

export function gridCells(runs, tasks, experiment, minRuns = 3) {
  const configurations = declaredConfigurations(experiment);
  const cells = [];
  for (const task of tasks) {
    for (const config of configurations) {
      const own = runs.filter((run) => run.task_id === task.task_id && run.config === config.label);
      const n = own.length;
      let successes = 0;
      let total = 0;
      let allCosted = true;
      for (const run of own) {
        if (isSuccess(run)) successes += 1;
        if (hasCost(run)) total += Number(run.cost_usd);
        else allCosted = false;
      }
      const costText = n > 0 && allCosted ? `mean cost ${money(total / n)}` : "no cost recorded";
      const planned = Number(experiment?.planned_repetitions);
      cells.push({
        task: task.task_id,
        label: config.label,
        n,
        slugs: own.map((run) => runSlug(run)),
        text: n === 0 ? "not run" : `${successes} of ${n} succeeded, ${costText}`,
        interval: n >= minRuns ? wilson(successes, n) : null,
        costSources: distinctSources(own),
        preliminary: n > 0 && (experiment?.preliminary === true || (Number.isFinite(planned) && n < planned))
      });
    }
  }
  return {tasks, configurations, cells};
}

export function questionCards(runs, experiment) {
  const stats = configStats(runs, experiment);
  return (experiment?.questions ?? []).map((q) => {
    const declared = stats.filter((s) => s.question === q.id);
    const scope = declared.length > 0 ? declared : stats;
    let n = 0;
    let preliminary = experiment?.preliminary === true;
    const slugs = [];
    for (const s of scope) {
      n += s.n;
      if (s.preliminary) preliminary = true;
      for (const slug of s.slugs) slugs.push(slug);
    }
    return {
      id: q.id,
      text: q.text,
      answerText: q.answer === null || q.answer === undefined ? "analysis pending" : q.answer,
      statusText: q.status === "not_yet_answered" ? `not yet answered: ${q.reason}` : "answered",
      scope,
      n,
      sampleText: `n = ${n} ${n === 1 ? "run" : "runs"}`,
      preliminary,
      slugs
    };
  });
}

export function filterRuns(rows, query) {
  const ids = query?.ids ? String(query.ids).split(",").map((s) => s.trim()).filter(Boolean) : null;
  return rows.filter((row) => {
    if (query?.config && row.label !== query.config) return false;
    if (query?.task && row.task !== query.task) return false;
    if (ids && !ids.includes(row.slug)) return false;
    return true;
  });
}
