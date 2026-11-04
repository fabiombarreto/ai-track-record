"""The pinned models and server of the local models plan.

They are listed in infra/local-inference/models.toml. Weights live in
$ATR_MODELS_DIR (default /mnt/d/atr/models, D: seen from WSL), and the server's
records in $ATR_DATA_DIR/local-inference (default ~/atr/data/local-inference).
"""

import os
import tomllib
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[4] / "infra" / "local-inference" / "models.toml"


def load() -> dict:
    with CONFIG.open("rb") as f:
        return tomllib.load(f)


def model(config: dict, model_id: str) -> dict:
    try:
        return config["models"][model_id]
    except KeyError:
        known = ", ".join(config["models"])
        raise SystemExit(f"unknown model {model_id!r}; known: {known}") from None


def models_dir() -> Path:
    return Path(os.environ.get("ATR_MODELS_DIR", "/mnt/d/atr/models")).expanduser()


def data_dir() -> Path:
    return Path(os.environ.get("ATR_DATA_DIR", "~/atr/data")).expanduser() / "local-inference"


def marker(weights: Path) -> Path:
    """The file that records a verified digest next to the weights."""
    return weights.with_name(weights.name + ".sha256")


def verified(entry: dict, directory: Path) -> bool:
    weights = directory / entry["file"]
    stamp = marker(weights)
    return (
        weights.exists()
        and weights.stat().st_size == entry["size"]
        and stamp.exists()
        and stamp.read_text().split()[0] == entry["sha256"]
    )
