# Agent environment: the task's base commit as a repository with a single
# commit, tagged "base", and the locked dependencies in /opt/venv.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /usr/local/bin/

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app/pyproject.toml app/uv.lock ./
RUN uv sync --frozen --no-install-project
COPY app/ ./
RUN git init -q -b main \
    && git add -A \
    && git -c user.name=atr -c user.email=atr@localhost commit -q -m "Base commit" \
    && git tag base
