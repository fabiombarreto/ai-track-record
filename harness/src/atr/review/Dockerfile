# Pinned independent reviewer (D-018): Claude Code through the Agent SDK, which
# bundles it, so the SDK version fixes the reviewer's version.
FROM python:3.12-slim

ARG SDK_VERSION
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && uv pip install --system "claude-agent-sdk==${SDK_VERSION}"
COPY reviewer.py /opt/atr/reviewer.py
