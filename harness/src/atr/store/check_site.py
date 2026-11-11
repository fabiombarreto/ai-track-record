"""Check a built dashboard before any deploy (PUB-01 to PUB-03, PRV-04).

Usage: python -m atr.store.check_site <dist dir> [--leak-terms <file>] [--data-dir <dir>]

Fail closed: the check stops with a message naming what is missing when the dist
directory, a data file or the terms file cannot be read, or when the site shows a
private target and no leak terms are available. Findings print as
`<file>: <rule> <match>` and the exit code is 2; a clean site exits 0.

Every file of the build is scanned for the private terms (<data dir>/leak-terms.txt,
or --leak-terms), absolute paths, secrets and e-mail addresses. The data files the
pages read also go through the exporter's own leak check, and the visible text of
each page is checked for file names and relative paths. The check then requires a
page for every run, the evidence markers each page's code must carry, links that
resolve, and methodology links that land on an existing anchor. Cards, tables and
charts render in the browser, so the check reads the data files and the built page
code, not rendered HTML. Nothing is written anywhere.
"""

import argparse
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from atr.store.export import PATTERNS, leak_check, read_leak_terms, text_findings

DATA_NAMES = ("runs", "tasks", "targets", "publication", "experiment")
# No page reads publication.json, so a real build does not carry it; every other file is required.
OPTIONAL_DATA = ("publication",)
ALL_FILE_LABELS = ("absolute path", "secret", "e-mail address")
TEXT_LABELS = ("source file name", "relative path")
VENDORED = ("_observablehq/", "_npm/")
# Exact finding suffixes ("<label> <match!r>") tolerated only in files under a VENDORED
# prefix and in built pages (.html outside those prefixes). The e-mail pattern matches the
# npm package specifiers (<name>@<version>) that Observable Framework writes into its
# vendored bundles under _npm/ and _observablehq/ and into the import maps and module
# preloads of every built page; none of them is an address. The list was taken from a real
# build (calibration, Observable Framework 1.13.4 as pinned in dashboard/package.json); a new
# specifier fails the check until it is reviewed and added here.
VENDORED_ALLOWED: frozenset[str] = frozenset({
    "e-mail address 'apache-arrow@21.2.0'",
    "e-mail address 'arquero@8.0.3'",
    "e-mail address 'd3-array@3.2.5'",
    "e-mail address 'd3-axis@3.0.1'",
    "e-mail address 'd3-brush@3.0.1'",
    "e-mail address 'd3-chord@3.0.2'",
    "e-mail address 'd3-color@3.1.1'",
    "e-mail address 'd3-contour@4.0.3'",
    "e-mail address 'd3-delaunay@6.0.6'",
    "e-mail address 'd3-dispatch@3.0.2'",
    "e-mail address 'd3-drag@3.0.1'",
    "e-mail address 'd3-dsv@3.0.2'",
    "e-mail address 'd3-ease@3.0.2'",
    "e-mail address 'd3-fetch@3.0.2'",
    "e-mail address 'd3-force@3.0.1'",
    "e-mail address 'd3-format@3.1.3'",
    "e-mail address 'd3-geo@3.1.2'",
    "e-mail address 'd3-hierarchy@3.1.3'",
    "e-mail address 'd3-interpolate@3.0.2'",
    "e-mail address 'd3-path@3.1.1'",
    "e-mail address 'd3-polygon@3.0.2'",
    "e-mail address 'd3-quadtree@3.0.2'",
    "e-mail address 'd3-random@3.0.2'",
    "e-mail address 'd3-scale-chromatic@3.1.1'",
    "e-mail address 'd3-scale@4.0.3'",
    "e-mail address 'd3-selection@3.0.1'",
    "e-mail address 'd3-shape@3.2.1'",
    "e-mail address 'd3-time-format@4.1.1'",
    "e-mail address 'd3-time@3.1.1'",
    "e-mail address 'd3-timer@3.0.2'",
    "e-mail address 'd3-transition@3.0.2'",
    "e-mail address 'd3@7.9.2'",
    "e-mail address 'duckdb-wasm@1.29.0'",
    "e-mail address 'htl@1.0.0'",
    "e-mail address 'isoformat@0.2.1'",
    "e-mail address 'parquet-wasm@0.9.0'",
    "e-mail address 'plot@0.6.19'",
    "e-mail address 'd3-zoom@3.0.1'",
    "e-mail address 'echarts@6.1.0'",
    "e-mail address 'leaflet@1.9.4'",
    "e-mail address 'lodash@4.18.1'",
    "e-mail address 'mapbox-gl@3.34.2'",
    "e-mail address 'react-dom@19.3.1'",
    "e-mail address 'react@19.3.1'",
    "e-mail address 'sample-datasets@1.0.1'",
    "e-mail address 'topojson-client@3.1.0'",
})

PAGES = ("index.html", "runs.html", "grid.html", "tasks.html", "methodology.html")
EVIDENCE_MARKERS = {
    "index.html": ("data-runs=", "./runs?ids=", "./runs?config=", "./methodology#"),
    "grid.html": ("data-runs=", "./runs?config=", "./methodology#"),
    "runs.html": ('get("ids")', 'get("config")', 'get("task")'),
}
NON_PAGE_PREFIXES = ("_observablehq/", "_npm/", "_file/")


def rel_path(dist: Path, path: Path) -> str:
    return path.relative_to(dist).as_posix()


def data_paths(dist: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name in DATA_NAMES:
        matches = sorted((dist / "_file" / "data").glob(f"{name}.*.json"))
        if not matches and name in OPTIONAL_DATA:
            continue
        if not matches:
            raise SystemExit(f"blocked: the data file {name}.json is missing from {dist}/_file/data")
        if len(matches) > 1:
            raise SystemExit(f"blocked: the data file {name}.json is ambiguous in {dist}/_file/data "
                             f"({', '.join(m.name for m in matches)})")
        paths[f"{name}.json"] = matches[0]
    return paths


def read_data(dist: Path) -> dict[str, object]:
    data: dict[str, object] = {}
    for name, path in data_paths(dist).items():
        try:
            data[name] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise SystemExit(f"blocked: the data file {name} is not readable JSON: {error}") from None
    return data


class _Text(HTMLParser):
    SKIP = ("script", "style", "template")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.chunks.append(data)


def visible_text(html: str) -> str:
    parser = _Text()
    parser.feed(html)
    parser.close()
    return " ".join(parser.chunks)


class _Anchors(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if tag == "a" and attributes.get("href") is not None:
            self.hrefs.append(attributes["href"])


def anchors(html: str) -> _Anchors:
    parser = _Anchors()
    parser.feed(html)
    parser.close()
    return parser


def tolerant_findings(rel: str, text: str, terms: list[str]) -> list[str]:
    """The all-file rules minus VENDORED_ALLOWED, applied to every match, not the first five."""
    findings = text_findings(rel, text, terms, ())
    for label in ALL_FILE_LABELS:
        for match in sorted(set(PATTERNS[label].findall(text))):
            if f"{label} {match!r}" not in VENDORED_ALLOWED:
                findings.append(f"{rel}: {label} {match!r}")
    return findings


def leak_findings(dist: Path, terms: list[str], private: set[str]) -> list[str]:
    data = read_data(dist)
    findings = []
    data_files = {name: rel_path(dist, path) for name, path in data_paths(dist).items()}
    for finding in leak_check(data, terms, private):
        name, _, rest = finding.partition(": ")
        findings.append(f"{data_files.get(name, name)}: {rest}")

    scanned = set(data_files.values())
    for path in sorted(p for p in dist.rglob("*") if p.is_file()):
        rel = rel_path(dist, path)
        if rel in scanned:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        page = rel.endswith(".html") and not rel.startswith(NON_PAGE_PREFIXES)
        if rel.startswith(VENDORED) or page:
            findings += tolerant_findings(rel, text, terms)
        else:
            findings += text_findings(rel, text, terms, ALL_FILE_LABELS)
        if page:
            findings += text_findings(rel, visible_text(text), [], TEXT_LABELS)
    return findings


def run_slug(run: dict) -> str:
    job, trial = run.get("job"), run.get("trial")
    if not job or not trial:
        raise ValueError(f"run without job or trial: {json.dumps({'job': job, 'trial': trial})}")
    return re.sub(r"[^A-Za-z0-9_-]", "-", f"{job}--{trial}")


def _resolve(dist: Path, page: Path, path: str) -> Path | None:
    base = dist if path.startswith("/") else page.parent
    target = base / unquote(path).lstrip("/") if path else page
    if path.endswith("/") or path in ("", ".", ".."):
        candidates = [target / "index.html"] if path else [page]
    else:
        candidates = [target, target.with_name(target.name + ".html"), target / "index.html"]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def evidence_findings(dist: Path, data: dict[str, object]) -> list[str]:
    findings = []
    runs = data["runs.json"]
    experiment = data["experiment.json"]
    declared = {c.get("label") for c in experiment.get("configurations", [])} if isinstance(experiment, dict) else set()

    seen: dict[str, dict] = {}
    for run in runs:
        try:
            slug = run_slug(run)
        except ValueError as error:
            findings.append(f"runs.json: {error}")
            continue
        if slug in seen:
            findings.append(f"run/{slug}.html: two runs share the page path {slug}")
        seen[slug] = run
        if not (dist / "run" / f"{slug}.html").is_file():
            findings.append(f"run/{slug}.html: run page missing")
        if run.get("config") not in declared:
            findings.append(f"run/{slug}.html: configuration {run.get('config')!r} is not declared "
                            f"in experiment.json, its aggregate evidence would be lost")

    for page in PAGES:
        if not (dist / page).is_file():
            findings.append(f"{page}: page missing")
    for page, markers in EVIDENCE_MARKERS.items():
        if not (dist / page).is_file():
            continue
        text = (dist / page).read_text(encoding="utf-8", errors="ignore")
        for marker in markers:
            if marker not in text:
                findings.append(f"{page}: no run identifiers or evidence link (missing '{marker}')")

    methodology = dist / "methodology.html"
    method_ids = (anchors(methodology.read_text(encoding="utf-8", errors="ignore")).ids
                  if methodology.is_file() else set())
    ids_cache: dict[Path, set[str]] = {}

    def ids_of(target: Path) -> set[str]:
        if target not in ids_cache:
            ids_cache[target] = anchors(target.read_text(encoding="utf-8", errors="ignore")).ids
        return ids_cache[target]

    for path in sorted(dist.rglob("*.html")):
        rel = rel_path(dist, path)
        if rel.startswith(NON_PAGE_PREFIXES):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for href in anchors(text).hrefs:
            if re.match(r"^([A-Za-z][A-Za-z0-9+.-]*:|//)", href) or "${" in href:
                continue
            parts = urlsplit(href)
            target = _resolve(dist, path, parts.path)
            if target is None:
                findings.append(f"{rel}: link to missing page '{href}'")
            elif parts.fragment and target.suffix == ".html" and unquote(parts.fragment) not in ids_of(target):
                findings.append(f"{rel}: link to missing anchor '{href}'")
        for anchor in sorted(set(re.findall(r"\./methodology#([A-Za-z0-9_-]+)", text))):
            if anchor not in method_ids:
                findings.append(f"{rel}: link to missing anchor 'methodology#{anchor}'")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dist_dir", type=Path)
    parser.add_argument("--leak-terms", type=Path)
    default_data = Path(os.environ.get("ATR_DATA_DIR", "~/atr/data")).expanduser()
    parser.add_argument("--data-dir", type=Path, default=default_data)
    args = parser.parse_args()

    dist = args.dist_dir
    if not dist.is_dir():
        raise SystemExit(f"blocked: {dist} is not a directory")
    if not any(dist.rglob("*.html")):
        raise SystemExit(f"blocked: {dist} holds no .html file")
    data = read_data(dist)
    terms_file = args.leak_terms or args.data_dir / "leak-terms.txt"
    if args.leak_terms and not terms_file.is_file():
        raise SystemExit(f"blocked: the leak terms file {terms_file} does not exist")
    try:
        terms = read_leak_terms(terms_file)
    except OSError as error:
        raise SystemExit(f"blocked: cannot read {terms_file}: {error}") from None
    private = {t["codename"] for t in data["targets.json"] if t["visibility"] != "public"}
    if private and not terms:
        raise SystemExit(f"blocked: the site shows a private target but {terms_file} lists no terms")

    findings = leak_findings(dist, terms, private) + evidence_findings(dist, data)
    if findings:
        print("blocked by the site check:")
        for finding in findings:
            print(f"  {finding}")
        raise SystemExit(2)
    files = sum(1 for p in dist.rglob("*") if p.is_file())
    print(f"site check passed: {files} files, {len(data['runs.json'])} runs")


if __name__ == "__main__":
    main()
