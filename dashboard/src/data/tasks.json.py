"""Pass tasks.json through from the publication export, unchanged."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "loaders"))

from exportdir import read  # noqa: E402

sys.stdout.write(read("tasks.json"))
