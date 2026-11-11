# Conventions

## Language

Everything is written in English: code, comments, documentation, commit messages and the dashboard (D-010). The operator may chat in another language; artifacts stay in English.

## Modules and entry points

- One module per command, run as `python -m atr.<area>.<module>`, for example `python -m atr.store.load`.
- Each module starts with a docstring whose first line is a one-sentence summary, followed by a `Usage:` line and a few paragraphs on what it does and why. `argparse` uses the first docstring line as its description: `argparse.ArgumentParser(description=__doc__.splitlines()[0])`.
- A `main()` function parses arguments; the module ends with `if __name__ == "__main__": main()`.
- Areas are packages under `harness/src/atr/`: `agents`, `tasks`, `checks`, `review`, `store`, `ops`, `local`.

## Naming

| Kind | Style | Example |
|---|---|---|
| Modules and packages | `snake_case` | `skipped_steps.py`, `atr.store` |
| Functions and variables | `snake_case`, verbs for actions | `spend_by_job`, `project_resources` |
| Classes | `PascalCase` | `ClaudeAgentSdk`, `ClaudeAgentSdkOptions` |
| Module constants | `UPPER_SNAKE_CASE` | `CEILING_USD`, `SDK_VERSION`, `ALLOWLIST_VERSION` |
| Harbor jobs | `<prefix>-r<rep>-<config>-<target>-task-0<n>` | `m3-r1-vanilla-sonnet-ta-task-01` |
| Local models | `<model>-<quantization>` id, `<model>` alias | `qwen3.6-35b-a3b-ud-q3_k_xl` |

Job prefixes separate experiments: `m2-`, `m3-` for the MVP, `lc-` for local runs, `gm-` reserved for Gemini.

## Code style

- Type hints with built-in generics and `X | None`.
- Standard library first. The package depends only on `duckdb`; Harbor is imported from its own checkout. Scripts that run inside containers or on the host without the venv use the standard library only.
- `pathlib.Path` for paths; data locations come from environment variables with defaults: `ATR_DATA_DIR` (`~/atr/data`), `ATR_MODELS_DIR` (`/mnt/d/atr/models`).
- JSON records are written with `json.dumps(..., indent=2)`; logs from tools are JSON lines.
- Comments explain why, and cite decision IDs (`D-051`) and capability IDs (`GRD-04`, `PUB-01`) where a rule comes from.

## Error handling

- Operator-facing failures end with `raise SystemExit("<what failed and what to do>")`, never a bare traceback for an expected condition.
- `subprocess.run(..., check=True)` for commands that must succeed; `capture_output=True` when the output is parsed.
- Reading optional records is tolerant (a helper returns `{}` on a missing or broken file), but a check that guards correctness or privacy fails closed: the exporter blocks on any leak finding, the runner stops on an unsupported option, the server start stops when its key check fails.

## Pinning

Versions of everything that affects a result are constants or config values, never "latest": the SDK version, the reviewer's model and effort, relay commits, the Harbor checkout, image digests and model file digests (D-020).

## Commits

Conventional commits with a scope: `feat(harness): ...`, `fix(harness): ...`, `docs: ...`, `docs(phase-0): ...`. The body explains what changed and why. Commits made with Claude end with a `Co-Authored-By:` line.

## Tests

Unit tests for the harness live in `harness/tests/`, one `test_<module or concern>.py` file per subject, written with plain pytest functions and asserts, with no network, Docker or `~/atr` data. Changes that need Docker, Harbor or a model are verified with check runs on the public synthetic task, recorded in the research reports in `documentation/research/` (see docs/context/testing.md).
