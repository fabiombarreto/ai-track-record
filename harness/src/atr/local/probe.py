"""Check L1 of the local models plan: a request shaped like Claude Code's, against the running server.

Usage: python -m atr.local.probe [--max-tokens 4096] [--timeout 1800]

Sends one streamed Messages API request with thinking, two system blocks, a tool
set, a tool call and its result, and cache markers, then reads the server's
/slots and its log. The check passes when the answer is a complete event stream
without an error event, /slots shows the sampling applied, and a random marker
placed in the prompt is absent from the log. The request is synthetic: nothing
from any target.

The tool set is infra/local-inference/claude-code-tools.json, a fixture with the
names and input schemas of Claude Code's built-in tools and descriptions of our
own. It approximates what Claude Code sends; checks L2 and L3 use the real
requests. The result goes to $ATR_DATA_DIR/local-inference/checks/l1-<model id>-<time>.json,
without the key and without the response text (block types and lengths only).
The exit status is non-zero when the check fails.
"""

import argparse
import copy
import json
import secrets
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from atr.local import config
from atr.local.serve import CONTAINER

TOOLS = Path(__file__).resolve().parents[4] / "infra" / "local-inference" / "claude-code-tools.json"
EPHEMERAL = {"type": "ephemeral"}


def build_request(alias: str, marker: str, max_tokens: int) -> dict:
    tools = json.loads(TOOLS.read_text())
    tools[-1] = {**tools[-1], "cache_control": EPHEMERAL}
    return {
        "model": alias,
        "max_tokens": max_tokens,
        "stream": True,
        "thinking": {"type": "enabled", "budget_tokens": 1024},
        "system": [
            {"type": "text", "text": "You are a coding agent working in a synthetic repository."},
            {"type": "text", "text": f"Session note {marker}. Answer briefly.", "cache_control": EPHEMERAL},
        ],
        "tools": tools,
        "messages": [
            {"role": "user", "content": f"List the files here. Reference {marker}."},
            {"role": "assistant", "content": [
                {"type": "text", "text": "I will list the directory."},
                {"type": "tool_use", "id": "toolu_probe_1", "name": "Bash", "input": {"command": "ls"}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "toolu_probe_1",
                 "content": f"README.md\nmain.py\nutils.py\nnotes-{marker}.txt"},
                {"type": "text", "text": "Summarize what you see in one sentence.",
                 "cache_control": EPHEMERAL},
            ]},
        ],
    }


def stream(port: int, key: str, body: dict, timeout: int) -> dict:
    """POST the request and read the server-sent events line by line."""
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/messages",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    result = {"http_status": None, "events": {}, "blocks": [], "stop_reason": None,
              "usage": None, "errors": []}
    lengths: dict[int, int] = {}
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        result["http_status"] = error.code
        result["errors"].append(error.read().decode(errors="replace")[:500])
        return result
    with response:
        result["http_status"] = response.status
        for raw in response:
            line = raw.decode(errors="replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:])
            except json.JSONDecodeError:
                result["errors"].append("unparseable event")
                continue
            kind = event.get("type", "?")
            result["events"][kind] = result["events"].get(kind, 0) + 1
            if kind == "content_block_start":
                result["blocks"].append({"type": event["content_block"].get("type"), "length": 0})
                lengths[event.get("index", len(result["blocks"]) - 1)] = len(result["blocks"]) - 1
            elif kind == "content_block_delta":
                delta = event.get("delta", {})
                text = delta.get("text") or delta.get("thinking") or delta.get("partial_json") or ""
                index = lengths.get(event.get("index"))
                if index is not None:
                    result["blocks"][index]["length"] += len(text)
            elif kind == "message_delta":
                result["stop_reason"] = event.get("delta", {}).get("stop_reason") or result["stop_reason"]
                result["usage"] = event.get("usage") or result["usage"]
            elif kind == "message_start" and result["usage"] is None:
                result["usage"] = event.get("message", {}).get("usage")
            elif kind == "error":
                result["errors"].append(json.dumps(event.get("error", event))[:500])
    return result


def slots(port: int, key: str) -> list[dict]:
    """Each slot's sampling and token counts; the prompt and generated text are dropped."""
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/slots", headers={"Authorization": f"Bearer {key}"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    kept = []
    for slot in data if isinstance(data, list) else []:
        slot = copy.deepcopy(slot)
        slot.pop("prompt", None)
        slot.pop("generated", None)
        kept.append(slot)
    return kept


def evaluate(stream_result: dict, sampling: list[dict], marker_in_log: bool) -> list[str]:
    """The reasons check L1 fails; empty when it passes."""
    reasons = []
    events = stream_result["events"]
    if stream_result["http_status"] != 200:
        reasons.append(f"HTTP status {stream_result['http_status']}")
    for needed in ("message_start", "content_block_start", "content_block_stop", "message_delta", "message_stop"):
        if not events.get(needed):
            reasons.append(f"no {needed} event")
    if stream_result["stop_reason"] not in ("end_turn", "tool_use"):
        reasons.append(f"stop_reason {stream_result['stop_reason']!r}")
    if stream_result["errors"] or events.get("error"):
        reasons.append(f"error: {stream_result['errors']}")
    if not any(slot.get("params") for slot in sampling):
        reasons.append("/slots shows no params")
    if marker_in_log:
        reasons.append("the marker appears in the server log")
    return reasons


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout", type=int, default=1800, help="seconds to wait for the response")
    args = parser.parse_args()

    records = config.data_dir()
    try:
        server = json.loads((records / "server.json").read_text())
        key = (records / "server.key").read_text().strip()
    except OSError:
        raise SystemExit("no server is running (server.json or server.key is missing)")
    port = server["port"]

    marker = secrets.token_hex(8)
    body = build_request(server["alias"], marker, args.max_tokens)
    try:
        answer = stream(port, key, body, args.timeout)
        sampling = slots(port, key)
    except (urllib.error.URLError, ConnectionError, TimeoutError) as error:
        raise SystemExit(f"the server did not answer: {error}")
    logs = subprocess.run(["docker", "logs", CONTAINER], capture_output=True, text=True)
    marker_in_log = marker in logs.stdout or marker in logs.stderr

    reasons = evaluate(answer, sampling, marker_in_log)
    result = {
        "check": "L1",
        "model_id": server["model_id"],
        "image": server["image"],
        "build": server["build"],
        "args": server["args"],
        "tools": len(body["tools"]),
        "http_status": answer["http_status"],
        "events": answer["events"],
        "blocks": answer["blocks"],
        "stop_reason": answer["stop_reason"],
        "usage": answer["usage"],
        "errors": answer["errors"],
        "sampling": sampling,
        "marker_in_log": marker_in_log,
        "passed": not reasons,
        "reasons": reasons,
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    serialized = json.dumps(result, indent=2)
    if key in serialized:
        raise SystemExit("the key appears in the check result; nothing was written")
    out_dir = records / "checks"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = out_dir / f"l1-{server['model_id']}-{stamp}.json"
    out.write_text(serialized)
    print(f"check L1 {'passed' if not reasons else 'FAILED'}: stop_reason {answer['stop_reason']}, "
          f"blocks {[b['type'] for b in answer['blocks']]}; written to {out}")
    if reasons:
        raise SystemExit("; ".join(reasons))


if __name__ == "__main__":
    main()
