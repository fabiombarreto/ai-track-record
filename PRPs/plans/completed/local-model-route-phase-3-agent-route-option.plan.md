# Feature: Agent route option (Phase 3 of local-model-route)

```
**Decision Gate**
- Active context: none
- Activated criteria: business rules for runs and local inference (docs/domain/areas/runs.md, docs/domain/areas/local-inference.md); change of a component (atr.agents.claude_sdk, the Harbor agent); cross-cutting pattern (a per-trial record next to agent/workflow.json; a pre-flight check like _check_collector); configuration as a job-config value (D-005)
- Decisions found:
  - Claude Code through the Agent SDK is the only harness (D-017, D-049); the local route changes where it sends requests, not the harness
  - Route to open-weight models (D-031, Proposed) and Target A on local open-weight models (D-057): on the local route the task container gets no Anthropic key, and every model alias names the model under test
  - Pin everything and fail instead of silently dropping an option (D-020): the route's settings are recorded in agent/route.json, and a run whose server does not match the job's model fails
  - Run folders are the system of record (D-033): agent/route.json is written into the trial's agent folder before the first model call
  - Normalized outcomes (D-019): a server that does not answer, or rejects the run's key, fails the trial before any model request
  - Synthetic task first (D-046): the check run of this phase is on the public synthetic task
- Applicable anti-patterns:
  - Sending Target A's content to a provider that is not allowed (the local route sends nothing to Anthropic's API; the check run is on the synthetic task)
  - Secrets in the repository or in a record (the server key reaches the container only through the run's environment, never route.json, a command string or a log)
  - Silently dropping a configuration option (an unknown route, a missing server record or a model that differs from the server's alias fails the run)
  - Running two benchmark runs at the same time (no check run while another Harbor job runs; D-058)
- Applicable architectural rules:
  - Configuration, not code (D-005): the route is a job-config option of the agent; without it, runs behave exactly as today
  - Graders sit outside the workflow and stay unchanged
  - Fail closed on checks that guard correctness or privacy (pre-flight check, model match, key absent from records)
  - Container-side code stays standard-library only; host-side code follows docs/context/conventions.md
- Result: PROCEED
```

## Source

- `PRPs/prds/local-model-route.prd.md` — Implementation Phases row 3: "Agent route option" — Goal: Claude Code reaches the local model, and nothing else, with the settings recorded. — Success signal: A vanilla run with L-Small on the synthetic task reaches the server and finishes.

## Summary

This phase adds a `route` option to the Harbor agent `atr.agents.claude_sdk`. With `route: "local"`, the agent reads the running server's record and key from `$ATR_DATA_DIR/local-inference`, checks that the job's model is the server's alias, and builds Claude Code's environment for the local server: `ANTHROPIC_BASE_URL` at `http://host.docker.internal:<port>`, the server's key as `ANTHROPIC_AUTH_TOKEN`, no `ANTHROPIC_API_KEY`, the session, Opus, Sonnet, Haiku, Fable and sub-agent models all set to the alias, the context and compaction window equal to the server's context, the request and stream timeouts raised to the run's time limit, the attribution header and experimental betas off. Before any model call, a pre-flight check from inside the task container proves the container has no Anthropic key, the server answers with the run's key and serves the alias; otherwise the trial fails and names the cause. The agent writes `agent/route.json` with the provider, the server's image digest and build, the model file and its SHA-256, the quantization, the flags, the sampling and the thinking setting, and the route's settings without the key. A vanilla check run with L-Small on the synthetic task proves the route end to end.

## User Story

As the operator of AI Track Record
I want a job config to name the local route and a local model, and have the run reach only that model with its settings recorded
So that a local run is configured the same way as an MVP run and proves which model, file and flags it used

## Problem Statement

The agent can only run on Anthropic's API: it refuses to start without `ANTHROPIC_API_KEY` and has no option for another endpoint (`harness/src/atr/agents/claude_sdk.py:229-231`). It pins only the Haiku alias besides the session and sub-agent models (`claude_sdk.py:234-240`), so a request for the Opus, Sonnet or Fable alias would name a Claude model. Claude Code assumes a 200K window for a model it does not know, and waits only ten minutes for a request and five on an idle stream behind a custom base URL, while a 128k prompt takes up to 33 minutes on L-Small at 66 tokens/s (`documentation/research/local-route.md`, L-Small table). Nothing records which server, model file and flags a run used.

## Solution Statement

Add the route option and three helpers to the agent, following the existing patterns: a pure method that builds the route's environment (so it can be checked without Harbor), a pre-flight check modelled on `_check_collector`, and a record writer modelled on `_record_workflow`. Leave the Anthropic route byte-for-byte as it is. Write a job config for the check run in the private workspace, run it against a server started with `atr.local.serve`, and record the outcome.

## Metadata

| Key | Value |
|---|---|
| Type | Enhancement (agent option) + check run |
| Complexity | Medium |
| Systems Affected | harness/src/atr/agents/claude_sdk.py; a job config in ~/atr/local/ (outside the repository); documentation/research/local-route.md |
| Dependencies | Phase 2 complete: `atr.local.serve start/record/stop`, `server.json` and `server.key` in `$ATR_DATA_DIR/local-inference`; Harbor 0.24.0 at `~/atr/tools/harbor`; the synthetic task built at `~/atr/data/tasks/synthetic-events/task-01`; the OpenTelemetry Collector |
| Estimated Tasks | 7 |
| Source PRD line ref | `PRPs/prds/local-model-route.prd.md:64-65` (AC-4, AC-5), `:167` (row 3), `:188-191` (Phase 3 details) |
| phase_type | feature |

## Mandatory Reading

| Priority | Path | Lines | Why |
|---|---|---|---|
| P0 | `PRPs/prds/local-model-route.prd.md` | 64-65, 167, 188-191 | AC-4, AC-5 and the Phase 3 scope and success signal |
| P0 | `documentation/plans/local-models.md` | 133-142 | The run's settings for the local route |
| P0 | `harness/src/atr/agents/claude_sdk.py` | 32-64, 127-131, 171-217, 219-280 | Options, `_model()`, `_check_collector`, `_record_workflow`, `run()` |
| P0 | `harness/src/atr/local/serve.py` | 130-224 | What `server.json` holds and where `server.key` is |
| P1 | `harness/src/atr/local/config.py` | 1-34 | `data_dir()` for the server's records |
| P1 | `harness/src/atr/agents/claude_sdk_runner.py` | 43-63 | The options the runner passes to the SDK (model, budget) |
| P1 | `harness/src/atr/store/load.py` | 165-182 | How a trial exception becomes an outcome |
| P1 | `docs/domain/areas/local-inference.md` | all | The area's rules |
| P2 | `docs/development.md` | 1-30 | How a Harbor job is run from WSL |

## Patterns to Mirror

```python
# SOURCE: harness/src/atr/agents/claude_sdk.py:171-191
    async def _check_collector(self, environment: BaseEnvironment, endpoint: str) -> None:
        """Fail the trial before any API call if the telemetry Collector does not answer.

        An empty OTLP request gets 200 and records nothing. Without this check a
        run would lose its telemetry without notice.
        """
        url = shlex.quote(f"{endpoint.rstrip('/')}/v1/logs")
        result = await environment.exec(
            command=(
                f"curl -sS -m 10 -o /dev/null -w '%{{http_code}}' -X POST {url} "
                "-H 'Content-Type: application/json' -d '{}'"
            )
        )
        # The exec may merge curl's error text into stdout; the status code is last.
        lines = (result.stdout or "").strip().splitlines() or [""]
        status, detail = lines[-1], " ".join(lines[:-1] + [(result.stderr or "").strip()])
        if result.return_code != 0 or status != "200":
            raise RuntimeError(
                f"telemetry Collector at {endpoint} did not answer "
                f"(HTTP {status or 'none'}): {detail.strip()[-500:]}"
            )
```
Mirrored by Task 2 for the local server's pre-flight check; the key goes through the exec's `env`, never into the command string.

```python
# SOURCE: harness/src/atr/agents/claude_sdk.py:193-199
    async def _record_workflow(self, environment: BaseEnvironment) -> None:
        """Write workflow.json: the plugin's name and version, and a digest of its files.

        Two copies of a plugin can share a version number, so the digest tells
        them apart. A run without a plugin is vanilla.
        """
        record: dict = {"workflow": "vanilla", "version": None, "digest": None}
```
```python
# SOURCE: harness/src/atr/agents/claude_sdk.py:217
        (self.logs_dir / "workflow.json").write_text(json.dumps(record, indent=2))
```
Mirrored by Task 3 for `route.json`, with a key-absent check before writing.

```python
# SOURCE: harness/src/atr/agents/claude_sdk.py:229-249
        api_key = self._get_env("ANTHROPIC_API_KEY")
        if api_key is None:
            raise ValueError("ANTHROPIC_API_KEY must be set")
        model = self._model()
        await self._record_workflow(environment)
        env = {
            "ANTHROPIC_API_KEY": api_key,
            "ANTHROPIC_MODEL": model,
            "CLAUDE_CODE_SUBAGENT_MODEL": model,
            "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
            # Background calls, such as WebFetch's summary, use the haiku alias.
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": model,
            "DISABLE_AUTOUPDATER": "1",
            "DISABLE_ERROR_REPORTING": "1",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
            # Lets bypassPermissions run as root inside the container.
            "IS_SANDBOX": "1",
            # Keeps the session transcripts in the synced logs folder.
            "CLAUDE_CONFIG_DIR": f"{LOGS_DIR}/claude-config",
        }
```
Split by Task 1: the shared part stays; the route decides the key and model variables.

```python
# SOURCE: harness/src/atr/local/serve.py:213-216
    serialized = json.dumps(record, indent=2)
    if key in serialized:
        stop()
        raise SystemExit("the key appears in the server record; nothing was written")
```
Mirrored by Task 3 (`route.json` is not written if the key would appear in it).

## Files to Change

| File | Action | Justification |
|---|---|---|
| `harness/src/atr/agents/claude_sdk.py` | UPDATE | AC-4: the `route` option and the local route's environment; AC-5: the pre-flight check; AC-4: `agent/route.json` |
| `~/atr/local/lc-p3-vanilla-l-small-synthetic-task-01.json` (WSL, outside the repository) | CREATE | The check run's Harbor job config |
| `documentation/research/local-route.md` | UPDATE | The route's settings and the check run's result |

## NOT Building (Scope Limits)

- The local launcher (a server per run, power sampling, the copy of the server's record into the trial folder, the MVP-priority refusal) and the allowlist variants — Phase 4. In this phase the server is started and stopped by hand around the check run, and `serve record` is called by hand.
- Store, budget and export changes, including mapping the pre-flight failure to an infrastructure-error outcome in the store — Phase 5. Here the trial fails with Harbor's exception, which names the cause.
- Checks L2 to L10 — Phase 6. The check run's records are kept for them.
- The independent review of the check run, which calls Anthropic's API — not in this phase; it needs the operator's approval.
- Any change to the runner (`claude_sdk_runner.py`) or the graders.

## Step-by-Step Tasks

All WSL commands run as `wsl.exe -d Ubuntu --exec bash -lc '<command>'` (never starting the string with `/`). `$CODE_ROOT` is the phase's code root seen from WSL (`/mnt/c/repos/ai-track-record/.worktrees/local-model-route`). `$PY="env PYTHONPATH=src $HOME/atr/tools/harness-venv/bin/python"` runs from `$CODE_ROOT/harness`; `$HPY="env PYTHONPATH=$CODE_ROOT/harness/src uv run --project $HOME/atr/tools/harbor python"` runs Python with Harbor importable (the agent module imports Harbor). Git commands on the worktree run from Windows (`git -C C:/repos/ai-track-record/.worktrees/local-model-route ...`).

### Task 1: UPDATE harness/src/atr/agents/claude_sdk.py (route option and environment)

- **ACTION**: (a) Add options: `route: Literal["anthropic", "local"] = "anthropic"`; `local_base_url: str = "http://host.docker.internal:8090"` (the server as the task container reaches it; its port must equal the server record's `port`); `local_timeout_ms: int = 10_800_000` (request and idle-stream timeouts on the local route: the run's three-hour limit). (b) `_model()` also strips a `local/` prefix. (c) Add a method `_route_env(self, model: str, server: dict | None, key: str | None) -> dict[str, str]` that returns the route's variables only. On `anthropic`: `ANTHROPIC_API_KEY` from `self._get_env` (raising `ValueError` as today when it is missing), `ANTHROPIC_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` and `ANTHROPIC_DEFAULT_HAIKU_MODEL`, exactly today's values. On `local`: no `ANTHROPIC_API_KEY`; `ANTHROPIC_BASE_URL=<local_base_url>`; `ANTHROPIC_AUTH_TOKEN=<key>`; `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_FABLE_MODEL` and `CLAUDE_CODE_SUBAGENT_MODEL` all `<model>`, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`; `CLAUDE_CODE_MAX_CONTEXT_TOKENS` and `CLAUDE_CODE_AUTO_COMPACT_WINDOW` both the server record's `context`; `API_TIMEOUT_MS` and `CLAUDE_STREAM_IDLE_TIMEOUT_MS` both `local_timeout_ms`; `CLAUDE_CODE_ATTRIBUTION_HEADER=0`; `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`. (d) Add `_local_server(self, model: str) -> tuple[dict, str]` that reads `server.json` and `server.key` from `atr.local.config.data_dir()` and raises `RuntimeError` naming the problem when either is missing, when the record's `alias` differs from `model`, or when the port in `local_base_url` differs from the record's `port`. (e) In `run()`, build `env` from `_route_env(...)` merged with the shared variables (`DISABLE_AUTOUPDATER` and the rest, unchanged), so the Anthropic route's environment is identical to today's. Delivers AC-A1.
- **MIRROR**: `harness/src/atr/agents/claude_sdk.py:229-249`
- **VALIDATE**: `cd $CODE_ROOT/harness && $HPY -c "
import os, json, tempfile, pathlib
os.environ['ANTHROPIC_API_KEY']='sk-test-dummy'
from atr.agents.claude_sdk import ClaudeAgentSdk
a=ClaudeAgentSdk.__new__(ClaudeAgentSdk); a._resolved_env_vars={}; a._extra_env={}
from atr.agents.claude_sdk import ClaudeAgentSdkOptions
a.options=ClaudeAgentSdkOptions(route='local')
srv={'alias':'qwen3.5-9b','context':131072,'port':8090}
e=a._route_env('qwen3.5-9b', srv, 'k-test')
assert 'ANTHROPIC_API_KEY' not in e, 'key leaked'
assert e['ANTHROPIC_BASE_URL']=='http://host.docker.internal:8090' and e['ANTHROPIC_AUTH_TOKEN']=='k-test'
assert all(e[v]=='qwen3.5-9b' for v in ('ANTHROPIC_MODEL','ANTHROPIC_DEFAULT_OPUS_MODEL','ANTHROPIC_DEFAULT_SONNET_MODEL','ANTHROPIC_DEFAULT_HAIKU_MODEL','ANTHROPIC_DEFAULT_FABLE_MODEL','CLAUDE_CODE_SUBAGENT_MODEL'))
assert e['CLAUDE_CODE_MAX_CONTEXT_TOKENS']==e['CLAUDE_CODE_AUTO_COMPACT_WINDOW']=='131072' and e['CLAUDE_CODE_ATTRIBUTION_HEADER']=='0'
a.options=ClaudeAgentSdkOptions()
e2=a._route_env('claude-sonnet-5-5', None, None)
assert e2['ANTHROPIC_API_KEY']=='sk-test-dummy' and 'ANTHROPIC_BASE_URL' not in e2
print('PASS')"`

### Task 2: UPDATE harness/src/atr/agents/claude_sdk.py (pre-flight check)

- **ACTION**: Add `async def _check_local_server(self, environment, env: dict[str, str]) -> None`, run in `run()` on the local route after `_local_server` and before the runner starts. It executes, inside the task container with the run's `env` passed through `environment.exec(..., env=env)` (never in the command string): (1) `[ -z "${ANTHROPIC_API_KEY:-}" ]` — fail if the container has an Anthropic key; (2) `curl -sS -m 10 -o /dev/null -w '%{http_code}' -X POST "$ANTHROPIC_BASE_URL/v1/messages/count_tokens" -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" -H 'Content-Type: application/json' -d '{"model":"<model>","messages":[{"role":"user","content":"ping"}]}'` — fail unless 200; (3) `curl -sS -m 10 "$ANTHROPIC_BASE_URL/v1/models" -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN"` — fail unless the JSON lists `<model>`. Each failure raises `RuntimeError` naming the cause: "the task container has ANTHROPIC_API_KEY set", "the local server at <url> did not answer (HTTP none)", "the local server at <url> rejected the run's key (HTTP 401)", "the local server at <url> answered HTTP <n>", "the local server serves <ids>, not <model>". The messages never contain the key. Parse the status the way `_check_collector` does (the code is the last line). Delivers AC-A2.
- **MIRROR**: `harness/src/atr/agents/claude_sdk.py:171-191`
- **VALIDATE**: `cd $CODE_ROOT/harness && $HPY -c "
import asyncio, os, subprocess, types
from atr.agents.claude_sdk import ClaudeAgentSdk, ClaudeAgentSdkOptions
class Env:
    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        p=subprocess.run(['bash','-c',command], capture_output=True, text=True, env={**os.environ, **(env or {})})
        return types.SimpleNamespace(return_code=p.returncode, stdout=p.stdout, stderr=p.stderr)
a=ClaudeAgentSdk.__new__(ClaudeAgentSdk); a._resolved_env_vars={}; a._extra_env={}; a.options=ClaudeAgentSdkOptions(route='local', local_base_url='http://127.0.0.1:8099')
env={'ANTHROPIC_BASE_URL':'http://127.0.0.1:8099','ANTHROPIC_AUTH_TOKEN':'k-test','ANTHROPIC_MODEL':'qwen3.5-9b'}
os.environ.pop('ANTHROPIC_API_KEY', None)
try: asyncio.run(a._check_local_server(Env(), env)); raise SystemExit('FAIL: no error on an unreachable server')
except RuntimeError as e: assert 'did not answer' in str(e) and 'k-test' not in str(e), e
os.environ['ANTHROPIC_API_KEY']='sk-test-dummy'
try: asyncio.run(a._check_local_server(Env(), env)); raise SystemExit('FAIL: no error with a key in the container')
except RuntimeError as e: assert 'ANTHROPIC_API_KEY' in str(e), e
print('PASS')"`

### Task 3: UPDATE harness/src/atr/agents/claude_sdk.py (agent/route.json)

- **ACTION**: Add `_record_route(self, model: str, server: dict | None, env: dict[str, str]) -> None`, called in `run()` after the pre-flight check and before the runner starts, that writes `self.logs_dir / "route.json"`. On `anthropic`: `{"provider": "anthropic", "model": <model>}`. On `local`: `provider` `local`, `model` (the alias), `base_url`, and from the server record `model_id`, `repo`, `revision`, `file`, `size`, `sha256`, `image`, `image_id`, `build`, `commit`, `context`, `args`, `published`, `machine` and `started_at`; `quantization` (the part of the model id after the model name, for example `q4_k_m`, `ud-q3_k_xl`, taken from the file name's last dash-separated part, lower-cased, without `.gguf`); `sampling` parsed from `args` (`--temp`, `--top-p`, `--top-k`, `--min-p`, `--presence-penalty`, as numbers); `thinking` (the `enable_thinking` value of `--chat-template-kwargs`, or `null`); and `settings`, the route's environment from `_route_env` with `ANTHROPIC_AUTH_TOKEN` replaced by `"<set>"`. Before writing, fail with `RuntimeError` if the key string appears anywhere in the serialized record. Delivers AC-A3.
- **MIRROR**: `harness/src/atr/agents/claude_sdk.py:193-217` and `harness/src/atr/local/serve.py:213-216`
- **VALIDATE**: `cd $CODE_ROOT/harness && $HPY -c "
import json, tempfile, pathlib
from atr.agents.claude_sdk import ClaudeAgentSdk, ClaudeAgentSdkOptions
a=ClaudeAgentSdk.__new__(ClaudeAgentSdk); a._resolved_env_vars={}; a._extra_env={}; a.options=ClaudeAgentSdkOptions(route='local'); a.logs_dir=pathlib.Path(tempfile.mkdtemp())
srv={'alias':'qwen3.5-9b','model_id':'qwen3.5-9b-q4_k_m','file':'Qwen3.5-9B-Q4_K_M.gguf','sha256':'0'*64,'size':1,'repo':'r','revision':'v','image':'i','image_id':'sha256:x','build':'b12063','commit':'c','context':131072,'port':8090,'published':['127.0.0.1:8090'],'machine':{},'started_at':'t','args':['--temp','0.6','--top-p','0.95','--top-k','20','--min-p','0','--presence-penalty','0','--chat-template-kwargs','{\"enable_thinking\":true}']}
env=a._route_env('qwen3.5-9b', srv, 'k-secret-test')
a._record_route('qwen3.5-9b', srv, env)
r=json.loads((a.logs_dir/'route.json').read_text())
assert r['provider']=='local' and r['quantization']=='q4_k_m' and r['sampling']['temp']==0.6 and r['thinking'] is True and r['sha256']=='0'*64 and r['build']=='b12063'
assert 'k-secret-test' not in (a.logs_dir/'route.json').read_text()
print('PASS')"`

### Task 4: CREATE the check run's job config (outside the repository)

- **ACTION**: Write `~/atr/local/lc-p3-vanilla-l-small-synthetic-task-01.json` in WSL, in the shape of the MVP's vanilla job configs: `job_name` `lc-p3-vanilla-l-small-synthetic-task-01`, `jobs_dir` `/root/atr/data/jobs`, `n_concurrent_trials` 1, `quiet` true, `environment` `{"type": "docker"}`; one agent `atr.agents.claude_sdk:ClaudeAgentSdk` with `model_name` `local/qwen3.5-9b` and kwargs `route` `local`, `cwd` `/app`, `config_label` `vanilla-l-small`, `otel_endpoint` `http://host.docker.internal:4318`, `disallowed_tools` `["WebSearch", "WebFetch"]` (D-050, as the MVP), and no `max_budget_usd` (Claude Code has no price for a local model; check L8 studies the cap in Phase 6); the task `/root/atr/data/tasks/synthetic-events/task-01` (its three-hour agent limit is the MVP's). Delivers AC-A4.
- **MIRROR**: `harness/src/atr/agents/claude_sdk.py:32-64`
- **VALIDATE**: `python3 -c "import json,os; d=json.load(open(os.path.expanduser('~/atr/local/lc-p3-vanilla-l-small-synthetic-task-01.json'))); a=d['agents'][0]; assert d['job_name'].startswith('lc-') and a['model_name']=='local/qwen3.5-9b' and a['kwargs']['route']=='local' and 'max_budget_usd' not in a['kwargs'] and d['tasks'][0]['path'].endswith('synthetic-events/task-01'); print('PASS')"`

### Task 5: RUN the check run with L-Small on the synthetic task

- **ACTION**: First make sure no other Harbor job is running (`pgrep -f 'harbor run'` finds nothing other than this check; if one runs, stop and report — D-058) and the Collector is up (`docker compose -f $CODE_ROOT/infra/otel-collector/docker-compose.yaml up -d`). Do not load `~/atr/.env`: the check run needs no Anthropic key, and its absence from the host process means a mistake cannot reach Anthropic's API. Then: `$PY -m atr.local.serve start qwen3.5-9b-q4_k_m` (from `$CODE_ROOT/harness`); from `~/atr/tools/harbor`, `HARBOR_TELEMETRY=off PYTHONPATH=$CODE_ROOT/harness/src uv run harbor run -c ~/atr/local/lc-p3-vanilla-l-small-synthetic-task-01.json -y` in the background, waiting for it to end (up to the task's three-hour limit; L-Small is expected to take 25–60 minutes); after it ends and before stopping the server, `$PY -m atr.local.serve record <trial dir>/server` to keep the server's record, slots, metrics and log with the trial; then `$PY -m atr.local.serve stop`. If the trial fails, keep every record, note the cause from the trial's `result.json` and `agent/runner.txt`, and do not retry more than once. Delivers AC-A4.
- **MIRROR**: `harness/src/atr/agents/claude_sdk.py:250-252`
- **VALIDATE**: `python3 -c "import json,glob,os; ts=[t for t in glob.glob(os.path.expanduser('~/atr/data/jobs/lc-p3-vanilla-l-small-synthetic-task-01/*/')) if os.path.isdir(t+'agent')]; assert ts, 'no trial'; t=sorted(ts)[-1]; r=json.load(open(t+'agent/route.json')); assert r['provider']=='local' and r['model']=='qwen3.5-9b' and 'ANTHROPIC_API_KEY' not in r['settings']; assert os.path.exists(t+'server/server.json'), 'no server record'; res=json.load(open(t+'result.json')); print('PASS', (res.get('exception_info') or {}).get('exception_type'), json.load(open(t+'agent/result.json')).get('subtype') if os.path.exists(t+'agent/result.json') else None)"`

### Task 6: UPDATE documentation/research/local-route.md

- **ACTION**: Add a section `## Agent route` after "Hardened server": the route option and its job-config keys; a table of the local route's environment variables and values with the reason for each (no Anthropic key; base URL and token; every alias pinned; context and compaction at the server's context; request and idle-stream timeouts at the three-hour limit; attribution header and experimental betas off); the pre-flight checks and their failure messages; what `agent/route.json` records. Add the check run's result: job name, model, outcome (the SDK's result subtype or the trial's exception), reward from the verifier, wall time, turns, input and output tokens from `agent/result.json`, and whether the server's log shows requests for the alias only; state that the run's independent review was not run (it calls Anthropic's API and needs the operator's approval). Update the Progress table (WP2 in progress: the route done) and the Compatibility checks table's notes where the check run gives early evidence (L2, L3, L7), without marking those checks as run. Use "Target A" only as a codename; no transcript text in the report. Delivers AC-A5.
- **MIRROR**: `documentation/research/local-route.md:1-20`
- **VALIDATE**: `set -euo pipefail; f=$CODE_ROOT/documentation/research/local-route.md; grep -q '^## Agent route' $f; grep -q 'ANTHROPIC_BASE_URL' $f; grep -q 'route.json' $f; grep -q 'lc-p3-vanilla-l-small-synthetic-task-01' $f; echo PASS`

### Task 7: VERIFY privacy on every new and changed file

- **ACTION**: Run the leak check (word match, as the exporter's) over `claude_sdk.py` and the report, and confirm the check run's `agent/route.json`, `agent/runner.txt` and Harbor's job log hold no server key (check while the key file still exists, before `serve stop` in Task 5, or against the key captured then). Delivers AC-A5.
- **MIRROR**: `harness/src/atr/local/serve.py:213-216`
- **VALIDATE**: `set -euo pipefail; files="$CODE_ROOT/harness/src/atr/agents/claude_sdk.py $CODE_ROOT/documentation/research/local-route.md"; if grep -lwiF -f <(grep -vE '^(#|[[:space:]]*$)' ~/atr/data/leak-terms.txt) $files; then echo "FAIL: private term"; exit 1; fi; echo PASS`

## Validation Commands

`$CODE_ROOT`, `$PY` and `$HPY` as in the Step-by-Step Tasks.

### Level 1: STATIC_ANALYSIS

```bash
set -euo pipefail
cd $CODE_ROOT/harness
$PY -m py_compile src/atr/agents/claude_sdk.py src/atr/agents/claude_sdk_runner.py
$HPY -c "from atr.agents.claude_sdk import ClaudeAgentSdk, ClaudeAgentSdkOptions; o=ClaudeAgentSdkOptions(); assert o.route=='anthropic'; ClaudeAgentSdkOptions(route='local'); print('import ok')"
echo PASS
```

### Level 2: CONTENT_INVARIANTS

```bash
set -euo pipefail
cd $CODE_ROOT/harness
# AC-4: the local route's environment has no Anthropic key and pins every alias; the Anthropic route is unchanged.
$HPY -c "
import os
os.environ['ANTHROPIC_API_KEY']='sk-test-dummy'
from atr.agents.claude_sdk import ClaudeAgentSdk, ClaudeAgentSdkOptions
a=ClaudeAgentSdk.__new__(ClaudeAgentSdk); a._resolved_env_vars={}; a._extra_env={}; a.options=ClaudeAgentSdkOptions(route='local')
e=a._route_env('qwen3.5-9b', {'alias':'qwen3.5-9b','context':131072,'port':8090}, 'k-test')
assert 'ANTHROPIC_API_KEY' not in e and e['CLAUDE_CODE_ATTRIBUTION_HEADER']=='0'
assert len({e[v] for v in ('ANTHROPIC_MODEL','ANTHROPIC_DEFAULT_OPUS_MODEL','ANTHROPIC_DEFAULT_SONNET_MODEL','ANTHROPIC_DEFAULT_HAIKU_MODEL','ANTHROPIC_DEFAULT_FABLE_MODEL','CLAUDE_CODE_SUBAGENT_MODEL')})==1
a.options=ClaudeAgentSdkOptions(); e2=a._route_env('claude-sonnet-5-5', None, None)
assert set(e2)=={'ANTHROPIC_API_KEY','ANTHROPIC_MODEL','CLAUDE_CODE_SUBAGENT_MODEL','CLAUDE_CODE_SUBAGENT_MODEL_FORCE','ANTHROPIC_DEFAULT_HAIKU_MODEL'}, sorted(e2)
print('route env ok')"
# Privacy: no private term (word match, as the exporter's leak check) in the files this phase changes.
files="src/atr/agents/claude_sdk.py ../documentation/research/local-route.md"
if grep -lwiF -f <(grep -vE '^(#|[[:space:]]*$)' ~/atr/data/leak-terms.txt) $files; then echo "FAIL: private term in a changed file"; exit 1; fi
echo PASS
```

### Level 3: INTEGRATION

```bash
set -euo pipefail
cd $CODE_ROOT/harness
# AC-5 against a real server: a wrong key is rejected and an unreachable server fails, both before any model call.
$PY -m atr.local.serve start qwen3.5-9b-q4_k_m > /dev/null
trap '$PY -m atr.local.serve stop' EXIT
$HPY -c "
import asyncio, os, subprocess, types
os.environ.pop('ANTHROPIC_API_KEY', None)
from atr.agents.claude_sdk import ClaudeAgentSdk, ClaudeAgentSdkOptions
class Env:
    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        p=subprocess.run(['bash','-c',command], capture_output=True, text=True, env={**os.environ, **(env or {})})
        return types.SimpleNamespace(return_code=p.returncode, stdout=p.stdout, stderr=p.stderr)
key=open(os.path.expanduser('~/atr/data/local-inference/server.key')).read().strip()
a=ClaudeAgentSdk.__new__(ClaudeAgentSdk); a._resolved_env_vars={}; a._extra_env={}; a.options=ClaudeAgentSdkOptions(route='local', local_base_url='http://127.0.0.1:8090')
good={'ANTHROPIC_BASE_URL':'http://127.0.0.1:8090','ANTHROPIC_AUTH_TOKEN':key,'ANTHROPIC_MODEL':'qwen3.5-9b'}
asyncio.run(a._check_local_server(Env(), good))
try: asyncio.run(a._check_local_server(Env(), {**good, 'ANTHROPIC_AUTH_TOKEN':'wrong'})); raise SystemExit('FAIL: wrong key accepted')
except RuntimeError as e: assert '401' in str(e) and key not in str(e), 'wrong-key message'
try: asyncio.run(a._check_local_server(Env(), {**good, 'ANTHROPIC_MODEL':'other-model'})); raise SystemExit('FAIL: wrong model accepted')
except RuntimeError as e: assert 'other-model' in str(e)
print('pre-flight ok')"
echo PASS
```

## Acceptance Criteria

- **AC-A1 (PRD AC-4):** With `route: "local"`, the environment the agent gives Claude Code has no `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL` at `http://host.docker.internal:<port>`, the server's key as `ANTHROPIC_AUTH_TOKEN`, the session, Opus, Sonnet, Haiku, Fable and sub-agent models all set to the model under test, `CLAUDE_CODE_ATTRIBUTION_HEADER=0`, and the context and compaction window equal to the server's context; without the option, the environment is exactly today's.
- **AC-A2 (PRD AC-5):** On the local route, a check from inside the task container runs before Claude Code starts and fails the trial, naming the cause, when the container has an Anthropic key, the server does not answer, the server rejects the run's key, or the server does not serve the job's model.
- **AC-A3 (PRD AC-4):** `agent/route.json` records the provider `local`, the server's image digest and build, the model file and its SHA-256, the quantization, the server flags, the sampling and the thinking setting, and the route's settings without the key.
- **AC-A4 (PRD AC-4, Phase 3 success signal):** A vanilla run with L-Small on the synthetic task, configured with the local route, reaches the server and finishes, with its `agent/route.json` and the server's record in its trial folder.
- **AC-A5 (PRD AC-4):** `documentation/research/local-route.md` records the route's settings and the check run's result, and no changed file or run record holds a private term or the server key.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Qwen3.5-9B's tool calls break inside Claude Code (PRD Technical Risks, row 1; check L3) | M | M | The run is a check run: a failure is recorded with its cause; the thinking setting and the fallbacks are decided in Phase 6 |
| The run reaches the three-hour limit because the server reprocesses every prompt (check L5) | M | M | Attribution header off; the limit is a measured outcome; the run's records are kept for check L5 |
| Claude Code rejects an unknown model name or sends a beta feature the server does not implement | L | M | `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`; the run's runner log names the error; a failure is recorded |
| The Harbor process holds `ANTHROPIC_API_KEY` from the environment and a bug passes it on | L | H | The check run does not load `~/atr/.env`; the route's environment drops the key; the pre-flight check fails a container that has one |
| The task container cannot reach `host.docker.internal:8090` | L | M | The pre-flight check fails the trial naming the cause; the Collector already uses the same host |

## Notes

- **TDD routing (this plan, against the relay repo):** Current value of `tdd` in `docs/context/methodology.md`: **false**. Test-after ordering — when a test framework is declared, the test pair (test-writer/test-reviewer) authors and maintains the suite from the Acceptance Criteria above, after the Implementer + Code Review; with no framework declared, no tests are authored.
- No test framework is declared (`test_frameworks: []`), so no test files are authored; the `VALIDATE` commands exercise the agent's methods directly, with a stub environment that runs commands on the host, and the check run exercises the whole route. The stubs build the agent with `__new__` and set the two attributes Harbor's constructor sets for `_get_env` (`_resolved_env_vars`, `_extra_env`), so no trial is needed to check the methods.
- Research for this plan (code.claude.com env-vars, model-config and llm-gateway pages): `ANTHROPIC_AUTH_TOKEN` is sent as `Authorization: Bearer`, which llama.cpp accepts, so the pre-flight check sends the key the same way; `ANTHROPIC_API_KEY`, when present, is always used in non-interactive mode, which is why the local route must not set it; `ANTHROPIC_MODEL` is not validated up front, so a wrong name would fail only on the first request, which is why the agent checks it against the server's alias and `/v1/models`; `API_TIMEOUT_MS` bounds the wait for response headers, which on a local server can come only after a long prefill; `CLAUDE_CODE_AUTO_COMPACT_WINDOW` accepts 100,000 to 1,000,000, so 131,072 is valid; `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` removes beta headers and tool-schema fields that gateways reject.
- The check run calls no Anthropic API: the task container gets no Anthropic key, the base URL is the local server, and the host process does not load `~/atr/.env`. Its independent review, which does call Anthropic's API, is not part of this phase.

*Generated: 2026-11-04*
*Approved: 2026-11-04*
*Implemented: 2026-11-04*
*Status: IMPLEMENTED*
