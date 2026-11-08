"""Measure the prompt and generation speeds of the running local server.

Usage: python -m atr.local.bench [--contexts 32768,65536,131072] [--predict 256]

For each prompt size, sends one completion with prompt caching off, so the whole
prompt is processed, and records llama.cpp's own timings, the GPU's power and
memory sampled every second (energy integrates power over the sample times),
the server container's memory (peak while the request runs, and after it) and
the VM's available memory. The prompt is random words from a fixed seed, nothing
from any target. Results go to $ATR_DATA_DIR/local-inference/bench/<model id>-<time>.json,
rewritten after every prompt size; a size that fails is recorded with an error,
the others still run, and the exit status is non-zero.
"""

import argparse
import json
import random
import re
import string
import subprocess
import threading
import time
import urllib.request
from datetime import UTC, datetime

from atr.local import config
from atr.local.serve import CONTAINER, container_memory, gpu_memory_used


def call(port: int, key: str, path: str, body: dict, timeout: int) -> dict:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def words(count: int, seed: int = 0) -> str:
    rng = random.Random(seed)
    return " ".join(
        "".join(rng.choices(string.ascii_lowercase, k=rng.randint(2, 9))) for _ in range(count)
    )


def available_memory_mib() -> int:
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    return -1


class GpuSampler:
    """Samples the GPU's power, memory and use every second while it runs."""

    def __init__(self) -> None:
        self.samples: list[tuple[float, float, int, float]] = []
        self.process = subprocess.Popen(
            ["nvidia-smi", "--query-gpu=power.draw,memory.used,utilization.gpu",
             "--format=csv,noheader,nounits", "--loop-ms=1000"],
            stdout=subprocess.PIPE, text=True,
        )
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self) -> None:
        for line in self.process.stdout:
            try:
                power, memory, use = (float(v) for v in line.split(","))
            except ValueError:
                continue
            self.samples.append((power, memory, int(use), time.monotonic()))

    def stop(self) -> dict:
        self.process.terminate()
        self.process.wait()
        self.thread.join(timeout=5)
        if not self.samples:
            return {}
        powers = [s[0] for s in self.samples]
        # Power times the interval between consecutive samples; the first sample has no interval.
        joules = sum(
            self.samples[i][0] * (self.samples[i][3] - self.samples[i - 1][3])
            for i in range(1, len(self.samples))
        )
        return {
            "samples": len(self.samples),
            "power_mean_w": round(sum(powers) / len(powers), 1),
            "power_peak_w": round(max(powers), 1),
            "energy_wh": round(joules / 3600, 3),
            "vram_peak_mib": int(max(s[1] for s in self.samples)),
            "use_mean_pct": round(sum(s[2] for s in self.samples) / len(self.samples)),
        }


def mib(line: str) -> float:
    """The used memory of one docker stats line such as '1.5GiB / 24GiB', in MiB."""
    found = re.search(r"([\d.]+)\s*([KMGT]?i?B)\s*/", line)
    if not found:
        raise ValueError(line)
    units = {"B": 1 / 1048576, "KiB": 1 / 1024, "MiB": 1, "GiB": 1024, "TiB": 1024 * 1024}
    return float(found.group(1)) * units[found.group(2)]


class MemorySampler:
    """Tracks the peak memory of the server container while it runs."""

    def __init__(self) -> None:
        self.peak = 0.0
        self.process = subprocess.Popen(
            ["docker", "stats", CONTAINER, "--format", "{{.MemUsage}}"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self) -> None:
        for line in self.process.stdout:
            try:
                self.peak = max(self.peak, mib(line))
            except ValueError:
                continue

    def stop(self) -> int | None:
        self.process.terminate()
        self.process.wait()
        self.thread.join(timeout=5)
        return round(self.peak) if self.peak else None


def measure(port: int, key: str, tokens: int, predict: int, ratio: float) -> dict:
    # The words-per-token ratio of a short sample drifts on a long prompt: tokenize and rescale
    # until the prompt is within 0.5% of the target and never above it.
    count = int(tokens / ratio)
    for _ in range(4):
        prompt = words(count)
        actual = len(call(port, key, "/tokenize", {"content": prompt}, 600)["tokens"])
        if tokens * 0.995 <= actual <= tokens:
            break
        count = int(count * tokens / actual * 0.998)
    sampler = GpuSampler()
    memory_sampler = MemorySampler()
    memory_before = available_memory_mib()
    started = time.monotonic()
    result = call(
        port, key, "/completion",
        {"prompt": prompt, "n_predict": predict, "cache_prompt": False, "ignore_eos": True,
         "temperature": 0, "seed": 1},
        timeout=7200,
    )
    wall = round(time.monotonic() - started, 1)
    gpu = sampler.stop()
    memory_peak = memory_sampler.stop()
    timings = result.get("timings", {})
    return {
        "target_tokens": tokens,
        "prompt_tokens": timings.get("prompt_n"),
        "prompt_per_second": round(timings.get("prompt_per_second", 0), 1),
        "generated_tokens": timings.get("predicted_n"),
        "generation_per_second": round(timings.get("predicted_per_second", 0), 2),
        "wall_seconds": wall,
        "gpu": gpu,
        "container_memory": container_memory(),
        "container_memory_peak_mib": memory_peak,
        "vm_available_mib": {"before": memory_before, "after": available_memory_mib()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contexts", default="32768,65536,131072",
                        help="prompt sizes in tokens, comma-separated")
    parser.add_argument("--predict", type=int, default=256, help="tokens to generate after each prompt")
    args = parser.parse_args()

    records = config.data_dir()
    server = json.loads((records / "server.json").read_text())
    key = (records / "server.key").read_text().strip()
    port = server["port"]

    sample = words(2000, seed=1)
    ratio = len(call(port, key, "/tokenize", {"content": sample}, 60)["tokens"]) / 2000

    results = []
    failed = []
    out_dir = records / "bench"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = out_dir / f"{server['model_id']}-{stamp}.json"
    vram_at_start = gpu_memory_used()
    for tokens in (int(t) for t in args.contexts.split(",")):
        if tokens + args.predict + 512 > server["context"]:
            tokens = server["context"] - args.predict - 512
        print(f"{server['model_id']}: prompt of about {tokens} tokens", flush=True)
        try:
            result = measure(port, key, tokens, args.predict, ratio)
            print(
                f"  prompt {result['prompt_tokens']} tokens at {result['prompt_per_second']}/s, "
                f"generation {result['generation_per_second']}/s, {result['wall_seconds']} s, "
                f"GPU {result['gpu'].get('power_mean_w')} W, VRAM peak {result['gpu'].get('vram_peak_mib')} MiB",
                flush=True,
            )
        except (OSError, ValueError, KeyError) as error:
            result = {"target_tokens": tokens, "error": f"{type(error).__name__}: {error}"}
            failed.append(tokens)
            print(f"  failed: {result['error']}", flush=True)
        results.append(result)
        out.write_text(json.dumps({"server": server, "words_per_token": round(1 / ratio, 3),
                                   "predict": args.predict, "vram_used_at_start_mib": vram_at_start,
                                   "results": results}, indent=2))
    print(f"written to {out}")
    if failed:
        raise SystemExit(f"prompt sizes that failed: {failed}")


if __name__ == "__main__":
    main()
