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
- Outcomes are normalized (D-019). A relay HALT ends as a successful SDK result, and the store turns it into `halted` from relay's own orchestrator record: the outcome in `orchestrator-run.json`, or the one in `orchestrator-halt.json` when relay 0.49.0 leaves the first empty or writes no run record.
- A run that fails before its agent makes any API call is an infrastructure error and is set aside and run again, up to three attempts. A run interrupted after its agent started is also run again from the start, and the attempt is recorded with its cost.
- The agent's `route` option is `"anthropic"` (default, unchanged behavior) or `"local"`. The local route takes a `model_name` of `local/<alias>`, `local_base_url` (default `http://host.docker.internal:8090`) and `local_timeout_ms` (default 10800000), and has no `max_budget_usd`.
- On the local route the agent reads `server.json` and `server.key` and fails the trial if either is missing, if the model is not the server's alias, or if the base URL's port differs from the record's. The container gets no `ANTHROPIC_API_KEY`; every model alias and the sub-agents are the local alias; context and compaction use the server's context; the attribution header and experimental betas are off.
- Before the runner starts on the local route, a pre-flight check from inside the container fails the trial, naming the cause, if the container has `ANTHROPIC_API_KEY`, the server does not answer, rejects the key, answers another status, or does not list the model. The key travels in the exec environment only.
- Telemetry carries the job, trial and configuration as resource attributes; each run gets a fixed session id.
- The runner records its own wall time (`atr_wall_ms`) and summed turns, because a session with background sub-agents emits several result messages.

## Relationships

Feeds grading (the trial folder and `changes.patch`), review, budget (`agent/result.json` cost) and the store. Local inference is the second route for the model (the `route` option; see local-inference).

## Main flow

Job config → Harbor starts the task container → agent installs uv and the SDK → runner runs Claude Code with the instruction → result and messages written to `/logs/agent` → Harbor's verifier grades.

## Open Questions

- The store maps the SDK subtype `error_max_turns` to `budget_exceeded`, while D-019 lists the turn limit under `timed_out` [INFERRED - VALIDATE]. Which one is intended?
- `agent/route.json` is written for every run: `{provider, model}` on the Anthropic route, and on the local route the server's identity, quantization, flags, sampling, thinking setting, context and the route's variables with the token as `<set>`; it is not written if the key would appear in it. Whether the store and export read it is not built yet.
- The first local check run (L-Small, synthetic task) failed at the server's chat template, which rejects a late system message; Phase 6 fixed it for L-Small with a template override (see local-inference and `documentation/research/local-route.md`).
- On the local route `agent/route.json` also holds a `network` record of a bare-curl probe of `api.anthropic.com` and `pypi.org`; a probe failure never fails the run.
- On the local route the turn limit ends as outcome `error` with `NonZeroAgentExitCodeError` (the SDK raises `error_max_turns` and writes no `agent/result.json`), not `budget_exceeded`; the time limit ends as `timed_out` as in the MVP. The skipped-step check cannot see a workflow that never started.
