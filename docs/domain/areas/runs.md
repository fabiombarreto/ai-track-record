# Runs

## Primary responsibility

Execute one configuration on one task, unattended, with the same harness and limits for every configuration, and record everything the run did. Code: `atr.agents.claude_sdk`, `atr.agents.claude_sdk_runner`, the batch launcher in the private workspace.

## Entities

Job, trial (run), configuration (`config_label`), model, workflow and workflow version, agent kwargs, outcome, telemetry events and metrics.

## Rules

- Claude Code through the Agent SDK is the only harness (D-017, D-049). The SDK version is pinned (0.2.170).
- The runner sets Claude Code's system prompt preset, loads the project's settings (`setting_sources = ["project"]`, which also loads `CLAUDE.md`) and runs with `bypassPermissions`.
- Every model alias and every sub-agent is forced onto the model under test (`CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, CFG-04).
- The runner stops with an error if the installed SDK does not support a requested option; it never drops one.
- On Target A, web tools are disabled and the network is allowlisted to the model API, the Collector and the package index (D-050).
- Every MVP run has a three-hour limit, a US$ 60 cost cap and web tools disabled; runs go one at a time.
- relay is mounted read-only from a copy of its exact commit; the run records the plugin version and digest (D-054).
- Outcomes are normalized (D-019). A relay HALT ends as a successful SDK result, and the store turns it into `halted` from relay's own orchestrator record.
- A run that fails before its agent makes any API call is an infrastructure error and is set aside and run again, up to three attempts. A run interrupted after its agent started is also run again from the start, and the attempt is recorded with its cost.
- Telemetry carries the job, trial and configuration as resource attributes; each run gets a fixed session id.
- The runner records its own wall time (`atr_wall_ms`) and summed turns, because a session with background sub-agents emits several result messages.

## Relationships

Feeds grading (the trial folder and `changes.patch`), review, budget (`agent/result.json` cost) and the store. Local inference will add a second route for the model (local models plan).

## Main flow

Job config → Harbor starts the task container → agent installs uv and the SDK → runner runs Claude Code with the instruction → result and messages written to `/logs/agent` → Harbor's verifier grades.

## Open Questions

- The store maps the SDK subtype `error_max_turns` to `budget_exceeded`, while D-019 lists the turn limit under `timed_out` [INFERRED - VALIDATE]. Which one is intended?
- How the route option for local models records its settings (`agent/route.json`) is designed in the local models plan but not built yet.
