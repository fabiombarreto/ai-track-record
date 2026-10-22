"""Harbor agent that runs Claude Code through the Claude Agent SDK.

AI Track Record pays for runs with API credits that cover the Agent SDK but
not the Claude Code CLI (D-049), so this agent replaces Harbor's built-in
Claude Code agent. It installs a pinned claude-agent-sdk in the task container
and runs claude_sdk_runner.py there.
"""

import json
import shlex
from pathlib import Path
from typing import override

from pydantic import Field

from harbor.agents.capabilities import AgentCapabilities
from harbor.agents.installed.base import BaseInstalledAgent, with_prompt_template
from harbor.agents.options import InstalledAgentOptions
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext, ModelUsage

DEFAULT_SDK_VERSION = "0.2.170"
UV_VERSION = "0.13.4"
VENV_DIR = "/opt/atr-sdk-venv"
RUNNER_PATH = "/installed-agent/claude_sdk_runner.py"
INSTRUCTION_PATH = "/installed-agent/instruction.txt"
LOGS_DIR = "/logs/agent"


class ClaudeAgentSdkOptions(InstalledAgentOptions):
    python_version: str = Field(
        default="3.12", description="Python version for the SDK venv."
    )
    max_turns: int | None = Field(default=None, description="Maximum agent turns.")
    max_budget_usd: float | None = Field(
        default=None, description="Soft cost cap for the run, in USD."
    )
    plugin_dir: str | None = Field(
        default=None, description="Plugin directory inside the container."
    )
    cwd: str | None = Field(
        default=None, description="Working directory for the agent."
    )
    prompt: str | None = Field(
        default=None,
        description="Prompt that replaces the task instruction, such as a workflow command.",
    )
    install_node: bool = Field(
        default=False, description="Install Node.js, for workflows whose scripts need it."
    )
    collect_worktrees: bool = Field(
        default=False,
        description="After the run, apply changes left in .worktrees/* to the main tree.",
    )


class ClaudeAgentSdk(BaseInstalledAgent):
    capabilities = AgentCapabilities()
    options_model = ClaudeAgentSdkOptions
    options: ClaudeAgentSdkOptions

    @staticmethod
    @override
    def name() -> str:
        return "atr-claude-agent-sdk"

    @override
    def get_version_command(self) -> str | None:
        return (
            f"{VENV_DIR}/bin/python -c 'import importlib.metadata as m; "
            "print(m.version(\"claude-agent-sdk\"))' 2>/dev/null"
        )

    @override
    def parse_version(self, stdout: str) -> str:
        return stdout.strip()

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        await self.ensure_system_dependencies(environment, ("curl", "coreutils", "git"))
        if self.options.install_node:
            # Harbor's package list has no Node.js, and task images are Debian based.
            await self.exec_as_root(
                environment,
                command=(
                    "command -v node >/dev/null 2>&1 || "
                    "(apt-get update && apt-get install -y --no-install-recommends nodejs "
                    "&& rm -rf /var/lib/apt/lists/*)"
                ),
            )
        installed = await environment.exec(
            command=f"{VENV_DIR}/bin/python -c 'import claude_agent_sdk' 2>/dev/null"
        )
        if installed.return_code != 0:
            sdk_version = self._version or DEFAULT_SDK_VERSION
            python_version = self.options.python_version
            await self.exec_as_root(
                environment,
                command=(
                    "set -euo pipefail; "
                    # Task images may forbid Python downloads for their own project.
                    "export UV_PYTHON_DOWNLOADS=automatic; "
                    f"curl -LsSf https://astral.sh/uv/{UV_VERSION}/install.sh "
                    "| env UV_UNMANAGED_INSTALL=/usr/local/bin sh && "
                    f"uv python install {python_version} && "
                    f"uv venv {VENV_DIR} --python {python_version} --clear && "
                    f"uv pip install --python {VENV_DIR}/bin/python "
                    f"claude-agent-sdk=={sdk_version}"
                ),
            )

        runner = Path(__file__).with_name("claude_sdk_runner.py")
        local_copy = self.logs_dir / runner.name
        local_copy.write_text(runner.read_text())
        await environment.upload_file(source_path=local_copy, target_path=RUNNER_PATH)

    def _model(self) -> str:
        if not self.model_name:
            raise ValueError("No model specified; pass one with -m")
        return self.model_name.removeprefix("anthropic/")

    @with_prompt_template
    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext
    ) -> None:
        instruction_file = self.logs_dir / "instruction.txt"
        instruction_file.write_text(self.options.prompt or instruction)
        await self._upload_agent_owned_file(
            environment, instruction_file, INSTRUCTION_PATH
        )

        api_key = self._get_env("ANTHROPIC_API_KEY")
        if api_key is None:
            raise ValueError("ANTHROPIC_API_KEY must be set")
        model = self._model()
        env = {
            "ANTHROPIC_API_KEY": api_key,
            "ANTHROPIC_MODEL": model,
            "CLAUDE_CODE_SUBAGENT_MODEL": model,
            "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
            "DISABLE_AUTOUPDATER": "1",
            "DISABLE_ERROR_REPORTING": "1",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
            # Lets bypassPermissions run as root inside the container.
            "IS_SANDBOX": "1",
            # Keeps the session transcripts in the synced logs folder.
            "CLAUDE_CONFIG_DIR": f"{LOGS_DIR}/claude-config",
        }

        args = [
            f"{VENV_DIR}/bin/python",
            RUNNER_PATH,
            "--instruction-file",
            INSTRUCTION_PATH,
            "--model",
            model,
            "--output-dir",
            LOGS_DIR,
        ]
        if self.options.max_turns is not None:
            args += ["--max-turns", str(self.options.max_turns)]
        if self.options.max_budget_usd is not None:
            args += ["--max-budget-usd", str(self.options.max_budget_usd)]
        if self.options.plugin_dir:
            args += ["--plugin-dir", self.options.plugin_dir]
        if self.options.cwd:
            args += ["--cwd", self.options.cwd]
        if self.options.collect_worktrees:
            args += ["--collect-worktrees"]

        command = (
            " ".join(shlex.quote(arg) for arg in args)
            + f" 2>&1 | stdbuf -oL tee {LOGS_DIR}/runner.txt"
        )
        await self.exec_as_agent(environment, command=command, env=env)

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
        result_file = self.logs_dir / "result.json"
        if not result_file.exists():
            self.logger.warning(f"No result file at {result_file}")
            return
        try:
            result = json.loads(result_file.read_text())
        except (OSError, json.JSONDecodeError) as error:
            self.logger.error(f"Failed to read {result_file}: {error}")
            return

        context.cost_usd = result.get("total_cost_usd")
        usage_by_model = result.get("model_usage") or result.get("modelUsage") or {}
        per_model: dict[str, ModelUsage] = {}
        for model, usage in usage_by_model.items():
            cache_read = usage.get("cacheReadInputTokens") or 0
            cache_write = usage.get("cacheCreationInputTokens") or 0
            per_model[model] = ModelUsage(
                n_input_tokens=(usage.get("inputTokens") or 0) + cache_read + cache_write,
                n_cache_tokens=cache_read,
                n_output_tokens=usage.get("outputTokens") or 0,
                cost_usd=usage.get("costUSD"),
            )
        if per_model:
            context.model_usage = per_model
            context.n_input_tokens = sum(u.n_input_tokens for u in per_model.values())
            context.n_cache_tokens = sum(u.n_cache_tokens for u in per_model.values())
            context.n_output_tokens = sum(u.n_output_tokens for u in per_model.values())
