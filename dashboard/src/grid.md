# Grid

Every task against every configuration declared in the experiment. A cell reads "not run" when that configuration has no runs on the task, and each cell opens exactly the runs behind it.

```js
const runs = FileAttachment("data/runs.json").json();
const tasks = FileAttachment("data/tasks.json").json();
const experiment = FileAttachment("data/experiment.json").json();
```

```js
import {gridCells} from "./components/answers.js";
const grid = gridCells(runs, tasks, experiment);
const pct = (v) => `${(v * 100).toFixed(0)}%`;
const cellAt = (task, label) => grid.cells.find((c) => c.task === task && c.label === label);
```

```js
htl.html`<table>
  <thead><tr>
    <th>Task</th>
    ${grid.configurations.map((c) => htl.html`<th>${c.name}</th>`)}
  </tr></thead>
  <tbody>
    ${grid.tasks.map((t) => htl.html`<tr>
      <th>${t.task_id}</th>
      ${grid.configurations.map((c) => {
        const cell = cellAt(t.task_id, c.label);
        if (cell.n === 0) return htl.html`<td data-runs="">${cell.text}</td>`;
        return htl.html`<td data-runs="${cell.slugs.join(",")}">
          <a href="./runs?config=${encodeURIComponent(cell.label)}&task=${encodeURIComponent(cell.task)}">${cell.text}</a>
          <div>Cost source: ${cell.costSources.length ? cell.costSources.join(", ") : "n/a"}</div>
          <div>Sample size: n = ${cell.n}</div>
          ${cell.interval ? htl.html`<div>95% interval: ${pct(cell.interval.low)} to ${pct(cell.interval.high)}</div>` : ""}
          ${cell.preliminary ? htl.html`<div>preliminary</div>` : ""}
        </td>`;
      })}
    </tr>`)}
  </tbody>
</table>`
```

Metrics used here: [success rate](./methodology#success-rate), [cost per run](./methodology#cost-per-run), [cost source](./methodology#cost-source), [sample size](./methodology#sample-size), [preliminary](./methodology#preliminary) and [Wilson interval](./methodology#wilson-interval).
