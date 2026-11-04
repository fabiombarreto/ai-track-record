"""Measure the prompt and generation speeds of the running local server.

Usage: python -m atr.local.bench [--contexts 32768,65536,131072] [--predict 256]

For each prompt size, sends one completion with prompt caching off, so the whole
prompt is processed, and records llama.cpp's own timings, the GPU's power and
memory sampled every second, the server container's memory and the VM's
available memory. The prompt is random words from a fixed seed, nothing from any
target. Results go to $ATR_DATA_DIR/local-inference/bench/<model id>-<time>.json.
"""

import argparse
import json
import random
import string
import subprocess
import threading
import time
import urllib.request
from datetime import UTC, datetime

from atr.local import config
from atr.local.serve import container_memory


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
        self.samples: list[tuple[float, float, int]] = []
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
            self.samples.append((power, memory, int(use)))

    def stop(self) -> dict:
        self.process.terminate()
        self.process.wait()
        self.thread.join(timeout=5)
        if not self.samples:
            return {}
        powers = [s[0] for s in self.samples]
        return {
            "samples": len(self.samples),
            "power_mean_w": round(sum(powers) / len(powers), 1),
            "energy_wh": round(sum(powers) / 3600, 3),
            "vram_peak_mib": int(max(s[1] for s in self.samples)),
            "use_mean_pct": round(sum(s[2] for s in self.samples) / len(self.samples)),
        }


def measure(port: int, key: str, tokens: int, predict: int, ratio: float) -> dict:
    prompt = words(int(tokens / ratio))
    sampler = GpuSampler()
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
    for tokens in (int(t) for t in args.contexts.split(",")):
        if tokens + args.predict + 512 > server["context"]:
            tokens = server["context"] - args.predict - 512
        print(f"{server['model_id']}: prompt of about {tokens} tokens", flush=True)
        result = measure(port, key, tokens, args.predict, ratio)
        results.append(result)
        print(
            f"  prompt {result['prompt_tokens']} tokens at {result['prompt_per_second']}/s, "
            f"generation {result['generation_per_second']}/s, {result['wall_seconds']} s, "
            f"GPU {result['gpu'].get('power_mean_w')} W, VRAM peak {result['gpu'].get('vram_peak_mib')} MiB",
            flush=True,
        )

    out_dir = records / "bench"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = out_dir / f"{server['model_id']}-{stamp}.json"
    out.write_text(json.dumps({"server": server, "words_per_token": round(1 / ratio, 3),
                               "predict": args.predict, "results": results}, indent=2))
    print(f"written to {out}")


if __name__ == "__main__":
    main()
