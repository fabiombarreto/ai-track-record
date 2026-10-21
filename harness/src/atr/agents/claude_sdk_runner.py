"""Run one task through the Claude Agent SDK inside a Harbor task container.

Writes every SDK message to messages.jsonl and the final result message to
result.json, both in --output-dir. Fails instead of dropping any requested
option that the installed SDK version does not support.
"""

import argparse
import asyncio
import dataclasses
import json
import sys
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query


def to_json(value):
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        data = {
            field.name: to_json(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
        data["_type"] = type(value).__name__
        return data
    if isinstance(value, dict):
        return {str(key): to_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def build_options(args: argparse.Namespace) -> ClaudeAgentOptions:
    requested = {
        "model": args.model,
        "permission_mode": "bypassPermissions",
        # The CLI uses Claude Code's system prompt and the project's settings
        # by default; the SDK has to be told.
        "system_prompt": {"type": "preset", "preset": "claude_code"},
        "setting_sources": ["project"],
        "cwd": args.cwd,
        "max_turns": args.max_turns,
        "max_budget_usd": args.max_budget_usd,
        "plugins": [{"type": "local", "path": args.plugin_dir}] if args.plugin_dir else None,
    }
    requested = {key: value for key, value in requested.items() if value is not None}
    supported = {field.name for field in dataclasses.fields(ClaudeAgentOptions)}
    unsupported = sorted(set(requested) - supported)
    if unsupported:
        raise SystemExit(f"[atr] this SDK version does not support: {', '.join(unsupported)}")
    return ClaudeAgentOptions(**requested)


async def run(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt = Path(args.instruction_file).read_text()

    result = None
    with (output_dir / "messages.jsonl").open("w") as messages:
        async for message in query(prompt=prompt, options=build_options(args)):
            messages.write(json.dumps(to_json(message)) + "\n")
            messages.flush()
            if isinstance(message, ResultMessage):
                result = message

    if result is None:
        print("[atr] the SDK finished without a result message", file=sys.stderr)
        return 2
    (output_dir / "result.json").write_text(json.dumps(to_json(result), indent=2))
    print(
        f"[atr] {getattr(result, 'subtype', '?')}: "
        f"turns={getattr(result, 'num_turns', '?')} "
        f"cost_usd={getattr(result, 'total_cost_usd', '?')}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instruction-file", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-turns", type=int)
    parser.add_argument("--max-budget-usd", type=float)
    parser.add_argument("--plugin-dir")
    parser.add_argument("--cwd")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
