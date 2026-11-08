"""Run one local Harbor job the same way every time, with its server and its power records.

Usage: python -m atr.local.launch <job config .json> [--model-id <id>] [--port 8090] [--dry-run]

The launcher refuses, before anything starts, while any other Harbor job runs
(the MVP keeps priority over the machine, D-058); unless the job is a local one
(an lc- name, every agent on route "local" with a local/<alias> model, every
task's agent behind an allowlist that does not name api.anthropic.com, D-050);
unless the alias maps to exactly one main-stage model of models.toml (or to the
--model-id given, which must have that alias); and when the job's folder already
exists, since no job is resumed or mixed. --dry-run stops after these checks.

Then it starts that model's server with a new key, samples the GPU's power every
second, and runs Harbor from its checkout with no ANTHROPIC_ variable in the
environment (the local route sends nothing to Anthropic's API, D-029), writing
Harbor's output to <jobs dir>/<job name>.launch.log. When Harbor ends it writes,
into every trial folder, server/ (the server's record, slots, metrics and log, as
`atr.local.serve record` does) plus server/power.csv (seconds from the sampler's
start, power in W, VRAM in MiB, GPU use in %) and server/power.json (the summary
and the wall-clock span), and launch.json into the job's folder (D-033). The
server is always stopped, also on failure or interruption. Nothing it writes may
hold the server key: the launcher scans its own outputs for it and exits
non-zero if it finds it. Exit status is Harbor's, or 1 when a record failed.
"""

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from atr.local import bench, config, serve

ANTHROPIC_HOST = "api.anthropic.com"
SRC = Path(__file__).resolve().parents[2]


def harbor_dir() -> Path:
    return Path(os.environ.get("ATR_HARBOR_DIR", "~/atr/tools/harbor")).expanduser()


def process_table() -> list[tuple[int, int, str]]:
    out = subprocess.run(["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True, check=True).stdout
    table = []
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            table.append((int(parts[0]), int(parts[1]), parts[2]))
    return table


def running_harbor_jobs() -> list[str]:
    """The `harbor run` processes that are not this launcher, its ancestors or its descendants."""
    table = process_table()
    parent = {pid: ppid for pid, ppid, _ in table}
    mine = {os.getpid()}
    pid = os.getpid()
    while pid in parent and parent[pid] not in mine and parent[pid] > 0:
        pid = parent[pid]
        mine.add(pid)
    # Descendants of this process only; an ancestor's other children are not ours.
    below = {os.getpid()}
    grew = True
    while grew:
        grew = False
        for child, ppid, _ in table:
            if ppid in below and child not in below:
                below.add(child)
                grew = True
    mine |= below
    found = []
    for pid, _, args in table:
        if pid in mine or "harbor run" not in args:
            continue
        words = args.split()
        config_path = next((words[i + 1] for i, w in enumerate(words[:-1]) if w in ("-c", "--config")), None)
        found.append(f"pid {pid} runs {config_path}" if config_path else f"pid {pid} runs `{args[:120]}`")
    return found


def load_job(path: Path) -> dict:
    try:
        job = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"{path}: the job config cannot be read: {error}")
    for key in ("job_name", "jobs_dir"):
        if not isinstance(job.get(key), str) or not job[key]:
            raise SystemExit(f"{path}: the job config has no {key}")
    return job


def check_local(job: dict) -> str:
    """Fail unless the job is a local one; return the alias of its model."""
    name = job["job_name"]
    if not name.startswith("lc-"):
        raise SystemExit(f"{name}: not a local job; its name must start with lc- (D-058)")
    agents, tasks = job.get("agents") or [], job.get("tasks") or []
    if not agents or not tasks:
        raise SystemExit(f"{name}: the job needs at least one agent and one task")
    aliases = set()
    for agent in agents:
        model = agent.get("model_name", "")
        if (agent.get("kwargs") or {}).get("route") != "local" or not model.startswith("local/"):
            raise SystemExit(f"{name}: agent {agent.get('name')} is not on route local with a local/<alias> model")
        aliases.add(model.removeprefix("local/"))
    if len(aliases) != 1:
        raise SystemExit(f"{name}: the agents name more than one model: {sorted(aliases)}")
    for task in tasks:
        task_toml = Path(task.get("path", "")) / "task.toml"
        try:
            agent_network = tomllib.loads(task_toml.read_text()).get("agent", {})
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise SystemExit(f"{task_toml}: the task cannot be read: {error}")
        if agent_network.get("network_mode") != "allowlist" or ANTHROPIC_HOST in agent_network.get("allowed_hosts", []):
            raise SystemExit(
                f"{task_toml}: the agent's network must be an allowlist without {ANTHROPIC_HOST}; "
                "build the task with --route local"
            )
    return aliases.pop()


def choose_model(alias: str, model_id: str | None) -> str:
    models = config.load()["models"]
    if model_id:
        if config.model({"models": models}, model_id)["alias"] != alias:
            raise SystemExit(f"{model_id} does not have the alias {alias}")
        return model_id
    mains = [i for i, entry in models.items() if entry["alias"] == alias and entry["stage"] == "main"]
    if len(mains) != 1:
        raise SystemExit(f"the alias {alias} maps to {len(mains)} main-stage models, not one; pass --model-id")
    return mains[0]


def trial_folders(job_dir: Path) -> list[Path]:
    if not job_dir.is_dir():
        return []
    return sorted(
        t for t in job_dir.iterdir()
        if t.is_dir() and ((t / "config.json").exists() or (t / "result.json").exists())
    )


def write_power(trial: Path, samples: list, start: float, summary: dict, span: dict, trials: int) -> None:
    folder = trial / "server"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "power.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["seconds", "power_w", "vram_mib", "gpu_use_pct"])
        for power, memory, use, at in samples:
            writer.writerow([round(at - start, 1), power, int(memory), use])
    record = {**summary, **span, "trials_sharing_samples": trials}
    (folder / "power.json").write_text(json.dumps(record, indent=2))


def run_job(job: dict, config_path: Path, model_id: str, port: int) -> int:
    jobs_dir = Path(job["jobs_dir"])
    job_dir = jobs_dir / job["job_name"]
    jobs_dir.mkdir(parents=True, exist_ok=True)
    log_path = jobs_dir / f"{job['job_name']}.launch.log"
    started = time.monotonic()
    failures: list[str] = []
    harbor_code = 1
    record: dict = {}
    key = ""
    sampler = None
    try:
        record = serve.start(model_id, port, None, [], 1200)
        key = (config.data_dir() / "server.key").read_text().strip()
        print(f"server up: {model_id}, key digest {hashlib.sha256(key.encode()).hexdigest()[:12]}")
        began_at = datetime.now(UTC).isoformat(timespec="seconds")
        start = time.monotonic()
        sampler = bench.GpuSampler()
        env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_")}
        env.update({"HARBOR_TELEMETRY": "off", "PYTHONPATH": str(SRC)})
        with log_path.open("w") as log:
            harbor = subprocess.Popen(
                ["uv", "run", "harbor", "run", "-c", str(config_path), "-y"],
                cwd=harbor_dir(), env=env, stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                harbor_code = harbor.wait()
            except BaseException:
                harbor.terminate()
                harbor.wait()
                raise
        ended_at = datetime.now(UTC).isoformat(timespec="seconds")
        summary = sampler.stop()
        samples = list(sampler.samples)
        sampler = None
        trials = trial_folders(job_dir)
        span = {"started_at": began_at, "ended_at": ended_at}
        for trial in trials:
            try:
                serve.snapshot(trial / "server")
                write_power(trial, samples, start, summary, span, len(trials))
            except (SystemExit, OSError) as error:
                failures.append(f"{trial.name}: {error}")
        job_dir.mkdir(parents=True, exist_ok=True)
        launch = {
            "model_id": model_id,
            "image": record.get("image"),
            "sha256": record.get("sha256"),
            "harbor_exit_code": harbor_code,
            "trials_recorded": len(trials) - len(failures),
            "trials": len(trials),
            "record_failures": failures,
            "wall_seconds": round(time.monotonic() - started, 1),
        }
        (job_dir / "launch.json").write_text(json.dumps(launch, indent=2))
        # Fail closed on the key: nothing the launcher wrote may hold it.
        written = [job_dir / "launch.json", log_path]
        for trial in trials:
            written += [p for p in (trial / "server").glob("*") if p.is_file()]
        leaked = [p.name for p in written if key in p.read_text(errors="replace")]
        if leaked:
            failures.append(f"the server key appears in {leaked}")
        print(f"harbor exit {harbor_code}; {len(trials)} trial(s); {len(failures)} record failure(s)")
    finally:
        if sampler is not None:
            sampler.stop()
        serve.stop()
    for failure in failures:
        print(f"record failure: {failure}", file=sys.stderr)
    return harbor_code if not failures else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("job_config", type=Path)
    parser.add_argument("--model-id", help="the pinned model (default: the alias's one main-stage model)")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--dry-run", action="store_true", help="run the checks and print what would run")
    args = parser.parse_args()

    job = load_job(args.job_config)
    others = running_harbor_jobs()
    if others:
        raise SystemExit(
            "another Harbor job is running; the MVP keeps priority (D-058): " + "; ".join(others)
        )
    alias = check_local(job)
    model_id = choose_model(alias, args.model_id)
    job_dir = Path(job["jobs_dir"]) / job["job_name"]
    if job_dir.exists():
        raise SystemExit(f"{job_dir} already exists; a job is never resumed or mixed")
    if args.dry_run:
        print(f"checks passed: would serve {model_id} on port {args.port} and run {job['job_name']} from {args.job_config}")
        return
    raise SystemExit(run_job(job, args.job_config.resolve(), model_id, args.port))


if __name__ == "__main__":
    main()
