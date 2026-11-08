"""Download the pinned weight files of the local models plan and verify them.

Usage: python -m atr.local.fetch [<model id>...] [--stage main] [--dry-run]

With no model id, fetches every model of the stage. Files come from their
Hugging Face repository at the pinned revision and go to $ATR_MODELS_DIR. A
download resumes where it stopped. A file counts as present only once its size
and SHA-256 match models.toml; a marker next to it records the digest, so later
calls skip the hash. A file whose size or digest does not match is kept as
<file>.bad, so the next call downloads afresh. The result line says "present,
verified" for a file that was already complete and "downloaded and verified"
only after a download.
"""

import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path

from atr.local import config


def url(entry: dict) -> str:
    return f"https://huggingface.co/{entry['repo']}/resolve/{entry['revision']}/{entry['file']}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(16 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def check(model_id: str, entry: dict, path: Path) -> None:
    """Fail unless the file has the pinned size and digest."""
    size = path.stat().st_size
    if size != entry["size"]:
        path.rename(path.with_name(entry["file"] + ".bad"))
        raise SystemExit(f"{model_id}: {path.name} has {size} bytes, expected {entry['size']}")
    print(f"{model_id}: hashing {path.name}", flush=True)
    digest = sha256(path)
    if digest != entry["sha256"]:
        path.rename(path.with_name(entry["file"] + ".bad"))
        raise SystemExit(f"{model_id}: SHA-256 {digest} does not match {entry['sha256']}")


def fetch(model_id: str, entry: dict, directory: Path, dry_run: bool = False) -> str:
    weights = directory / entry["file"]
    if config.verified(entry, directory):
        return f"{model_id}: present, verified"
    downloaded = not weights.exists()
    if not downloaded:
        if dry_run:
            return f"{model_id}: would verify {weights}"
        check(model_id, entry, weights)
    else:
        partial = weights.with_name(entry["file"] + ".part")
        have = partial.stat().st_size if partial.exists() else 0
        existing = directory
        while not existing.exists():
            existing = existing.parent
        free = shutil.disk_usage(existing).free
        if free < entry["size"] - have:
            raise SystemExit(
                f"{model_id}: needs {(entry['size'] - have) / 1e9:.1f} GB, "
                f"{directory} has {free / 1e9:.1f} GB free"
            )
        if dry_run:
            return f"{model_id}: would download {(entry['size'] - have) / 1e9:.2f} GB from {url(entry)}"
        if have < entry["size"]:
            subprocess.run(
                ["curl", "--fail", "--location", "--retry", "5", "--continue-at", "-",
                 "--output", str(partial), url(entry)],
                check=True,
            )
        check(model_id, entry, partial)
        partial.rename(weights)
    config.marker(weights).write_text(f"{entry['sha256']}  {entry['file']}\n")
    return f"{model_id}: {'downloaded and verified' if downloaded else 'present, verified'}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model_ids", nargs="*", help="models to fetch (default: every model of --stage)")
    parser.add_argument("--stage", default="main", help="stage to fetch when no model is named")
    parser.add_argument("--dry-run", action="store_true", help="show what would be done")
    args = parser.parse_args()

    settings = config.load()
    ids = args.model_ids or [i for i, m in settings["models"].items() if m["stage"] == args.stage]
    if not ids:
        raise SystemExit(f"no model in stage {args.stage!r}")
    directory = config.models_dir()
    if not args.dry_run:
        directory.mkdir(parents=True, exist_ok=True)
    for model_id in ids:
        print(fetch(model_id, config.model(settings, model_id), directory, args.dry_run), flush=True)


if __name__ == "__main__":
    main()
