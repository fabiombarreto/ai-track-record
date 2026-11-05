# Feature: Local launcher and allowlists (Phase 4 of local-model-route)

```
**Decision Gate**
- Active context: none
- Activated criteria: business rules for runs and local inference (docs/domain/areas/runs.md, docs/domain/areas/local-inference.md); creation of a component (atr.local.launch); change of a component (atr.tasks.build); cross-cutting pattern (the server's record and power samples copied into every trial folder, D-033); the network allowlist (D-050)
- Decisions found:
  - Local models experiment outside the frozen MVP; the MVP keeps priority over the operator's time and the machine (D-058): the launcher refuses while any other Harbor job runs
  - Network allowlist and no web tools on Target A (D-050): on the local route the agent's allowlist names the local server's host and the package index, not Anthropic's API
  - Target A on local open-weight models only (D-057); the local route sends nothing to Anthropic's API (D-029)
  - Run folders are the system of record (D-033): the server's record, slots, metrics, log and power samples go into each trial folder
  - Pin everything and fail instead of silently dropping an option (D-020): the launcher refuses a job that is not a local job, a model it cannot map to one pinned entry, or a server that fails its checks
  - Synthetic task first (D-046): the launcher's check run is on the public synthetic task
- Applicable anti-patterns:
  - Private-target material in the repository (Target A's manifests and task builds stay in ~/atr; the repository gets only the code and the synthetic manifest's key)
  - Running two benchmark runs at the same time (the launcher refuses while a Harbor job runs)
  - Web tools or an open network on Target A runs (the local variant keeps the allowlist and drops only Anthropic's API)
  - Secrets in the repository or in a record (the server key reaches only the agent through server.key; the launcher strips Anthropic keys from the job's environment)
- Applicable architectural rules:
  - Configuration, not code (D-005): the local allowlist is a manifest key, the route a job-config value
  - Files first: every record the launcher writes is a file in the trial folder
  - Fail closed on checks that guard correctness or privacy; the server is always stopped, also on failure
  - Host-side code follows docs/context/conventions.md (one module per command, docstring with Usage, SystemExit messages, standard library only)
- Result: PROCEED
```

## Source

- `PRPs/prds/local-model-route.prd.md` — Implementation Phases row 4: "Local launcher and allowlists" — Goal: Local runs are started the same way every time, never alongside an MVP job, and behind the right network. — Success signal: A local job run through the launcher leaves the server's records and power samples in its trial folder, and the launcher refuses while an MVP job runs.

## Summary

This phase adds `python -m atr.local.launch <job config>`, which runs one local Harbor job the same way every time: it refuses while any other Harbor job runs (the MVP keeps priority), refuses a job that is not a local one (`lc-` name, `route: "local"`, a `local/<alias>` model that maps to one main-stage model), starts that model's server with a new key, samples GPU power every second for the whole job, runs Harbor without any Anthropic key in its environment, then writes into every trial folder the server's record, slots, metrics and log (`serve record`) and the power samples with their summary, and always stops the server. It also adds an allowlist variant to the task builder: `python -m atr.tasks.build <manifest> --route local` builds `<task id>-local` with the agent's allowlist from the manifest's `network.agent_allowed_hosts_local`, or, when that key is absent, the manifest's agent allowlist without `api.anthropic.com` and with `host.docker.internal`. The synthetic manifest gets a local allowlist (the server's host and the package index), and Target A's private manifests get the same key in `~/atr/manifests`, outside the repository.

## User Story

As the operator of AI Track Record
I want one command that starts the right server, runs a local job behind the right network and leaves the server's state and the GPU's power in the run's folder
So that every local run is started the same way, never competes with an MVP batch, and proves what served it and what it cost in energy

## Problem Statement

After Phase 3 a local run works only by hand: the operator starts the server, runs Harbor, remembers to call `serve record` before stopping the server, and nothing measures power during the run (`documentation/research/local-route.md`, "Agent route"). Nothing stops a local run from starting while an MVP batch runs (D-058). The task builds have one allowlist per manifest (`harness/src/atr/tasks/build.py:108-112`); Target A's names Anthropic's API, which a local run must not reach, and the synthetic task's manifest has no allowlist at all, so check L9 cannot run on it (`documentation/plans/local-models.md:185`).

## Solution Statement

Write the launcher as a small host-side module that composes what exists — `serve.start`, `serve.snapshot`, `serve.stop` and `bench.GpuSampler` — around a `harbor run` subprocess, with the refusals checked before anything starts and the server stopped in a `finally`. Extend `build.py` with one option and one manifest key; leave the default build byte-for-byte as it is.

## Metadata

| Key | Value |
|---|---|
| Type | New component (launcher) + enhancement (task builder) + check run |
| Complexity | Medium |
| Systems Affected | harness/src/atr/local/ (new launch); harness/src/atr/tasks/build.py; targets/synthetic-events/task-01.toml; documentation/research/local-route.md; outside the repository: ~/atr/manifests/target-a/*.toml, the built tasks in ~/atr/data/tasks, a job config in ~/atr/local |
| Dependencies | Phases 1–3 complete: `atr.local.serve` (start, snapshot, stop), `atr.local.bench.GpuSampler`, the agent's `route: "local"`; Harbor 0.24.0 at `~/atr/tools/harbor`; the OpenTelemetry Collector |
| Estimated Tasks | 8 |
| Source PRD line ref | `PRPs/prds/local-model-route.prd.md:67-68` (AC-7, AC-8), `:168` (row 4), `:193-196` (Phase 4 details) |
| phase_type | feature |

## Mandatory Reading

| Priority | Path | Lines | Why |
|---|---|---|---|
| P0 | `PRPs/prds/local-model-route.prd.md` | 67-68, 168, 193-196 | AC-7 (the refusal half), AC-8 and the Phase 4 scope and success signal |
| P0 | `documentation/plans/local-models.md` | 144-156, 163 | The server per run, the local record, the network for Target A, the launcher's row |
| P0 | `harness/src/atr/local/serve.py` | 125-128, 130-224, 226-271 | `stop()`, `start()` and `snapshot()` the launcher composes |
| P0 | `harness/src/atr/local/bench.py` | 55-95 | `GpuSampler`, reused for the power samples |
| P0 | `harness/src/atr/tasks/build.py` | 1-21, 108-120, 180-205 | The manifest keys, `network_policy()`, `build()` and its `main()` |
| P1 | `targets/synthetic-events/task-01.toml` | all | The synthetic manifest that gets the local allowlist |
| P1 | `harness/src/atr/agents/claude_sdk.py` | the `route` option and `_local_server()` | What the agent expects from the server and its records |
| P1 | `docs/development.md` | 1-30 | How Harbor jobs run from WSL |
| P2 | `harness/src/atr/ops/cleanup.py` | 35-57 | How unfinished trials are found in a job folder |

## Patterns to Mirror

```python
# SOURCE: harness/src/atr/tasks/build.py:108-112
def network_policy(hosts: list[str] | None) -> str:
    """Lines for a phase's Harbor network allowlist; nothing keeps the default network."""
    if hosts is None:
        return ""
    return f'network_mode = "allowlist"\nallowed_hosts = {json.dumps(hosts)}\n'
```
Used unchanged by Task 1; the local variant only chooses which hosts it receives.

```python
# SOURCE: harness/src/atr/local/bench.py:55-66
class GpuSampler:
    """Samples the GPU's power, memory and use every second while it runs."""

    def __init__(self) -> None:
        self.samples: list[tuple[float, float, int, float]] = []
        self.process = subprocess.Popen(
            ["nvidia-smi", "--query-gpu=power.draw,memory.used,utilization.gpu",
             "--format=csv,noheader,nounits", "--loop-ms=1000"],
            stdout=subprocess.PIPE, text=True,
        )
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()
```
Reused by Task 3 for the job's power samples; the launcher writes the raw samples and `stop()`'s summary.

```python
# SOURCE: harness/src/atr/local/serve.py:125-128
def stop() -> None:
    subprocess.run(["docker", "rm", "--force", CONTAINER], capture_output=True)
    (config.data_dir() / "server.key").unlink(missing_ok=True)
```
Called by Task 3 in a `finally`, so the server never outlives the job.

## Files to Change

| File | Action | Justification |
|---|---|---|
| `harness/src/atr/tasks/build.py` | UPDATE | AC-8: `--route local` builds `<task id>-local` with the local agent allowlist |
| `targets/synthetic-events/task-01.toml` | UPDATE | AC-8: `network.agent_allowed_hosts_local` for the synthetic task (the server's host and the package index) |
| `harness/src/atr/local/launch.py` | CREATE | AC-7 refusal half and the Phase 4 scope: server per job, power samples, records into every trial, MVP-priority refusal |
| `documentation/research/local-route.md` | UPDATE | The launcher, the allowlist variants and the check run |
| `~/atr/manifests/target-a/task-0{1,2,3}.toml` (WSL, private, outside the repository) | UPDATE | AC-8: Target A's local allowlist, its agent hosts without Anthropic's API |
| `~/atr/local/lc-p4-launcher-l-small-synthetic-task-01-local.json` (WSL, outside the repository) | CREATE | The launcher's check-run job config |

## NOT Building (Scope Limits)

- Store, budget and export changes, including keeping `lc-` jobs out of the MVP's ceiling (the budget half of AC-7) and loading the power samples — Phase 5.
- Checks L2 to L10, including the network check L9 that proves the allowlist blocks other hosts — Phase 6. This phase builds the variants and confirms their `task.toml`.
- A fix for the Qwen3.5-9B chat template that rejected Claude Code's late system message in Phase 3 — Phase 6 (checks L1 and L3 decide the template, the thinking setting or another model). The launcher's check run is expected to end with the same error; it proves the launcher, not the model.
- Running any Target A task: the Target A variants are built and inspected, not run.
- Whole-system energy with a plug meter — PRD Could item.

## Step-by-Step Tasks

All WSL commands run as `wsl.exe -d Ubuntu --exec bash -lc '<command>'` (never starting the string with `/`). `$CODE_ROOT` is the phase's code root seen from WSL (`/mnt/c/repos/ai-track-record/.worktrees/local-model-route`); `$PY="env PYTHONPATH=src $HOME/atr/tools/harness-venv/bin/python"` runs from `$CODE_ROOT/harness`. Git commands on the worktree run from Windows.

### Task 1: UPDATE harness/src/atr/tasks/build.py (the local allowlist variant)

- **ACTION**: Add a pure function `local_hosts(network: dict) -> list[str] | None` that returns `network["agent_allowed_hosts_local"]` when the key exists; otherwise, when `agent_allowed_hosts` exists, that list without `api.anthropic.com` and with `host.docker.internal` added if missing; otherwise `None`. It raises `SystemExit` if the result contains `api.anthropic.com`, or does not contain `host.docker.internal`. Add a `route: str = "anthropic"` parameter to `build()`: on `local`, the output folder and the task's `name` in `task.toml` use `<task id>-local`, the agent phase's network comes from `local_hosts()` (failing with `SystemExit` when it returns `None`: a local variant without an allowlist is not built), and `atr-task.json` keeps `task_id` unchanged and adds `"route": "local"`, so the store compares the variant with the same task's other runs. The verifier's network is unchanged. Add `--route {anthropic,local}` to `main()` (default `anthropic`). Document the new key and option in the module docstring. The default build must produce exactly today's output. Delivers AC-A1.
- **MIRROR**: `harness/src/atr/tasks/build.py:108-112`
- **VALIDATE**: `cd $CODE_ROOT/harness && $PY -c "
from atr.tasks.build import local_hosts
assert local_hosts({'agent_allowed_hosts':['api.anthropic.com','host.docker.internal','pypi.org']})==['host.docker.internal','pypi.org']
assert local_hosts({'agent_allowed_hosts':['api.anthropic.com','pypi.org']})==['pypi.org','host.docker.internal']
assert local_hosts({'agent_allowed_hosts_local':['host.docker.internal','pypi.org']})==['host.docker.internal','pypi.org']
assert local_hosts({}) is None
try: local_hosts({'agent_allowed_hosts_local':['api.anthropic.com','host.docker.internal']}); raise SystemExit('FAIL')
except SystemExit as e: assert str(e)!='FAIL'
print('PASS')"`

### Task 2: UPDATE targets/synthetic-events/task-01.toml and build the synthetic variant

- **ACTION**: Add a `[network]` section with only `agent_allowed_hosts_local = ["host.docker.internal", "pypi.org", "files.pythonhosted.org"]` and a comment: the local route's allowlist (the local server and the Collector on the host, and the package index, D-050); the default build keeps the open network. Build both variants: `$PY -m atr.tasks.build ../targets/synthetic-events/task-01.toml` (unchanged output) and `$PY -m atr.tasks.build ../targets/synthetic-events/task-01.toml --route local` (writes `~/atr/data/tasks/synthetic-events/task-01-local`). Delivers AC-A2.
- **MIRROR**: `harness/src/atr/tasks/build.py:180-205`
- **VALIDATE**: `python3 -c "import tomllib,os,json; b=os.path.expanduser('~/atr/data/tasks/synthetic-events/'); t=tomllib.load(open(b+'task-01-local/task.toml','rb')); a=t['agent']; assert a['network_mode']=='allowlist' and 'api.anthropic.com' not in a['allowed_hosts'] and 'host.docker.internal' in a['allowed_hosts'], a; d=tomllib.load(open(b+'task-01/task.toml','rb')); assert 'network_mode' not in d['agent'], 'default build changed'; m=json.load(open(b+'task-01-local/atr-task.json')); assert m['task_id']=='task-01' and m['route']=='local'; print('PASS')"`

### Task 3: CREATE harness/src/atr/local/launch.py

- **ACTION**: `python -m atr.local.launch <job config .json> [--model-id <id>] [--port 8090] [--dry-run]`. Before starting anything: (a) refuse with `SystemExit` while any other Harbor job runs: list processes (`ps -eo pid,args`) whose arguments contain `harbor run`, excluding the launcher's own process, its ancestors (the shell that started it) and its descendants, and name the job they run when the arguments carry `-c <config>`; (b) refuse unless the config's `job_name` starts with `lc-`, every agent has `kwargs.route == "local"` and a `model_name` of `local/<alias>`, and every task path's `task.toml` has an agent `network_mode` of `allowlist` without `api.anthropic.com`; (c) map the alias to exactly one main-stage entry of `models.toml` (or the `--model-id` given, which must have that alias), else refuse; (d) refuse when the job folder `<jobs_dir>/<job_name>` already exists (no job is resumed or mixed). `--dry-run` stops after the checks and prints what it would run. Then: `serve.start(model_id, port, ...)`; start a `bench.GpuSampler`; run `uv run harbor run -c <config> -y` from `~/atr/tools/harbor` with `HARBOR_TELEMETRY=off`, `PYTHONPATH=<repo>/harness/src` and every variable whose name starts with `ANTHROPIC_` removed from the environment, streaming its output to `<jobs_dir>/<job_name>.launch.log`; when it ends, stop the sampler; for every trial folder of the job (a folder holding `config.json` or `result.json`), call `serve.snapshot(<trial>/server)` and write `<trial>/server/power.csv` (monotonic seconds from the job's start, power W, VRAM MiB, GPU use %) and `<trial>/server/power.json` (the sampler's summary plus `started_at`, `ended_at` and the number of trials sharing the samples); write `<jobs_dir>/<job_name>/launch.json` with the model id, the server record's image and SHA-256, the Harbor exit code, the trials recorded and the wall time. Stop the server in a `finally`, also on failure or interruption. Exit with Harbor's exit code, or non-zero when a record could not be written. Never print or write the key. Delivers AC-A3 and AC-A4.
- **MIRROR**: `harness/src/atr/local/bench.py:55-66` and `harness/src/atr/local/serve.py:125-128`
- **VALIDATE**: `set -euo pipefail; cd $CODE_ROOT/harness; $PY -m atr.local.launch --help > /dev/null; echo '{"job_name":"m3-not-local","jobs_dir":"/tmp","agents":[{"name":"x","model_name":"claude-sonnet-5-5","kwargs":{}}],"tasks":[]}' > /tmp/atr-launch-bad.json; if $PY -m atr.local.launch /tmp/atr-launch-bad.json --dry-run; then echo 'FAIL: a non-local job was accepted'; exit 1; fi; echo PASS`

### Task 4: VERIFY the MVP-priority refusal

- **ACTION**: First write the launcher's check-run job config, `~/atr/local/lc-p4-launcher-l-small-synthetic-task-01-local.json`, in the shape of Phase 3's check-run config (`~/atr/local/lc-p3-vanilla-l-small-synthetic-task-01.json`), with `job_name` `lc-p4-launcher-l-small-synthetic-task-01-local` and the task `/root/atr/data/tasks/synthetic-events/task-01-local` (Task 6 runs it). Then start a stand-in for an MVP job, a process whose arguments read like one (`bash -c 'exec -a "harbor run -c /root/atr/m3/m3-standin.json -y" sleep 120' &`, its PID kept so it is stopped with `kill`, never with `pkill -f`, which would match the calling shell), run `$PY -m atr.local.launch <check-run config> --dry-run`, and confirm it refuses, names the running job and starts no server (`docker ps --filter name=^atr-llm$ -q` is empty); then kill the stand-in and confirm the same dry run passes its checks. Delivers AC-A4.
- **MIRROR**: `harness/src/atr/local/serve.py:125-128`
- **VALIDATE**: `set -euo pipefail; cd $CODE_ROOT/harness; C=~/atr/local/lc-p4-launcher-l-small-synthetic-task-01-local.json; [ -f $C ] || { echo "FAIL: no check-run config"; exit 1; }; D=$(mktemp /tmp/lc-p4-dryrun-XXXXXX.json); python3 -c "import json,sys; d=json.load(open(sys.argv[1])); d['job_name']+='-dryrun-'+sys.argv[3]; json.dump(d,open(sys.argv[2],'w'))" $C $D $$; bash -c 'exec -a "harbor run -c /root/atr/m3/m3-standin.json -y" sleep 120' & S=$!; sleep 1; if out=$($PY -m atr.local.launch $D --dry-run 2>&1); then echo "FAIL: launched beside a running job"; kill $S; exit 1; fi; echo "$out" | grep -q 'm3-standin' || { echo "FAIL: running job not named"; kill $S; exit 1; }; [ -z "$(docker ps --filter name=^atr-llm$ -q)" ] || { echo "FAIL: a server was started"; kill $S; exit 1; }; kill $S; wait $S 2>/dev/null || true; $PY -m atr.local.launch $D --dry-run; rm -f $D; echo PASS`

### Task 5: UPDATE Target A's private manifests (outside the repository)

- **ACTION**: In each of `~/atr/manifests/target-a/task-01.toml`, `task-02.toml` and `task-03.toml`, add `agent_allowed_hosts_local` to the `[network]` section: the manifest's `agent_allowed_hosts` without `api.anthropic.com`, with `host.docker.internal` (already present for the Collector). Build each local variant with `$PY -m atr.tasks.build ~/atr/manifests/target-a/task-0N.toml --route local` into `~/atr/data/tasks/target-a/task-0N-local`. Do not run them. Write nothing about Target A's hosts, files or content into the repository or the report beyond the count of variants built. Delivers AC-A2.
- **MIRROR**: `harness/src/atr/tasks/build.py:108-112`
- **VALIDATE**: `python3 -c "import tomllib,glob,os; fs=sorted(glob.glob(os.path.expanduser('~/atr/data/tasks/target-a/task-0*-local/task.toml'))); assert len(fs)==3, len(fs); bad=[f for f in fs if (lambda a: a.get('network_mode')!='allowlist' or 'api.anthropic.com' in a.get('allowed_hosts',[]) or 'host.docker.internal' not in a.get('allowed_hosts',[]))(tomllib.load(open(f,'rb'))['agent'])]; assert not bad, len(bad); print('PASS', len(fs))"`

### Task 6: RUN the launcher's check run on the synthetic task

- **ACTION**: Using the check-run config written in Task 4, make sure the Collector is up, do not load `~/atr/.env`, and run `$PY -m atr.local.launch ~/atr/local/lc-p4-launcher-l-small-synthetic-task-01-local.json` in the background, waiting for it to end. The run is expected to end with the chat-template error found in Phase 3; that is recorded, not fixed. Then confirm the trial folder holds `server/server.json`, `server/slots.json`, `server/metrics.prom`, `server/server.log`, `server/power.csv` and `server/power.json`, that the job folder holds `launch.json`, that no `atr-llm` container is left and that `server.key` is gone. Delivers AC-A3.
- **MIRROR**: `harness/src/atr/local/bench.py:55-66`
- **VALIDATE**: `python3 -c "import json,glob,os; j=os.path.expanduser('~/atr/data/jobs/lc-p4-launcher-l-small-synthetic-task-01-local/'); ts=[t for t in glob.glob(j+'*/') if os.path.exists(t+'config.json') or os.path.exists(t+'result.json')]; assert ts, 'no trial'; t=ts[0]; need=['server.json','slots.json','metrics.prom','server.log','power.csv','power.json']; miss=[n for n in need if not os.path.exists(t+'server/'+n)]; assert not miss, miss; p=json.load(open(t+'server/power.json')); assert p['samples']>0 and p['energy_wh']>0; assert os.path.exists(j+'launch.json'); assert not os.path.exists(os.path.expanduser('~/atr/data/local-inference/server.key')); print('PASS', p['samples'], p['energy_wh'])" && [ -z "$(docker ps --filter name=^atr-llm$ -q)" ]`

### Task 7: UPDATE documentation/research/local-route.md

- **ACTION**: Add a section `## Launcher and allowlists` after "Agent route": the launcher's command, its refusals (another Harbor job running, a job that is not local, an unmapped model, an existing job folder) and what it writes into each trial and job folder; the allowlist variants (`--route local`, the `agent_allowed_hosts_local` key, the derivation when the key is absent), the synthetic task's local allowlist and that Target A's three variants were built in the private workspace (count only); the check run's result (job name, outcome, power samples, energy, the records present) and the refusal check. Update the Progress table (WP2: the launcher and allowlists done). Use "Target A" only as a codename and name no host of Target A. Delivers AC-A5.
- **MIRROR**: `documentation/research/local-route.md:1-20`
- **VALIDATE**: `set -euo pipefail; f=$CODE_ROOT/documentation/research/local-route.md; grep -q '^## Launcher and allowlists' $f; grep -q 'atr.local.launch' $f; grep -q -- '--route local' $f; grep -q 'power.json' $f; echo PASS`

### Task 8: VERIFY privacy on every new and changed file

- **ACTION**: Run the leak check (word match, as the exporter's) over `build.py`, `launch.py`, `task-01.toml` and the report; confirm that the repository's diff holds no Target A host or file name (the private manifests changed only in `~/atr`), and that the check run's `launch.json`, `power.json` and `<job>.launch.log` hold no server key (check while the key file exists, or against the key captured before the launcher stopped the server; the launcher can print a key digest for this, never the key). Delivers AC-A5.
- **MIRROR**: `harness/src/atr/local/serve.py:125-128`
- **VALIDATE**: `set -euo pipefail; files="$CODE_ROOT/harness/src/atr/tasks/build.py $CODE_ROOT/harness/src/atr/local/launch.py $CODE_ROOT/targets/synthetic-events/task-01.toml $CODE_ROOT/documentation/research/local-route.md"; if grep -lwiF -f <(grep -vE '^(#|[[:space:]]*$)' ~/atr/data/leak-terms.txt) $files; then echo "FAIL: private term"; exit 1; fi; echo PASS`

## Validation Commands

`$CODE_ROOT` and `$PY` as in the Step-by-Step Tasks.

### Level 1: STATIC_ANALYSIS

```bash
set -euo pipefail
cd $CODE_ROOT/harness
$PY -m py_compile src/atr/tasks/build.py src/atr/local/launch.py src/atr/local/serve.py src/atr/local/bench.py
$PY -c "import tomllib; tomllib.load(open('../targets/synthetic-events/task-01.toml','rb')); print('manifest ok')"
$PY -m atr.local.launch --help > /dev/null
$PY -m atr.tasks.build --help > /dev/null
echo PASS
```

### Level 2: CONTENT_INVARIANTS

```bash
set -euo pipefail
cd $CODE_ROOT/harness
# AC-8: the local allowlist never names Anthropic's API and always names the local server's host.
$PY -c "
from atr.tasks.build import local_hosts
assert local_hosts({'agent_allowed_hosts':['api.anthropic.com','host.docker.internal','pypi.org']})==['host.docker.internal','pypi.org']
assert local_hosts({}) is None
print('allowlist ok')"
# The default synthetic build is unchanged (open network) and the local one has an allowlist.
python3 -c "import tomllib,os; b=os.path.expanduser('~/atr/data/tasks/synthetic-events/'); assert 'network_mode' not in tomllib.load(open(b+'task-01/task.toml','rb'))['agent']; a=tomllib.load(open(b+'task-01-local/task.toml','rb'))['agent']; assert a['network_mode']=='allowlist' and 'api.anthropic.com' not in a['allowed_hosts']; print('variants ok')"
# AC-7: a job that is not local is refused before anything starts.
echo '{"job_name":"m3-not-local","jobs_dir":"/tmp","agents":[{"name":"x","model_name":"claude-sonnet-5-5","kwargs":{}}],"tasks":[]}' > /tmp/atr-launch-bad.json
if $PY -m atr.local.launch /tmp/atr-launch-bad.json --dry-run; then echo "FAIL: non-local job accepted"; exit 1; fi
# Privacy: no private term (word match, as the exporter's leak check) in the files this phase changes or creates.
files="src/atr/tasks/build.py src/atr/local/launch.py ../targets/synthetic-events/task-01.toml ../documentation/research/local-route.md"
if grep -lwiF -f <(grep -vE '^(#|[[:space:]]*$)' ~/atr/data/leak-terms.txt) $files; then echo "FAIL: private term in a changed file"; exit 1; fi
echo PASS
```

### Level 3: INTEGRATION

```bash
set -euo pipefail
cd $CODE_ROOT/harness
# AC-7 refusal against a stand-in for a running MVP job, then the dry run passes once it is gone.
# The check run (Task 6) created its job folder, which the launcher must refuse (Task 3 check (d)),
# so the stand-in and post-kill dry runs use a copy of its config with a fresh job name.
C=~/atr/local/lc-p4-launcher-l-small-synthetic-task-01-local.json
D=$(mktemp /tmp/lc-p4-dryrun-XXXXXX.json)
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); d['job_name']+='-dryrun-'+sys.argv[3]; json.dump(d,open(sys.argv[2],'w'))" $C $D $$
bash -c 'exec -a "harbor run -c /root/atr/m3/m3-standin.json -y" sleep 120' & S=$!
sleep 1
if $PY -m atr.local.launch $D --dry-run; then kill $S; echo "FAIL: launched beside a running job"; exit 1; fi
[ -z "$(docker ps --filter name=^atr-llm$ -q)" ] || { kill $S; echo "FAIL: a server was started"; exit 1; }
kill $S; wait $S 2>/dev/null || true
$PY -m atr.local.launch $D --dry-run
rm -f $D
# Task 3 check (d): the check run's existing job folder is refused.
if $PY -m atr.local.launch $C --dry-run; then echo "FAIL: an existing job folder was accepted"; exit 1; fi
# The check run's records (Task 6) are in its trial folder.
python3 -c "import glob,os; t=[x for x in glob.glob(os.path.expanduser('~/atr/data/jobs/lc-p4-launcher-l-small-synthetic-task-01-local/*/')) if os.path.exists(x+'server/power.json')]; assert t, 'no trial with power samples'; print('records ok')"
echo PASS
```

## Acceptance Criteria

- **AC-A1 (PRD AC-8):** `atr.tasks.build --route local` builds `<task id>-local` whose agent allowlist comes from `network.agent_allowed_hosts_local`, or from the agent allowlist without `api.anthropic.com` and with `host.docker.internal`; it refuses to build a local variant without an allowlist or with Anthropic's API in it; the default build is unchanged.
- **AC-A2 (PRD AC-8):** The synthetic task's local variant and Target A's three local variants are built, each with an agent allowlist that names `host.docker.internal` and not `api.anthropic.com`; Target A's manifests and builds stay outside the repository.
- **AC-A3 (PRD AC-7, Phase 4 success signal):** `atr.local.launch` starts the job's server with a new key, samples GPU power for the whole job, runs Harbor without any `ANTHROPIC_` variable in its environment, writes the server's record, slots, metrics, log and the power samples with their summary into every trial folder and `launch.json` into the job folder, and always stops the server.
- **AC-A4 (PRD AC-7):** While another Harbor job runs, `atr.local.launch` refuses, names that job and starts nothing; it also refuses a job that is not local, a model it cannot map to one pinned entry and an existing job folder.
- **AC-A5 (PRD AC-7, AC-8):** `documentation/research/local-route.md` records the launcher, the variants and the check run, and no changed file or run record holds a private term, a Target A host or the server key.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The process check misses an MVP batch started another way (a batch script waiting between runs) | M | M | The check covers every `harbor run` process; the report states the limit; the budget's `lc-` filter in Phase 5 keeps the money apart either way |
| The agent's install step needs a host the local allowlist does not name | M | M | The MVP's allowlisted runs install the same way; the check run shows it; a failure is recorded and the allowlist fixed in the manifest |
| The check run ends early on the chat-template error, so the power samples cover only a few minutes | H | L | Expected; the launcher is what is checked; the template is Phase 6's |
| `nvidia-smi` power under WSL 2 is the driver's average, not an instantaneous reading | M | L | Energy integrates over the measured sample times, as in Phase 1; whole-system energy stays a Could item |
| The launcher is interrupted and leaves the server running | L | M | `finally` stops it; `serve stop` is idempotent; the next launch's `serve.start` also stops any old server first |

## Notes

- **TDD routing (this plan, against the relay repo):** Current value of `tdd` in `docs/context/methodology.md`: **false**. Test-after ordering — when a test framework is declared, the test pair (test-writer/test-reviewer) authors and maintains the suite from the Acceptance Criteria above, after the Implementer + Code Review; with no framework declared, no tests are authored.
- No test framework is declared (`test_frameworks: []`), so no test files are authored; the `VALIDATE` commands exercise the builder and the launcher directly, and the check run exercises the launcher end to end.
- Research for this plan: Harbor applies a task's `[agent]` network policy only to `agent.run()`; `agent.setup()`, where the agent's SDK is installed, uses the environment's baseline, so the local allowlist does not need the installer's hosts (docs.harborframework.com, network policies). `GpuSampler` keeps monotonic times only, so the launcher records the job's wall-clock start and end in `power.json` and the samples as seconds from the start. nvidia-smi's power readings are accurate to about 5% of the reading and averaged by the driver (arXiv 2312.02741), which is why energy is reported as a GPU estimate. No code detects a running Harbor job yet (`cleanup.unfinished_trials` cannot tell a running job from a killed one), so the launcher checks processes.
- The check run calls no Anthropic API: the job is local, the launcher removes every `ANTHROPIC_` variable from Harbor's environment, and `~/atr/.env` is not loaded.

*Generated: 2026-11-04*
*Approved: 2026-11-04*
*Implemented: 2026-11-04*
*Status: IMPLEMENTED*
