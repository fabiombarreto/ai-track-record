# AI Track Record

Local-first benchmark for AI coding agents: it runs the same specification-to-pull-request task under different models and workflows, grades every run with checks the agent never sees, and publishes cost, time and quality. This repository holds the harness (`atr`), its infrastructure configuration and the planning documentation; runs and private targets live in `~/atr` in WSL.

`documentation/` is the source of truth for the product, plans and decisions (D-011). Everything is written in English (D-010). The repository is public: never write private-target material, secrets or personal data into it.

## Stack

- Python 3.12, uv, hatchling; DuckDB 2.0.0
- Harbor 0.24.0 (local checkout in `~/atr/tools/harbor`)
- Claude Code through the Claude Agent SDK 0.2.170, in task containers
- Docker Desktop on WSL 2; OpenTelemetry Collector 0.162.0
- llama.cpp server b12063 for local models (in preparation)

## Commands

Run in WSL: `wsl.exe -d Ubuntu --exec bash -lc '<command>'` (never start the string with `/`).

- `cd harness && uv sync`
- `make test-pytest` from Windows, or `cd harness && uv run pytest` in WSL — the harness tests
- `uv run python -m atr.store.load` — rebuild the store from `~/atr/data`
- `uv run python -m atr.ops.budget` — spend against the US$ 800 ceiling
- `docker compose -f infra/otel-collector/docker-compose.yaml up -d` — Collector
- From `~/atr/tools/harbor`: `HARBOR_TELEMETRY=off PYTHONPATH=<repo>/harness/src uv run harbor run -c <job>.json -y`
- `cd dashboard && npm ci && ATR_EXPORT_DIR=<export dir> npm run build` — the site, in WSL with Node 24.22.2
- Full list: docs/development.md

## Key patterns

1. Run folders are the system of record; the DuckDB store is rebuilt from them (D-033).
2. Graders sit outside the workflow: hidden oracle, existing tests, static analysis, a pinned independent review (D-015, D-018).
3. Pin everything and fail instead of silently dropping an option (D-020).

Index: docs/KNOWLEDGE_BASE.md

## Context & Domain

Before implementing anything, read:
- docs/context/architecture.md — stack and patterns
- docs/context/conventions.md — naming and code standards
- docs/context/constraints.md — what NOT to do
- docs/context/methodology.md — methodology declaration (TDD opt-in)
- docs/context/testing.md — mandatory test guardrail (see section below)
- docs/domain/areas/[relevant-area].md — business rules for the area being changed
- docs/decision-gate.md — mandatory gate before planning or coding

Domain areas:
runs
grading
review
store-and-publication
budget
local-inference

## Test Guardrail (mandatory — every change)

Applies to EVERY code change, including small or single-file ones, and
whether or not a relay command was used. Do NOT skip this silently. It is
NOT waived by the Decision Gate scope exemptions.

- Before finishing, check which test suites cover the code you changed
  (see docs/context/testing.md) and state whether tests exist.
- If your change alters tested behavior, UPDATE those tests to match —
  never leave them stale, never delete/skip/weaken them to force a pass.
- Run the suites covering your change; treat all tiers equally and at a
  minimum run the e2e suite.
- If you CANNOT run them for any reason, do not stay silent: at the end of
  your response warn the user, say exactly why, and give copy-pasteable
  manual run instructions. Full protocol: docs/context/testing.md
