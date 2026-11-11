"""The dashboard's run, review and catalog rules (PRD mvp-dashboard AC-3, AC-9, AC-10, phase 3).

The pure ES module and the Framework config are exercised through `node` with synthetic
data: no network, no npm install, no ~/atr data.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from atr.store.export import PATTERNS

REPO = Path(__file__).resolve().parents[2]
DASHBOARD = REPO / "dashboard"
MODULE = (DASHBOARD / "src" / "components" / "runs.js").as_uri()
CONFIG = (DASHBOARD / "observablehq.config.js").as_uri()

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH (run in WSL)")


def node(script: str, data=None, env_extra=None, drop_env=()):
    """Run an ES-module snippet; `data` arrives as DATA, the JSON result is returned."""
    env = {k: v for k, v in os.environ.items() if k not in drop_env}
    env["DATA"] = json.dumps(data)
    env.update(env_extra or {})
    prelude = f'import * as m from "{MODULE}"; const data = JSON.parse(process.env.DATA);\n'
    result = subprocess.run(
        ["node", "--input-type=module", "-e", prelude + script],
        capture_output=True, text=True, env=env, cwd=DASHBOARD,
    )
    return result


def call(script: str, data=None):
    result = node(f"console.log(JSON.stringify({script}));", data)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def throws(script: str, data=None) -> str:
    result = node(script, data)
    assert result.returncode != 0, "expected the call to throw"
    return result.stderr


def run(trial, config, outcome, reward, cost, review, **extra):
    return {
        "job": "job-1", "trial": trial, "codename": "synthetic", "task_id": "task-1", "config": config,
        "model": "model-a", "outcome": outcome, "native_outcome": outcome + "-native", "wall_ms": 723000,
        "cost_usd": cost, "cost_source": "sdk", "reward": reward, "criteria_satisfied": 3,
        "input_tokens": 10, "output_tokens": None, "cache_read_tokens": 30, "cache_creation_tokens": 40,
        "review_by_category": review, "relay_deviations": None, "skipped_steps": None, **extra,
    }


RUNS = [
    run("task-1__a1", "vanilla-sonnet", "completed", 1.0, 0.5, {"logic": {"findings": 2, "confirmed": 0, "judged": 0}}),
    run("task-1__b2", "relay049-sonnet", "completed", 0.0, 2.5,
        {"logic": {"findings": 3, "confirmed": 2, "judged": 3}, "style": {"findings": 1, "confirmed": 1, "judged": 1}}),
    run("task-1__c3", "relay049-sonnet", "halted", 0.0, None, {}),
]
EXPERIMENT = {"configurations": [{"label": "vanilla-sonnet", "name": "Baseline"},
                                 {"label": "relay049-sonnet", "name": "Reference"}]}


# PRPs/prds/mvp-dashboard.prd.md AC-3 Run explorer and run pages
def test_run_page_path_replaces_unsafe_characters_and_keeps_case():
    assert call("m.runSlug(data[0])", [RUNS[0]]) == "job-1--task-1__a1"
    slug = call("m.runSlug(data)", {"job": "Job.X", "trial": "c/d e.f"})
    assert slug == "Job-X--c-d-e-f"
    assert re.fullmatch(r"[A-Za-z0-9_-]+", slug)


@pytest.mark.parametrize("bad", [{"job": "x"}, {"trial": "y"}, {"job": "", "trial": "y"}])
def test_run_without_job_or_trial_has_no_page_path(bad):
    throws("m.runSlug(data)", bad)


def test_two_runs_sharing_a_page_path_fail_naming_the_path():
    stderr = throws("m.runSlugs(data)", [RUNS[0], RUNS[0]])
    assert "job-1--task-1__a1" in stderr
    # distinct trials that collapse to one slug collide too
    stderr = throws("m.runSlugs(data)", [{"job": "j", "trial": "a.b"}, {"job": "j", "trial": "a/b"}])
    assert "j--a-b" in stderr


def test_distinct_runs_get_distinct_paths_in_input_order():
    assert call("m.runSlugs(data)", RUNS) == ["job-1--task-1__a1", "job-1--task-1__b2", "job-1--task-1__c3"]


def test_explorer_lists_every_run_halted_ones_included():
    rows = call("m.runRows(data.runs, data.experiment)", {"runs": RUNS, "experiment": EXPERIMENT})
    assert len(rows) == len(RUNS)
    assert [r["outcome"] for r in rows] == ["completed", "completed", "halted"]
    assert [r["slug"] for r in rows] == call("m.runSlugs(data)", RUNS)


def test_explorer_rows_carry_exactly_the_documented_columns_with_cost_and_its_source():
    rows = call("m.runRows(data.runs, data.experiment)", {"runs": RUNS, "experiment": EXPERIMENT})
    for row in rows:
        assert sorted(row) == ["configuration", "cost", "costSource", "criteria", "label", "outcome",
                               "run", "slug", "success", "task", "time"]
    first = rows[0]
    assert first["configuration"] == "Baseline" and first["label"] == "vanilla-sonnet"
    assert first["run"] == "task-1__a1" and first["task"] == "task-1"
    assert first["cost"] == "US$ 0.50" and first["costSource"] == "sdk"
    assert first["criteria"] == 3 and first["time"] == "12m 03s"


def test_task_success_means_reward_equal_to_one_only():
    rows = call("m.runRows(data.runs, data.experiment)", {"runs": RUNS, "experiment": EXPERIMENT})
    assert [r["success"] for r in rows] == ["yes", "no", "no"]
    cases = [{"reward": 1.0}, {"reward": 0.99}, {"reward": 0}, {"reward": None}, {}]
    assert call("data.map((r) => m.isSuccess(r))", cases) == [True, False, False, False, False]


def test_run_without_recorded_cost_reads_no_cost_recorded_never_zero():
    assert call("m.formatCost(data)", RUNS[2]) == "no cost recorded"
    assert call("m.formatCost(data)", {}) == "no cost recorded"
    assert call("m.formatCost(data)", {"cost_usd": 0}) == "US$ 0.00"
    assert call("m.formatCost(data)", RUNS[1]) == "US$ 2.50"


def test_missing_values_read_n_a_in_the_explorer():
    bare = run("t", "vanilla-sonnet", "halted", None, None, {}, criteria_satisfied=None, cost_source=None, wall_ms=None)
    row = call("m.runRows(data.runs, data.experiment)[0]", {"runs": [bare], "experiment": EXPERIMENT})
    assert row["criteria"] == "n/a" and row["costSource"] == "n/a" and row["time"] == "n/a"
    assert row["cost"] == "no cost recorded" and row["success"] == "no"


def test_duration_is_minutes_and_zero_padded_seconds():
    assert call("[m.formatDuration(723000), m.formatDuration(59000), m.formatDuration(null)]") == [
        "12m 03s", "0m 59s", "n/a"]


def test_configuration_display_name_comes_from_the_experiment_and_unknown_labels_fail():
    assert call("m.configName(data, 'relay049-sonnet')", EXPERIMENT) == "Reference"
    assert "ghost" in throws("m.configName(data, 'ghost')", EXPERIMENT)
    stderr = throws("m.runRows(data.runs, data.experiment)",
                    {"runs": [run("t", "ghost", "completed", 1.0, 1, {})], "experiment": EXPERIMENT})
    assert "ghost" in stderr


# PRPs/prds/mvp-dashboard.prd.md AC-9 Review status "not yet judged"
def test_unjudged_findings_show_the_count_with_not_yet_judged():
    assert call("m.reviewStatus(data)", RUNS[0]) == "2 findings, not yet judged"
    rows = call("m.reviewRows(data)", RUNS[0])
    assert rows[0]["status"] == "2 findings, not yet judged"


def test_judged_findings_show_confirmed_of_judged_overall_and_per_category():
    assert call("m.reviewStatus(data)", RUNS[1]) == "3 of 4 judged findings confirmed"
    rows = {r["category"]: r for r in call("m.reviewRows(data)", RUNS[1])}
    assert rows["logic"]["status"] == "2 of 3 judged findings confirmed"
    assert rows["style"]["status"] == "1 of 1 judged findings confirmed"
    assert rows["logic"]["findings"] == 3 and rows["logic"]["confirmed"] == 2 and rows["logic"]["judged"] == 3


def test_a_category_with_no_judged_findings_stays_unjudged_next_to_a_judged_one():
    mixed = run("t", "vanilla-sonnet", "completed", 1.0, 1, {
        "logic": {"findings": 3, "confirmed": 2, "judged": 3},
        "style": {"findings": 4, "confirmed": 0, "judged": 0}})
    by_cat = {r["category"]: r["status"] for r in call("m.reviewRows(data)", mixed)}
    assert by_cat == {"logic": "2 of 3 judged findings confirmed", "style": "4 findings, not yet judged"}


def test_run_without_review_has_no_status_and_no_category_rows():
    assert call("m.reviewStatus(data)", RUNS[2]) == "no review recorded"
    assert call("m.reviewStatus(data)", {}) == "no review recorded"
    assert call("m.reviewRows(data)", RUNS[2]) == []


def test_run_page_lists_every_exported_field_in_order_none_dropped():
    fields = call("m.runFields(data)", RUNS[1])
    assert [k for k, _ in fields] == list(RUNS[1])
    as_text = dict(fields)
    assert as_text["native_outcome"] == "completed-native"
    assert as_text["relay_deviations"] == "n/a"
    assert as_text["reward"] == "0"
    assert json.loads(as_text["review_by_category"]) == RUNS[1]["review_by_category"]


def test_tokens_are_shown_by_type_with_n_a_for_missing_counts():
    rows = call("m.tokenRows(data)", RUNS[0])
    assert len(rows) == 4
    assert [str(v) for _, v in rows] == ["10", "n/a", "30", "40"]
    assert len({label for label, _ in rows}) == 4


# PRPs/prds/mvp-dashboard.prd.md AC-10 Task catalog shows five fields only
TASKS = [{"codename": "synthetic", "task_id": "task-1", "category": "feature", "difficulty": "easy",
          "task_title": "A public title", "prompt": "secret prompt"}]
TARGETS = [{"codename": "other", "visibility": "public", "target_description": "Not this one"},
           {"codename": "synthetic", "visibility": "public", "target_description": "A synthetic target"}]


def test_catalog_has_the_five_allowed_fields_and_the_matching_targets_description():
    rows = call("m.taskCatalog(data.tasks, data.targets)", {"tasks": TASKS, "targets": TARGETS})
    assert rows == [{"codename": "synthetic", "task_id": "task-1", "category": "feature",
                     "difficulty": "easy", "description": "A synthetic target"}]
    assert "A public title" not in json.dumps(rows) and "secret prompt" not in json.dumps(rows)


def test_catalog_has_one_row_per_task_each_joined_to_its_own_target():
    tasks = TASKS + [{"codename": "other", "task_id": "task-2", "category": "bug", "difficulty": "hard"}]
    rows = call("m.taskCatalog(data.tasks, data.targets)", {"tasks": tasks, "targets": TARGETS})
    assert [(r["task_id"], r["description"]) for r in rows] == [
        ("task-1", "A synthetic target"), ("task-2", "Not this one")]


def test_task_without_a_target_fails_naming_the_codename():
    stderr = throws("m.taskCatalog(data.tasks, data.targets)",
                    {"tasks": [{"codename": "ghost", "task_id": "t"}], "targets": TARGETS})
    assert "ghost" in stderr


def test_no_dashboard_source_names_task_titles():
    offenders = [p for p in (DASHBOARD / "src").rglob("*")
                 if p.is_file() and ".observablehq" not in p.parts and "task_title" in p.read_text(encoding="utf-8")]
    assert offenders == []


# PRPs/prds/mvp-dashboard.prd.md AC-3 One page generated per run
def paths_from_config(export_dir):
    script = (
        f'const cfg = (await import("{CONFIG}")).default;\n'
        "const out = []; for await (const p of cfg.dynamicPaths()) out.push(p);\n"
        "console.log(JSON.stringify(out));"
    )
    env = {"ATR_EXPORT_DIR": str(export_dir)} if export_dir is not None else {}
    return node(script, None, env_extra=env, drop_env=() if export_dir is not None else ("ATR_EXPORT_DIR",))


def test_config_generates_one_run_path_per_run_in_file_order(tmp_path):
    (tmp_path / "runs.json").write_text(json.dumps(RUNS), encoding="utf-8")
    result = paths_from_config(tmp_path)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        "/run/job-1--task-1__a1", "/run/job-1--task-1__b2", "/run/job-1--task-1__c3"]


def test_config_keeps_the_existing_site_settings():
    script = (f'const cfg = (await import("{CONFIG}")).default;\n'
              "console.log(JSON.stringify([cfg.root, cfg.pages.map((p) => p.name), cfg.theme]));")
    result = node(script)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        "src", ["Runs", "Grid", "Tasks", "Methodology"], ["light", "dark", "dashboard"]]


def test_config_fails_naming_the_variable_when_no_export_is_set():
    result = paths_from_config(None)
    assert result.returncode != 0
    assert "ATR_EXPORT_DIR" in result.stderr


def test_config_fails_naming_the_runs_file_when_the_export_lacks_it(tmp_path):
    result = paths_from_config(tmp_path / "absent")
    assert result.returncode != 0
    assert "runs.json" in result.stderr


def test_config_fails_when_runs_are_not_a_list_or_collide(tmp_path):
    (tmp_path / "runs.json").write_text('{"a": 1}', encoding="utf-8")
    result = paths_from_config(tmp_path)
    assert result.returncode != 0 and "runs.json" in result.stderr
    (tmp_path / "runs.json").write_text(json.dumps([RUNS[0], RUNS[0]]), encoding="utf-8")
    result = paths_from_config(tmp_path)
    assert result.returncode != 0 and "job-1--task-1__a1" in result.stderr


# PRPs/prds/mvp-dashboard.prd.md AC-3 and AC-11 Page text avoids leak shapes
def visible_text(page: Path) -> str:
    text = re.sub(r"```.*?```", "", page.read_text(encoding="utf-8"), flags=re.S)
    return re.sub(r"\$\{[^}]*\}", "", text)


@pytest.mark.parametrize("relative", ["runs.md", "tasks.md", "run/[run].md"])
def test_phase_pages_start_with_a_heading_and_pass_the_leak_patterns(relative):
    page = DASHBOARD / "src" / relative
    assert page.is_file()
    text = visible_text(page)
    assert text.lstrip().startswith("# ")
    for label, pattern in PATTERNS.items():
        assert not pattern.search(text), f"{relative}: {label}"


def test_generated_run_paths_pass_the_leak_patterns():
    for slug in call("m.runSlugs(data)", RUNS):
        for label, pattern in PATTERNS.items():
            assert not pattern.search(f"/run/{slug}"), label
