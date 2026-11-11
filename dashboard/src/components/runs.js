// Pure rules for the runs and tasks pages, shared by the Framework config (Node) and the pages
// (browser). Outcomes keep the native reason beside the normalized one (D-019); every cost is
// shown with its source and a missing cost is never zero (D-022); the catalog copies five task
// fields only (D-013). No imports, no file or network access.

export function runSlug(run) {
  const job = run?.job;
  const trial = run?.trial;
  if (!job || !trial) {
    throw new Error(`run without job or trial: ${JSON.stringify({job: job ?? null, trial: trial ?? null})}`);
  }
  return `${job}--${trial}`.replace(/[^A-Za-z0-9_-]/g, "-");
}

export function runSlugs(runs) {
  const seen = new Set();
  return runs.map((run) => {
    const slug = runSlug(run);
    if (seen.has(slug)) throw new Error(`two runs share the page path ${slug}`);
    seen.add(slug);
    return slug;
  });
}

export function isSuccess(run) {
  return Number(run?.reward) === 1 && run.reward !== null;
}

export function formatCost(run) {
  const cost = run?.cost_usd;
  if (cost === null || cost === undefined || !Number.isFinite(Number(cost))) return "no cost recorded";
  return `US$ ${Number(cost).toFixed(2)}`;
}

export function formatDuration(ms) {
  if (ms === null || ms === undefined || !Number.isFinite(Number(ms))) return "n/a";
  const total = Math.round(Number(ms) / 1000);
  const minutes = Math.floor(total / 60);
  const seconds = String(total % 60).padStart(2, "0");
  return `${minutes}m ${seconds}s`;
}

function status(findings, confirmed, judged) {
  return judged > 0
    ? `${confirmed} of ${judged} judged findings confirmed`
    : `${findings} findings, not yet judged`;
}

export function reviewStatus(run) {
  const categories = Object.values(run?.review_by_category ?? {});
  if (categories.length === 0) return "no review recorded";
  let findings = 0;
  let confirmed = 0;
  let judged = 0;
  for (const c of categories) {
    findings += Number(c.findings) || 0;
    confirmed += Number(c.confirmed) || 0;
    judged += Number(c.judged) || 0;
  }
  return status(findings, confirmed, judged);
}

export function configName(experiment, label) {
  const found = (experiment?.configurations ?? []).find((c) => c.label === label);
  if (!found) throw new Error(`run config ${JSON.stringify(label)} is not declared in the experiment`);
  return found.name;
}

const orNa = (value) => (value === null || value === undefined ? "n/a" : value);

export function runRows(runs, experiment) {
  return runs.map((run) => ({
    slug: runSlug(run),
    run: run.trial,
    configuration: configName(experiment, run.config),
    label: run.config,
    task: run.task_id,
    outcome: run.outcome,
    success: isSuccess(run) ? "yes" : "no",
    criteria: orNa(run.criteria_satisfied),
    cost: formatCost(run),
    costSource: orNa(run.cost_source),
    time: formatDuration(run.wall_ms)
  }));
}

export function runFields(run) {
  return Object.keys(run).map((key) => {
    const value = run[key];
    let text;
    if (value === null || value === undefined) text = "n/a";
    else if (typeof value === "object") text = JSON.stringify(value);
    else text = String(value);
    return [key, text];
  });
}

export function tokenRows(run) {
  return [
    ["Input tokens", orNa(run.input_tokens)],
    ["Output tokens", orNa(run.output_tokens)],
    ["Cache read tokens", orNa(run.cache_read_tokens)],
    ["Cache creation tokens", orNa(run.cache_creation_tokens)]
  ];
}

export function reviewRows(run) {
  return Object.entries(run?.review_by_category ?? {}).map(([category, c]) => ({
    category,
    findings: c.findings,
    confirmed: c.confirmed,
    judged: c.judged,
    status: status(Number(c.findings) || 0, Number(c.confirmed) || 0, Number(c.judged) || 0)
  }));
}

export function taskCatalog(tasks, targets) {
  return tasks.map((task) => {
    const target = targets.find((t) => t.codename === task.codename);
    if (!target) throw new Error(`task ${task.task_id} has no target for codename ${task.codename}`);
    return {
      codename: task.codename,
      task_id: task.task_id,
      category: task.category,
      difficulty: task.difficulty,
      description: target.target_description
    };
  });
}
