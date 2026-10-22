# Separate verifier: a clean copy of the base commit in /pristine and the
# grading files in /grading. The agent's /app arrives as an artifact.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /usr/local/bin/

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /pristine
COPY pristine/pyproject.toml pristine/uv.lock ./
RUN uv sync --frozen --no-install-project
COPY pristine/ /pristine/
COPY grading/ /grading/
COPY --chmod=755 test.sh /tests/test.sh
