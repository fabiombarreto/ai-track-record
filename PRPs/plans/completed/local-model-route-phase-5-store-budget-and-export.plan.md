# Feature: Store, budget and export (Phase 5 of local-model-route)

```
**Decision Gate**
- Active context: none
- Activated criteria: business rules for store and publication and for budget (docs/domain/areas/store-and-publication.md, docs/domain/areas/budget.md); change of three components (atr.store.load, atr.ops.budget, atr.store.export); cross-cutting pattern (the reconciliation view; the export allowlist and leak check)
- Decisions found:
  - Cost computed from tokens, with its source labeled (D-022): a local run has no API cost, recorded as zero with the label "local", never as a missing value
  - Run folders are the system of record (D-033): the store is rebuilt from the trial folders, including the route, the power samples and the server's counters the launcher wrote
  - The MVP ceiling of US$ 800 is never drawn on by other experiments (D-028, D-058): `lc-` jobs add nothing to the total the budget checks
  - Normalized outcomes (D-019): a local run's failure stays `error`, with the cause kept as its native reason
  - Export through an allowlist with a leak check (PUB-02, D-013); results of local runs carry a workflow-portability label (R9 of the scope and roadmap)
- Applicable anti-patterns:
  - Private-target material in the repository or an export (the leak check still runs on every export; the check data of this phase is synthetic)
  - Publishing local runs unlabeled, or on the same cost axis as API runs (the export labels them; their cost is zero with its source)
  - A false mismatch in the reconciliation caused by a cost the local route cannot have
  - Silently dropping a configuration option (a trial whose route record says local but lacks the server's records is loaded with the gaps visible, not dropped)
- Applicable architectural rules:
  - The store is a rebuildable view of the run folders; the loader never writes to them
  - Graders sit outside the workflow and stay unchanged
  - Deny by default in the export: a new field is published only when it is on the allowlist, and the allowlist version is raised when it changes
- Result: PROCEED
```

## Source

- `PRPs/prds/local-model-route.prd.md` — Implementation Phases row 5: "Store, budget and export" — Goal: Local runs are counted, reconciled and published correctly. — Success signal: The synthetic local run is loaded with route `local`, reconciled across three sources, excluded from the MVP's ceiling and exported with its label.

## Summary

This phase teaches the store, the budget and the export about the local route. The loader reads `agent/route.json` and the launcher's `server/` records: each trial gets its `route`, `provider`, `quantization` and `server_build`, the GPU energy and mean power from `server/power.json`, and the server's prompt, cached-prompt and generated token counters from `server/metrics.prom`; a local run's `cost_usd` is zero with `cost_source` `local` and the SDK's own estimate kept apart in `sdk_cost_estimate_usd`, while API runs keep their cost with `cost_source` `sdk`. A failed run keeps the exception's cause as its native outcome. The reconciliation view gains the server as a third source for local runs and compares tokens only for them, so a cost the local route cannot have never reads as a mismatch. `atr.ops.budget` leaves `lc-` jobs out of the total it checks against the ceiling and reports them on their own line. The export adds `route`, `provider`, `quantization` and a `label` that names local runs as workflow portability on a quantized open-weight model on one consumer machine, publishes a local run's model as its alias (so the leak check's path pattern does not mistake `local/qwen3.5-9b` for a file path) and raises the allowlist version to 3.

## User Story

As the operator of AI Track Record
I want local runs loaded, reconciled, budgeted and exported with their route and their real cost, which is no API cost but machine energy
So that the store and the dashboard never mix local runs with API runs, never count them against the MVP's ceiling and never report a false mismatch

## Problem Statement

The store has no route column, so a local run is indistinguishable from an API run (`harness/src/atr/store/load.py:37-55`). The reconciliation view compares costs within 1e-6 across the SDK, events and metrics, so a local run, whose cost Claude Code cannot price, may read as a mismatch, and the server's own token counters are not a source at all (`load.py:81-128`). A failed local run has no SDK result, so its outcome is `error` with no native reason (`load.py:165-182`, `:283-285`); the cause sits only in Harbor's exception. The budget sums every job's spend against the ceiling (`harness/src/atr/ops/budget.py:38-61`), so `lc-` jobs would count. The export has no route or label (`harness/src/atr/store/export.py:33-40`), and its relative-path pattern matches a model id like `local/qwen3.5-9b`, which would block the export of any local run (`export.py:46-52`).

## Solution Statement

Extend the three modules in place, following their existing shapes: new nullable columns appended to `trials` and filled from the trial folder's files when present; a reconciliation view with a server source joined per trial; a prefix filter in the budget; new export fields with the alias as the published model. Check every change on two kinds of data: the real local trials of Phases 3 and 4 (which ended before any model output, so their counts are zero), and a synthetic data folder built in a temporary directory for the checks, with one API trial and one local trial whose sources agree, so the matching and the cost labels are exercised end to end.

## Metadata

| Key | Value |
|---|---|
| Type | Enhancement (three store and ops modules) |
| Complexity | Medium |
| Systems Affected | harness/src/atr/store/load.py; harness/src/atr/ops/budget.py; harness/src/atr/store/export.py; documentation/research/local-route.md |
| Dependencies | Phases 3 and 4 complete: `agent/route.json` from the agent, `server/{server.json,metrics.prom,power.json}` from `atr.local.launch`; the local trials in `~/atr/data/jobs/lc-p3-*` and `lc-p4-*`; DuckDB in the harness venv |
| Estimated Tasks | 7 |
| Source PRD line ref | `PRPs/prds/local-model-route.prd.md:66-67` (AC-6, AC-7), `:69` (AC-9), `:169` (row 5), `:198-201` (Phase 5 details) |
| phase_type | feature |

## Mandatory Reading

| Priority | Path | Lines | Why |
|---|---|---|---|
| P0 | `PRPs/prds/local-model-route.prd.md` | 66-69, 169, 198-201 | AC-6, AC-7 (the budget half), AC-9 and the Phase 5 scope |
| P0 | `harness/src/atr/store/load.py` | 37-55, 81-135, 165-182, 228-239, 256-358 | The trials table, the reconciliation and spend views, `normalize_outcome`, `TRIAL_COLUMNS`, `load_trials` |
| P0 | `harness/src/atr/ops/budget.py` | 1-71 | `spend_by_job` and the ceiling check |
| P0 | `harness/src/atr/store/export.py` | 1-54, 66-131 | Fields, patterns, `build_export`, `leak_check`, the allowlist version |
| P1 | `documentation/plans/local-models.md` | 162-169, 215-228 | What the store, budget and export must do for local runs, and how metrics compare across routes |
| P1 | `harness/src/atr/agents/claude_sdk.py` | `_record_route` | The keys of `agent/route.json` |
| P1 | `harness/src/atr/local/launch.py` | the records it writes | The keys of `server/power.json`; `server/metrics.prom` is llama.cpp's Prometheus text |
| P1 | `docs/domain/areas/store-and-publication.md`, `docs/domain/areas/budget.md` | all | The rules of the two areas |

## Patterns to Mirror

```python
# SOURCE: harness/src/atr/store/load.py:165-182
def normalize_outcome(exception_type: str | None, subtype: str | None) -> str | None:
    """Map Harbor's exception and the SDK's result subtype to D-019's outcomes.

    Agents without an SDK result, such as `oracle` and `nop`, get None. A
    relay HALT ends as a successful SDK result; load_trials turns it into
    `halted` from relay's own orchestrator record.
    """
    if exception_type == "AgentTimeoutError":
        return "timed_out"
    if exception_type:
        return "error"
    if subtype is None:
        return None
    if subtype == "success":
        return "completed"
    if subtype in ("error_max_budget_usd", "error_max_turns"):
        return "budget_exceeded"
    return "error"
```
Unchanged by Task 1; only the native reason of an exception without an SDK result is added beside it.

```python
# SOURCE: harness/src/atr/ops/budget.py:38-48
def spend_by_job(jobs_dir: Path) -> dict[str, float]:
    spend: dict[str, float] = defaultdict(float)
    for trial in sorted(p.parent for p in jobs_dir.glob("*/*/config.json")):
        # A regrade copies the agent folder of the trial it regraded.
        regrade = (read_json(trial / "config.json").get("source_trial") or {}).get("action") == "regrade"
        run = None if regrade else read_json(trial / "agent" / "result.json").get("total_cost_usd")
        # The SDK reports a session's cost cumulatively, so the last turn has it all.
        review = [c for c in read_json(trial / "review" / "review.json").get("cost_usd_per_turn") or []
                  if c is not None]
        spend[trial.parent.name] += (run or 0.0) + (review[-1] if review else 0.0)
    return dict(spend)
```
Kept by Task 3; the ceiling check filters its result by job prefix.

```python
# SOURCE: harness/src/atr/store/export.py:46-52
PATTERNS = {
    "absolute path": re.compile(r"(/root/|/home/|/mnt/|/app/|/opt/|[A-Za-z]:\\\\)"),
    "source file name": re.compile(r"\b[\w-]+\.(py|tsx?|sql|toml|ya?ml|html)\b"),
    "relative path": re.compile(r"\b[\w.-]+/[\w./-]*\.\w+\b"),
    "secret": re.compile(r"(sk-ant-[\w-]+|ANTHROPIC_API_KEY|Bearer\s+\S+|api[_-]?key)", re.I),
    "e-mail address": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),
}
```
Unchanged by Task 4: the leak check is not weakened; the export publishes the alias instead.

## Files to Change

| File | Action | Justification |
|---|---|---|
| `harness/src/atr/store/load.py` | UPDATE | AC-6: route, energy, server tokens, labeled cost, native reason of a failure; the reconciliation view with the server as a third source |
| `harness/src/atr/ops/budget.py` | UPDATE | AC-7, budget half: `lc-` jobs out of the ceiling's total |
| `harness/src/atr/store/export.py` | UPDATE | AC-9: route, provider, quantization and label fields; the alias as a local run's model; allowlist version 3 |
| `documentation/research/local-route.md` | UPDATE | The store, budget and export of local runs and the checks of this phase |

## NOT Building (Scope Limits)

- A completed local run with tokens to reconcile: the local runs so far ended at their first request on the Qwen3.5-9B chat-template error (Phase 3). The matching across three sources is checked on synthetic check data here and on a real run in Phase 6 (check L7), once checks L1 and L3 have fixed the template or the model.
- The independent review of a local run, which calls Anthropic's API: it needs the operator's approval and a run with changes to review (Phase 6).
- Dashboard changes — M4 work; local results publish only after the MVP is public.
- Whole-system energy — PRD Could item; the store carries the GPU's energy only, labeled as such.
- Any change to the graders or to the trial folders.

## Step-by-Step Tasks

All commands run in WSL (`wsl.exe -d Ubuntu --exec bash -lc '<command>'`, never starting the string with `/`) from `$CODE_ROOT/harness`, where `$CODE_ROOT` is `/mnt/c/repos/ai-track-record/.worktrees/local-model-route` and `PY="env PYTHONPATH=src $HOME/atr/tools/harness-venv/bin/python"`. Git runs from Windows. The synthetic check data is built by `$CHECK` below into a fresh temporary directory, never under `~/atr/data`, and removed afterwards:

```bash
CHECK='import json,os,sys,pathlib
d=pathlib.Path(sys.argv[1]); j=d/"jobs"; t=d/"tasks"/"synthetic-events"/"task-01"; t.mkdir(parents=True)
(t/"atr-task.json").write_text(json.dumps({"target":"synthetic-events","codename":"synthetic-events","target_description":"Synthetic","visibility":"public","task_id":"task-01","title":"Check","difficulty":"easy","category":"backend","criteria":1}))
def trial(job,name,model,route,cost,u):
    p=j/job/name; (p/"agent").mkdir(parents=True); (p/"server").mkdir()
    (p/"config.json").write_text("{}")
    (p/"result.json").write_text(json.dumps({"trial_name":name,"task_name":"t","started_at":"2026-11-04T00:00:00","finished_at":"2026-11-04T00:10:00","config":{"agent":{"model_name":model,"kwargs":{"config_label":"c","route":route}},"task":{"path":str(t)}},"verifier_result":{"rewards":{"reward":1.0}}}))
    (p/"agent"/"result.json").write_text(json.dumps({"subtype":"success","total_cost_usd":cost,"session_id":"s-"+name,"modelUsage":{model.split("/")[-1]:{"inputTokens":u[0],"outputTokens":u[1],"cacheReadInputTokens":u[2],"cacheCreationInputTokens":u[3],"costUSD":cost}}}))
    if route=="local":
        (p/"agent"/"route.json").write_text(json.dumps({"provider":"local","model":"qwen3.5-9b","quantization":"q4_k_m","build":"b12063","file":"x.gguf","sha256":"0"*64}))
        (p/"server"/"power.json").write_text(json.dumps({"samples":10,"energy_wh":1.5,"power_mean_w":90.0}))
        (p/"server"/"metrics.prom").write_text("llamacpp:prompt_tokens_total %d\nllamacpp:prompt_tokens_cached_total %d\nllamacpp:tokens_predicted_total %d\n"%(u[0]+u[3],u[2],u[1]))
trial("m3-check-api","t1","claude-sonnet-5-5","anthropic",0.5,(100,50,1000,200))
trial("lc-check-local","t2","local/qwen3.5-9b","local",0.37,(100,50,1000,200))
tel=d/"telemetry"; tel.mkdir()
def ev(job,tr,model,u,cost): return {"resourceLogs":[{"resource":{"attributes":[{"key":"atr.job","value":{"stringValue":job}},{"key":"atr.trial","value":{"stringValue":tr}}]},"scopeLogs":[{"logRecords":[{"attributes":[{"key":"event.name","value":{"stringValue":"api_request"}},{"key":"event.sequence","value":{"intValue":"1"}},{"key":"model","value":{"stringValue":model}},{"key":"input_tokens","value":{"intValue":str(u[0])}},{"key":"output_tokens","value":{"intValue":str(u[1])}},{"key":"cache_read_tokens","value":{"intValue":str(u[2])}},{"key":"cache_creation_tokens","value":{"intValue":str(u[3])}},{"key":"cost_usd","value":{"doubleValue":cost}}]}]}]}]}
(tel/"logs.jsonl").write_text(json.dumps(ev("m3-check-api","t1","claude-sonnet-5-5",(100,50,1000,200),0.5))+"\n"+json.dumps(ev("lc-check-local","t2","qwen3.5-9b",(100,50,1000,200),0.37))+"\n")
def pt(attrs,v): return {"attributes":[{"key":k,"value":{"stringValue":s}} for k,s in attrs],"asDouble":v}
def me(job,tr,model,u,cost): return {"resourceMetrics":[{"resource":{"attributes":[{"key":"atr.job","value":{"stringValue":job}},{"key":"atr.trial","value":{"stringValue":tr}}]},"scopeMetrics":[{"metrics":[{"name":"claude_code.token.usage","sum":{"aggregationTemporality":1,"dataPoints":[pt([("type",k),("model",model)],v) for k,v in zip(("input","output","cacheRead","cacheCreation"),u)]}},{"name":"claude_code.cost.usage","sum":{"aggregationTemporality":1,"dataPoints":[pt([("model",model)],cost)]}}]}]}]}
(tel/"metrics.jsonl").write_text(json.dumps(me("m3-check-api","t1","claude-sonnet-5-5",(100,50,1000,200),0.5))+"\n"+json.dumps(me("lc-check-local","t2","qwen3.5-9b",(100,50,1000,200),0.37))+"\n")
print(d)'
```

`$CHECK` writes all four sources for both trials with the same token counts (100 input, 50 output, 1000 cache read, 200 cache creation): the SDK's `modelUsage`, an `api_request` event in `telemetry/logs.jsonl`, `claude_code.token.usage` and `claude_code.cost.usage` delta points in `telemetry/metrics.jsonl` (the shapes `load_events` and `load_metrics` read, `load.py:360-425`), and, for the local trial, the server's counters (300 processed plus 1000 cached prompt tokens, 50 output). If the loader's readers expect a different OTLP shape than `$CHECK` writes, adapt `$CHECK` to the loader, never the loader to `$CHECK`, and say so in the report.

### Task 1: UPDATE harness/src/atr/store/load.py (route-aware trials)

- **ACTION**: Append nullable columns to the `trials` table and to `TRIAL_COLUMNS`: `route TEXT`, `provider TEXT`, `quantization TEXT`, `server_build TEXT`, `cost_source TEXT`, `sdk_cost_estimate_usd DOUBLE`, `energy_wh DOUBLE`, `power_mean_w DOUBLE`, `server_prompt_tokens BIGINT`, `server_cached_prompt_tokens BIGINT`, `server_output_tokens BIGINT`. In `load_trials`, read `agent/route.json` (when present), `server/power.json` and `server/metrics.prom` (when present; parse `llamacpp:prompt_tokens_total`, `llamacpp:prompt_tokens_cached_total` and `llamacpp:tokens_predicted_total` from the Prometheus text, ignoring comments). `route` is `route.json`'s `provider`, else the job config's `kwargs.route`, else `anthropic` for trials with an SDK result and `None` for agents without one (oracle, nop). On `local`: `cost_usd = 0.0`, `cost_source = "local"`, `sdk_cost_estimate_usd` = the SDK's `total_cost_usd`; otherwise `cost_usd` as today and `cost_source = "sdk"` when it is not null. When a trial has an exception and no SDK subtype, set `native_outcome` so a failed run names its cause: the exception type, then `: ` and the first line of Harbor's exception message (`exception_info.exception_message`, cut at 200 characters) when that line is the agent's own message (a pre-flight failure such as "the local server at ... rejected the run's key"); when the line is Harbor's "Command failed ..." (the runner's command line, which holds container paths the export's leak check blocks), use instead the `error` value of the last `AssistantMessage` in `agent/messages.jsonl` (for example `server_error`), or the exception type alone. `outcome` stays as `normalize_outcome` returns it. The `spend` view keeps summing `cost_usd`, which is now zero for local runs. Update the module docstring. Delivers AC-A1.
- **MIRROR**: `harness/src/atr/store/load.py:165-182` and `harness/src/atr/store/load.py:256-330`
- **VALIDATE**: `set -euo pipefail; T=$(mktemp -d); $PY -c "$CHECK" $T > /dev/null; $PY -m atr.store.load --data-dir $T > /dev/null; $PY -c "import duckdb,sys; c=duckdb.connect(sys.argv[1]+'/atr.duckdb', read_only=True); r=dict(c.execute(\"SELECT job,(route,cost_usd,cost_source,sdk_cost_estimate_usd,energy_wh,server_output_tokens) FROM trials\").fetchall()); assert r['lc-check-local']==('local',0.0,'local',0.37,1.5,50), r['lc-check-local']; assert r['m3-check-api'][0]=='anthropic' and r['m3-check-api'][1]==0.5 and r['m3-check-api'][2]=='sdk', r['m3-check-api']; print('PASS')" $T; rm -rf $T`

### Task 2: UPDATE harness/src/atr/store/load.py (the reconciliation view)

- **ACTION**: Rewrite the `reconciliation` view so it keeps every existing column and adds a `route` column (from `trials`), the server's counts per trial (`server_prompt` = prompt plus cached prompt tokens, `server_output`) and, for local trials, the SDK's total input (`input + cache read + cache creation`) beside them. The `status` rule: on the Anthropic route, exactly today's rule; on the local route, `match` when the SDK, the events and the metrics agree on all four token counts (as today) and the server's prompt total equals the SDK's total input and its output equals the SDK's output, with no cost comparison; `mismatch` otherwise; `no telemetry` and `model missing from modelUsage` as today. Events and metrics of a local run name the alias, and `modelUsage` may name it with or without the `local/` prefix: join on the model with that prefix removed. The `main()` summary prints the route next to each row. Delivers AC-A2.
- **MIRROR**: `harness/src/atr/store/load.py:81-128`
- **VALIDATE**: `set -euo pipefail; T=$(mktemp -d); $PY -c "$CHECK" $T > /dev/null; $PY -m atr.store.load --data-dir $T; $PY -c "import duckdb,sys; c=duckdb.connect(sys.argv[1]+'/atr.duckdb', read_only=True); r={j:(route,s) for j,route,s in c.execute('SELECT job,route,status FROM reconciliation').fetchall()}; print(r); assert r['lc-check-local']==('local','match'), r; assert r['m3-check-api']==('anthropic','match'), r; print('PASS')" $T; rm -rf $T`

### Task 3: UPDATE harness/src/atr/ops/budget.py

- **ACTION**: Add a constant `LOCAL_PREFIX = "lc-"`. In `main()`, compute the MVP's total over the jobs that do not start with `lc-`; that total is the one printed as "spent", compared with the ceiling and used by `--next`. Report the `lc-` jobs on a separate line: their run cost recorded by the SDK (an estimate Claude Code makes for a model it cannot price, not money spent) and their reviews' cost, which is money spent on Anthropic credits but counted with the local models experiment (documentation/plans/local-models.md, section 11.2), not against the MVP's ceiling. Keep the first line's format (`budget.py:62-64`): `spent: US$ <total> (jobs m3-*: US$ <batch>); target US$ 400, ceiling US$ 800, left US$ <left>`, so the check below reads `spent: US$ 0.50 ` for the synthetic data. Update the module docstring. `spend_by_job` stays unchanged. Delivers AC-A3.
- **MIRROR**: `harness/src/atr/ops/budget.py:38-48`
- **VALIDATE**: `set -euo pipefail; T=$(mktemp -d); $PY -c "$CHECK" $T > /dev/null; out=$($PY -m atr.ops.budget --data-dir $T --next 799.4); echo "$out"; echo "$out" | grep -q 'US\$ 0.50 '; $PY -m atr.ops.budget --data-dir $T --next 799.6 && { echo 'FAIL: ceiling not checked'; exit 1; }; rm -rf $T; echo PASS`

### Task 4: UPDATE harness/src/atr/store/export.py

- **ACTION**: Raise `ALLOWLIST_VERSION` to `"3"`. Add `route`, `provider`, `quantization`, `cost_source`, `energy_wh` and a computed `label` to every exported run: `label` is `"workflow portability, quantized local model"` for local runs (under the leak check's 64-character limit for text in a private run, `export.py:53`) and `null` for API runs. For local runs, export `model` as the alias without the `local/` prefix. Leave `PATTERNS`, `leak_check` and the deny-by-default rule as they are. Update the module docstring. Delivers AC-A4.
- **MIRROR**: `harness/src/atr/store/export.py:33-40` and `harness/src/atr/store/export.py:46-52`
- **VALIDATE**: `set -euo pipefail; T=$(mktemp -d); $PY -c "$CHECK" $T > /dev/null; $PY -m atr.store.load --data-dir $T > /dev/null; $PY -m atr.store.export $T/out lc-check-local m3-check-api --data-dir $T; $PY -c "import json,sys; d=sys.argv[1]+'/out/'; r={x['job']:x for x in json.load(open(d+'runs.json'))}; l=r['lc-check-local']; assert l['route']=='local' and l['model']=='qwen3.5-9b' and l['label'].startswith('workflow portability') and l['cost_usd']==0.0 and l['cost_source']=='local', l; assert r['m3-check-api']['label'] is None; assert json.load(open(d+'publication.json'))['allowlist_version']=='3'; print('PASS')" $T; rm -rf $T`

### Task 5: RUN the store, the budget and an export on the real local trials

- **ACTION**: Rebuild the real store (`$PY -m atr.store.load`, which rebuilds `~/atr/data/atr.duckdb` from the run folders as always) and confirm that the Phase 3 and Phase 4 local trials load with route `local`, `cost_source` `local`, a native outcome naming the chat-template error, the Phase 4 trial's GPU energy, and server counts of zero; and that the API trials of the MVP are unchanged (the same count of trials and the same total `cost_usd` over `m2-` and `m3-` jobs as before the change — record both numbers before rebuilding, from the current store). Run `$PY -m atr.ops.budget` and confirm the MVP's spent total is unchanged and the `lc-` line appears. Export the two local jobs to a temporary folder with a temporary data directory for the publication record, so nothing is appended to the real `publications.jsonl`: `$PY -m atr.store.export $(mktemp -d)/out lc-p3-vanilla-l-small-synthetic-task-01 lc-p4-launcher-l-small-synthetic-task-01-local --db ~/atr/data/atr.duckdb --data-dir $(mktemp -d)`; confirm it passes the leak check and carries the route and label. Delivers AC-A5.
- **MIRROR**: `harness/src/atr/store/load.py:427-450`
- **VALIDATE**: `set -euo pipefail; $PY -c "import duckdb,os; c=duckdb.connect(os.path.expanduser('~/atr/data/atr.duckdb'), read_only=True); r=c.execute(\"SELECT count(*), count(*) FILTER (WHERE route='local' AND cost_source='local' AND cost_usd=0) FROM trials WHERE job LIKE 'lc-p%'\").fetchone(); assert r[0]>=2 and r[0]==r[1], r; n=c.execute(\"SELECT native_outcome FROM trials WHERE job='lc-p4-launcher-l-small-synthetic-task-01-local'\").fetchone()[0]; assert n, 'no native reason'; e=c.execute(\"SELECT energy_wh FROM trials WHERE job='lc-p4-launcher-l-small-synthetic-task-01-local'\").fetchone()[0]; assert e and e>0, e; print('PASS', r)" && $PY -m atr.ops.budget | grep -q 'lc-' && echo PASS`

### Task 6: UPDATE documentation/research/local-route.md

- **ACTION**: Add a section `## Store, budget and export` after "Launcher and allowlists": the new trial columns and where each comes from; the cost rule (zero with source `local`, the SDK's estimate kept apart); the reconciliation rule for local runs (tokens across four sources, no cost); the budget rule (`lc-` jobs out of the MVP's total, reported on their own line); the export fields, the label, the alias as the model and allowlist version 3. Record the checks: the synthetic check data's results (match, labels) and the real local trials' load, budget and export (outcome, native reason, energy, zero server counts, the MVP's totals unchanged), and state that the matching on a completed local run waits for check L7 in Phase 6. Update the Progress table (WP2: store, budget and export done). Delivers AC-A5.
- **MIRROR**: `documentation/research/local-route.md:1-20`
- **VALIDATE**: `set -euo pipefail; f=$CODE_ROOT/documentation/research/local-route.md; grep -q '^## Store, budget and export' $f; grep -q 'cost_source' $f; grep -q 'allowlist version 3' $f; echo PASS`

### Task 7: VERIFY privacy on every changed file

- **ACTION**: Run the leak check (word match, as the exporter's) over the four files, and confirm that no temporary check directory or export folder remains under `~/atr/data` and that the real `publications.jsonl` has the same number of lines as before Task 5. Delivers AC-A5.
- **MIRROR**: `harness/src/atr/store/export.py:115-131`
- **VALIDATE**: `set -euo pipefail; files="src/atr/store/load.py src/atr/ops/budget.py src/atr/store/export.py ../documentation/research/local-route.md"; if grep -lwiF -f <(grep -vE '^(#|[[:space:]]*$)' ~/atr/data/leak-terms.txt) $files; then echo "FAIL: private term"; exit 1; fi; echo PASS`

## Validation Commands

`$CODE_ROOT`, `$PY` and `$CHECK` as in the Step-by-Step Tasks.

### Level 1: STATIC_ANALYSIS

```bash
set -euo pipefail
cd $CODE_ROOT/harness
$PY -m py_compile src/atr/store/load.py src/atr/ops/budget.py src/atr/store/export.py
for m in atr.store.load atr.ops.budget atr.store.export; do $PY -m $m --help > /dev/null; done
$PY -c "import duckdb; from atr.store.load import SCHEMA; c=duckdb.connect(); c.execute(SCHEMA); print('schema ok')"
echo PASS
```

### Level 2: CONTENT_INVARIANTS

```bash
set -euo pipefail
cd $CODE_ROOT/harness
T=$(mktemp -d); $PY -c "$CHECK" $T > /dev/null
$PY -m atr.store.load --data-dir $T > /dev/null
# AC-6: a local run is loaded with route local, zero cost labeled local, and reconciles across four sources.
$PY -c "import duckdb,sys; c=duckdb.connect(sys.argv[1]+'/atr.duckdb', read_only=True); t=c.execute(\"SELECT route,cost_usd,cost_source FROM trials WHERE job='lc-check-local'\").fetchone(); assert t==('local',0.0,'local'), t; s=c.execute(\"SELECT status FROM reconciliation WHERE job='lc-check-local'\").fetchone()[0]; assert s=='match', s; print('store ok')" $T
# AC-7: lc- jobs add nothing to the ceiling's total.
$PY -m atr.ops.budget --data-dir $T | grep -q 'spent: US\$ 0.50 '
# AC-9: the export carries the route and the label, the alias as the model, allowlist version 3, and passes the leak check.
$PY -m atr.store.export $T/out lc-check-local --data-dir $T > /dev/null
$PY -c "import json,sys; r=json.load(open(sys.argv[1]+'/out/runs.json'))[0]; assert r['route']=='local' and r['model']=='qwen3.5-9b' and r['label']; print('export ok')" $T
rm -rf $T
# Privacy: no private term (word match, as the exporter's leak check) in the changed files.
files="src/atr/store/load.py src/atr/ops/budget.py src/atr/store/export.py ../documentation/research/local-route.md"
if grep -lwiF -f <(grep -vE '^(#|[[:space:]]*$)' ~/atr/data/leak-terms.txt) $files; then echo "FAIL: private term in a changed file"; exit 1; fi
echo PASS
```

### Level 3: INTEGRATION

```bash
set -euo pipefail
cd $CODE_ROOT/harness
# The real store rebuilt from the run folders: local trials labeled, the MVP's numbers unchanged.
$PY -m atr.store.load > /dev/null
$PY -c "import duckdb,os; c=duckdb.connect(os.path.expanduser('~/atr/data/atr.duckdb'), read_only=True); r=c.execute(\"SELECT count(*) FILTER (WHERE route='local'), count(*) FILTER (WHERE job LIKE 'm3-%' AND route='anthropic') FROM trials\").fetchone(); assert r[0]>=2 and r[1]>0, r; print('store ok', r)"
$PY -m atr.ops.budget | grep -q 'lc-'
O=$(mktemp -d); P=$(mktemp -d)
$PY -m atr.store.export $O/out lc-p4-launcher-l-small-synthetic-task-01-local --db ~/atr/data/atr.duckdb --data-dir $P > /dev/null
$PY -c "import json,sys; r=json.load(open(sys.argv[1]+'/out/runs.json'))[0]; assert r['route']=='local' and r['label'] and '/' not in r['model']; print('export ok')" $O
rm -rf $O $P
echo PASS
```

## Acceptance Criteria

- **AC-A1 (PRD AC-6):** The store loads a local run with route `local`, its provider, quantization and server build, an API cost of zero labeled `local` with the SDK's estimate kept apart, its GPU energy and mean power, the server's prompt, cached-prompt and output token counts, and, when it failed before an SDK result, a native outcome naming the cause; API runs keep their cost, labeled `sdk`.
- **AC-A2 (PRD AC-6):** The reconciliation view compares a local run's input and output tokens across the SDK, Claude Code's events, its metrics and the server's record, and reports `match` when they agree, never a mismatch caused by a missing or unpriced cost; API runs are reconciled exactly as before.
- **AC-A3 (PRD AC-7):** `python -m atr.ops.budget --next <usd>` leaves `lc-` jobs out of the total it checks against the MVP's ceiling and reports them on their own line.
- **AC-A4 (PRD AC-9):** The export carries each run's route, provider, quantization, cost source and energy, labels local runs as workflow portability, publishes a local run's model as its alias so the leak check passes on it, and records allowlist version 3; the leak check itself is unchanged.
- **AC-A5 (PRD AC-6, AC-7, AC-9):** On the real data, the local trials load labeled with their cause and energy, the MVP's trial count and cost are unchanged, the budget reports the `lc-` line, an export of a local job passes the leak check without touching the real publication record, and `documentation/research/local-route.md` records all of it.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The server's counters do not follow Anthropic's split of cached and fresh input, so a completed local run reads as a mismatch | M | M | The rule compares the server's prompt total with the SDK's total input, which does not depend on the split; check L7 in Phase 6 confirms it on a real run and records the rule's result |
| The server's counters include requests outside the run (the pre-flight `count_tokens`) | M | L | `count_tokens` does not decode; check L7 shows whether it is counted; the server lives for one job only |
| A store change alters the MVP's numbers | L | H | Task 5 compares the MVP's trial count and cost before and after; API trials keep today's reconciliation rule |
| A real export appends to `publications.jsonl` | L | M | Task 5 uses a temporary data directory for the publication record |

## Notes

- **TDD routing (this plan, against the relay repo):** Current value of `tdd` in `docs/context/methodology.md`: **false**. Test-after ordering — when a test framework is declared, the test pair (test-writer/test-reviewer) authors and maintains the suite from the Acceptance Criteria above, after the Implementer + Code Review; with no framework declared, no tests are authored.
- No test framework is declared (`test_frameworks: []`), so no test files are authored; the `VALIDATE` commands exercise the modules on synthetic check data in a temporary directory and on the real run folders.
- The synthetic check data is built only for these checks, in a temporary directory, and removed after each command. It is never written under `~/atr/data`, loaded into the real store or exported for publication.
- Research for this plan (llama.cpp's server README and `server-task.cpp`, `server-context.cpp` on master; code.claude.com monitoring-usage and agent-sdk cost-tracking pages): on `/v1/messages` llama.cpp reports `input_tokens` as the prompt tokens not reused from its cache, `cache_read_input_tokens` as the reused prefix and no `cache_creation_input_tokens`; its `llamacpp:prompt_tokens_total` counts processed prompt tokens and `llamacpp:prompt_tokens_cached_total` the reused ones (`server/metrics.prom` of the Phase 4 check run lists both). The server's prompt total (processed plus cached) is therefore compared with the SDK's total input (input plus cache read plus cache creation), which holds whatever the split. The SDK's `costUSD` for a model it cannot price is a client-side estimate with `costBasis` `unknown`, which is why the store keeps it apart from the cost. Master may differ from build b12063; check L7 confirms the rule on a real run.
- No step calls Anthropic's API.

*Generated: 2026-11-04*
*Approved: 2026-11-04*
*Implemented: 2026-11-04*
*Status: IMPLEMENTED*
