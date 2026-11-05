# Feature: Hardened server (Phase 2 of local-model-route)

```
**Decision Gate**
- Active context: none
- Activated criteria: business rules for local inference (docs/domain/areas/local-inference.md); change of a component (atr.local.serve) and creation of another (atr.local.probe, check L1); cross-cutting pattern (the server record copied into each trial, D-033); pinned configuration (infra/local-inference/models.toml)
- Decisions found:
  - Pin everything and fail instead of silently dropping an option (D-020): the final flags are explicit in models.toml, and a start without them fails
  - Allowed providers for Target A: local open-weight models on the operator's machine (D-029, D-057); the server stays offline and on the loopback, and check L1 runs on a synthetic request with no target content
  - Local models experiment outside the frozen MVP; the MVP keeps priority over the machine (D-058)
  - Run folders are the system of record (D-033): the server record is written into a folder the launcher names (the trial folder in Phase 4)
  - Python 3.12 with uv; English everywhere; planning in documentation/ (D-047, D-010, D-011)
- Applicable anti-patterns:
  - Private-target material in the repository (the probe's request is synthetic; no Target A content in code, fixtures or the report)
  - Secrets in the repository or in a record (the key never reaches server.json, the snapshot files or the check result)
  - Silently dropping a configuration option (a start without --offline, or with a download flag, fails)
  - Prompt text outside the run folder (the server's /slots returns the prompt; the check result and the snapshot drop it)
  - Unpinned versions (the image by digest, the weights by SHA-256, both unchanged)
- Applicable architectural rules:
  - Configuration, not code (D-005): the flags live in models.toml
  - Files first: every check result and server record is a JSON or text file
  - Fail closed on checks that guard correctness or privacy (offline, loopback, key, prompt text in the log)
  - Host-side code follows docs/context/conventions.md (one module per command, docstring with Usage, SystemExit messages, standard library only)
- Result: PROCEED
```

## Source

- `PRPs/prds/local-model-route.prd.md` — Implementation Phases row 2: "Hardened server" — Goal: A server that is pinned, isolated and accountable for each run. — Success signal: Check L1 passes for both main models.

## Summary

This phase settles the server's final flags and makes the server accountable for each run. `models.toml` gains the prompt-cache RAM per main model, the web UI off and the slots endpoint on; `atr.local.serve start` adds an offline check (the start fails without `--offline` or with any download flag) and checks that `/slots` and `/metrics` also refuse requests without the key; a new `serve record <folder>` writes the server's record, its `/slots` and `/metrics` snapshots and its log into a folder the launcher names, without the key and without prompt text. A new module, `atr.local.probe`, runs check L1 of the local models plan against the running server: one streamed Messages API request shaped like Claude Code's, with thinking, system blocks, the full set of Claude Code's built-in tools, a tool result and cache markers, and a unique marker that must not appear in the server's log. Check L1 is run for L-Small and L-MoE, and the results and flags go into `documentation/research/local-route.md`.

## User Story

As the operator of AI Track Record
I want a server whose flags are final, that refuses to run online or unauthenticated, and whose state I can copy into a run's folder
So that every local run proves which model and flags served it, and Claude Code's requests are known to translate before any run starts

## Problem Statement

After Phase 1 the server starts and is measured, but it is not yet hardened or accountable. The prompt-cache RAM is left at llama.cpp's default of 8192 MiB, which the 18 GB VM cannot give L-MoE beside its 13 GiB container (docs/libs/llama-cpp.md:23; documentation/research/local-route.md, L-MoE table). The web UI is on by default. `--offline` is only a flag, and nothing stops a start without it (serve.py:117-127). The key check covers `count_tokens` only (serve.py:151-156), while `/slots` and `/metrics` are the endpoints the launcher will read. There is no way to write the server's state into a trial folder; `server.json` is overwritten at the next start. And no request shaped like Claude Code's has ever been sent: whether streaming, thinking, tools, tool results and cache markers translate without an HTTP error (check L1, documentation/plans/local-models.md:177) is unknown. The server's `/slots` also returns each slot's detokenized prompt and generated text (llama.cpp `server-context.cpp`, `server_slot::to_json`), so a copy of it must drop them.

## Solution Statement

Set the flags in `models.toml`; extend `serve.start()` with an argument check and the key check on two more endpoints; add `serve.snapshot()` and a `record` subcommand; add `atr.local.probe` with the request built from a tool fixture in `infra/local-inference/`; then run the probe and a snapshot for each main model and record the results. Everything stays standard-library only, and every check fails closed.

## Metadata

| Key | Value |
|---|---|
| Type | Enhancement (harden a script) + new check module + measurement |
| Complexity | Medium |
| Systems Affected | harness/src/atr/local/ (serve, new probe); infra/local-inference/ (models.toml, new tool fixture); documentation/research/local-route.md |
| Dependencies | Phase 1 complete: both main weights verified on D:, the pinned image present (`ghcr.io/ggml-org/llama.cpp@sha256:d5ffba7d…`), `serve start/stop` working; Docker Desktop with the GPU in WSL 2 |
| Estimated Tasks | 8 |
| Source PRD line ref | `PRPs/prds/local-model-route.prd.md:62` (AC-2), `:166` (row 2), `:183-186` (Phase 2 details) |
| phase_type | feature |

## Mandatory Reading

| Priority | Path | Lines | Why |
|---|---|---|---|
| P0 | `PRPs/prds/local-model-route.prd.md` | 62, 166, 183-186 | AC-2 and the Phase 2 scope and success signal |
| P0 | `documentation/plans/local-models.md` | 105-107, 144-152, 177 | Sampling and thinking, the server's recorded flags and local record, check L1's pass condition |
| P0 | `harness/src/atr/local/serve.py` | 32-45, 108-193, 204-226 | `status()`, `start()` with its checks and record, the subcommands |
| P0 | `infra/local-inference/models.toml` | 18-33, 35-73, 93-112 | The shared flags, the two main-stage entries and the L-MoE fallback this phase changes |
| P0 | `documentation/research/local-route.md` | 1-20, "What Phase 2 must still decide" | The report this phase extends and the questions it answers |
| P1 | `harness/src/atr/local/bench.py` | 30-37, 171-215 | `call()`, and how a host-side check finds the running server and writes a result file |
| P1 | `docs/libs/llama-cpp.md` | 11-27 | Flags and gotchas (`--cache-ram`, `/slots`, endpoints that may skip the key) |
| P1 | `docs/context/conventions.md` | 5-39 | Module shape, naming, standard library first, `SystemExit` messages, fail closed |
| P1 | `harness/src/atr/agents/claude_sdk.py` | 61-63, 234-273 | The tools the runs disallow and the aliases Claude Code uses, so the fixture matches the runs |
| P2 | `docs/domain/areas/local-inference.md` | all | The area's rules, updated in Phase 1 |

## Patterns to Mirror

```python
# SOURCE: harness/src/atr/local/serve.py:150-156
    # The endpoint Claude Code calls to count tokens; listing models may not need a key.
    probe = {"model": entry["alias"], "messages": [{"role": "user", "content": "ping"}]}
    without_key = status(port, "/v1/messages/count_tokens", body=probe)
    with_key = status(port, "/v1/messages/count_tokens", key, probe)
    if without_key != 401 or with_key != 200:
        stop()
        raise SystemExit(f"key check failed: {without_key} without the key, {with_key} with it")
```
Extended by Task 2: `/slots` and `/metrics` must also answer 401 without the key and 200 with it, with the same stop-and-raise shape.

```python
# SOURCE: harness/src/atr/local/serve.py:183-186
    serialized = json.dumps(record, indent=2)
    if key in serialized:
        stop()
        raise SystemExit("the key appears in the server record; nothing was written")
```
Mirrored by Task 3 for every file the snapshot writes and by Task 4 for the check result.

```python
# SOURCE: harness/src/atr/local/bench.py:30-37
def call(port: int, key: str, path: str, body: dict, timeout: int) -> dict:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)
```
Shape for the probe's requests (Task 4), which add a GET variant and a streamed read of the response line by line.

```python
# SOURCE: harness/src/atr/local/bench.py:178-181
    records = config.data_dir()
    server = json.loads((records / "server.json").read_text())
    key = (records / "server.key").read_text().strip()
    port = server["port"]
```
Copied by Tasks 3 and 4 to find the running server.

```python
# SOURCE: harness/src/atr/local/bench.py:188-191
    out_dir = records / "bench"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = out_dir / f"{server['model_id']}-{stamp}.json"
```
Copied by Task 4 for `checks/l1-<model id>-<stamp>.json`.

```toml
# SOURCE: infra/local-inference/models.toml:26-33
args = [
    "--flash-attn", "on",
    "--cache-type-k", "q8_0",
    "--cache-type-v", "q8_0",
    "--parallel", "1",
    "--metrics",
    "--offline",
]
```
Extended by Task 1.

## Files to Change

| File | Action | Justification |
|---|---|---|
| `infra/local-inference/models.toml` | UPDATE | Final flags: `--no-webui` and `--slots` in the shared flags, `--cache-ram` per main and fallback model, header comment |
| `harness/src/atr/local/serve.py` | UPDATE | AC-2 offline check (fail without `--offline` or with a download flag); key check on `/slots` and `/metrics`; `snapshot()` and the `record <folder>` subcommand for the launcher |
| `infra/local-inference/claude-code-tools.json` | CREATE | The tool set check L1 sends: the names and input schemas of Claude Code's built-in tools, with short descriptions of our own |
| `harness/src/atr/local/probe.py` | CREATE | Check L1 against the running server: request translation, sampling applied, no prompt text in the log |
| `documentation/research/local-route.md` | UPDATE | The hardened server's flags and choices; check L1's results for both main models; Progress |

## NOT Building (Scope Limits)

- The agent's route option, `agent/route.json` and the pre-flight check from the task container — Phase 3.
- The launcher (server per run, power sampling, the copy into the trial folder, the MVP-priority refusal) — Phase 4. This phase only provides `serve record <folder>` for it to call.
- Checks L2 to L10, prefix reuse (L5) and the attribution header — Phase 6. The prompt-cache RAM chosen here is a first budget that check L5 revisits.
- A capture of the request Claude Code really sends: Claude Code is not installed on the host, and its first requests reach the server in Phase 3; the fixture approximates the tool set, and checks L2 and L3 use the real requests.
- A Docker network without internet access for the server: port publishing does not work on an internal network, so the offline guarantee is llama.cpp's `--offline`, the absence of download flags and the loopback binding.
- Changing the WSL memory profile or stopping other projects' containers.

## Step-by-Step Tasks

All commands run in WSL (`wsl.exe -d Ubuntu --exec bash -lc '<command>'`) from `$CODE_ROOT/harness`, where `$CODE_ROOT` is the phase's code root seen from WSL (`/mnt/c/repos/ai-track-record/.worktrees/local-model-route`), with `PY="env PYTHONPATH=src $HOME/atr/tools/harness-venv/bin/python"`. Git commands on the worktree must run from Windows (`git -C C:/repos/ai-track-record/.worktrees/local-model-route ...`): the worktree's `.git` pointer is a Windows path that git in WSL cannot follow.

### Task 1: UPDATE infra/local-inference/models.toml

- **ACTION**: Add `"--no-webui"` and `"--slots"` to `[server].args` (the web UI is not used; `/slots` is enabled explicitly, since check L1 and the record read it). Add `"--cache-ram", "<MiB>"` to the args of each main-stage and fallback entry: `4096` for `qwen3.5-9b-q4_k_m` (its container peaked at about 5.6 GiB of the VM's 17.6 GiB in Phase 1) and `2048` for `qwen3.6-35b-a3b-ud-q3_k_xl` and `qwen3.6-35b-a3b-ud-iq3_xxs` (L-MoE's container peaked at 13.4 GiB, leaving about 4 GiB for the prompt cache, the task container, the Collector and the other containers). Add a comment next to each value giving that reason and naming check L5 as the place it is revisited. Update the header comment: the flags are final for Phase 2 (2026-11-04) and recorded in `documentation/research/local-route.md`. Do not change any pinned image, revision, size or digest. Delivers AC-A1.
- **MIRROR**: `infra/local-inference/models.toml:26-33`
- **VALIDATE**: `$PY -c "from atr.local import config; s=config.load(); a=s['server']['args']; assert '--no-webui' in a and '--slots' in a and '--offline' in a; m={i:e for i,e in s['models'].items() if e['stage'] in ('main','fallback')}; v={i:e['args'][e['args'].index('--cache-ram')+1] for i,e in m.items() if '--cache-ram' in e['args']}; assert len(v)==len(m)==3, v; assert v['qwen3.5-9b-q4_k_m']=='4096' and v['qwen3.6-35b-a3b-ud-q3_k_xl']=='2048', v; print('PASS', v)"`

### Task 2: UPDATE harness/src/atr/local/serve.py (offline and key checks)

- **ACTION**: (a) Add a pure function `check_args(args: list[str]) -> None` that raises `SystemExit` naming the problem unless `--offline` is in `args`, and if any download flag is present (`-hf`, `--hf-repo`, `-hfr`, `--hf-file`, `-hff`, `-hft`, `--hf-token`, `-mu`, `--model-url`, `-dr`, `--docker-repo`). Call it in `start()` on the full argument list before `docker run`, so a start that could reach the network never starts. (b) After the `count_tokens` check, check `GET /slots` and `GET /metrics` the same way: 401 without the key and 200 with it, else stop and raise (extend `status()` to send GET when `body` is `None`, as it does today). (c) Add `"offline": true` and `"key_checked": ["/v1/messages/count_tokens", "/slots", "/metrics"]` to the record. Update the module docstring. Delivers AC-A2.
- **MIRROR**: `harness/src/atr/local/serve.py:150-156`
- **VALIDATE**: `$PY -c "from atr.local import serve
def fails(a):
    try: serve.check_args(a)
    except SystemExit: return True
    return False
assert not fails(['--model','/models/x.gguf','--offline']); assert fails(['--model','/models/x.gguf']); assert fails(['--offline','-hf','a/b']); assert fails(['--offline','--model-url','http://x']); print('PASS')"`

### Task 3: UPDATE harness/src/atr/local/serve.py (the record for a trial)

- **ACTION**: Add `snapshot(dest: Path) -> list[Path]` and a subcommand `record <folder>` that call it for the running server (found from `server.json` and `server.key`, as `bench.main()` does). It creates `dest` and writes: `server.json` (a copy of the record), `slots.json` (`GET /slots` with the key, with every slot's `prompt` and `generated` fields removed, since the endpoint returns the detokenized prompt and output), `metrics.prom` (`GET /metrics` with the key, as text) and `server.log` (`docker logs --timestamps atr-llm`, stdout and stderr). Before writing anything, check that the key appears in none of the four texts; if it does, write nothing and raise `SystemExit`. It fails with a clear message when no server is running. It prints the written paths, never the key. Delivers AC-A3.
- **MIRROR**: `harness/src/atr/local/serve.py:183-186`
- **VALIDATE**: `$PY -m atr.local.serve start qwen3.5-9b-q4_k_m > /dev/null && d=$(mktemp -d) && $PY -m atr.local.serve record $d/server && $PY -c "import json,pathlib,sys; d=pathlib.Path(sys.argv[1]); k=(pathlib.Path.home()/'atr/data/local-inference/server.key').read_text().strip(); names=sorted(p.name for p in d.iterdir()); assert names==['metrics.prom','server.json','server.log','slots.json'], names; assert all(k not in p.read_text(errors='replace') for p in d.iterdir()), 'key in snapshot'; s=json.loads((d/'slots.json').read_text()); assert all('prompt' not in x and 'generated' not in x for x in s), 'prompt text in slots'; print('PASS')" $d/server; r=$?; $PY -m atr.local.serve stop; exit $r`

### Task 4: CREATE infra/local-inference/claude-code-tools.json and harness/src/atr/local/probe.py

- **ACTION**: (a) The fixture is a JSON list of tool definitions in the Messages API shape (`name`, `description`, `input_schema`) for Claude Code's built-in tools: `Agent`, `Bash`, `BashOutput`, `KillShell`, `Edit`, `MultiEdit`, `ExitPlanMode`, `Glob`, `Grep`, `NotebookEdit`, `Read`, `Skill`, `SlashCommand`, `TodoWrite`, `WebFetch`, `WebSearch`, `Write`. Each `input_schema` carries the tool's real parameter names, types, enums, nested objects and arrays and `required` lists, so the server's template meets the same structure; each `description` is one or two sentences of our own, not Claude Code's text. A top-level comment is not possible in JSON, so the file is a list and `probe.py`'s docstring says where it comes from and that checks L2 and L3 use the real requests. (b) `python -m atr.local.probe [--max-tokens 4096] [--timeout 1800]` runs check L1 against the running server (found from `server.json` and `server.key`). It builds one request: `model` the server's alias; `stream: true`; `thinking: {"type": "enabled", "budget_tokens": 1024}`; `system` two text blocks, the last with `cache_control: {"type": "ephemeral"}`; `tools` the fixture, the last tool with `cache_control`; `messages` a user turn, an assistant turn with a `tool_use` block calling `Bash` with `{"command": "ls"}`, and a user turn with the matching `tool_result` (a short file listing) and a text block with `cache_control` asking for a one-sentence summary. A random marker (`secrets.token_hex(8)`) is placed in the system prompt, the first user turn and the tool result. It sends `POST /v1/messages` with the key and reads the server-sent events line by line, recording the HTTP status, the count of each event type, the content block types, the `stop_reason`, the usage and any `error` event. Then it reads `GET /slots` and keeps each slot's `params` (sampling applied) and token counts, dropping `prompt` and `generated`. Then it reads `docker logs atr-llm` and checks that the marker is absent. The check passes when the status is 200, the events include `message_start`, at least one `content_block_start` and `content_block_stop`, a `message_delta` carrying a `stop_reason` of `end_turn` or `tool_use`, and `message_stop`, with no `error` event; when `/slots` answered with `params`; and when the marker is not in the log. It writes `$ATR_DATA_DIR/local-inference/checks/l1-<model id>-<stamp>.json` with the server record's model id, image, build and args, every measured field, the pass result and the reasons for a failure, never the key (checked before writing) and never the response text beyond the block types and lengths. It exits non-zero when the check fails. Delivers AC-A4.
- **MIRROR**: `harness/src/atr/local/bench.py:30-37` and `harness/src/atr/local/bench.py:188-191`
- **VALIDATE**: `$PY -c "import json; t=json.load(open('../infra/local-inference/claude-code-tools.json')); n={x['name'] for x in t}; need={'Agent','Bash','Edit','Glob','Grep','Read','TodoWrite','Write','WebFetch','WebSearch','NotebookEdit'}; assert need<=n, need-n; assert all(x['input_schema']['type']=='object' and 'properties' in x['input_schema'] for x in t); print('PASS', len(t))" && $PY -m atr.local.probe --help > /dev/null && echo PASS`

### Task 5: RUN check L1 and the record for L-Small

- **ACTION**: `$PY -m atr.local.serve start qwen3.5-9b-q4_k_m`, then `$PY -m atr.local.probe`, then `$PY -m atr.local.serve record "$(mktemp -d)/server"` to confirm the snapshot after a real request (its `slots.json` holds no prompt text and `server.log` no marker), then `$PY -m atr.local.serve stop`. If the probe fails, record the failure and its reasons, try once with the model's thinking off (`--arg=--chat-template-kwargs --arg='{"enable_thinking":false}'`) to learn whether thinking causes it, and record both results; do not change models.toml's thinking setting in this phase (checks L1 and L3 decide it, PRD Open Questions). Delivers AC-A5.
- **MIRROR**: `harness/src/atr/local/bench.py:178-181`
- **VALIDATE**: `$PY -c "import json,glob,os; fs=sorted(glob.glob(os.path.expanduser('~/atr/data/local-inference/checks/l1-qwen3.5-9b-q4_k_m-*.json'))); assert fs, 'no L1 result'; r=json.load(open(fs[-1])); assert 'passed' in r and 'stop_reason' in r and 'sampling' in r and 'marker_in_log' in r, sorted(r); print('PASS', r['passed'], r.get('stop_reason'))"`

### Task 6: RUN check L1 and the record for L-MoE

- **ACTION**: The same as Task 5 for `qwen3.6-35b-a3b-ud-q3_k_xl` (loading takes about four minutes). If the server does not load with `--cache-ram 2048` beside the running containers, record it and retry once with `--cache-ram 1024` set in models.toml; ask the operator before stopping any other project's container. Delivers AC-A5.
- **MIRROR**: `harness/src/atr/local/bench.py:178-181`
- **VALIDATE**: `$PY -c "import json,glob,os; fs=sorted(glob.glob(os.path.expanduser('~/atr/data/local-inference/checks/l1-qwen3.6-35b-a3b-ud-q3_k_xl-*.json'))); assert fs, 'no L1 result'; r=json.load(open(fs[-1])); assert 'passed' in r and 'stop_reason' in r and 'sampling' in r and 'marker_in_log' in r, sorted(r); print('PASS', r['passed'], r.get('stop_reason'))"`

### Task 7: UPDATE documentation/research/local-route.md

- **ACTION**: Add a section `## Hardened server` after "Machine baseline": the final shared and per-model flags with the reason for each (prompt-cache RAM, web UI off, slots on, offline, loopback, one slot), the checks a start now makes (weights, offline and download flags, key on three endpoints, loopback, key absent from the record) and what `serve record` writes, including that `/slots` returns prompt text and the copy drops it. Add a section `## Compatibility checks` with a table of checks L1 to L10 (columns: check, model, result, date, notes), L1 filled for both main models from the result files of Tasks 5 and 6 (pass or fail, stop reason, block types, sampling applied, marker in the log, the thinking-off retry if one was made), L2 to L10 marked "Phase 6". Note that the tool set is a fixture with Claude Code's tool names and input schemas and that checks L2 and L3 use the real requests. Update the Progress table (WP1 done on 2026-11-04 if L1 passed for both models, otherwise "Blocked" with the reason) and the "What Phase 2 must still decide" list into what is decided and what stays open for later phases. Delivers AC-A6.
- **MIRROR**: `documentation/research/local-route.md:1-20`
- **VALIDATE**: `set -euo pipefail; f=../documentation/research/local-route.md; grep -q '^## Hardened server' $f; grep -q '^## Compatibility checks' $f; grep -q -- '--cache-ram' $f; grep -q 'L1' $f; echo PASS`

### Task 8: VERIFY the area's privacy rules on every new and changed file

- **ACTION**: Run the leak check (word match, as the exporter's) over the five files of this phase and confirm no private term, key or container name of another project is in them. Confirm that no result file under `~/atr/data/local-inference/checks/` contains the key. Delivers AC-A6.
- **MIRROR**: `harness/src/atr/local/serve.py:183-186`
- **VALIDATE**: `set -euo pipefail; files="../infra/local-inference/models.toml ../infra/local-inference/claude-code-tools.json src/atr/local/serve.py src/atr/local/probe.py ../documentation/research/local-route.md"; if grep -lwiF -f <(grep -vE '^(#|[[:space:]]*$)' ~/atr/data/leak-terms.txt) $files; then echo "FAIL: private term"; exit 1; fi; for f in ~/atr/data/local-inference/checks/l1-*.json; do if grep -qF "$(cat ~/atr/data/local-inference/server.key 2>/dev/null || echo NO-KEY-FILE)" "$f"; then echo "FAIL: key in $f"; exit 1; fi; done; echo PASS`

## Validation Commands

Every block runs in WSL from `$CODE_ROOT/harness` with `PY="env PYTHONPATH=src $HOME/atr/tools/harness-venv/bin/python"`.

### Level 1: STATIC_ANALYSIS

```bash
set -euo pipefail
$PY -m py_compile src/atr/local/config.py src/atr/local/serve.py src/atr/local/probe.py src/atr/local/bench.py src/atr/local/fetch.py
$PY -c "import tomllib,json; tomllib.load(open('../infra/local-inference/models.toml','rb')); json.load(open('../infra/local-inference/claude-code-tools.json')); print('config ok')"
for m in serve probe bench fetch; do $PY -m atr.local.$m --help > /dev/null; done
echo PASS
```

### Level 2: CONTENT_INVARIANTS

```bash
set -euo pipefail
# AC-2 offline guard: no start without --offline or with a download flag.
$PY -c "from atr.local import serve
def fails(a):
    try: serve.check_args(a)
    except SystemExit: return True
    return False
assert not fails(['--offline']) and fails([]) and fails(['--offline','-hf','a/b']) and fails(['--offline','--hf-repo','a/b']); print('offline guard ok')"
# Final flags present in the configuration.
$PY -c "from atr.local import config; s=config.load(); a=s['server']['args']; assert all(f in a for f in ('--offline','--metrics','--no-webui','--slots')); assert all('--cache-ram' in e['args'] for e in s['models'].values() if e['stage'] in ('main','fallback')); print('flags ok')"
# Privacy: no private term (word match, as the exporter's leak check) in the files this phase changes or creates.
files="../infra/local-inference/models.toml ../infra/local-inference/claude-code-tools.json src/atr/local/serve.py src/atr/local/probe.py ../documentation/research/local-route.md"
if grep -lwiF -f <(grep -vE '^(#|[[:space:]]*$)' ~/atr/data/leak-terms.txt) $files; then echo "FAIL: private term in a changed file"; exit 1; fi
echo PASS
```

### Level 3: INTEGRATION

```bash
set -euo pipefail
# AC-2 and check L1 on the real machine, with L-Small (the faster model to load).
$PY -m atr.local.serve start qwen3.5-9b-q4_k_m > /dev/null
trap '$PY -m atr.local.serve stop' EXIT
KEY=$(cat ~/atr/data/local-inference/server.key)
for p in /slots /metrics; do
  [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8090$p)" = 401 ]
  [ "$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $KEY" http://127.0.0.1:8090$p)" = 200 ]
done
[ "$(docker port atr-llm 8080/tcp)" = "127.0.0.1:8090" ]
$PY -c "import json,pathlib; r=json.loads((pathlib.Path.home()/'atr/data/local-inference/server.json').read_text()); assert r['offline'] is True and '--no-webui' in r['args'] and '--cache-ram' in r['args']; print('record ok')"
$PY -m atr.local.probe
D=$(mktemp -d); $PY -m atr.local.serve record $D/server
if grep -rqF "$KEY" $D/server; then echo "FAIL: key in the snapshot"; exit 1; fi
echo PASS
```

## Acceptance Criteria

- **AC-A1 (PRD AC-2):** `models.toml` holds the final flags: offline, metrics, web UI off, slots on, one slot, and a prompt-cache RAM for each main and fallback model with its reason.
- **AC-A2 (PRD AC-2):** `atr.local.serve start` fails closed, before starting a container, unless `--offline` is in the flags and no download flag is; and it fails closed unless `count_tokens`, `/slots` and `/metrics` each refuse a request without the key (401) and accept it with the key (200), besides the loopback and key-in-record checks of Phase 1. The record states `offline` and the endpoints checked.
- **AC-A3 (PRD AC-2, Phase 2 scope):** `atr.local.serve record <folder>` writes `server.json`, `slots.json` without prompt or generated text, `metrics.prom` and `server.log` for the running server, and writes nothing when the key would appear in any of them.
- **AC-A4 (PRD AC-10, check L1):** `atr.local.probe` sends one streamed request with thinking, system blocks, Claude Code's tool set, a tool result and cache markers, and passes only when the answer is a complete event stream with no HTTP or stream error, `/slots` shows the sampling applied, and a marker placed in the prompt is absent from the server's log; it writes a result file without the key.
- **AC-A5 (PRD AC-10, Phase 2 success signal):** A check L1 result file exists for L-Small and for L-MoE; each is a pass, or a failure whose reasons and thinking-off retry are recorded.
- **AC-A6 (PRD AC-10):** `documentation/research/local-route.md` records the hardened server's flags and checks and check L1's results, and no new or changed file holds a private term, a key or another project's container name.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Qwen3.5/3.6 put a tool call inside the thinking block, or the template rejects part of the request (PRD Technical Risks, row 1; llama.cpp issue 20837) | M | M | The probe records the failure and its reasons; a thinking-off retry tells whether thinking causes it; the setting itself is decided by checks L1 and L3, not here |
| `cache_control` or `thinking` is rejected by the server's translation (not documented for `/v1/messages`) | M | M | The probe sends both, as Claude Code does; an HTTP error is recorded as a check L1 failure with the server's message |
| The prompt-cache RAM chosen does not fit L-MoE beside the other containers | L | M | Retry with 1024 MiB in models.toml; ask the operator before stopping another project's container; check L5 revisits the budget |
| The server's default log level prints prompt text | L | H | The probe's marker check fails closed; the fix (a lower `--log-verbosity`) goes into models.toml with the result |
| The fixture's tool set differs from what Claude Code really sends | H | L | Stated in the report; checks L2 and L3 in Phase 6 use Claude Code's real requests |

## Notes

- **TDD routing (this plan, against the relay repo):** Current value of `tdd` in `docs/context/methodology.md`: **false**. Test-after ordering — when a test framework is declared, the test pair (test-writer/test-reviewer) authors and maintains the suite from the Acceptance Criteria above, after the Implementer + Code Review; with no framework declared, no tests are authored.
- No test framework is declared (`test_frameworks: []`), so no test files are authored; the `VALIDATE` commands exercise the modules directly and on the real machine.
- Research for this plan read the pinned image's own `--help` (b12063): `--cache-ram` (default 8192 MiB), `--slots/--no-slots` (default on), `--no-webui`, `--offline`, `--log-verbosity` (default 3), `--api-key`; and llama.cpp's server code: only `/health` and `/v1/health` skip the key, `X-Api-Key` is accepted as well as `Authorization`, and `/slots` returns each slot's prompt and generated text.
- The machine is used as it is: the desktop keeps its share of VRAM and the other projects' containers keep running.

*Generated: 2026-11-04*
*Approved: 2026-11-04*
*Implemented: 2026-11-04*
*Status: IMPLEMENTED*
