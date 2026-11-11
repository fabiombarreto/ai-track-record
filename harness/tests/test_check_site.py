"""The site check over a built dist/ (PUB-01 to PUB-03): a leak or a broken evidence link blocks a deploy.

Every test builds a synthetic dist/ by hand in tmp_path; no Framework build, no network, no ~/atr data.

PRPs/prds/mvp-dashboard.prd.md AC-4 (every aggregate reaches its runs), AC-11 (leak scan of dist/),
AC-12 (methodology anchors).
"""

import json
import sys
from pathlib import Path

import pytest

from atr.store import check_site
from atr.store.check_site import evidence_findings, leak_findings, read_data, run_slug, visible_text

PAGE = ('<html><body><h1>P</h1><script type="module">const a=`<div data-runs="x">'
        '<a href="./runs?ids=x">r</a><a href="./runs?config=c">c</a>'
        '<a href="./methodology#m1">m</a></div>`</script></body></html>')
RUNS_PAGE = '<html><body><script>p.get("ids");p.get("config");p.get("task")</script></body></html>'
CLEAN_RUN = {"job": "j", "trial": "t one", "config": "c1", "codename": "pub"}


def put_data(dist: Path, name: str, value) -> None:
    (dist / "_file" / "data" / f"{name}.abc123.json").write_text(json.dumps(value), encoding="utf-8")


def make_dist(root: Path, runs=None, configs=None, visibility="public") -> Path:
    dist = root / "dist"
    (dist / "_file" / "data").mkdir(parents=True)
    (dist / "_observablehq").mkdir()
    (dist / "run").mkdir()
    runs = [CLEAN_RUN] if runs is None else runs
    configs = [{"label": "c1"}] if configs is None else configs
    put_data(dist, "runs", runs)
    put_data(dist, "tasks", [])
    put_data(dist, "targets", [{"codename": "pub", "visibility": visibility}])
    put_data(dist, "experiment", {"configurations": configs})
    for page in ("index", "grid"):
        (dist / f"{page}.html").write_text(PAGE, encoding="utf-8")
    (dist / "tasks.html").write_text("<html><body><h1>T</h1></body></html>", encoding="utf-8")
    (dist / "runs.html").write_text(RUNS_PAGE, encoding="utf-8")
    (dist / "methodology.html").write_text('<html><body><h3 id="m1">M</h3></body></html>', encoding="utf-8")
    for run in runs:
        if run.get("job") and run.get("trial"):
            (dist / "run" / f"{run_slug(run)}.html").write_text("<html><body><h1>R</h1></body></html>",
                                                                encoding="utf-8")
    return dist


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    return make_dist(tmp_path)


def leaks(dist: Path, rel: str, content: str, terms=("zzterm",), private=()) -> list[str]:
    target = dist / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return leak_findings(dist, list(terms), set(private))


def evidence(dist: Path) -> list[str]:
    return evidence_findings(dist, read_data(dist))


# --- reading the data files -------------------------------------------------


def test_data_files_are_read_by_their_logical_name(dist):
    assert {"runs.json", "tasks.json", "targets.json", "experiment.json"} <= set(read_data(dist))


def test_a_missing_data_file_stops_the_check_naming_it(dist):
    (dist / "_file" / "data" / "tasks.abc123.json").unlink()
    with pytest.raises(SystemExit, match="tasks"):
        read_data(dist)


def test_two_hashed_copies_of_a_data_file_stop_the_check(dist):
    (dist / "_file" / "data" / "runs.def456.json").write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit, match="runs.*ambiguous"):
        read_data(dist)


def test_a_data_file_that_is_not_json_stops_the_check(dist):
    (dist / "_file" / "data" / "targets.abc123.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(SystemExit, match="targets"):
        read_data(dist)


def test_publication_data_is_optional_because_no_page_reads_it(dist):
    assert "publication.json" not in read_data(dist)
    put_data(dist, "publication", {})
    assert "publication.json" in read_data(dist)


# --- visible text -----------------------------------------------------------


def test_visible_text_keeps_text_nodes_and_drops_scripts_and_styles():
    html = ("<html><head><style>.a{content:'in-style.py'}</style></head><body><p>shown prose</p>"
            "<script>const s='in-script.py'</script><template>in-template.py</template></body></html>")
    text = visible_text(html)
    assert "shown prose" in text
    assert "in-style.py" not in text and "in-script.py" not in text and "in-template.py" not in text


# --- leak scan (AC-11) ------------------------------------------------------


def test_a_clean_dist_has_no_findings(dist):
    assert leak_findings(dist, ["zzterm"], set()) == []


def test_a_private_term_in_a_page_is_found_and_names_the_file(dist):
    assert any(f.startswith("a.html: private term") for f in leaks(dist, "a.html", "<p>zzterm</p>"))


def test_a_private_term_is_found_in_a_vendored_file_too(dist):
    findings = leaks(dist, "_observablehq/v.js", "const x='zzterm'")
    assert any(f.startswith("_observablehq/v.js: private term") for f in findings)


def test_an_email_address_in_page_text_is_found(dist):
    findings = leaks(dist, "b.html", "<p>mail x@example.com</p>")
    assert any(f.startswith("b.html: e-mail address") for f in findings)


def test_a_secret_shape_in_a_script_is_found(dist):
    findings = leaks(dist, "c.html", "<script>const k='sk-ant-abc123'</script>")
    assert any(f.startswith("c.html: secret") for f in findings)


def test_an_absolute_path_in_a_vendored_bundle_is_found(dist):
    findings = leaks(dist, "_observablehq/v.js", 'const p="/home/u/x"')
    assert any(f.startswith("_observablehq/v.js: absolute path") for f in findings)


def test_an_absolute_path_in_a_non_page_file_outside_the_vendored_prefixes_is_found(dist):
    findings = leaks(dist, "notes.txt", "see /home/u/x")
    assert any(f.startswith("notes.txt: absolute path") for f in findings)


def test_a_relative_path_in_visible_page_text_is_found(dist):
    findings = leaks(dist, "c.html", "<p>see src/app/models.py</p>")
    assert any(f.startswith("c.html: relative path") for f in findings)
    assert any(f.startswith("c.html: source file name") for f in findings)


def test_file_names_in_script_text_do_not_count_as_visible_text(dist):
    assert leaks(dist, "d.html", '<p>Clean.</p><script>const s="src/lib/models.py"</script>') == []


def test_file_name_and_relative_path_rules_skip_vendored_bundles(dist):
    assert leaks(dist, "_observablehq/w.js", 'const p="src/lib/models.py"') == []
    assert leaks(dist, "_npm/w.js", 'import "x/y.js"; const f="main.py"') == []


def test_a_private_term_in_a_data_file_names_the_hashed_data_file(dist):
    put_data(dist, "runs", [{"note": "zzterm"}])
    findings = leak_findings(dist, ["zzterm"], set())
    assert any(f.startswith("_file/data/runs.abc123.json: private term") for f in findings)


def test_a_source_file_name_in_a_data_file_is_found(dist):
    put_data(dist, "runs", [{"note": "x.py"}])
    findings = leak_findings(dist, [], set())
    assert any(f.startswith("_file/data/runs.abc123.json: source file name") for f in findings)


def test_long_text_in_a_private_run_of_a_data_file_is_found(dist):
    put_data(dist, "runs", [{"codename": "priv", "trial": "t", "note": "x" * 65}])
    assert any("long text" in f for f in leak_findings(dist, [], {"priv"}))


def test_long_text_in_a_public_run_is_not_a_finding(dist):
    put_data(dist, "runs", [{"codename": "pub", "trial": "t", "note": "x" * 65}])
    assert not any("long text" in f for f in leak_findings(dist, [], set()))


def test_long_page_prose_is_not_a_finding(dist):
    assert leaks(dist, "e.html", "<p>" + "plain words " * 20 + "</p>", private={"pub"}) == []


def test_pinned_npm_specifiers_are_tolerated_in_vendored_files_and_pages(dist):
    assert leaks(dist, "_npm/bundle.js", 'import "npm:d3@7.9.2/+esm"') == []
    assert leaks(dist, "f.html", '<script>import("npm:d3@7.9.2/+esm")</script>') == []


def test_an_unreviewed_specifier_in_a_vendored_file_is_still_found(dist):
    findings = leaks(dist, "_npm/bundle.js", 'import "npm:brandnew@1.2.3/+esm"')
    assert any(f.startswith("_npm/bundle.js: e-mail address") for f in findings)


def test_an_allowed_specifier_does_not_hide_a_real_address_in_the_same_file(dist):
    findings = leaks(dist, "_npm/bundle.js", 'import "npm:d3@7.9.2/+esm"; // ops@example.com')
    assert any("ops@example.com" in f for f in findings)


def test_the_specifier_tolerance_does_not_reach_other_files(dist):
    findings = leaks(dist, "data.txt", "npm:d3@7.9.2")
    assert any(f.startswith("data.txt: e-mail address") for f in findings)


# --- run pages and evidence markers (AC-4) -----------------------------------


def test_run_slug_replaces_unsafe_characters():
    assert run_slug({"job": "j", "trial": "t one"}) == "j--t-one"
    assert run_slug({"job": "a.b", "trial": "x__y"}) == "a-b--x__y"


@pytest.mark.parametrize("run", [{"job": "", "trial": "t"}, {"job": "j"}, {"trial": "t"}])
def test_run_slug_refuses_a_run_without_job_or_trial(run):
    with pytest.raises(ValueError):
        run_slug(run)


def test_a_clean_dist_has_no_evidence_findings(dist):
    assert evidence(dist) == []


def test_a_run_without_its_page_is_a_finding_naming_the_page(dist):
    (dist / "run" / "j--t-one.html").unlink()
    assert any(f.startswith("run/j--t-one.html: run page missing") for f in evidence(dist))


def test_two_runs_sharing_a_page_path_are_a_finding(tmp_path):
    runs = [CLEAN_RUN, CLEAN_RUN | {"trial": "t-one"}]
    findings = evidence(make_dist(tmp_path, runs=runs))
    assert any("share the page path" in f for f in findings)


def test_a_run_without_job_or_trial_is_a_finding(tmp_path):
    findings = evidence(make_dist(tmp_path, runs=[CLEAN_RUN, {"config": "c1", "codename": "pub"}]))
    assert any(f.startswith("runs.json: run without job or trial") for f in findings)


def test_a_run_with_an_undeclared_configuration_is_a_finding(tmp_path):
    findings = evidence(make_dist(tmp_path, configs=[]))
    assert any("'c1'" in f and "not declared" in f for f in findings)


@pytest.mark.parametrize("page", ["index.html", "runs.html", "grid.html", "tasks.html", "methodology.html"])
def test_a_missing_top_level_page_is_a_finding(dist, page):
    (dist / page).unlink()
    assert any(f.startswith(f"{page}: page missing") for f in evidence(dist))


@pytest.mark.parametrize("page,marker", [
    ("index.html", "data-runs="), ("index.html", "./runs?ids="), ("index.html", "./runs?config="),
    ("index.html", "./methodology#"), ("grid.html", "data-runs="), ("grid.html", "./runs?config="),
    ("grid.html", "./methodology#"),
])
def test_removing_an_evidence_marker_from_an_aggregate_page_is_a_finding(dist, page, marker):
    (dist / page).write_text(PAGE.replace(marker, "x-removed"), encoding="utf-8")
    assert any(f.startswith(f"{page}: no run identifiers or evidence link") and marker in f
               for f in evidence(dist))


@pytest.mark.parametrize("parameter", ["ids", "config", "task"])
def test_the_runs_page_must_read_every_filter_parameter(dist, parameter):
    (dist / "runs.html").write_text(RUNS_PAGE.replace(f'get("{parameter}")', "get(0)"), encoding="utf-8")
    assert any(f.startswith("runs.html: no run identifiers") and f'get("{parameter}")' in f
               for f in evidence(dist))


# --- internal links and methodology anchors (AC-4, AC-12) ---------------------


def test_a_link_to_a_missing_page_is_a_finding(dist):
    (dist / "tasks.html").write_text('<a href="./nope">x</a>', encoding="utf-8")
    assert any(f.startswith("tasks.html: link to missing page") and "nope" in f for f in evidence(dist))


def test_a_link_to_an_existing_page_with_a_query_resolves(dist):
    (dist / "tasks.html").write_text('<a href="./runs?ids=j--t-one">x</a><a href="./grid">g</a>',
                                     encoding="utf-8")
    assert evidence(dist) == []


def test_a_root_relative_link_is_resolved_against_dist(dist):
    (dist / "tasks.html").write_text('<a href="/run/j--t-one">x</a><a href="/run/other">y</a>',
                                     encoding="utf-8")
    findings = evidence(dist)
    assert any("link to missing page" in f and "/run/other" in f for f in findings)
    assert not any("/run/j--t-one" in f for f in findings)


def test_external_and_mail_links_are_not_checked(dist):
    (dist / "tasks.html").write_text(
        '<a href="https://example.org/x">x</a><a href="mailto:a@b.co">m</a><a href="//cdn.example/y">c</a>',
        encoding="utf-8")
    assert evidence(dist) == []


def test_a_link_to_a_missing_anchor_is_a_finding(dist):
    (dist / "tasks.html").write_text('<a href="./methodology#absent">x</a>', encoding="utf-8")
    assert any("tasks.html: link to missing anchor" in f and "absent" in f for f in evidence(dist))


def test_a_link_to_an_existing_anchor_passes(dist):
    (dist / "tasks.html").write_text('<a href="./methodology#m1">x</a>', encoding="utf-8")
    assert evidence(dist) == []


def test_a_methodology_link_inside_script_code_must_land_on_an_anchor(dist):
    (dist / "tasks.html").write_text(
        '<script>const l=`<a href="./methodology#gone">d</a>`</script>', encoding="utf-8")
    assert any(f.startswith("tasks.html: link to missing anchor 'methodology#gone'") for f in evidence(dist))


def test_renaming_the_methodology_anchor_breaks_the_links_that_point_to_it(dist):
    (dist / "methodology.html").write_text('<h3 id="other">M</h3>', encoding="utf-8")
    findings = evidence(dist)
    assert any("methodology#m1" in f and f.startswith("index.html") for f in findings)
    assert any("methodology#m1" in f and f.startswith("grid.html") for f in findings)


# --- command line (fail closed, exit codes) -----------------------------------


def run_cli(monkeypatch, capsys, *args: str):
    monkeypatch.setattr(sys, "argv", ["check_site", *map(str, args)])
    try:
        check_site.main()
        code = 0
    except SystemExit as stop:
        code = stop.code if isinstance(stop.code, int) else 1
        message = stop.code if isinstance(stop.code, str) else ""
    else:
        message = ""
    out = capsys.readouterr().out
    return code, out, message


@pytest.fixture
def terms(tmp_path: Path) -> Path:
    path = tmp_path / "terms.txt"
    path.write_text("# synthetic\nzzterm\n", encoding="utf-8")
    return path


@pytest.fixture
def empty_data_dir(tmp_path: Path) -> Path:
    path = tmp_path / "empty-data"
    path.mkdir()
    return path


def test_a_clean_site_passes_with_exit_zero(monkeypatch, capsys, dist, terms, empty_data_dir):
    code, out, _ = run_cli(monkeypatch, capsys, dist, "--leak-terms", terms, "--data-dir", empty_data_dir)
    assert code == 0
    assert "site check passed" in out and "1 runs" in out


def test_a_public_only_site_needs_no_terms(monkeypatch, capsys, dist, empty_data_dir):
    code, out, _ = run_cli(monkeypatch, capsys, dist, "--data-dir", empty_data_dir)
    assert code == 0 and "site check passed" in out


def test_a_planted_finding_exits_two_and_names_the_file(monkeypatch, capsys, dist, terms, empty_data_dir):
    (dist / "a.html").write_text("<p>zzterm</p>", encoding="utf-8")
    code, out, _ = run_cli(monkeypatch, capsys, dist, "--leak-terms", terms, "--data-dir", empty_data_dir)
    assert code == 2
    assert "blocked by the site check" in out and "a.html" in out


def test_a_missing_run_page_exits_two(monkeypatch, capsys, dist, terms, empty_data_dir):
    (dist / "run" / "j--t-one.html").unlink()
    code, out, _ = run_cli(monkeypatch, capsys, dist, "--leak-terms", terms, "--data-dir", empty_data_dir)
    assert code == 2 and "j--t-one" in out


def test_terms_default_to_the_data_directory_file(monkeypatch, capsys, dist, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "leak-terms.txt").write_text("zzterm\n", encoding="utf-8")
    (dist / "a.html").write_text("<p>zzterm</p>", encoding="utf-8")
    code, out, _ = run_cli(monkeypatch, capsys, dist, "--data-dir", data_dir)
    assert code == 2 and "a.html" in out


def test_a_missing_dist_directory_stops_with_exit_one_naming_it(monkeypatch, capsys, tmp_path, terms,
                                                                empty_data_dir):
    code, _, message = run_cli(monkeypatch, capsys, tmp_path / "absent", "--leak-terms", terms,
                               "--data-dir", empty_data_dir)
    assert code == 1 and "absent" in message


def test_a_dist_without_html_stops_with_exit_one(monkeypatch, capsys, tmp_path, terms, empty_data_dir):
    empty = tmp_path / "bare"
    empty.mkdir()
    code, _, message = run_cli(monkeypatch, capsys, empty, "--leak-terms", terms, "--data-dir", empty_data_dir)
    assert code == 1 and ".html" in message


def test_a_missing_terms_file_given_on_the_command_line_stops_the_check(monkeypatch, capsys, dist, tmp_path,
                                                                        empty_data_dir):
    code, _, message = run_cli(monkeypatch, capsys, dist, "--leak-terms", tmp_path / "nope.txt",
                               "--data-dir", empty_data_dir)
    assert code == 1 and "nope.txt" in message


def test_a_missing_data_file_stops_the_check_with_exit_one(monkeypatch, capsys, dist, terms, empty_data_dir):
    (dist / "_file" / "data" / "tasks.abc123.json").unlink()
    code, _, message = run_cli(monkeypatch, capsys, dist, "--leak-terms", terms, "--data-dir", empty_data_dir)
    assert code == 1 and "tasks" in message


def test_a_private_target_without_terms_blocks_the_check(monkeypatch, capsys, tmp_path, empty_data_dir):
    private = make_dist(tmp_path, visibility="private")
    code, out, message = run_cli(monkeypatch, capsys, private, "--data-dir", empty_data_dir)
    assert code == 1 and "blocked" in message and "no terms" in message
    assert "site check passed" not in out


def test_a_private_target_with_terms_and_a_clean_site_passes(monkeypatch, capsys, tmp_path, terms,
                                                             empty_data_dir):
    private = make_dist(tmp_path, visibility="private")
    code, out, _ = run_cli(monkeypatch, capsys, private, "--leak-terms", terms, "--data-dir", empty_data_dir)
    assert code == 0 and "site check passed" in out


def test_the_check_writes_nothing(monkeypatch, capsys, dist, terms, empty_data_dir):
    before = sorted((p.relative_to(dist), p.stat().st_size) for p in dist.rglob("*") if p.is_file())
    run_cli(monkeypatch, capsys, dist, "--leak-terms", terms, "--data-dir", empty_data_dir)
    after = sorted((p.relative_to(dist), p.stat().st_size) for p in dist.rglob("*") if p.is_file())
    assert before == after
