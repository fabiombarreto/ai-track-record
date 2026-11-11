# Tasks

The catalog lists each task by codename, id, category and difficulty with the target's generic description. Private targets appear under a codename only.

```js
const tasks = FileAttachment("data/tasks.json").json();
const targets = FileAttachment("data/targets.json").json();
```

```js
import {taskCatalog} from "./components/runs.js";
const catalog = taskCatalog(tasks, targets);
```

```js
Inputs.table(catalog, {
  columns: ["codename", "task_id", "category", "difficulty", "description"],
  header: {
    codename: "Codename",
    task_id: "Task id",
    category: "Category",
    difficulty: "Difficulty",
    description: "Description"
  },
  select: false,
  rows: Math.max(25, catalog.length)
})
```
