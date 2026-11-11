"""The dashboard's pinned scaffold and export loaders (PRD mvp-dashboard AC-2, phase 2).

The Node build itself is verified by the plan's build run; here the plain-Python loaders,
the pins and the skeleton pages are exercised without network or ~/atr data.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from atr.store.export import PATTERNS

# PRPs/prds/mvp-dashboard.prd.md AC-2 Pinned build without telemetry
REPO = Path(__file__).resolve().parents[2]
DASHBOARD = REPO / "dashboard"
LOADERS = sorted((DASHBOARD / "src" / "data").glob("*.json.py"))
CHECK = DASHBOARD / "loaders" / "exportdir.py"
NAMES = ("runs", "tasks", "targets", "publication", "experiment")

# Bytes chosen so that any re-serialization (indent, key order, escapes, line endings) shows.
CONTENT = {
    "runs": b'[\r\n  {"z": 1, "a": "caf\xc3\xa9 \\u00e9"}\r\n]\r\n',
    "tasks": b'[{"b":2,"a":1}]',
    "targets": b"[ ]\n",
    "publication": b'{"runs":   []}\n',
    "experiment": b'{"preliminary": true,\n\n "x": 1.50}\n',
}


def make_export(directory: Path, skip: str | None = None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in CONTENT.items():
        if name != skip:
            (directory / f"{name}.json").write_bytes(data)
    return directory


def run_py(script: Path, export: Path | None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "ATR_EXPORT_DIR"}
    if export is not None:
        env["ATR_EXPORT_DIR"] = str(export)
    return subprocess.run([sys.executable, str(script)], capture_output=True, env=env, cwd=script.parent)


def test_there_is_one_loader_per_export_file():
    assert sorted(p.name for p in LOADERS) == sorted(f"{n}.json.py" for n in NAMES)


@pytest.mark.parametrize("name", NAMES)
def test_loader_passes_its_export_file_through_byte_for_byte(tmp_path, name):
    export = make_export(tmp_path / "export")
    result = run_py(DASHBOARD / "src" / "data" / f"{name}.json.py", export)
    assert result.returncode == 0, result.stderr
    assert result.stdout == CONTENT[name]


@pytest.mark.parametrize("name", NAMES)
def test_loader_fails_naming_the_variable_when_no_export_is_set(name):
    result = run_py(DASHBOARD / "src" / "data" / f"{name}.json.py", None)
    assert result.returncode != 0
    assert b"ATR_EXPORT_DIR" in result.stderr
    assert result.stdout == b""


def test_loader_fails_when_the_variable_names_no_directory(tmp_path):
    result = run_py(DASHBOARD / "src" / "data" / "runs.json.py", tmp_path / "absent")
    assert result.returncode != 0
    assert b"ATR_EXPORT_DIR" in result.stderr
    assert result.stdout == b""


@pytest.mark.parametrize("name", NAMES)
def test_loader_fails_naming_its_file_when_the_export_lacks_it(tmp_path, name):
    export = make_export(tmp_path / "export", skip=name)
    result = run_py(DASHBOARD / "src" / "data" / f"{name}.json.py", export)
    assert result.returncode != 0
    assert f"{name}.json".encode() in result.stderr
    assert result.stdout == b"", "no sample data may stand in for a missing file"


def test_loader_does_not_pass_on_a_file_that_is_not_json(tmp_path):
    export = make_export(tmp_path / "export")
    (export / "runs.json").write_text("not json", encoding="utf-8")
    result = run_py(DASHBOARD / "src" / "data" / "runs.json.py", export)
    assert result.returncode != 0
    assert b"runs.json" in result.stderr
    assert result.stdout == b""


def test_loader_reads_only_the_named_directory(tmp_path):
    export = make_export(tmp_path / "export")
    decoy = make_export(tmp_path / "decoy")
    (decoy / "runs.json").write_bytes(b'["decoy"]')
    result = run_py(DASHBOARD / "src" / "data" / "runs.json.py", export)
    assert result.stdout == CONTENT["runs"]


def test_check_mode_accepts_a_complete_export(tmp_path):
    result = run_py(CHECK, make_export(tmp_path / "export"))
    assert result.returncode == 0, result.stderr


def test_check_mode_fails_without_an_export_variable():
    result = run_py(CHECK, None)
    assert result.returncode != 0
    assert b"ATR_EXPORT_DIR" in result.stderr


@pytest.mark.parametrize("name", NAMES)
def test_check_mode_fails_naming_the_missing_file(tmp_path, name):
    result = run_py(CHECK, make_export(tmp_path / "export", skip=name))
    assert result.returncode != 0
    assert f"{name}.json".encode() in result.stderr


def test_framework_is_pinned_exactly_and_the_lockfile_agrees():
    pkg = json.loads((DASHBOARD / "package.json").read_text(encoding="utf-8"))
    assert pkg["dependencies"] == {"@observablehq/framework": "1.13.4"}
    assert pkg["engines"]["node"] == "24.22.2"
    lock = json.loads((DASHBOARD / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["packages"]["node_modules/@observablehq/framework"]["version"] == "1.13.4"
    assert (DASHBOARD / ".nvmrc").read_text(encoding="utf-8").strip() == "24.22.2"
    assert "engine-strict=true" in (DASHBOARD / ".npmrc").read_text(encoding="utf-8").splitlines()


def test_build_script_sets_telemetry_off_itself():
    script = (DASHBOARD / "scripts" / "build.mjs").read_text(encoding="utf-8")
    assert 'OBSERVABLE_TELEMETRY_DISABLE: "1"' in script


def test_generated_site_paths_are_ignored_by_git():
    lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    for pattern in ("dashboard/node_modules/", "dashboard/dist/", "dashboard/src/.observablehq/cache/"):
        assert pattern in lines


def visible_text(page: Path) -> str:
    text = page.read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"\$\{[^}]*\}", "", text)


@pytest.mark.parametrize("page", ["index", "runs", "grid", "tasks", "methodology"])
def test_skeleton_page_exists_and_its_visible_text_passes_the_leak_patterns(page):
    path = DASHBOARD / "src" / f"{page}.md"
    assert path.is_file()
    text = visible_text(path)
    assert text.lstrip().startswith("# ")
    for label, pattern in PATTERNS.items():
        assert not pattern.search(text), f"{page}: {label}"
