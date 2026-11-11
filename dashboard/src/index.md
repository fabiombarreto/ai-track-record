# AI Track Record

AI Track Record runs the same specification-to-pull-request task under different models and workflows, grades every run with checks the agent never sees, and shows cost next to quality. Each question below links to the runs behind its numbers.

```js
const runs = FileAttachment("data/runs.json").json();
const tasks = FileAttachment("data/tasks.json").json();
const experiment = FileAttachment("data/experiment.json").json();
```

```js
import {configStats, questionCards, paretoLabels} from "./components/answers.js";
const stats = configStats(runs, experiment);
const cards = questionCards(runs, experiment);
const frontier = paretoLabels(stats);
const pct = (v) => `${(v * 100).toFixed(0)}%`;
const usd = (v) => `US$ ${Number(v).toFixed(2)}`;
const plotted = stats.filter((s) => s.n > 0 && s.meanCost !== null);
const notShown = stats
  .filter((s) => !(s.n > 0 && s.meanCost !== null))
  .map((s) => `${s.name} (${s.n === 0 ? "no runs" : "no cost recorded for every run"})`);
const interval = (s) => (s.interval ? ` (95% interval ${pct(s.interval.low)} to ${pct(s.interval.high)})` : "");
```

${experiment.preliminary ? `These results are preliminary: ${runs.length} runs so far, against ${experiment.planned_repetitions} planned repetitions per cell.` : ""}

## Questions

```js
display(html`${cards.map((card) => {
  const shown = card.scope.filter((s) => s.n > 0 && s.meanCost !== null);
  const link = card.slugs.length
    ? html`<a href="./runs?ids=${card.slugs.map(encodeURIComponent).join(",")}">See the ${card.n} runs behind this answer</a>`
    : html`<a href="./grid">No runs yet: see the grid</a>`;
  return html`<div class="card" data-runs="${card.slugs.join(",")}">
    <h3>${card.id}: ${card.text}</h3>
    <p>${card.answerText}</p>
    <p>${card.statusText}. ${card.sampleText}. ${card.preliminary ? "preliminary" : ""}</p>
    <p>${link}</p>
    ${shown.length ? Plot.plot({
      height: 220,
      marginRight: 90,
      x: {label: "Mean cost per run (US$)"},
      y: {label: "Success rate", domain: [0, 1]},
      marks: [
        Plot.dot(shown, {x: "meanCost", y: "successRate", fill: "steelblue", r: 5}),
        Plot.text(shown, {x: "meanCost", y: "successRate", text: "name", dx: 8, textAnchor: "start"})
      ]
    }) : html`<p>No configuration in this question has runs with a recorded cost yet.</p>`}
    <table>
      <thead><tr><th>Configuration</th><th>Sample size</th><th>Success rate</th><th>False completion</th><th>Mean cost per run</th><th>Cost source</th><th>Cost per successful task</th></tr></thead>
      <tbody>${card.scope.map((s) => html`<tr data-runs="${s.slugs.join(",")}">
        <td>${s.n ? html`<a href="./runs?config=${encodeURIComponent(s.label)}">${s.name}</a>` : s.name}</td>
        <td>${s.n === 0 ? "not run" : `n = ${s.n}`}${s.preliminary ? ", preliminary" : ""}</td>
        <td>${s.successRate === null ? "not run" : pct(s.successRate) + interval(s)}</td>
        <td>${s.n === 0 ? "not run" : s.falseCompletionText}</td>
        <td>${s.meanCost === null ? (s.n === 0 ? "not run" : "no cost recorded") : usd(s.meanCost)}</td>
        <td>${s.costSources.length ? s.costSources.join(", ") : "n/a"}</td>
        <td>${s.n === 0 ? "not run" : s.costPerSuccessText}</td>
      </tr>`)}</tbody>
    </table>
  </div>`;
})}`);
```

## Cost versus quality

Every configuration with a recorded cost sits on one chart. The configurations on the frontier are drawn in orange and joined by a step line.

```js
const onFrontier = plotted.filter((s) => frontier.includes(s.label)).sort((a, b) => a.meanCost - b.meanCost);
display(Plot.plot({
  height: 360,
  marginRight: 120,
  x: {label: "Mean cost per run (US$)"},
  y: {label: "Success rate", domain: [0, 1]},
  color: {domain: ["on the frontier", "beaten"], range: ["orange", "steelblue"], legend: true},
  marks: [
    Plot.line(onFrontier, {x: "meanCost", y: "successRate", curve: "step-after", stroke: "orange"}),
    Plot.dot(plotted, {
      x: "meanCost",
      y: "successRate",
      r: 6,
      fill: (s) => (frontier.includes(s.label) ? "on the frontier" : "beaten"),
      tip: true,
      title: (s) => `${s.name}\nn = ${s.n}\nsuccess rate ${pct(s.successRate)}\nmean cost ${usd(s.meanCost)}`
    }),
    Plot.text(plotted, {x: "meanCost", y: "successRate", text: "name", dx: 9, textAnchor: "start"})
  ]
}));
```

${notShown.length ? `not shown: ${notShown.join("; ")}.` : ""}

Metrics used here: [cost per run](./methodology#cost-per-run), [success rate](./methodology#success-rate), [Pareto frontier](./methodology#pareto-frontier), [false completion](./methodology#false-completion), [cost per successful task](./methodology#cost-per-successful-task), [cost source](./methodology#cost-source), [sample size](./methodology#sample-size), [preliminary](./methodology#preliminary) and [Wilson interval](./methodology#wilson-interval).
