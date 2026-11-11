# Runs

Every attempt is listed here, halted runs included. Each row opens the run's own page.

```js
const runs = FileAttachment("data/runs.json").json();
const experiment = FileAttachment("data/experiment.json").json();
```

```js
import {runRows} from "./components/runs.js";
const rows = runRows(runs, experiment);
```

```js
import {filterRuns} from "./components/answers.js";
const params = new URLSearchParams(location.search);
const query = {config: params.get("config"), task: params.get("task"), ids: params.get("ids")};
const filtered = filterRuns(rows, query);
const filtering = Boolean(query.config || query.task || query.ids);
```

${filtering ? htl.html`Showing ${filtered.length} of ${rows.length} runs for this selection. <a href="./runs">Show every run</a>.` : `${rows.length} runs are listed.`} ${experiment.preliminary ? "These results are preliminary." : ""}

```js
const found = view(Inputs.search(filtered));
```

```js
Inputs.table(found, {
  columns: ["run", "configuration", "task", "outcome", "success", "criteria", "cost", "costSource", "time"],
  header: {
    run: "Run",
    configuration: "Configuration",
    task: "Task",
    outcome: "Outcome",
    success: "Task success",
    criteria: "Criteria satisfied",
    cost: "Cost",
    costSource: "Cost source",
    time: "Wall-clock time"
  },
  format: {
    run: (value, index, data) => htl.html`<a href="./run/${data[index].slug}">${value}</a>`
  },
  select: false,
  rows: Math.max(25, rows.length)
})
```
