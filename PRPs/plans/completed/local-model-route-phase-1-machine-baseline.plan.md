# Feature: Machine baseline (Phase 1 of local-model-route)

```
**Decision Gate**
- Active context: none
- Activated criteria: business rules for local inference (docs/domain/areas/local-inference.md); reuse and change of components (atr.local.fetch, atr.local.serve, atr.local.bench); cross-cutting pattern (the server record later copied into trials); pinned configuration (infra/local-inference/models.toml)
- Decisions found:
  - Pin everything and follow the rigor rules: model files by revision and SHA-256, the server image by digest (D-020)
  - Allowed providers for Target A: local open-weight models on the operator's machine (D-029, D-057); the benchmark prompt is random words, never target content
  - Local models experiment outside the frozen MVP; the MVP keeps priority over the machine (D-058)
  - Run folders are the system of record (D-033): the baseline is a file in $ATR_DATA_DIR, summarized in documentation/research/
  - Python 3.12 with uv; English everywhere; planning in documentation/ (D-047, D-010, D-011)
- Applicable anti-patterns:
  - Private-target material in the repository (no Target A content in code, prompts or the report)
  - Unpinned versions (image by digest, weights by SHA-256)
  - Silently dropping a configuration option (a flag the server rejects stops the start)
  - Secrets in the repository (the server key stays in $ATR_DATA_DIR/local-inference/server.key, owner-only, never in server.json)
  - Large files on C: or inside the WSL and Docker disks (weights on D: only)
  - Running two benchmark runs at the same time (no bench while an MVP job runs)
- Applicable architectural rules:
  - Configuration, not code (D-005): the chosen flags live in models.toml
  - Files first: every measurement is a JSON file
  - Fail closed on checks that guard correctness or privacy (key check, loopback check, digest check)
  - Host-side code follows docs/context/conventions.md (one module per command, docstring with Usage, SystemExit messages)
- Result: PROCEED
```

## Source

- `PRPs/prds/local-model-route.prd.md` — Implementation Phases row 1: "Machine baseline" — Goal: Know what this machine can serve before configuring the route. — Success signal: Benchmark files for both main models, and the chosen quantization, context and slot count recorded in `models.toml`.

## Summary

This phase finishes the drafted local inference scripts so they meet PRD AC-1 to AC-3, then runs them on the machine: it downloads and verifies the two main model files onto D:, starts llama.cpp's pinned server with each model, checks the key and the loopback binding, and measures prompt and generation speeds, GPU power, energy, VRAM and memory at 32k, 64k and 128k tokens. The measured choices (quantization, context, experts on the CPU, slot count) go into `infra/local-inference/models.toml`, and the numbers into a new report, `documentation/research/local-route.md`, that later phases extend with the compatibility checks.

## User Story

As the operator of AI Track Record
I want to know how fast and how big the two main local models can run on my machine, with verified weights and a server I can trust
So that I can configure the local route (context, offload, slots) from measurements instead of community guesses

## Problem Statement

The local route cannot be configured without the machine's real limits. The drafted `atr.local` scripts have never run: the weights are not on D:, the server has never started, and the flag values in `models.toml` (`--n-cpu-moe`, context, slots) are first guesses (docs/domain/areas/local-inference.md, Open Questions). The drafts also have gaps against the PRD's criteria: `serve.py` does not prove the port is published on the loopback only and does not guard against the key reaching `server.json`; `bench.py` writes nothing if one prompt size fails, assumes exactly one second between power samples and records the container's memory once, after the run.

## Solution Statement

Close the gaps in the three scripts, keeping them standard-library only and following the module conventions; then run them: `fetch` for the main stage, `serve start` and `bench` for L-Small and for L-MoE (tuning `--n-cpu-moe` for L-MoE so that a 128k context fits beside the desktop's share of VRAM), and `serve stop`. Record the chosen values in `models.toml` and the measurements in the new report. The machine is measured as it is during this session (the desktop on the discrete GPU, the other containers running), and that state is recorded with every result.

## Metadata

| Key | Value |
|---|---|
| Type | Enhancement (finish drafted scripts) + measurement |
| Complexity | Medium |
| Systems Affected | harness/src/atr/local/ (fetch, serve, bench); infra/local-inference/models.toml; documentation/research/ |
| Dependencies | Docker Desktop with the GPU in WSL 2; the pinned image `ghcr.io/ggml-org/llama.cpp:server-cuda-b12063@sha256:d5ffba7d…`; the two main GGUF files (16.85 GB and 5.68 GB) on D:, approved by the operator on 2026-11-04; `curl`, `nvidia-smi` |
| Estimated Tasks | 8 |
| Source PRD line ref | `PRPs/prds/local-model-route.prd.md:61-63` (AC-1 to AC-3), `:165` (row 1), `:178-181` (Phase 1 details) |
| phase_type | feature |

## Mandatory Reading

| Priority | Path | Lines | Why |
|---|---|---|---|
| P0 | `PRPs/prds/local-model-route.prd.md` | 61-63, 165, 178-181 | AC-1 to AC-3 and the Phase 1 scope and success signal |
| P0 | `harness/src/atr/local/fetch.py` | 33-76 | `check()` and `fetch()`: the size and digest check, the `.bad` rename and the marker |
| P0 | `harness/src/atr/local/config.py` | 12-49 | Where `models.toml`, the weights and the records are found; `verified()` |
| P0 | `harness/src/atr/local/serve.py` | 79-149 | `start()`: the Docker run, the health wait, the key probe and the record |
| P0 | `harness/src/atr/local/bench.py` | 51-150 | `GpuSampler`, `measure()` and `main()` |
| P0 | `infra/local-inference/models.toml` | 13-46, 84-100 | The pinned server and the two main-stage entries this phase tunes |
| P1 | `documentation/plans/local-models.md` | 50-66, 103, 144-152, 257-263 | The machine, the quantization and context rule (at least 128k, aiming for about 160k), the server's recorded flags, WP0's done criterion |
| P1 | `docs/libs/llama-cpp.md` | 11-27 | Server flags, `/completion` timings, `--cache-ram` and `--load-mode` gotchas |
| P1 | `docs/context/conventions.md` | 5-39 | Module shape, naming, standard library first, `SystemExit` messages, fail closed |
| P2 | `harness/src/atr/ops/budget.py` | 31-35 | The tolerant JSON reader used by host-side modules |
| P2 | `documentation/research/m3-results.md` | 1-20 | The shape of a research report (status line, Progress table) |

## Patterns to Mirror

```python
# SOURCE: harness/src/atr/local/fetch.py:33-42
def check(model_id: str, entry: dict, path: Path) -> None:
    """Fail unless the file has the pinned size and digest."""
    size = path.stat().st_size
    if size != entry["size"]:
        raise SystemExit(f"{model_id}: {path.name} has {size} bytes, expected {entry['size']}")
    print(f"{model_id}: hashing {path.name}", flush=True)
    digest = sha256(path)
    if digest != entry["sha256"]:
        path.rename(path.with_name(entry["file"] + ".bad"))
        raise SystemExit(f"{model_id}: SHA-256 {digest} does not match {entry['sha256']}")
```
Copied by Task 1 (the size mismatch gets the same `.bad` rename).

```python
# SOURCE: harness/src/atr/local/config.py:41-49
def verified(entry: dict, directory: Path) -> bool:
    weights = directory / entry["file"]
    stamp = marker(weights)
    return (
        weights.exists()
        and weights.stat().st_size == entry["size"]
        and stamp.exists()
        and stamp.read_text().split()[0] == entry["sha256"]
    )
```
Used unchanged by Tasks 1, 2 and the Level 3 check.

```python
# SOURCE: harness/src/atr/local/serve.py:121-127
    # The endpoint Claude Code calls to count tokens; listing models may not need a key.
    probe = {"model": entry["alias"], "messages": [{"role": "user", "content": "ping"}]}
    without_key = status(port, "/v1/messages/count_tokens", body=probe)
    with_key = status(port, "/v1/messages/count_tokens", key, probe)
    if without_key != 401 or with_key != 200:
        stop()
        raise SystemExit(f"key check failed: {without_key} without the key, {with_key} with it")
```
Mirrored by Task 3 for the loopback check and the key-in-record guard (check, stop the server, fail closed).

```python
# SOURCE: harness/src/atr/local/serve.py:129-148
    record = {
        "model_id": model_id,
        **{field: entry[field] for field in ("alias", "role", "repo", "revision", "file", "size", "sha256")},
        "image": server["image"],
        "build": server["build"],
        "commit": server["commit"],
        "context": context,
        "args": args,
        "port": port,
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "load_seconds": load_seconds,
        "vram_used_mib": {"before": vram_before, "loaded": gpu_memory_used()},
        "container_memory": container_memory(),
    }
    records = config.data_dir()
    records.mkdir(parents=True, exist_ok=True)
    key_file = records / "server.key"
    key_file.write_text(key)
    key_file.chmod(0o600)
    (records / "server.json").write_text(json.dumps(record, indent=2))
```
Extended by Task 3 with the image id, the published address and the machine, and guarded so the key never reaches `server.json`.

```python
# SOURCE: harness/src/atr/local/bench.py:72-85
    def stop(self) -> dict:
        self.process.terminate()
        self.process.wait()
        self.thread.join(timeout=5)
        if not self.samples:
            return {}
        powers = [s[0] for s in self.samples]
        return {
            "samples": len(self.samples),
            "power_mean_w": round(sum(powers) / len(powers), 1),
            "energy_wh": round(sum(powers) / 3600, 3),
            "vram_peak_mib": int(max(s[1] for s in self.samples)),
            "use_mean_pct": round(sum(s[2] for s in self.samples) / len(self.samples)),
        }
```
Changed by Task 4: samples carry their time, and energy integrates power over the measured intervals.

```toml
# SOURCE: infra/local-inference/models.toml:30-46
# L-MoE. Thinking, precise coding: the model card's sampling.
[models."qwen3.6-35b-a3b-ud-q3_k_xl"]
alias = "qwen3.6-35b-a3b"
role = "L-MoE"
stage = "main"
repo = "unsloth/Qwen3.6-35B-A3B-GGUF"
revision = "a483e9e6cbd595906af30beda3187c2663a1118c"
file = "Qwen3.6-35B-A3B-UD-Q3_K_XL.gguf"
size = 16845511648
sha256 = "a832b9689925f1bd335bbe985cdfb06c36bf2cf268f4f8f6eceafa3ceb515617"
context = 131072
args = [
    "--n-gpu-layers", "999",
    "--n-cpu-moe", "36",
    "--temp", "0.6", "--top-p", "0.95", "--top-k", "20", "--min-p", "0", "--presence-penalty", "0",
    "--chat-template-kwargs", '{"enable_thinking":true}',
]
```
Updated by Task 7 with the measured `--n-cpu-moe`, context and a `baseline` pointer.

```python
# SOURCE: harness/src/atr/ops/budget.py:31-35
def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        return {}
```
Shape for any optional record Task 4 reads.

```markdown
# SOURCE: documentation/research/m3-results.md:1-5
# M3 results: the MVP runs

> **Status:** In progress · **Last updated:** 2026-11-02 · **Owner:** Fabio Martins Barreto

This report records milestone M3: the 45 runs of the MVP experiment, 3 tasks on Target A × 5 configurations × 3 repetitions, with their grades and analysis ([schedule](../product/06-scope-and-roadmap.md#4-schedule-to-the-mvp)). Target A and its tasks are described in the [M1 results](m1-results.md), and the harness and graders in the [M2 results](m2-results.md).
```
Copied by Task 8 for the report's title, status line and opening paragraph; the report's next section is a Progress table with `Item | Status | Date` columns, as in lines 7-9 of the same file.

## Files to Change

| File | Action | Justification |
|---|---|---|
| `harness/src/atr/local/fetch.py` | UPDATE | AC-1: a size mismatch is also kept as `<file>.bad`; the result message tells a verified existing file from a download |
| `harness/src/atr/local/serve.py` | UPDATE | AC-2: fail closed unless the port is published on 127.0.0.1 only and the key is absent from the record; record the image id, the published address and the machine |
| `harness/src/atr/local/bench.py` | UPDATE | AC-3: write after every prompt size, record a failed size instead of losing the others, integrate energy over sample times, sample the container's memory during each request, record the VRAM in use at the start |
| `infra/local-inference/models.toml` | UPDATE | Phase 1 success signal: the chosen quantization, context, experts on the CPU and slot count, with a pointer to the baseline |
| `documentation/research/local-route.md` | CREATE | The report of the local route: the machine baseline now, the compatibility checks in Phase 6 |

## NOT Building (Scope Limits)

- The final server flags, the prompt-cache RAM budget and check L1 — Phase 2.
- Any agent, launcher, allowlist, store, budget or export change — Phases 3 to 5.
- The L-Alt candidates (gpt-oss-20b, Gemma 4 26B-A4B) and the 4-bit L-MoE with a larger WSL memory profile — PRD Could items, not downloaded.
- Changing the WSL memory profile, moving the display to the integrated graphics or stopping other projects' containers: operator actions on the machine; this phase measures the machine as it is and records its state.
- Whole-system energy with a plug meter — PRD Could item; only GPU power is measured.
- Any run on Target A — outside this PRD.

## Step-by-Step Tasks

All commands run in WSL (`wsl.exe -d Ubuntu --exec bash -lc '<command>'`) from `$CODE_ROOT/harness`, where `$CODE_ROOT` is the phase's code root seen from WSL (`/mnt/c/repos/ai-track-record/.worktrees/local-model-route`), with `PY="env PYTHONPATH=src $HOME/atr/tools/harness-venv/bin/python"`.

### Task 1: UPDATE harness/src/atr/local/fetch.py

- **ACTION**: In `check()`, rename the file to `<file>.bad` before raising on a size mismatch too, exactly as on a digest mismatch, so a later call downloads afresh instead of failing on the same file. In `fetch()`, return `"<id>: present, verified"` when an existing complete file was hashed and `"<id>: downloaded and verified"` only after a download. Keep the module docstring in step with the behavior. Delivers AC-A1.
- **MIRROR**: `harness/src/atr/local/fetch.py:33-42`
- **VALIDATE**: `$PY -c "import hashlib,tempfile; from pathlib import Path; from atr.local import config, fetch; d=Path(tempfile.mkdtemp()); (d/'g.gguf').write_bytes(b'abc'); g={'file':'g.gguf','size':3,'sha256':hashlib.sha256(b'abc').hexdigest()}; print(fetch.fetch('g',g,d)); assert config.verified(g,d); (d/'b.gguf').write_bytes(b'abc'); b={'file':'b.gguf','size':3,'sha256':'0'*64}; r=None
try: fetch.fetch('b',b,d)
except SystemExit as e: r=e
assert r is not None and (d/'b.gguf.bad').exists() and not (d/'b.gguf').exists(), 'digest mismatch not kept as .bad'; (d/'s.gguf').write_bytes(b'abcd'); s={'file':'s.gguf','size':3,'sha256':'0'*64}; r=None
try: fetch.fetch('s',s,d)
except SystemExit as e: r=e
assert r is not None and (d/'s.gguf.bad').exists(), 'size mismatch not kept as .bad'; print('PASS')"`

### Task 2: RUN the main-stage download and verification

- **ACTION**: Run `$PY -m atr.local.fetch` (stage `main`: `qwen3.6-35b-a3b-ud-q3_k_xl` and `qwen3.5-9b-q4_k_m`) until both files are in `$ATR_MODELS_DIR` (`/mnt/d/atr/models`) with their markers. A download already started in this session resumes from its `.part` file. Pull the pinned image by digest if it is not present. Delivers AC-A2.
- **MIRROR**: `harness/src/atr/local/config.py:41-49`
- **VALIDATE**: `$PY -c "from atr.local import config; s=config.load(); d=config.models_dir(); m=[i for i,e in s['models'].items() if e['stage']=='main']; bad=[i for i in m if not config.verified(s['models'][i], d)]; assert len(m)==2 and not bad, f'not verified: {bad}'; print('PASS', m)" && docker image inspect ghcr.io/ggml-org/llama.cpp@sha256:d5ffba7d096ab0236c65dc147d797b4b7658a7e5425634593373635d661bccda --format '{{.Id}}'`

### Task 3: UPDATE harness/src/atr/local/serve.py

- **ACTION**: After the key probe in `start()`, read the container with `docker inspect atr-llm` and (a) fail closed — stop the server and raise `SystemExit` — unless every host binding of `8080/tcp` has `HostIp` `127.0.0.1`; (b) record `image_id` (the container's image id) and `published` (the list of `host:port` bindings, for example `["127.0.0.1:8090"]`). Add a `machine` field with the GPU's name and total VRAM from `nvidia-smi`, the VM's total memory from `/proc/meminfo` and the processor count. Before writing `server.json`, fail closed (stop, raise) if the key string appears anywhere in the serialized record. Keep the key out of every printed output. Delivers AC-A3.
- **MIRROR**: `harness/src/atr/local/serve.py:121-127` and `harness/src/atr/local/serve.py:129-148`
- **VALIDATE**: `$PY -m atr.local.serve start qwen3.5-9b-q4_k_m > /dev/null && $PY -c "import json,pathlib; d=pathlib.Path.home()/'atr/data/local-inference'; r=json.loads((d/'server.json').read_text()); k=(d/'server.key').read_text().strip(); assert k not in json.dumps(r), 'key in server.json'; assert r['published']==['127.0.0.1:8090'], r['published']; missing=[x for x in ('image','image_id','build','sha256','context','args','machine') if x not in r]; assert not missing, missing; print('PASS')"; s=$?; $PY -m atr.local.serve stop; exit $s`

### Task 4: UPDATE harness/src/atr/local/bench.py

- **ACTION**: (a) `GpuSampler` keeps a monotonic time with every sample and computes `energy_wh` as the sum of power × interval between consecutive samples, divided by 3600; it also records `power_peak_w`. (b) Add a container-memory sampler (a thread reading `docker stats atr-llm --format '{{.MemUsage}}'` in stream mode) whose peak, in MiB, is recorded per prompt size next to the point value after the request. (c) Record `vram_used_at_start_mib` (from `serve.gpu_memory_used()`) once per bench. (d) Write the output file after every prompt size, not only at the end; a size whose request fails is recorded with an `error` field and the bench continues, then exits non-zero naming the failed sizes. Keep the prompt as random words from a fixed seed. Delivers AC-A4.
- **MIRROR**: `harness/src/atr/local/bench.py:72-85`
- **VALIDATE**: `$PY -c "import time; from atr.local.bench import GpuSampler; g=GpuSampler(); time.sleep(3.5); r=g.stop(); print(r); assert r.get('samples',0)>=2 and r['energy_wh']>0 and 'power_peak_w' in r and r['vram_peak_mib']>0, 'GPU sampling incomplete'; print('PASS')"`

### Task 5: RUN the server and the benchmark for L-Small

- **ACTION**: `$PY -m atr.local.serve start qwen3.5-9b-q4_k_m`, then `$PY -m atr.local.bench` with the default sizes 32768, 65536 and 131072, then `$PY -m atr.local.serve stop`. If the model does not load at 131072 tokens, record the failure and measure at the largest context that loads. Delivers AC-A3 and AC-A5.
- **MIRROR**: `harness/src/atr/local/serve.py:121-127`
- **VALIDATE**: `$PY -c "import json,glob,os; fs=glob.glob(os.path.expanduser('~/atr/data/local-inference/bench/qwen3.5-9b-q4_k_m-*.json')); best=max((sum(1 for x in json.load(open(f))['results'] if not x.get('error') and x['prompt_per_second']>0 and x['generation_per_second']>0 and x['gpu']['power_mean_w']>0) for f in fs), default=0); assert best>=3, f'{best} complete sizes'; print('PASS', best)"`

### Task 6: RUN the server and the benchmark for L-MoE, tuning the experts on the CPU

- **ACTION**: Start `qwen3.6-35b-a3b-ud-q3_k_xl` at context 131072 with the `--n-cpu-moe` value in `models.toml` (36). If it fails to load (out of VRAM or RAM), raise `--n-cpu-moe` (through `--arg`) until it loads; if it loads with more than about 1 GB of VRAM free, try lower values and keep the lowest that still leaves about 0.5 GB free at a full 128k prompt. Record every value tried, its VRAM and RAM use and its outcome. Run `$PY -m atr.local.bench` on the chosen value, then `serve stop`. If L-MoE cannot load at 128k with the containers that are running, stop and ask the operator before stopping any other project's container. Delivers AC-A5.
- **MIRROR**: `harness/src/atr/local/bench.py:72-85`
- **VALIDATE**: `$PY -c "import json,glob,os; fs=glob.glob(os.path.expanduser('~/atr/data/local-inference/bench/qwen3.6-35b-a3b-ud-q3_k_xl-*.json')); best=max((sum(1 for x in json.load(open(f))['results'] if not x.get('error') and x['prompt_per_second']>0 and x['generation_per_second']>0 and x['gpu']['power_mean_w']>0) for f in fs), default=0); assert best>=3, f'{best} complete sizes'; print('PASS', best)"`

### Task 7: UPDATE infra/local-inference/models.toml

- **ACTION**: For both main-stage entries, set `context` to the context chosen from the measurements (at least 131072 when it fits) and L-MoE's `--n-cpu-moe` to the value chosen in Task 6; keep `--parallel 1` in the shared flags (one run at a time, D-058) and add a comment stating the slot choice. Add a `baseline` key to each main-stage entry naming its benchmark file (basename only, under `$ATR_DATA_DIR/local-inference/bench/`). Update the header comment: the flags are measured in WP0 on 2026-11-04 and recorded in `documentation/research/local-route.md`. Delivers AC-A6.
- **MIRROR**: `infra/local-inference/models.toml:30-46`
- **VALIDATE**: `$PY -c "from atr.local import config; s=config.load(); m={i:e for i,e in s['models'].items() if e['stage']=='main'}; assert all(e.get('baseline','').endswith('.json') and e['context']>=131072 for e in m.values()), 'baseline or context missing'; import pathlib; assert all((pathlib.Path.home()/'atr/data/local-inference/bench'/e['baseline']).exists() for e in m.values()), 'baseline file missing'; a=s['server']['args']; assert a[a.index('--parallel')+1]=='1'; print('PASS')"`

### Task 8: CREATE documentation/research/local-route.md

- **ACTION**: Write the report of the local route in the shape of the other research reports (title, status line, Progress table with WP0 to WP3 items), with a section "Machine baseline" holding: the machine's state during the measurement (GPU, VRAM in use at the start, the VM's memory, the containers running counted, not named, the image digest and build); a table per main model with, for each prompt size, prompt tokens, prompt tokens/s, generation tokens/s, wall time, mean and peak GPU power, GPU energy, peak VRAM and the container's peak memory; the `--n-cpu-moe` values tried for L-MoE and their outcomes; and the choices (quantization, context, experts on the CPU, slot count) with their reasons. List what Phase 2 must still decide (prompt-cache RAM, final flags). Use "Target A" only as a codename; the report holds no target content. Delivers AC-A6.
- **MIRROR**: `documentation/research/m3-results.md:1-5`
- **VALIDATE**: `set -euo pipefail; f=../documentation/research/local-route.md; grep -q '^## Machine baseline' $f; grep -q 'qwen3.5-9b-q4_k_m' $f; grep -q 'qwen3.6-35b-a3b-ud-q3_k_xl' $f; grep -q -- '--n-cpu-moe' $f; echo PASS`

## Validation Commands

Every block runs in WSL from `$CODE_ROOT/harness` with `PY="env PYTHONPATH=src $HOME/atr/tools/harness-venv/bin/python"`.

### Level 1: STATIC_ANALYSIS

```bash
set -euo pipefail
$PY -m py_compile src/atr/local/config.py src/atr/local/fetch.py src/atr/local/serve.py src/atr/local/bench.py
$PY -c "import tomllib; tomllib.load(open('../infra/local-inference/models.toml','rb')); print('toml ok')"
for m in fetch serve bench; do $PY -m atr.local.$m --help > /dev/null; done
echo PASS
```

### Level 2: CONTENT_INVARIANTS

```bash
set -euo pipefail
# AC-1: a digest mismatch and a size mismatch are kept as <file>.bad and fail.
$PY -c "import hashlib,tempfile; from pathlib import Path; from atr.local import config, fetch; d=Path(tempfile.mkdtemp()); (d/'g.gguf').write_bytes(b'abc'); g={'file':'g.gguf','size':3,'sha256':hashlib.sha256(b'abc').hexdigest()}; fetch.fetch('g',g,d); assert config.verified(g,d); (d/'b.gguf').write_bytes(b'abc'); b={'file':'b.gguf','size':3,'sha256':'0'*64}; r=None
try: fetch.fetch('b',b,d)
except SystemExit as e: r=e
assert r is not None and (d/'b.gguf.bad').exists(); print('fetch ok')"
# Privacy: no private term (word match, as the exporter's leak check) in the files this phase changes or creates.
files="$(git -C .. diff --name-only HEAD -- harness/src/atr/local infra/local-inference | sed 's|^|../|') $(ls ../documentation/research/local-route.md 2>/dev/null || true)"
if [ -n "${files// /}" ] && grep -lwiF -f <(grep -vE '^(#|[[:space:]]*$)' ~/atr/data/leak-terms.txt) $files; then echo "FAIL: private term in a changed file"; exit 1; fi
echo PASS
```

### Level 3: INTEGRATION

```bash
set -euo pipefail
# AC-1, AC-2 and AC-3 on the real machine, with L-Small (the faster model to load).
$PY -m atr.local.serve list
$PY -m atr.local.serve start qwen3.5-9b-q4_k_m > /dev/null
trap '$PY -m atr.local.serve stop' EXIT
KEY=$(cat ~/atr/data/local-inference/server.key)
[ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8090/health)" = 200 ]
[ "$(curl -s -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' -d '{"model":"qwen3.5-9b","messages":[{"role":"user","content":"ping"}]}' http://127.0.0.1:8090/v1/messages/count_tokens)" = 401 ]
[ "$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' -d '{"model":"qwen3.5-9b","messages":[{"role":"user","content":"ping"}]}' http://127.0.0.1:8090/v1/messages/count_tokens)" = 200 ]
[ "$(docker port atr-llm 8080/tcp)" = "127.0.0.1:8090" ]
if grep -qF "$KEY" ~/atr/data/local-inference/server.json; then echo "FAIL: key in server.json"; exit 1; fi
$PY -c "import json,pathlib; r=json.loads((pathlib.Path.home()/'atr/data/local-inference/server.json').read_text()); missing=[k for k in ('image','image_id','build','sha256','context','args','published','machine') if k not in r]; assert not missing, missing; print('record ok')"
$PY -m atr.local.bench --contexts 4096 --predict 32
echo PASS
```

## Acceptance Criteria

- **AC-A1 (PRD AC-1):** `atr.local.fetch` keeps a file only when its size and SHA-256 match `models.toml` and writes a marker next to it; a file whose digest (or size) does not match is renamed to `<file>.bad` and the command exits non-zero.
- **AC-A2 (PRD AC-1):** Both main-stage files are in `/mnt/d/atr/models` with their verified markers, and the pinned image is present by digest.
- **AC-A3 (PRD AC-2):** `atr.local.serve start <id>` answers `/health`; `POST /v1/messages/count_tokens` returns 401 without the key and 200 with it; the start fails closed unless the port is published on `127.0.0.1` only; `server.json` records the image and its id, the build, the file's SHA-256, the context and the flags, and never the key.
- **AC-A4 (PRD AC-3):** `atr.local.bench` writes a JSON file with, for each prompt size (32k, 64k and 128k tokens, or the largest that fits), the prompt and generation tokens per second, mean and peak GPU power, GPU energy integrated over the sample times, peak VRAM and the container's memory (peak and after), keeps the sizes measured before a failure and exits non-zero on one.
- **AC-A5 (PRD AC-3):** Benchmark files exist for L-Small and L-MoE with three complete prompt sizes each.
- **AC-A6 (PRD AC-3):** `models.toml` records the chosen quantization, context, experts on the CPU and slot count for both main models, with a pointer to each benchmark file, and `documentation/research/local-route.md` records the measurements and the choices.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Not enough RAM or VRAM for L-MoE at 128k beside the desktop and the other containers (PRD Technical Risks, row 3) | M | H | Raise `--n-cpu-moe`; the UD-IQ3_XXS fallback is already pinned; ask the operator before stopping any other project's container |
| Loading weights from D: through Docker Desktop's file sharing is slow (PRD Open Questions) | M | L | The load time is recorded in `server.json`; it is not part of a run |
| `nvidia-smi` power readings under WSL 2 are averaged by the driver rather than instantaneous | M | L | Energy integrates over measured intervals; the field used is recorded; whole-system energy stays a Could item |
| A b12063 flag differs from the master README (`--load-mode`, `--cache-ram`) | L | M | The server rejects an unknown flag and the start stops (no silent drop); flags are checked against the image's `--help` |
| The downloads (about 22.5 GB) fail or are slow | L | M | `curl --continue-at -` resumes; the digest check rejects a corrupt file |

## Notes

- **TDD routing (this plan, against the relay repo):** Current value of `tdd` in `docs/context/methodology.md`: **false**. Test-after ordering — when a test framework is declared, the test pair (test-writer/test-reviewer) authors and maintains the suite from the Acceptance Criteria above, after the Implementer + Code Review; with no framework declared, no tests are authored.
- No test framework is declared (`test_frameworks: []`), so no test files are authored; the `VALIDATE` commands exercise the scripts directly and on the real machine.
- The downloads were approved by the operator in chat on 2026-11-04 and started before this plan was written, with the drafted `fetch.py`; Task 4 finishes and verifies them with the updated module.
- The machine is measured as it is: the Windows desktop keeps its share of VRAM and the other projects' containers keep running. Both are recorded, so a later run can tell whether it ran under the same conditions.

*Generated: 2026-11-04*
*Approved: 2026-11-04*
*Implemented: 2026-11-04*
*Status: IMPLEMENTED*
