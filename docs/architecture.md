# Architecture for developers

A short, workflow-focused companion to docs/context/architecture.md, which has the full stack and folder map.

## The pieces you touch

| You want to | Change | Then check |
|---|---|---|
| Change how a run starts or what it records | `harness/src/atr/agents/claude_sdk.py` (host side) or `claude_sdk_runner.py` (inside the container) | A run on the synthetic task |
| Change how runs are graded | `harness/src/atr/tasks/grade.py` (copied into every built task) | Rebuild the task, then `harbor job regrade` |
| Change what tasks contain | `harness/src/atr/tasks/build.py` and the target's templates | Build the task and run the oracle and nop agents |
| Change the review | `harness/src/atr/review/` | Review one graded trial |
| Change what the store holds | `harness/src/atr/store/load.py` | Rebuild the store and query it |
| Change what is published | `harness/src/atr/store/export.py` | Export the pilots; the leak check must pass, and must block with an extra private term |
| Add a local model | `infra/local-inference/models.toml` | `atr.local.fetch`, `atr.local.serve start`, `atr.local.bench` |

## Two sides of a run

- **Host side** (WSL, the operator's shell): Harbor, the agent class, the grader's builder, the review launcher, the store, the exporter, the local inference scripts.
- **Container side**: the runner and the SDK in the task container; `grade.py` in the verifier; `reviewer.py` in the reviewer image. Container-side scripts use the standard library only.

## Where results go

Each run is a trial folder under `~/atr/data/jobs/<job>/<trial>/`: `agent/` (runner output, workflow record), `verifier/` (rewards, patch), `review/`, `checks/`. Everything downstream reads those folders.
