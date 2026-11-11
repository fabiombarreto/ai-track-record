# Run

This page shows everything the export carries about one run. Back to [all runs](../runs).

```js
const runs = FileAttachment("../data/runs.json").json();
const experiment = FileAttachment("../data/experiment.json").json();
```

```js
import {runSlug, isSuccess, formatCost, formatDuration, reviewStatus, configName, runFields, tokenRows, reviewRows} from "../components/runs.js";
const run = runs.find((r) => runSlug(r) === observable.params.run);
if (!run) throw new Error(`no run matches the page parameter ${observable.params.run}`);
const reviews = reviewRows(run);
```

**Configuration:** ${configName(experiment, run.config)} (${run.config}). **Task:** ${run.task_id}. **Outcome:** ${run.outcome} (native: ${run.native_outcome ?? "n/a"}). **Task success:** ${isSuccess(run) ? "yes" : "no"}. **Criteria satisfied:** ${run.criteria_satisfied ?? "n/a"}. **Cost:** ${formatCost(run)} (source: ${run.cost_source ?? "n/a"}). **Wall-clock time:** ${formatDuration(run.wall_ms)}.

## Tokens by type

```js
Inputs.table(tokenRows(run).map(([type, value]) => ({type, value})), {header: {type: "Type", value: "Tokens"}, select: false})
```

## Review findings

Overall: ${reviewStatus(run)}.

```js
reviews.length
  ? Inputs.table(reviews, {
      columns: ["category", "findings", "confirmed", "judged", "status"],
      header: {category: "Category", findings: "Findings", confirmed: "Confirmed", judged: "Judged", status: "Status"},
      select: false
    })
  : html`<p>No review recorded for this run.</p>`
```

## All exported fields

```js
Inputs.table(runFields(run).map(([field, value]) => ({field, value})), {header: {field: "Field", value: "Value"}, select: false, rows: 60})
```
