"""Run one task through the Claude Agent SDK inside a Harbor task container.

Writes every SDK message to messages.jsonl and the final result message to
result.json, both in --output-dir. Fails instead of dropping any requested
option that the installed SDK version does not support.
"""

import argparse
import asyncio
import dataclasses
import json
import os
import subprocess
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


def trust_workspace(workspace: Path) -> None:
    """Mark the workspace as trusted, as an operator does once in the CLI.

    Without it, Claude Code ignores the project's permission rules.
    """
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if not config_dir:
        return
    config_file = Path(config_dir) / ".claude.json"
    config = json.loads(config_file.read_text()) if config_file.exists() else {}
    config.setdefault("projects", {}).setdefault(str(workspace), {})[
        "hasTrustDialogAccepted"
    ] = True
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(config, indent=2))


def collect_worktrees(repo: Path, output_dir: Path) -> None:
    """Apply changes left in git worktrees under .worktrees/ to the main tree.

    Workflows such as relay work in a worktree and leave it uncommitted. The
    grader reads the main tree's diff against the "base" tag, so the
    worktree's diff against the same tag is applied there. The outcome of
    each worktree is recorded in worktrees.json.
    """
    root = repo / ".worktrees"
    worktrees = sorted(p for p in root.glob("*") if (p / ".git").exists()) if root.exists() else []
    report = []
    for worktree in worktrees:
        subprocess.run(["git", "-C", str(worktree), "add", "-A"], check=True)
        diff = subprocess.run(
            ["git", "-C", str(worktree), "diff", "--cached", "--binary", "base"],
            check=True,
            capture_output=True,
        ).stdout
        applied = subprocess.run(
            ["git", "-C", str(repo), "apply", "--whitespace=nowarn", "-"],
            input=diff,
            capture_output=True,
        )
        report.append(
            {
                "worktree": str(worktree.relative_to(repo)),
                "patch_bytes": len(diff),
                "applied": applied.returncode == 0,
                "error": applied.stderr.decode()[-2000:],
            }
        )
    (output_dir / "worktrees.json").write_text(json.dumps(report, indent=2))
    print(f"[atr] worktrees collected: {report}")


async def run(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt = Path(args.instruction_file).read_text()
    workspace = Path(args.cwd or os.getcwd())
    trust_workspace(workspace)

    result = None
    with (output_dir / "messages.jsonl").open("w") as messages:
        async for message in query(prompt=prompt, options=build_options(args)):
            messages.write(json.dumps(to_json(message)) + "\n")
            messages.flush()
            if isinstance(message, ResultMessage):
                result = message

    if args.collect_worktrees:
        collect_worktrees(workspace, output_dir)

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
    parser.add_argument("--collect-worktrees", action="store_true")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
