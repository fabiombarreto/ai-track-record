"""Start and stop llama.cpp's server with one pinned model of the local models plan.

Usage: python -m atr.local.serve start <model id> [--port 8090] [--context N] [--arg FLAG]...
       python -m atr.local.serve stop
       python -m atr.local.serve list

The server runs in Docker as the container atr-llm, with the GPU, the weights
folder mounted read-only and its port published on the host's loopback only.
Task containers reach it at host.docker.internal:<port>, as they reach the
Collector. Each start makes a new API key, written to server.key in
$ATR_DATA_DIR/local-inference, and records what it started, without the key,
in server.json next to it. A start fails unless the weights are verified and
the server refuses requests that lack the key.
"""

import argparse
import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime

from atr.local import config

CONTAINER = "atr-llm"


def status(port: int, path: str, key: str | None = None, body: dict | None = None) -> int:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if key:
        request.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        return 0


def gpu_memory_used() -> int | None:
    """MiB of VRAM in use, by every process."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            check=True, capture_output=True, text=True,
        ).stdout
        return int(out.split()[0])
    except (OSError, subprocess.CalledProcessError, ValueError, IndexError):
        return None


def container_memory() -> str | None:
    out = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", CONTAINER],
        capture_output=True, text=True,
    )
    return out.stdout.strip() or None


def running() -> bool:
    out = subprocess.run(
        ["docker", "ps", "--quiet", "--filter", f"name=^{CONTAINER}$"], capture_output=True, text=True
    )
    return bool(out.stdout.strip())


def stop() -> None:
    subprocess.run(["docker", "rm", "--force", CONTAINER], capture_output=True)
    (config.data_dir() / "server.key").unlink(missing_ok=True)


def start(model_id: str, port: int, context: int | None, extra: list[str], timeout: int) -> dict:
    settings = config.load()
    server, entry = settings["server"], config.model(settings, model_id)
    weights_dir = config.models_dir()
    if not config.verified(entry, weights_dir):
        raise SystemExit(f"{model_id}: {entry['file']} is not verified in {weights_dir}; run atr.local.fetch")
    stop()

    context = context or entry["context"]
    args = [
        "--model", f"/models/{entry['file']}",
        "--host", "0.0.0.0",
        "--port", "8080",
        "--alias", entry["alias"],
        "--ctx-size", str(context),
        *server["args"],
        *entry["args"],
        *extra,
    ]
    key = secrets.token_urlsafe(32)
    vram_before = gpu_memory_used()
    started = time.monotonic()
    subprocess.run(
        ["docker", "run", "--detach", "--name", CONTAINER, "--gpus", "all",
         "--publish", f"127.0.0.1:{port}:8080",
         "--volume", f"{weights_dir}:/models:ro",
         "--env", server["api_key_env"],
         server["image"], *args],
        check=True, env={**os.environ, server["api_key_env"]: key}, stdout=subprocess.DEVNULL,
    )

    while status(port, "/health") != 200:
        if not running():
            logs = subprocess.run(["docker", "logs", "--tail", "40", CONTAINER], capture_output=True, text=True)
            stop()
            raise SystemExit(f"the server stopped while loading:\n{logs.stdout}{logs.stderr}")
        if time.monotonic() - started > timeout:
            stop()
            raise SystemExit(f"the server was not ready after {timeout} s")
        time.sleep(2)
    load_seconds = round(time.monotonic() - started, 1)

    # The endpoint Claude Code calls to count tokens; listing models may not need a key.
    probe = {"model": entry["alias"], "messages": [{"role": "user", "content": "ping"}]}
    without_key = status(port, "/v1/messages/count_tokens", body=probe)
    with_key = status(port, "/v1/messages/count_tokens", key, probe)
    if without_key != 401 or with_key != 200:
        stop()
        raise SystemExit(f"key check failed: {without_key} without the key, {with_key} with it")

    record = {
        "model_id": model_id,
        **{field: entry[field] for field in ("alias", "role", "repo", "revision", "file", "size", "sha256")},
        "image": server["image"],
        "build": server["build"],
        "commit": server["commit"],
        "context": context,
        "args": args,
        "port": port,
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "load_seconds": load_seconds,
        "vram_used_mib": {"before": vram_before, "loaded": gpu_memory_used()},
        "container_memory": container_memory(),
    }
    records = config.data_dir()
    records.mkdir(parents=True, exist_ok=True)
    key_file = records / "server.key"
    key_file.write_text(key)
    key_file.chmod(0o600)
    (records / "server.json").write_text(json.dumps(record, indent=2))
    return record


def listing() -> None:
    settings = config.load()
    weights_dir = config.models_dir()
    for model_id, entry in settings["models"].items():
        state = "verified" if config.verified(entry, weights_dir) else "missing"
        print(f"{model_id:30} {entry['role']:8} {entry['stage']:10} {entry['size'] / 1e9:6.2f} GB  {state}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    begin = commands.add_parser("start", help="start the server with one model")
    begin.add_argument("model_id")
    begin.add_argument("--port", type=int, default=8090)
    begin.add_argument("--context", type=int, help="context size (default: the model's)")
    begin.add_argument("--arg", action="append", default=[], dest="extra",
                       help="an extra server flag or value, repeatable, e.g. --arg=--n-cpu-moe --arg=30")
    begin.add_argument("--timeout", type=int, default=1200, help="seconds to wait for the model to load")
    commands.add_parser("stop", help="stop the server")
    commands.add_parser("list", help="list the models and whether their weights are verified")
    args = parser.parse_args()

    if args.command == "start":
        print(json.dumps(start(args.model_id, args.port, args.context, args.extra, args.timeout), indent=2))
    elif args.command == "stop":
        stop()
    else:
        listing()


if __name__ == "__main__":
    main()
