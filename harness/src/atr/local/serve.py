"""Start and stop llama.cpp's server with one pinned model of the local models plan.

Usage: python -m atr.local.serve start <model id> [--port 8090] [--context N] [--arg FLAG]...
       python -m atr.local.serve stop
       python -m atr.local.serve record <folder>
       python -m atr.local.serve list

The server runs in Docker as the container atr-llm, with the GPU, the weights
folder mounted read-only and its port published on the host's loopback only.
Task containers reach it at host.docker.internal:<port>, as they reach the
Collector. Each start makes a new API key, written to server.key in
$ATR_DATA_DIR/local-inference, and records what it started, without the key,
in server.json next to it. A start fails unless the weights are verified and
the server refuses requests that lack the key (count_tokens, /slots and
/metrics), Docker publishes the port on 127.0.0.1 only and the key is absent
from the record. A start also fails, before any container starts, unless
--offline is among the flags and no download flag is.
A model's chat-template override lives in infra/local-inference/templates, mounted
read-only at /templates; the start refuses a template whose SHA-256 differs from the
model entry's chat_template_sha256, and server.json records that digest.

`record <folder>` copies the running server's state into a folder the launcher
names: server.json, slots.json (every slot's prompt and generated text removed,
since /slots returns them), metrics.prom and server.log. Nothing is written if
the key would appear in any of them.
"""

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from atr.local import config

CONTAINER = "atr-llm"
TEMPLATES_MOUNT = "/templates"
DOWNLOAD_FLAGS = {
    "-hf", "--hf-repo", "-hfr", "--hf-file", "-hff", "-hft", "--hf-token",
    "-mu", "--model-url", "-dr", "--docker-repo",
}


def templates_folder() -> Path:
    """The pinned chat-template overrides, in the repository's infra folder."""
    return Path(__file__).resolve().parents[4] / "infra" / "local-inference" / "templates"


def check_args(args: list[str], entry: dict | None = None, templates_dir: Path | None = None) -> None:
    """Fail unless the server is offline: --offline present and no download flag.

    A --chat-template-file must name a file under /templates/ whose SHA-256 equals the
    model entry's chat_template_sha256 (the pinned override), else the start is refused.
    """
    if "--offline" not in args:
        raise SystemExit("the server flags lack --offline; a start that could reach the network is refused")
    found = sorted({a.split("=", 1)[0] for a in args} & DOWNLOAD_FLAGS)
    if found:
        raise SystemExit(f"download flags are refused: {found}")
    for index, arg in enumerate(args):
        if arg.split("=", 1)[0] != "--chat-template-file":
            continue
        value = arg.split("=", 1)[1] if "=" in arg else (args[index + 1] if index + 1 < len(args) else "")
        if not value.startswith(TEMPLATES_MOUNT + "/"):
            raise SystemExit(f"--chat-template-file must name a file under {TEMPLATES_MOUNT}/: {value}")
        pinned = (entry or {}).get("chat_template_sha256")
        path = (templates_dir or templates_folder()) / value.removeprefix(TEMPLATES_MOUNT + "/")
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise SystemExit(f"the chat template {value} cannot be read: {error}")
        if not pinned or digest != pinned:
            raise SystemExit(
                f"the chat template {path.name} has digest {digest}, not the pinned {pinned}; start refused"
            )


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


def inspect() -> dict:
    out = subprocess.run(["docker", "inspect", CONTAINER], capture_output=True, text=True)
    try:
        return json.loads(out.stdout)[0]
    except (json.JSONDecodeError, IndexError):
        return {}


def machine() -> dict:
    """The GPU, the VM's memory and its processors, for the record."""
    gpu = None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            check=True, capture_output=True, text=True,
        ).stdout.splitlines()[0]
        name, total = (part.strip() for part in out.rsplit(",", 1))
        gpu = {"name": name, "vram_total_mib": int(total)}
    except (OSError, subprocess.CalledProcessError, ValueError, IndexError):
        pass
    memory = None
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemTotal:"):
                memory = int(line.split()[1]) // 1024
    return {"gpu": gpu, "vm_memory_total_mib": memory, "processors": os.cpu_count()}


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
    check_args(args, entry)
    key = secrets.token_urlsafe(32)
    vram_before = gpu_memory_used()
    started = time.monotonic()
    subprocess.run(
        ["docker", "run", "--detach", "--name", CONTAINER, "--gpus", "all",
         "--publish", f"127.0.0.1:{port}:8080",
         "--volume", f"{weights_dir}:/models:ro",
         "--volume", f"{templates_folder()}:{TEMPLATES_MOUNT}:ro",
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
    for path in ("/slots", "/metrics"):
        without_key, with_key = status(port, path), status(port, path, key)
        if without_key != 401 or with_key != 200:
            stop()
            raise SystemExit(f"key check failed on {path}: {without_key} without the key, {with_key} with it")

    # Fail closed unless Docker published the port on the loopback only.
    details = inspect()
    bindings = (details.get("NetworkSettings", {}).get("Ports") or {}).get("8080/tcp") or []
    published = [f"{b.get('HostIp')}:{b.get('HostPort')}" for b in bindings]
    if not bindings or any(b.get("HostIp") != "127.0.0.1" for b in bindings):
        stop()
        raise SystemExit(f"the port is not published on 127.0.0.1 only: {published}")

    record = {
        "model_id": model_id,
        **{field: entry[field] for field in ("alias", "role", "repo", "revision", "file", "size", "sha256")},
        "image": server["image"],
        "image_id": details.get("Image"),
        "build": server["build"],
        "commit": server["commit"],
        "context": context,
        "args": args,
        "chat_template_sha256": entry.get("chat_template_sha256"),
        "offline": True,
        "key_checked": ["/v1/messages/count_tokens", "/slots", "/metrics"],
        "port": port,
        "published": published,
        "machine": machine(),
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "load_seconds": load_seconds,
        "vram_used_mib": {"before": vram_before, "loaded": gpu_memory_used()},
        "container_memory": container_memory(),
    }
    serialized = json.dumps(record, indent=2)
    if key in serialized:
        stop()
        raise SystemExit("the key appears in the server record; nothing was written")
    records = config.data_dir()
    records.mkdir(parents=True, exist_ok=True)
    key_file = records / "server.key"
    key_file.write_text(key)
    key_file.chmod(0o600)
    (records / "server.json").write_text(serialized)
    return record


def get(port: int, path: str, key: str) -> str:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", headers={"Authorization": f"Bearer {key}"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode()


def snapshot(dest: Path) -> list[Path]:
    """Copy the running server's state into dest, without the key and without prompt text."""
    records = config.data_dir()
    try:
        server_text = (records / "server.json").read_text()
        key = (records / "server.key").read_text().strip()
    except OSError:
        raise SystemExit("no server is running (server.json or server.key is missing)")
    if not running():
        raise SystemExit(f"no server is running (container {CONTAINER} is not up)")
    port = json.loads(server_text)["port"]
    try:
        slots = json.loads(get(port, "/slots", key))
        metrics = get(port, "/metrics", key)
    except (urllib.error.URLError, ConnectionError, TimeoutError, json.JSONDecodeError) as error:
        raise SystemExit(f"the server did not answer: {error}")
    # /slots returns each slot's detokenized prompt and generated text; drop them.
    for slot in slots if isinstance(slots, list) else []:
        slot.pop("prompt", None)
        slot.pop("generated", None)
    logs = subprocess.run(
        ["docker", "logs", "--timestamps", CONTAINER], capture_output=True, text=True
    )
    files = {
        "server.json": server_text,
        "slots.json": json.dumps(slots, indent=2),
        "metrics.prom": metrics,
        "server.log": logs.stdout + logs.stderr,
    }
    if any(key in text for text in files.values()):
        raise SystemExit("the key appears in the server's state; nothing was written")
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in files.items():
        (dest / name).write_text(text)
        written.append(dest / name)
    return written


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
    keep = commands.add_parser("record", help="copy the running server's state into a folder")
    keep.add_argument("folder", type=Path)
    commands.add_parser("list", help="list the models and whether their weights are verified")
    args = parser.parse_args()

    if args.command == "start":
        print(json.dumps(start(args.model_id, args.port, args.context, args.extra, args.timeout), indent=2))
    elif args.command == "stop":
        stop()
    elif args.command == "record":
        for path in snapshot(args.folder):
            print(path)
    else:
        listing()


if __name__ == "__main__":
    main()
