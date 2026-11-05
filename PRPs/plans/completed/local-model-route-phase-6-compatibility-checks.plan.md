# Feature: Compatibility checks (Phase 6 of local-model-route)

```
**Decision Gate**
- Active context: none
- Activated criteria: business rules for local inference, runs, grading, review and budget (docs/domain/areas/local-inference.md, runs.md, grading.md, review.md, budget.md); change of components (the server's chat template in infra/local-inference/, atr.local.serve, atr.agents.claude_sdk, atr.store.load); check runs that feed a research report; runs that call Anthropic's API (the independent review)
- Decisions found:
  - Synthetic task first (D-046): every run of this phase is on the public synthetic task, behind its local allowlist variant
  - Target A on local open-weight models only (D-057); the runs send nothing to Anthropic's API; only the independent review does, on the synthetic runs, approved by the operator in chat on 2026-11-04 for up to three runs
  - Graders sit outside the workflow and stay unchanged; the reviewer is Claude Code's `/code-review` at effort high on Sonnet 5.5 (D-015, D-018)
  - Pin everything (D-020): a chat-template override is a pinned file with its SHA-256 checked at every start, never an untracked edit
  - Normalized outcomes (D-019); the MVP keeps priority over the machine (D-058): the launcher refuses while any other Harbor job runs
  - Reviews of local runs are counted with this experiment, not against the MVP's ceiling (D-028; documentation/plans/local-models.md, section 11.2)
- Applicable anti-patterns:
  - Private-target material in the repository (the report holds counts, rates and outcomes of synthetic runs, no transcript text)
  - Running two benchmark runs at the same time (every run goes through `atr.local.launch`, one at a time)
  - Silently dropping a configuration option (a template whose digest differs from models.toml stops the start)
  - Weakening a check to make it pass (a failed check is recorded with its fallback, never reworded into a pass)
- Applicable architectural rules:
  - Configuration, not code (D-005): the template override and its digest live in models.toml and infra/local-inference/templates/
  - Run folders are the system of record (D-033); the report summarizes them
  - Fail closed on checks that guard correctness or privacy
- Result: PROCEED
```

## Source

- `PRPs/prds/local-model-route.prd.md` — Implementation Phases row 6: "Compatibility checks" — Goal: Every compatibility question of the plan has an answer before any Target A run. — Success signal: Ten check results recorded, each with its fallback where it failed, and the relay probe's outcome when it was run.

## Summary

This phase answers checks L1 to L10 of the local models plan on the synthetic task and runs the relay probe, which the operator asked for on 2026-11-04. It first removes the blocker found in Phase 3: Claude Code's requests reached the server and the Qwen3.5 chat template rejected a system message that was not the first message. A debug run with the server's verbose log shows where that message comes from; the fix, within the plan's fallbacks, is a pinned chat-template override that renders a later system message in place instead of raising, mounted read-only and checked by SHA-256 at every start, with check L1 re-run on it. Two small fixes the checks call for come with it: the agent's pre-flight records whether Anthropic's API and the package index answer from the task container (evidence for check L9), and the store's native reason for a failed run is limited to local runs, so the MVP's exports are unchanged. Then, through the launcher, it runs a vanilla job with L-Small, a vanilla job with L-MoE, the relay probe on L-MoE, and two short jobs that hit the turn limit and the time limit; it grades them, runs the skipped-step check and the independent review on up to three runs, rebuilds the store, and records every check's result, with its fallback where it failed, in `documentation/research/local-route.md`.

## User Story

As the operator of AI Track Record
I want each compatibility question of the local route answered on the synthetic task, with a fallback chosen where the answer is no
So that I can decide D-031 and plan the Target A pilots from evidence, not from community reports

## Problem Statement

Only check L1 has a result (`documentation/research/local-route.md`, "Compatibility checks"). Every local run so far ended at its first request with HTTP 500: the chat template embedded in Qwen3.5-9B's GGUF raises "System message must be at the beginning" when a system message is not first (the server log of `lc-p4-launcher-l-small-synthetic-task-01-local`), so checks L2 to L10 cannot be observed until that is solved (documentation/plans/local-models.md, section 13, first row: a newer build, the model's fixed template, another candidate). Check L9 needs evidence from inside the task container that only the allowed hosts answer, and nothing records it. The store's new native reason, added in Phase 5 for failed local runs, also applies to three API runs, and one of their reasons is 131 characters, longer than the exporter's 64-character limit for text in a private run (`harness/src/atr/store/export.py:53`), so a future MVP export could be blocked (Phase 5 code review, advisory).

## Solution Statement

Find the late system message with one verbose debug run, fix it with the smallest pinned change that keeps the model's behavior (a template override that renders the message instead of raising), confirm with check L1, then run the planned jobs through the launcher and read each check's answer from the records the launcher, the agent, Harbor, the store and the reviewer already write. Record failures with their fallback; do not tune a check until it passes.

## Metadata

| Key | Value |
|---|---|
| Type | Check runs + small fixes + research report |
| Complexity | High |
| Systems Affected | infra/local-inference/ (models.toml, new templates/); harness/src/atr/local/serve.py; harness/src/atr/agents/claude_sdk.py; harness/src/atr/store/load.py; documentation/research/local-route.md; outside the repository: job configs in ~/atr/local, run folders in ~/atr/data/jobs |
| Dependencies | Phases 1–5 complete: the server, the probe, the agent's local route, the launcher and the local allowlist variant `~/atr/data/tasks/synthetic-events/task-01-local`, the store's route-aware loader; relay 0.49.0 at `~/atr/relay/cfe5e0b2a834/plugins/relay` (the copy the MVP's relay049 runs use); the operator's approval of up to three reviews (2026-11-04) |
| Estimated Tasks | 12 |
| Source PRD line ref | `PRPs/prds/local-model-route.prd.md:70` (AC-10), `:66` (AC-6), `:68` (AC-8), `:170` (row 6), `:203-206` (Phase 6 details) |
| phase_type | feature |

## Mandatory Reading

| Priority | Path | Lines | Why |
|---|---|---|---|
| P0 | `PRPs/prds/local-model-route.prd.md` | 66-70, 170, 203-206 | AC-6, AC-8, AC-10 and the Phase 6 scope |
| P0 | `documentation/plans/local-models.md` | 171-186, 196-201, 275-287 | The ten checks, the relay probe and the fallbacks |
| P0 | `documentation/research/local-route.md` | "Compatibility checks" and the sections before it | Where results go; what each earlier phase recorded |
| P0 | `harness/src/atr/local/serve.py` | 45-53, 130-224 | `check_args()` and `start()`: the mounts, the flags and the record |
| P0 | `infra/local-inference/models.toml` | 18-112 | The flags and the main-stage entries that get the template override |
| P0 | `harness/src/atr/agents/claude_sdk.py` | 210-256, 258-300 | `_check_local_server` and `_record_route` |
| P1 | `harness/src/atr/local/launch.py` | 98-127, 161-232 | What a local job needs and what the launcher writes |
| P1 | `harness/src/atr/store/load.py` | 188-206, 290-310, 355-360 | `normalize_outcome`, `failure_cause` and where the native reason is applied (Task 4) |
| P1 | `harness/src/atr/local/probe.py` | 37-66, 150-209 | Check L1's request and result file |
| P1 | `docs/development.md` | 13-26 | The review and skipped-step commands |

## Patterns to Mirror

```python
# SOURCE: harness/src/atr/local/serve.py:45
def check_args(args: list[str]) -> None:
```
Extended by Task 2: a `--chat-template-file` must name a file under `/templates/` whose digest matches models.toml.

```python
# SOURCE: harness/src/atr/local/serve.py:156
         "--volume", f"{weights_dir}:/models:ro",
```
Mirrored by Task 2 for the templates folder, mounted read-only at `/templates`.

```python
# SOURCE: harness/src/atr/agents/claude_sdk.py:210-212
    async def _check_local_server(
        self, environment: BaseEnvironment, env: dict[str, str]
    ) -> None:
```
Extended by Task 3 with two recorded reachability probes from the container, which never fail the run.

```python
# SOURCE: harness/src/atr/store/load.py:357-359
        native = agent.get("subtype")
        if exception and native is None:
            native = failure_cause(exception, trial_dir)
```
Narrowed by Task 4 to trials whose route is local.

## Files to Change

| File | Action | Justification |
|---|---|---|
| `infra/local-inference/templates/<model>.jinja` | CREATE | The chat-template override for each main-stage model whose embedded template raises on a later system message, with a header naming its source and the change |
| `infra/local-inference/models.toml` | UPDATE | `--chat-template-file /templates/<file>` and `chat_template_sha256` for each overridden model |
| `harness/src/atr/local/serve.py` | UPDATE | Mount the templates folder read-only; check the template's digest before starting; record it in `server.json` |
| `harness/src/atr/agents/claude_sdk.py` | UPDATE | Record in `route.json` whether Anthropic's API and the package index answer from the task container (check L9) |
| `harness/src/atr/store/load.py` | UPDATE | Limit the failure's native reason to local runs (the MVP's exports keep their fields) |
| `documentation/research/local-route.md` | UPDATE | Checks L1 to L10, the relay probe, the fallbacks and the runs' figures |
| `~/atr/local/lc-p6-*.json` (WSL, outside the repository) | CREATE | The job configs of the debug run, the two vanilla runs, the relay probe and the two limit runs |

## NOT Building (Scope Limits)

- Any run on Target A, D-031's decision, the hypotheses and the batches (WP4 onward).
- A newer server build or another candidate model: if the template override cannot fix the late system message, that is recorded as check L3's failure with the fallback left for the operator to choose; no new image or model is pinned here.
- Tuning the server's flags to make check L5 pass: its result is recorded with the setting that would be tried next.
- Reviews beyond the three the operator approved; any other call to Anthropic's API.
- L-Alt candidates, the 4-bit L-MoE, whole-system energy (PRD Could items).

## Step-by-Step Tasks

All WSL commands run as `wsl.exe -d Ubuntu --exec bash -lc '<command>'` (never starting the string with `/`). `$CODE_ROOT=/mnt/c/repos/ai-track-record/.worktrees/local-model-route`; `$PY="env PYTHONPATH=src $HOME/atr/tools/harness-venv/bin/python"` runs from `$CODE_ROOT/harness`. Git runs from Windows. Every Harbor job of this phase is started with `$PY -m atr.local.launch <config>` (in the background, waiting in bounded intervals), never with `harbor run` directly, except the debug run of Task 1, which needs a verbose server the launcher does not start. `~/atr/.env` is loaded only for the review command of Task 9, in its own shell, never while a local job runs.

### Task 1: RUN a debug run to find the late system message

- **ACTION**: Write `~/atr/local/lc-p6-debug-l-small-synthetic-task-01-local.json` (the shape of Phase 4's check-run config, `max_turns` 1, task `task-01-local`). Start the server by hand with the verbose log: `$PY -m atr.local.serve start qwen3.5-9b-q4_k_m --arg=--verbose`; run the job with Harbor directly (`HARBOR_TELEMETRY=off PYTHONPATH=$CODE_ROOT/harness/src uv run harbor run -c <config> -y` from `~/atr/tools/harbor`, without `~/atr/.env`); copy the server's state into the trial with `serve record <trial>/server`; stop the server. From the verbose log of the first rejected `/v1/messages` request, write `~/atr/data/local-inference/checks/l3-template-<stamp>.json` with the request's structure only: the roles in order, the content block types per message, where the system prompt and each later system message come from (the Anthropic `system` field, a converted block, or a message), and the template's failing line. Write no prompt text into the result file or the repository. If the verbose log does not hold the request, repeat with `--arg=--log-verbosity --arg=5`. Delivers AC-A1.
- **MIRROR**: `harness/src/atr/local/serve.py:45`
- **VALIDATE**: `python3 -c "import json,glob,os; fs=sorted(glob.glob(os.path.expanduser('~/atr/data/local-inference/checks/l3-template-*.json'))); assert fs, 'no template finding'; r=json.load(open(fs[-1])); assert r.get('roles') and 'late_system_source' in r, sorted(r); print('PASS', r['late_system_source'])"`

### Task 2: CREATE the chat-template override and pin it

- **ACTION**: With a running server for each main-stage model, read its embedded template from `GET /props` (with the key; field `chat_template`). Where the template raises on a system message that is not first, write `infra/local-inference/templates/<model id>.jinja`: the embedded template with that raise replaced by rendering the message as a system turn at its position, in the template's own turn format, and nothing else changed. Start the file with a Jinja comment naming the source (`repo` and `revision` from models.toml), its license (Apache 2.0), the date and the one change. Add `"--chat-template-file", "/templates/<model id>.jinja"` to that model's args and `chat_template_sha256 = "<digest>"` to its entry. In `serve.py`, mount `infra/local-inference/templates` read-only at `/templates`; extend `check_args()` (or `start()`) so a `--chat-template-file` must be under `/templates/` and the file's SHA-256 must equal the entry's `chat_template_sha256`, else stop with `SystemExit` before starting; record `chat_template_sha256` in `server.json`. If Task 1 shows the late system message is not something a template can render (for example a request the server rejects before the template), write no override, record that finding and its cause, and go on with Tasks 3 and 4 and the report, marking checks L2 to L8 and L10 as not observable with the fallback "a newer pinned build, or another candidate (operator decision)". Delivers AC-A1.
- **MIRROR**: `harness/src/atr/local/serve.py:156`
- **VALIDATE**: `cd $CODE_ROOT/harness && $PY -c "import hashlib,pathlib; from atr.local import config; s=config.load(); d=pathlib.Path('../infra/local-inference/templates'); m={i:e for i,e in s['models'].items() if e.get('chat_template_sha256')}; assert m, 'no override pinned (or record why in the report)'; [None for i,e in m.items() if hashlib.sha256((d/(e['args'][e['args'].index('--chat-template-file')+1].split('/')[-1])).read_bytes()).hexdigest()==e['chat_template_sha256'] or (_ for _ in ()).throw(SystemExit(i+': digest mismatch'))]; print('PASS', sorted(m))"`

### Task 3: UPDATE harness/src/atr/agents/claude_sdk.py (network evidence for check L9)

- **ACTION**: In `_check_local_server`, after its checks pass, run two probes from the task container that never fail the run: `curl -sS -m 10 -o /dev/null -w '%{http_code}' https://api.anthropic.com/` and the same for `https://pypi.org/simple/`, with no key, header or body. Record in `route.json` a `network` object: for each host, the HTTP status, or `null` with curl's exit code when the connection failed. On the Anthropic route nothing changes. Delivers AC-A2.
- **MIRROR**: `harness/src/atr/agents/claude_sdk.py:210-212`
- **VALIDATE**: `cd $CODE_ROOT/harness && env PYTHONPATH=src uv run --project $HOME/atr/tools/harbor python -c "import inspect; from atr.agents import claude_sdk as m; s=inspect.getsource(m.ClaudeAgentSdk); assert 'api.anthropic.com' in s and 'pypi.org' in s and 'network' in s; print('PASS')"`

### Task 4: UPDATE harness/src/atr/store/load.py (native reason on local runs only)

- **ACTION**: Apply the Phase 5 rule that gives a failed run without an SDK result a native reason only when the trial's route is `local`; other trials keep `native_outcome` as it was before Phase 5 (the SDK subtype, or null). Rebuild the store and confirm that no non-local trial has a native reason it did not have before Phase 5, and that the local trials keep theirs. Delivers AC-A2.
- **MIRROR**: `harness/src/atr/store/load.py:357-359`
- **VALIDATE**: `cd $CODE_ROOT/harness && $PY -m atr.store.load > /dev/null && $PY -c "import duckdb,os; c=duckdb.connect(os.path.expanduser('~/atr/data/atr.duckdb'), read_only=True); n=c.execute(\"SELECT count(*) FROM trials WHERE coalesce(route,'')<>'local' AND exception IS NOT NULL AND native_outcome IS NOT NULL AND native_outcome NOT IN ('success','error_max_turns','error_max_budget_usd','error_during_execution')\").fetchone()[0]; l=c.execute(\"SELECT count(*) FROM trials WHERE route='local' AND native_outcome IS NOT NULL\").fetchone()[0]; assert n==0 and l>=1, (n,l); print('PASS', n, l)"`

### Task 5: RUN check L1 again with the override

- **ACTION**: For each model with an override, start its server (`serve start <id>`), run `$PY -m atr.local.probe`, stop it. Delivers AC-A1.
- **MIRROR**: `harness/src/atr/local/probe.py:150-209`
- **VALIDATE**: `python3 -c "import json,glob,os,tomllib; s=tomllib.load(open('$CODE_ROOT/infra/local-inference/models.toml','rb')); ids=[i for i,e in s['models'].items() if e.get('chat_template_sha256')]; assert ids; bad=[i for i in ids if not json.load(open(sorted(glob.glob(os.path.expanduser('~/atr/data/local-inference/checks/l1-'+i+'-*.json')))[-1]))['passed']]; assert not bad, bad; print('PASS', ids)"`

### Task 6: RUN the vanilla job with L-Small through the launcher

- **ACTION**: Write `~/atr/local/lc-p6-vanilla-l-small-synthetic-task-01-local.json` (the Phase 4 check-run shape: model `local/qwen3.5-9b`, `route` `local`, `config_label` `vanilla-l-small`, the web tools disallowed, no `max_budget_usd`, task `task-01-local`) and run it with the launcher. Wait for it to end (up to the task's three-hour limit). Keep every record whatever the outcome. Delivers AC-A3.
- **MIRROR**: `harness/src/atr/local/launch.py:161-232`
- **VALIDATE**: `python3 -c "import glob,os; t=glob.glob(os.path.expanduser('~/atr/data/jobs/lc-p6-vanilla-l-small-synthetic-task-01-local/*/server/power.json')); assert t, 'no trial with records'; print('PASS')"`

### Task 7: RUN the vanilla job with L-MoE through the launcher

- **ACTION**: The same as Task 6 with model `local/qwen3.6-35b-a3b`, `config_label` `vanilla-l-moe`, job `lc-p6-vanilla-l-moe-synthetic-task-01-local`. Delivers AC-A3.
- **MIRROR**: `harness/src/atr/local/launch.py:161-232`
- **VALIDATE**: `python3 -c "import glob,os; t=glob.glob(os.path.expanduser('~/atr/data/jobs/lc-p6-vanilla-l-moe-synthetic-task-01-local/*/server/power.json')); assert t, 'no trial with records'; print('PASS')"`

### Task 8: RUN the relay probe and the two limit runs through the launcher

- **ACTION**: (a) The relay probe: `~/atr/local/lc-p6-relay049-l-moe-synthetic-task-01-local.json`, in the shape of the MVP's relay049 configs (`plugin_dir` `/opt/relay`, `install_node` true, `prompt` `/relay:relay-execute PRPs/prds/event-registration.prd.md`, and the environment mount of `/root/atr/relay/cfe5e0b2a834/plugins/relay` read-only at `/opt/relay`), model `local/qwen3.6-35b-a3b`, `route` `local`, `config_label` `relay049-l-moe`, task `task-01-local`; run it with the launcher and wait (up to three hours). (b) The turn limit: `lc-p6-limit-turns-l-small-synthetic-task-01-local` with `max_turns` 2. (c) The time limit: `lc-p6-limit-time-l-small-synthetic-task-01-local` with the job's `agent_timeout_multiplier` 0.01 (a 108-second agent limit). Run (b) and (c) with the launcher, one after the other. Delivers AC-A3.
- **MIRROR**: `harness/src/atr/local/launch.py:98-127`
- **VALIDATE**: `python3 -c "import glob,os; j=os.path.expanduser('~/atr/data/jobs/'); miss=[n for n in ('lc-p6-relay049-l-moe-synthetic-task-01-local','lc-p6-limit-turns-l-small-synthetic-task-01-local','lc-p6-limit-time-l-small-synthetic-task-01-local') if not glob.glob(j+n+'/*/result.json')]; assert not miss, miss; print('PASS')"`

### Task 9: RUN the graders: skipped-step check and the independent review

- **ACTION**: The verifier graded each trial during its job. Run `$PY -m atr.checks.skipped_steps <relay probe trial>`. Run the independent review on up to three trials that ended with changes, in this order of preference: the L-Small vanilla trial, the L-MoE vanilla trial, the relay probe trial: `set -a; . ~/atr/.env; set +a; $PY -m atr.review.run <trial dir> --task ~/atr/data/tasks/synthetic-events/task-01-local`, one at a time, in a shell of its own, with no local job running. Never review more than three trials; skip a trial with no changes and say so. Delivers AC-A4.
- **MIRROR**: `harness/src/atr/local/launch.py:161-232`
- **VALIDATE**: `python3 -c "import glob,os; r=glob.glob(os.path.expanduser('~/atr/data/jobs/lc-p6-*/*/review/review.json')); assert len(r)<=3, len(r); print('PASS', len(r))"`

### Task 10: RUN the store and the budget

- **ACTION**: Rebuild the store (`$PY -m atr.store.load`) and read, for every `lc-p6-*` trial: outcome, native outcome, reward and criteria, new static findings, review findings, turns, wall time, tokens, server counts, energy and the reconciliation status. Run `$PY -m atr.ops.budget` and confirm the MVP's total is unchanged and the `lc-` line includes the reviews' cost. Delivers AC-A4.
- **MIRROR**: `harness/src/atr/store/load.py:357-359`
- **VALIDATE**: `cd $CODE_ROOT/harness && $PY -c "import duckdb,os; c=duckdb.connect(os.path.expanduser('~/atr/data/atr.duckdb'), read_only=True); n=c.execute(\"SELECT count(*) FROM trials WHERE job LIKE 'lc-p6-%' AND route='local'\").fetchone()[0]; assert n>=5, n; print('PASS', n)" && $PY -m atr.ops.budget | grep -q 'lc-'`

### Task 11: UPDATE documentation/research/local-route.md

- **ACTION**: Replace the "L2 to L10 / Phase 6" row of the "Compatibility checks" table with one row per check and model (L1 to L10; L1 re-run on the override), each with its result (Pass, Fail or Partial), the date, the evidence (the record it comes from and the figures: requests and model names for L2; malformed tool calls counted from `agent/messages.jsonl` and stalled streams for L3; compaction events, context errors and the largest request against the window for L4; processed against cached prompt tokens from the server's counters for L5; the verifier's reward and criteria, the static findings, the skipped-step check and the review for L6; the reconciliation status for L7; the SDK's recorded cost, the cap and the turn and time limit runs' outcomes for L8; the `route.json` network record for L9, Anthropic's API unreachable and the package index and the server reachable; the server's uptime, VRAM and memory peaks and the runs' durations for L10) and, for each failure or partial result, the fallback chosen from section 13 of the plan or the operator decision it needs. Add a section on the template finding and the override (source, change, digest). Add the relay probe's outcome (completed, halted with its code, timed out, or error), its protocol steps and its figures. Add a table of the runs (job, model, outcome, reward, turns, wall time, input and output tokens, energy). Update the Progress table (WP1 to WP3). Use "Target A" only as a codename; no transcript text. Delivers AC-A5.
- **MIRROR**: `documentation/research/local-route.md:1-20`
- **VALIDATE**: `set -euo pipefail; f=$CODE_ROOT/documentation/research/local-route.md; for c in L2 L3 L4 L5 L6 L7 L8 L9 L10; do grep -qE "^\| $c \|" $f || { echo "FAIL: no row for $c"; exit 1; }; done; grep -qi 'relay probe' $f; echo PASS`

### Task 12: VERIFY privacy on every new and changed file

- **ACTION**: Run the leak check (word match, as the exporter's) over the changed and new files of this phase, and confirm that no file under `infra/` or `documentation/` holds prompt or transcript text, a key, or another project's container name. Delivers AC-A5.
- **MIRROR**: `harness/src/atr/store/export.py:115-131`
- **VALIDATE**: `set -euo pipefail; cd $CODE_ROOT; files="infra/local-inference/models.toml $(ls infra/local-inference/templates/*.jinja 2>/dev/null) harness/src/atr/local/serve.py harness/src/atr/agents/claude_sdk.py harness/src/atr/store/load.py documentation/research/local-route.md"; if grep -lwiF -f <(grep -vE '^(#|[[:space:]]*$)' ~/atr/data/leak-terms.txt) $files; then echo "FAIL: private term"; exit 1; fi; echo PASS`

## Validation Commands

`$CODE_ROOT` and `$PY` as in the Step-by-Step Tasks.

### Level 1: STATIC_ANALYSIS

```bash
set -euo pipefail
cd $CODE_ROOT/harness
$PY -m py_compile src/atr/local/serve.py src/atr/agents/claude_sdk.py src/atr/store/load.py
$PY -c "import tomllib; tomllib.load(open('../infra/local-inference/models.toml','rb')); print('toml ok')"
$PY -m atr.local.serve --help > /dev/null
echo PASS
```

### Level 2: CONTENT_INVARIANTS

```bash
set -euo pipefail
cd $CODE_ROOT/harness
# Pinned templates: every override's digest matches models.toml, and the start refuses a mismatch.
$PY -c "
import hashlib, pathlib
from atr.local import config
s = config.load(); d = pathlib.Path('../infra/local-inference/templates')
for i, e in s['models'].items():
    if e.get('chat_template_sha256'):
        f = e['args'][e['args'].index('--chat-template-file') + 1].split('/')[-1]
        assert hashlib.sha256((d / f).read_bytes()).hexdigest() == e['chat_template_sha256'], i
print('templates pinned')"
# The native reason is limited to local runs.
$PY -c "import duckdb,os; c=duckdb.connect(os.path.expanduser('~/atr/data/atr.duckdb'), read_only=True); n=c.execute(\"SELECT count(*) FROM trials WHERE coalesce(route,'')<>'local' AND exception IS NOT NULL AND native_outcome IS NOT NULL AND native_outcome NOT IN ('success','error_max_turns','error_max_budget_usd','error_during_execution')\").fetchone()[0]; assert n==0, n; print('native reason ok')"
# Privacy: no private term (word match, as the exporter's leak check) in the changed files.
files="../infra/local-inference/models.toml $(ls ../infra/local-inference/templates/*.jinja 2>/dev/null) src/atr/local/serve.py src/atr/agents/claude_sdk.py src/atr/store/load.py ../documentation/research/local-route.md"
if grep -lwiF -f <(grep -vE '^(#|[[:space:]]*$)' ~/atr/data/leak-terms.txt) $files; then echo "FAIL: private term in a changed file"; exit 1; fi
echo PASS
```

### Level 3: INTEGRATION

```bash
set -euo pipefail
cd $CODE_ROOT/harness
# Check L1 on the override with L-Small, the faster model to load.
$PY -m atr.local.serve start qwen3.5-9b-q4_k_m > /dev/null
trap '$PY -m atr.local.serve stop' EXIT
$PY -c "import json,pathlib; r=json.loads((pathlib.Path.home()/'atr/data/local-inference/server.json').read_text()); assert r.get('chat_template_sha256'), 'template not recorded'; print('record ok')"
$PY -m atr.local.probe
$PY -m atr.local.serve stop; trap - EXIT
# Every check has a recorded result, and the runs are in the store.
python3 -c "import re,os; t=open(os.path.expandvars('$CODE_ROOT/documentation/research/local-route.md')).read(); rows=[c for c in ['L%d'%i for i in range(1,11)] if re.search(r'^\| '+c+r' \| [^|]*\| (Pass|Fail|Partial)', t, re.M)]; assert len(rows)==10, rows; print('checks recorded')"
$PY -c "import duckdb,os; c=duckdb.connect(os.path.expanduser('~/atr/data/atr.duckdb'), read_only=True); assert c.execute(\"SELECT count(*) FROM trials WHERE job LIKE 'lc-p6-%'\").fetchone()[0]>=5; print('runs loaded')"
echo PASS
```

## Acceptance Criteria

- **AC-A1 (PRD AC-10):** The cause of the late system message is recorded from a debug run, and, where a template can fix it, a pinned override (file, digest checked at every start, recorded in `server.json`) makes check L1 pass again on each overridden model; where it cannot, the finding and the fallback are recorded.
- **AC-A2 (PRD AC-8, AC-10):** Every local run's `route.json` records whether Anthropic's API and the package index answered from the task container; the store gives a failure's native reason only to local runs, so non-local trials keep their exported fields.
- **AC-A3 (PRD AC-10):** A vanilla job with each main model, the relay probe on L-MoE and the two limit jobs ran through the launcher on the synthetic task's local variant, each with its records in its trial folder.
- **AC-A4 (PRD AC-6):** The runs are graded by the unchanged verifier, the skipped-step check runs on the relay probe, at most three runs are reviewed by the pinned reviewer, the store loads them with their reconciliation status and the budget keeps them out of the MVP's total.
- **AC-A5 (PRD AC-10):** `documentation/research/local-route.md` records a result for each of checks L1 to L10, with the fallback where one failed, the relay probe's outcome, the template finding and the runs' figures, and no changed file holds a private term, transcript text or a key.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The late system message cannot be fixed by a template (PRD Technical Risks, row 1) | M | H | Record the cause; checks L2–L8 and L10 recorded as not observable with the fallback (a newer build or another candidate) for the operator |
| Tool calls break inside thinking blocks (llama.cpp issue 20837) | M | M | Check L3 counts malformed calls; the fallback is thinking off for that model, recorded, not applied silently |
| A run reaches the three-hour limit (no prefix reuse, check L5) | M | M | The limit is a measured outcome; check L5 records the reuse rate and the next setting to try |
| The machine runs out of memory during the L-MoE runs beside the other containers | L | H | The launcher stops the server in a `finally`; check L10 records the failure; ask the operator before stopping any other project's container |
| Reviews cost more than estimated | L | L | At most three reviews (about US$ 0.40 each), counted on the `lc-` line of the budget |
| The debug run's verbose log holds the synthetic task's prompt text | H | L | It stays in the trial folder under `~/atr/data`; the result file and the report hold the structure only |

## Notes

- **TDD routing (this plan, against the relay repo):** Current value of `tdd` in `docs/context/methodology.md`: **false**. Test-after ordering — when a test framework is declared, the test pair (test-writer/test-reviewer) authors and maintains the suite from the Acceptance Criteria above, after the Implementer + Code Review; with no framework declared, no tests are authored.
- No test framework is declared (`test_frameworks: []`), so no test files are authored; the checks are the phase's evidence.
- Research for this plan: llama.cpp's Anthropic-to-OpenAI converter puts the top-level `system` field first and copies any system-role turn from `messages` after it, and recent Claude Code versions append such a turn (harness context) on most requests, so a template that accepts one leading system message rejects the request (llama.cpp discussion 27281; a Claude Code issue reports it persists with `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`). Fixes used in practice are a template patch that renders the later system turn instead of raising (deleting the raise alone drops the message silently), served with `--chat-template-file`, and unmerged converter patches; merging later system content into the leading message was measured to break prefix reuse, which is why Task 2 renders it in place. No source tests Qwen3.5-9B with Claude Code; Task 1's debug run confirms the mechanism on this build before Task 2 relies on it.
- The operator approved in chat on 2026-11-04 the independent review of up to three local runs on the synthetic task (about US$ 1.20) and the relay probe; no other step calls Anthropic's API.
- The machine time of this phase is several hours (L-Small 25–60 minutes, L-MoE up to three hours, the relay probe up to three hours, the limit runs a few minutes each).

*Generated: 2026-11-04*
*Approved: 2026-11-04*
*Implemented: 2026-11-05*
*Status: IMPLEMENTED*
