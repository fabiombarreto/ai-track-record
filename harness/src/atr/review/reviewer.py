"""Run Claude Code's built-in code review on /review, inside the reviewer image.

The review runs as `/code-review <effort>` on the working-tree diff against
HEAD. A second turn in the same session asks for the findings it listed
through the ReportFindings tool, so they come back as data. Every SDK message
goes to /out/messages.jsonl and the findings to /out/findings.json.
"""

import argparse
import asyncio
import dataclasses
import json
import sys
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

FOLLOW_UP = (
    "Now report exactly the findings you listed above with the ReportFindings tool, in the "
    "same order. Do not review again and do not add or drop findings. If you listed none, "
    "call it with an empty list."
)


def to_json(value):
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        data = {f.name: to_json(getattr(value, f.name)) for f in dataclasses.fields(value)}
        data["_type"] = type(value).__name__
        return data
    if isinstance(value, dict):
        return {str(key): to_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


async def turn(prompt: str, options: ClaudeAgentOptions, out, results: list) -> str | None:
    session_id = None
    async for message in query(prompt=prompt, options=options):
        out.write(json.dumps(to_json(message)) + "\n")
        out.flush()
        if isinstance(message, ResultMessage):
            session_id = message.session_id
            results.append(
                {
                    "subtype": message.subtype,
                    "total_cost_usd": message.total_cost_usd,
                    "num_turns": message.num_turns,
                    "duration_ms": message.duration_ms,
                }
            )
    return session_id


def reported_findings(messages_file: Path) -> list[dict] | None:
    """The findings of the last ReportFindings call, or None if there was none."""
    findings = None
    for line in messages_file.read_text().splitlines():
        message = json.loads(line)
        if message.get("_type") != "AssistantMessage":
            continue
        for block in message.get("content", []):
            if block.get("_type") == "ToolUseBlock" and block.get("name") == "ReportFindings":
                findings = block.get("input", {}).get("findings", [])
    return findings


async def main(args: argparse.Namespace) -> int:
    out_dir = Path("/out")
    base = {
        "model": args.model,
        "permission_mode": "bypassPermissions",
        "system_prompt": {"type": "preset", "preset": "claude_code"},
        "cwd": "/review",
        "disallowed_tools": ["WebSearch", "WebFetch"],
        "max_budget_usd": args.max_budget_usd,
    }
    results: list[dict] = []
    messages_file = out_dir / "messages.jsonl"
    with messages_file.open("w") as out:
        session_id = await turn(f"/code-review {args.effort}", ClaudeAgentOptions(**base), out, results)
        if session_id:
            await turn(FOLLOW_UP, ClaudeAgentOptions(**base, resume=session_id), out, results)
    findings = reported_findings(messages_file)
    (out_dir / "findings.json").write_text(
        json.dumps({"findings": findings, "turns": results}, indent=2)
    )
    print(f"[atr-review] findings={None if findings is None else len(findings)} turns={results}")
    return 0 if findings is not None else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", required=True)
    parser.add_argument("--max-budget-usd", type=float, default=4.0)
    sys.exit(asyncio.run(main(parser.parse_args())))
