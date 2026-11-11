"""Locate and read the publication export that the dashboard is built from.

Usage: python exportdir.py   (check mode: verifies the export, exits 0 when complete)

The site is a static output rebuilt from one export directory (D-025, D-033). That
directory is named by ATR_EXPORT_DIR and nothing else is read: there is no default
and no sample data, so a build with no export fails instead of showing invented or
stale data (D-020).
"""

import json
import os
import sys
from pathlib import Path

REQUIRED = ("runs.json", "tasks.json", "targets.json", "publication.json", "experiment.json")


def export_dir() -> Path:
    value = os.environ.get("ATR_EXPORT_DIR")
    if not value:
        raise SystemExit("ATR_EXPORT_DIR is not set; point it at a publication export directory")
    path = Path(value).expanduser()
    if not path.is_dir():
        raise SystemExit(f"ATR_EXPORT_DIR does not name a directory: {value}")
    return path


def read(name: str) -> str:
    path = export_dir() / name
    if not path.is_file():
        raise SystemExit(f"the export is missing {name}")
    with open(path, encoding="utf-8", newline="") as handle:
        text = handle.read()
    try:
        json.loads(text)
    except ValueError as error:
        raise SystemExit(f"{name} in the export is not valid JSON: {error}")
    return text


def main() -> None:
    for name in REQUIRED:
        read(name)


if __name__ == "__main__":
    main()
