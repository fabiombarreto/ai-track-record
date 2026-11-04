# Constraints

## Versions

- Python 3.12 or later (`harness/pyproject.toml`, D-047).
- Claude Agent SDK 0.2.170 for runs and reviews; the reviewer is Claude Code's `/code-review` on Sonnet 5.5 at high effort.
- Harbor 0.24.0.
- relay 0.49.0 (commit `cfe5e0b`) and 0.47.0 (commit `e1844b6`) for the MVP (D-054).
- llama.cpp server build b12063, CUDA 12.8, pinned by digest. Not a CUDA 13.2 build for Qwen3.6.

## The machine

- One Windows machine runs everything: RTX 3060 Ti with 8 GB of VRAM, Ryzen 5 5600G, 28 GB of RAM visible to Windows.
- The WSL 2 VM, shared with Docker Desktop, is capped at 18 GB of memory and 10 processors (`.wslconfig`).
- C: holds the WSL and Docker disks and has little free space. Large files, such as model weights, go to D: (`/mnt/d`).
- The machine cannot stay on overnight, so runs go in sessions of about four hours, and a run must fit in what is left of the session.
- Runs go one at a time. Time is one of the graders, and parallel runs would compete for the machine and the API.

## Experiment rules

- The MVP scope is frozen (D-024); new work goes to later phases or to experiments outside it, such as the local models plan (D-058).
- Pin everything, repeat at least three times, change one factor at a time, declare hypotheses before running, same limits for all (D-020).
- Tasks, specifications and oracles stay frozen during an experiment (D-014, D-053).
- Hitting a limit is a measured outcome, not a reason to exclude a run. Runs that end in `error` are infrastructure failures, retried and reported apart (D-019).
- MVP spend is capped at US$ 800 (D-028). `atr.ops.budget --next <usd>` stops a batch before a run whose cap could pass it.
- Every MVP run has a three-hour limit, a US$ 60 cost cap and web tools disabled.

## Privacy and network

- Target A's content may go only to Anthropic's API (D-029) and to local open-weight models (D-057).
- Target A runs use Harbor's network allowlist: the model API, the Collector and the package index; `WebSearch` and `WebFetch` are disabled (D-050).
- This repository is public. Nothing from a private target goes into it: no real product name, specification, code, data, prompt or transcript. Private targets appear under a codename only (D-013). This applies to `docs/` and `PRPs/` as well as `documentation/`.
- No secrets in the repository. They live in `~/atr/.env`.

## Known limitations in the code

- Runs before M3 keep a recorded shortfall in their telemetry metrics; it is recorded, not corrected.
- The SDK's USD cap is a client-side estimate. For a model Claude Code does not know, such as a local one, it has no price, so the time and turn limits are what bound a local run.
