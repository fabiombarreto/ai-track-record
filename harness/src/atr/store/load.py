"""Load Harbor trials and Claude Code telemetry into DuckDB.

Usage: python -m atr.store.load [--data-dir <dir>] [--db <file>]

Rebuilds the database from scratch on every run, from two sources under the
data directory (default $ATR_DATA_DIR or ~/atr/data):
- jobs/<job>/<trial>/: Harbor's result.json, the runner's agent/result.json
  and the verifier's changes.patch;
- telemetry/: the Collector's logs*.jsonl and metrics*.jsonl files.

Telemetry joins to trials on the atr.job and atr.trial resource attributes
the agent sets. The reconciliation view compares, per trial and model, the
api_request events and the token and cost metrics with the SDK's modelUsage.
Events are ordered by event.sequence, not by time, because the WSL clock can
jump while a run is in progress.
"""

import argparse
import json
import os
from pathlib import Path

import duckdb

SCHEMA = """
CREATE TABLE trials (
    job TEXT, trial TEXT, task TEXT, config TEXT, model TEXT, agent_version TEXT,
    session_id TEXT, outcome TEXT, native_outcome TEXT, num_turns INTEGER,
    wall_ms BIGINT, duration_ms BIGINT, duration_api_ms BIGINT, cost_usd DOUBLE,
    reward DOUBLE, criteria_satisfied DOUBLE, existing_tests_pass DOUBLE,
    exception TEXT, changes_patch_bytes BIGINT,
    started_at TIMESTAMP, finished_at TIMESTAMP,
    PRIMARY KEY (job, trial)
);
CREATE TABLE model_usage (
    job TEXT, trial TEXT, model TEXT,
    input_tokens BIGINT, output_tokens BIGINT,
    cache_read_tokens BIGINT, cache_creation_tokens BIGINT, cost_usd DOUBLE
);
CREATE TABLE events (
    job TEXT, trial TEXT, session_id TEXT, sequence BIGINT, name TEXT,
    timestamp TIMESTAMP, prompt_id TEXT, model TEXT, query_source TEXT,
    agent_name TEXT, tool_name TEXT,
    input_tokens BIGINT, output_tokens BIGINT,
    cache_read_tokens BIGINT, cache_creation_tokens BIGINT,
    cost_usd DOUBLE, duration_ms BIGINT, attributes JSON
);
CREATE TABLE metric_points (
    job TEXT, trial TEXT, name TEXT, type TEXT, model TEXT, query_source TEXT,
    agent_name TEXT, value DOUBLE, attributes JSON
);

CREATE VIEW reconciliation AS
WITH sdk AS (
    SELECT job, trial, model, input_tokens, output_tokens,
           cache_read_tokens, cache_creation_tokens, cost_usd
    FROM model_usage
), ev AS (
    SELECT job, trial, model,
           sum(input_tokens) AS input_tokens, sum(output_tokens) AS output_tokens,
           sum(cache_read_tokens) AS cache_read_tokens,
           sum(cache_creation_tokens) AS cache_creation_tokens,
           sum(cost_usd) AS cost_usd, count(*) AS requests
    FROM events WHERE name = 'api_request' GROUP BY ALL
), met AS (
    SELECT job, trial, model,
           sum(value) FILTER (WHERE name = 'claude_code.token.usage' AND type = 'input') AS input_tokens,
           sum(value) FILTER (WHERE name = 'claude_code.token.usage' AND type = 'output') AS output_tokens,
           sum(value) FILTER (WHERE name = 'claude_code.token.usage' AND type = 'cacheRead') AS cache_read_tokens,
           sum(value) FILTER (WHERE name = 'claude_code.token.usage' AND type = 'cacheCreation') AS cache_creation_tokens,
           sum(value) FILTER (WHERE name = 'claude_code.cost.usage') AS cost_usd
    FROM metric_points GROUP BY ALL
)
SELECT
    coalesce(sdk.job, ev.job) AS job, coalesce(sdk.trial, ev.trial) AS trial,
    coalesce(sdk.model, ev.model) AS model, ev.requests,
    sdk.input_tokens AS sdk_input, ev.input_tokens AS event_input, met.input_tokens AS metric_input,
    sdk.output_tokens AS sdk_output, ev.output_tokens AS event_output, met.output_tokens AS metric_output,
    sdk.cache_read_tokens AS sdk_cache_read, ev.cache_read_tokens AS event_cache_read,
    met.cache_read_tokens AS metric_cache_read,
    sdk.cache_creation_tokens AS sdk_cache_creation, ev.cache_creation_tokens AS event_cache_creation,
    met.cache_creation_tokens AS metric_cache_creation,
    sdk.cost_usd AS sdk_cost, ev.cost_usd AS event_cost, met.cost_usd AS metric_cost,
    CASE
        WHEN ev.requests IS NULL THEN 'no telemetry'
        WHEN sdk.model IS NULL THEN 'model missing from modelUsage'
        WHEN sdk.input_tokens = ev.input_tokens AND sdk.output_tokens = ev.output_tokens
         AND sdk.cache_read_tokens = ev.cache_read_tokens
         AND sdk.cache_creation_tokens = ev.cache_creation_tokens
         AND ev.input_tokens = met.input_tokens AND ev.output_tokens = met.output_tokens
         AND ev.cache_read_tokens = met.cache_read_tokens
         AND ev.cache_creation_tokens = met.cache_creation_tokens
         AND abs(sdk.cost_usd - ev.cost_usd) < 1e-6 AND abs(ev.cost_usd - met.cost_usd) < 1e-6
        THEN 'match'
        ELSE 'mismatch'
    END AS status
FROM sdk
FULL JOIN ev USING (job, trial, model)
LEFT JOIN met ON met.job = coalesce(sdk.job, ev.job)
    AND met.trial = coalesce(sdk.trial, ev.trial) AND met.model = coalesce(sdk.model, ev.model);

CREATE VIEW usage_by_agent AS
SELECT job, trial, coalesce(agent_name, '(main)') AS agent, query_source, model,
       count(*) AS requests, sum(input_tokens) AS input_tokens,
       sum(output_tokens) AS output_tokens, sum(cache_read_tokens) AS cache_read_tokens,
       sum(cache_creation_tokens) AS cache_creation_tokens, sum(cost_usd) AS cost_usd
FROM events WHERE name = 'api_request' GROUP BY ALL;
"""


def read_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def otlp_value(value: dict):
    for kind in ("stringValue", "boolValue", "doubleValue"):
        if kind in value:
            return value[kind]
    if "intValue" in value:
        return int(value["intValue"])
    if "arrayValue" in value:
        return [otlp_value(item) for item in value["arrayValue"].get("values", [])]
    return None


def otlp_attributes(attributes: list[dict]) -> dict:
    return {item["key"]: otlp_value(item["value"]) for item in attributes or []}


def normalize_outcome(exception_type: str | None, subtype: str | None) -> str | None:
    """Map Harbor's exception and the SDK's result subtype to D-019's outcomes.

    Agents without an SDK result, such as `oracle` and `nop`, get None. A
    relay HALT ends as a successful SDK result whose text names the HALT
    code; telling it apart from `completed` waits for a workflow adapter.
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


def load_trials(con: duckdb.DuckDBPyConnection, jobs_dir: Path) -> int:
    count = 0
    for result_file in sorted(jobs_dir.glob("*/*/result.json")):
        trial_dir = result_file.parent
        result = read_json(result_file)
        if "trial_name" not in result:
            continue
        agent = read_json(trial_dir / "agent" / "result.json")
        rewards = (result.get("verifier_result") or {}).get("rewards") or {}
        kwargs = result["config"]["agent"].get("kwargs") or {}
        patch = trial_dir / "verifier" / "changes.patch"
        exception = result.get("exception_info")
        exception_type = exception.get("exception_type") if exception else None
        job, trial = trial_dir.parent.name, trial_dir.name
        con.execute(
            f"INSERT INTO trials VALUES ({', '.join('?' * 21)})",
            [
                job, trial, result.get("task_name"),
                kwargs.get("config_label"),
                result["config"]["agent"].get("model_name"),
                (result.get("agent_info") or {}).get("version"),
                agent.get("session_id"),
                normalize_outcome(exception_type, agent.get("subtype")),
                agent.get("subtype"),
                # Results written before the runner's atr_ fields count only
                # the last segment's turns.
                agent.get("atr_num_turns", agent.get("num_turns")),
                agent.get("atr_wall_ms"),
                agent.get("duration_ms"), agent.get("duration_api_ms"),
                agent.get("total_cost_usd"),
                rewards.get("reward"), rewards.get("criteria_satisfied"),
                rewards.get("existing_tests_pass"),
                exception_type,
                patch.stat().st_size if patch.exists() else None,
                result.get("started_at"), result.get("finished_at"),
            ],
        )
        usage = agent.get("model_usage") or agent.get("modelUsage") or {}
        for model, u in usage.items():
            con.execute(
                "INSERT INTO model_usage VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    job, trial, model, u.get("inputTokens"), u.get("outputTokens"),
                    u.get("cacheReadInputTokens"), u.get("cacheCreationInputTokens"),
                    u.get("costUSD"),
                ],
            )
        count += 1
    return count


def load_events(con: duckdb.DuckDBPyConnection, telemetry_dir: Path) -> int:
    rows = []
    for path in sorted(telemetry_dir.glob("logs*.jsonl")):
        for line in path.open():
            for resource_logs in json.loads(line).get("resourceLogs", []):
                resource = otlp_attributes(resource_logs.get("resource", {}).get("attributes"))
                for scope_logs in resource_logs.get("scopeLogs", []):
                    for record in scope_logs.get("logRecords", []):
                        a = resource | otlp_attributes(record.get("attributes"))
                        rows.append(
                            [
                                a.get("atr.job"), a.get("atr.trial"), a.get("session.id"),
                                a.get("event.sequence"), a.get("event.name"),
                                a.get("event.timestamp"), a.get("prompt.id"),
                                a.get("model"), a.get("query_source"),
                                a.get("agent.name"), a.get("tool_name"),
                                a.get("input_tokens"), a.get("output_tokens"),
                                a.get("cache_read_tokens"), a.get("cache_creation_tokens"),
                                a.get("cost_usd"), a.get("duration_ms"), json.dumps(a),
                            ]
                        )
    if rows:
        con.executemany(f"INSERT INTO events VALUES ({', '.join('?' * 18)})", rows)
    return len(rows)


def load_metrics(con: duckdb.DuckDBPyConnection, telemetry_dir: Path) -> int:
    rows = []
    for path in sorted(telemetry_dir.glob("metrics*.jsonl")):
        for line in path.open():
            for resource_metrics in json.loads(line).get("resourceMetrics", []):
                resource = otlp_attributes(
                    resource_metrics.get("resource", {}).get("attributes")
                )
                for scope_metrics in resource_metrics.get("scopeMetrics", []):
                    for metric in scope_metrics.get("metrics", []):
                        data = metric.get("sum") or metric.get("gauge") or {}
                        for point in data.get("dataPoints", []):
                            a = resource | otlp_attributes(point.get("attributes"))
                            value = point.get("asDouble", point.get("asInt"))
                            rows.append(
                                [
                                    a.get("atr.job"), a.get("atr.trial"), metric["name"],
                                    a.get("type"), a.get("model"), a.get("query_source"),
                                    a.get("agent.name"),
                                    float(value) if value is not None else None,
                                    json.dumps(a),
                                ]
                            )
    if rows:
        con.executemany(f"INSERT INTO metric_points VALUES ({', '.join('?' * 9)})", rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_data = Path(os.environ.get("ATR_DATA_DIR", "~/atr/data")).expanduser()
    parser.add_argument("--data-dir", type=Path, default=default_data)
    parser.add_argument("--db", type=Path)
    args = parser.parse_args()
    db = args.db or args.data_dir / "atr.duckdb"

    db.unlink(missing_ok=True)
    con = duckdb.connect(str(db))
    con.execute(SCHEMA)
    trials = load_trials(con, args.data_dir / "jobs")
    events = load_events(con, args.data_dir / "telemetry")
    points = load_metrics(con, args.data_dir / "telemetry")
    print(f"{db}: {trials} trials, {events} events, {points} metric points")

    rows = con.execute(
        "SELECT job, trial, model, requests, status FROM reconciliation "
        "WHERE status <> 'no telemetry' ORDER BY job, trial, model"
    ).fetchall()
    for job, trial, model, requests, status in rows:
        print(f"  {job}/{trial} {model}: {requests} requests, {status}")
    con.close()


if __name__ == "__main__":
    main()
