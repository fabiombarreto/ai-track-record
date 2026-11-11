"""The dashboard's answers rules (PRD mvp-dashboard AC-5, AC-6, AC-7, AC-8, AC-12, AC-13, phase 4).

The pure ES module is exercised through `node` with synthetic data, and the static pages are
read as text: no network, no npm install, no ~/atr data.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard"
SRC = DASHBOARD / "src"
MODULE = (SRC / "components" / "answers.js").as_uri()

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH (run in WSL)")


def node(script: str, data=None):
    env = {**os.environ, "DATA": json.dumps(data)}
    prelude = f'import * as m from "{MODULE}"; const data = JSON.parse(process.env.DATA);\n'
    return subprocess.run(["node", "--input-type=module", "-e", prelude + script],
                          capture_output=True, text=True, env=env, cwd=DASHBOARD)


def call(script: str, data=None):
    result = node(f"console.log(JSON.stringify({script}));", data)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def throws(script: str, data=None) -> str:
    result = node(script, data)
    assert result.returncode != 0, "expected the call to throw"
    return result.stderr


def run(trial, config, task, reward, cost, outcome="completed", source="sdk"):
    return {"job": "j", "trial": trial, "codename": "synthetic", "task_id": task, "config": config,
            "outcome": outcome, "reward": reward, "cost_usd": cost, "cost_source": source}


def slug(trial):
    return f"j--{trial}"


EXPERIMENT = {
    "preliminary": True,
    "planned_repetitions": 3,
    "configurations": [
        {"label": "vanilla-sonnet", "name": "Baseline", "question": "Q1"},
        {"label": "relay049-sonnet", "name": "Reference", "question": "Q1"},
        {"label": "relay047-sonnet", "name": "Earlier release", "question": "Q2"},
    ],
    "questions": [
        {"id": "Q1", "text": "Is a workflow worth it?", "status": "answered", "reason": None, "answer": "Not yet."},
        {"id": "Q2", "text": "Did a new workflow version help?", "status": "not_yet_answered",
         "reason": "Pending.", "answer": None},
        {"id": "Q3", "text": "What does a working feature cost?", "status": "answered", "reason": None,
         "answer": "About a dollar."},
    ],
}
TASKS = [{"task_id": "T1"}, {"task_id": "T2"}]
RUNS = [
    run("a", "vanilla-sonnet", "T1", 1.0, 0.5),
    run("b", "vanilla-sonnet", "T2", 1.0, 1.5),
    run("c", "relay049-sonnet", "T1", 0.0, 5.0, outcome="halted"),
    run("d", "relay049-sonnet", "T2", 0.99, 3.0),
]
PAYLOAD = {"runs": RUNS, "experiment": EXPERIMENT}
STATS = "m.configStats(data.runs, data.experiment)"


def stats_by_label(runs=RUNS, experiment=EXPERIMENT):
    stats = call(STATS, {"runs": runs, "experiment": experiment})
    return {s["label"]: s for s in stats}


# PRPs/prds/mvp-dashboard.prd.md AC-5 Sample size and preliminary label
def test_wilson_interval_at_the_documented_points_and_none_without_runs():
    full = call("m.wilson(3, 3)")
    assert full["low"] == pytest.approx(0.4385, abs=1e-4) and full["high"] == pytest.approx(1.0, abs=1e-4)
    none = call("m.wilson(0, 3)")
    assert none["low"] == pytest.approx(0.0, abs=1e-4) and none["high"] == pytest.approx(0.5615, abs=1e-4)
    assert call("m.wilson(0, 0)") is None


def test_every_configuration_reports_its_sample_size_in_declared_order():
    stats = call(STATS, PAYLOAD)
    assert [(s["label"], s["name"], s["n"]) for s in stats] == [
        ("vanilla-sonnet", "Baseline", 2), ("relay049-sonnet", "Reference", 2), ("relay047-sonnet", "Earlier release", 0)]


def test_no_interval_and_a_preliminary_label_below_three_runs_per_cell():
    for s in stats_by_label().values():
        assert s["interval"] is None
        assert s["preliminary"] is True


def test_no_interval_when_any_task_cell_of_the_group_has_fewer_than_three_runs():
    runs = [run(f"x{i}", "vanilla-sonnet", "T1", 1.0, 0.5) for i in range(3)]
    runs += [run(f"y{i}", "vanilla-sonnet", "T2", 1.0, 0.5) for i in range(2)]
    vanilla = stats_by_label(runs)["vanilla-sonnet"]
    assert vanilla["cellMin"] == 2 and vanilla["interval"] is None


def test_three_runs_per_cell_show_a_wilson_interval_and_drop_the_label_once_not_preliminary():
    runs = [run(f"{t}{i}", "vanilla-sonnet", t, 1.0 if i < 2 else 0.0, 0.5) for t in ("T1", "T2") for i in range(3)]
    experiment = {**EXPERIMENT, "preliminary": False}
    vanilla = stats_by_label(runs, experiment)["vanilla-sonnet"]
    assert vanilla["n"] == 6 and vanilla["cellMin"] == 3
    expected = call("m.wilson(4, 6)")
    assert vanilla["interval"]["low"] == pytest.approx(expected["low"])
    assert vanilla["interval"]["high"] == pytest.approx(expected["high"])
    assert 0 < vanilla["interval"]["low"] < 4 / 6 < vanilla["interval"]["high"] < 1
    assert vanilla["preliminary"] is False


def test_a_cell_with_fewer_runs_than_planned_is_preliminary_even_when_the_experiment_is_not():
    runs = [run(f"{i}", "vanilla-sonnet", "T1", 1.0, 0.5) for i in range(2)]
    experiment = {**EXPERIMENT, "preliminary": False}
    assert stats_by_label(runs, experiment)["vanilla-sonnet"]["preliminary"] is True


def test_grid_cells_show_an_interval_only_from_three_runs_in_the_cell():
    runs = [run(f"{i}", "vanilla-sonnet", "T1", 1.0, 0.5) for i in range(3)]
    runs.append(run("z", "relay049-sonnet", "T1", 1.0, 0.5))
    cells = {(c["task"], c["label"]): c for c in
             call("m.gridCells(data.runs, data.tasks, data.experiment).cells",
                  {"runs": runs, "tasks": TASKS, "experiment": EXPERIMENT})}
    assert cells[("T1", "vanilla-sonnet")]["interval"]["low"] == pytest.approx(0.4385, abs=1e-4)
    assert cells[("T1", "relay049-sonnet")]["interval"] is None
    assert cells[("T1", "relay049-sonnet")]["preliminary"] is True


# PRPs/prds/mvp-dashboard.prd.md AC-6 Not run and not yet answered
def test_grid_has_a_cell_per_task_and_declared_configuration_and_shows_not_run_for_the_missing_ones():
    grid = call("m.gridCells(data.runs, data.tasks, data.experiment)",
                {"runs": RUNS, "tasks": TASKS, "experiment": EXPERIMENT})
    assert [c["name"] for c in grid["configurations"]] == ["Baseline", "Reference", "Earlier release"]
    assert len(grid["cells"]) == len(TASKS) * 3
    earlier = [c for c in grid["cells"] if c["label"] == "relay047-sonnet"]
    assert [c["task"] for c in earlier] == ["T1", "T2"]
    assert all(c["text"] == "not run" and c["n"] == 0 and c["slugs"] == [] for c in earlier)
    assert all(c["text"] != "not run" for c in grid["cells"] if c["label"] != "relay047-sonnet")


def test_not_yet_answered_question_shows_its_reason_and_analysis_pending():
    cards = call("m.questionCards(data.runs, data.experiment)", PAYLOAD)
    q2 = cards[1]
    assert q2["id"] == "Q2" and q2["statusText"] == "not yet answered: Pending."
    assert q2["answerText"] == "analysis pending"


def test_a_run_of_an_undeclared_configuration_fails_naming_it_instead_of_vanishing():
    bad = {"runs": [run("z", "ghost", "T1", 1.0, 1.0)], "experiment": EXPERIMENT, "tasks": TASKS}
    assert "ghost" in throws(f"{STATS}", bad)
    assert "ghost" in throws("m.questionCards(data.runs, data.experiment)", bad)


# PRPs/prds/mvp-dashboard.prd.md AC-7 Cost with quality, and its source
def test_every_configuration_carries_its_cost_source_next_to_its_success_rate():
    vanilla = stats_by_label()["vanilla-sonnet"]
    assert vanilla["successRate"] == 1 and vanilla["meanCost"] == 1.0
    assert vanilla["costSources"] == ["sdk"]
    mixed = stats_by_label([run("a", "vanilla-sonnet", "T1", 1.0, 1.0, source="sdk"),
                            run("b", "vanilla-sonnet", "T2", 0.0, 1.0, source="estimate")])["vanilla-sonnet"]
    assert mixed["costSources"] == ["sdk", "estimate"]


def test_grid_cell_states_success_and_mean_cost_together_with_the_cost_source():
    runs = [run("a", "vanilla-sonnet", "T1", 1.0, 0.5), run("b", "vanilla-sonnet", "T1", 0.0, 1.5)]
    cell = call("m.gridCells(data.runs, data.tasks, data.experiment).cells[0]",
                {"runs": runs, "tasks": TASKS, "experiment": EXPERIMENT})
    assert cell["text"] == "1 of 2 succeeded, mean cost US$ 1.00"
    assert cell["costSources"] == ["sdk"]


def test_a_missing_cost_is_never_zero_and_never_a_partial_mean():
    partial = stats_by_label([run("a", "vanilla-sonnet", "T1", 1.0, 2.0),
                              run("b", "vanilla-sonnet", "T2", 1.0, None)])["vanilla-sonnet"]
    assert partial["meanCost"] is None
    assert not partial["costPerSuccessText"].startswith("US$")
    cell = call("m.gridCells(data.runs, data.tasks, data.experiment).cells[0]",
                {"runs": [run("a", "vanilla-sonnet", "T1", 1.0, None)], "tasks": TASKS, "experiment": EXPERIMENT})
    assert cell["text"] == "1 of 1 succeeded, no cost recorded"
    zero = stats_by_label([run("a", "vanilla-sonnet", "T1", 1.0, 0)])["vanilla-sonnet"]
    assert zero["meanCost"] == 0


def test_a_configuration_without_runs_has_no_rate_and_no_mean_cost():
    earlier = stats_by_label()["relay047-sonnet"]
    assert earlier["n"] == 0 and earlier["successRate"] is None and earlier["meanCost"] is None
    assert earlier["slugs"] == []


# PRPs/prds/mvp-dashboard.prd.md AC-8 Task success, false completion and the frontier
def test_task_success_counts_a_reward_of_exactly_one_only():
    by = stats_by_label()
    assert by["vanilla-sonnet"]["successes"] == 2
    assert by["relay049-sonnet"]["successes"] == 0  # a reward of 0.99 is not task success


def test_false_completion_counts_completed_runs_without_success_and_ignores_halted_ones():
    reference = stats_by_label()["relay049-sonnet"]
    assert reference["completed"] == 1 and reference["falseCompletions"] == 1
    assert reference["falseCompletionText"] == "1 of 1 completed runs"
    baseline = stats_by_label()["vanilla-sonnet"]
    assert baseline["falseCompletionText"] == "0 of 2 completed runs"


def test_cost_per_successful_task_spreads_the_whole_cost_over_the_successes():
    runs = [run("a", "vanilla-sonnet", "T1", 1.0, 1.0), run("b", "vanilla-sonnet", "T2", 0.0, 3.0)]
    assert stats_by_label(runs)["vanilla-sonnet"]["costPerSuccessText"] == "US$ 4.00"


def test_cost_per_successful_task_reads_no_successful_run_when_there_is_none():
    by = stats_by_label()
    assert by["relay049-sonnet"]["costPerSuccessText"] == "no successful run"
    assert by["relay047-sonnet"]["costPerSuccessText"] == "no successful run"


def test_frontier_marks_the_configurations_no_other_beats_on_cost_and_success_rate():
    assert call("m.paretoLabels(m.configStats(data.runs, data.experiment))", PAYLOAD) == ["vanilla-sonnet"]
    stats = [
        {"label": "a", "n": 1, "meanCost": 1, "successRate": 1},
        {"label": "slower", "n": 1, "meanCost": 2, "successRate": 1},
        {"label": "cheap", "n": 1, "meanCost": 0.5, "successRate": 0.5},
        {"label": "unrun", "n": 0, "meanCost": None, "successRate": None},
        {"label": "uncosted", "n": 1, "meanCost": None, "successRate": 1},
    ]
    assert call("m.paretoLabels(data)", stats) == ["a", "cheap"]


def test_two_configurations_with_identical_cost_and_rate_are_both_on_the_frontier():
    stats = [{"label": "a", "n": 1, "meanCost": 1, "successRate": 1},
             {"label": "b", "n": 1, "meanCost": 1, "successRate": 1}]
    assert call("m.paretoLabels(data)", stats) == ["a", "b"]


# PRPs/prds/mvp-dashboard.prd.md AC-13 Headline answers
def test_questions_come_in_declared_order_each_with_answer_status_and_sample_size():
    cards = call("m.questionCards(data.runs, data.experiment)", PAYLOAD)
    assert [c["id"] for c in cards] == ["Q1", "Q2", "Q3"]
    assert [c["text"] for c in cards] == [q["text"] for q in EXPERIMENT["questions"]]
    assert cards[0]["answerText"] == "Not yet." and cards[0]["statusText"] == "answered"
    assert cards[0]["n"] == 4 and cards[0]["sampleText"] == "n = 4 runs"
    assert cards[1]["n"] == 0 and cards[1]["sampleText"] == "n = 0 runs"
    assert cards[2]["answerText"] == "About a dollar."


def test_a_question_scopes_to_the_configurations_that_declare_it_or_to_all_when_none_does():
    cards = call("m.questionCards(data.runs, data.experiment)", PAYLOAD)
    assert [s["label"] for s in cards[0]["scope"]] == ["vanilla-sonnet", "relay049-sonnet"]
    assert [s["label"] for s in cards[1]["scope"]] == ["relay047-sonnet"]
    assert [s["label"] for s in cards[2]["scope"]] == ["vanilla-sonnet", "relay049-sonnet", "relay047-sonnet"]
    assert cards[2]["n"] == 4


def test_a_single_run_reads_n_equals_one_run_in_the_singular():
    cards = call("m.questionCards(data.runs, data.experiment)", {"runs": RUNS[:1], "experiment": EXPERIMENT})
    assert cards[0]["sampleText"] == "n = 1 run"


def test_each_card_and_configuration_carries_the_identifiers_of_exactly_its_runs():
    cards = call("m.questionCards(data.runs, data.experiment)", PAYLOAD)
    assert sorted(cards[0]["slugs"]) == sorted(slug(t) for t in "abcd")
    assert cards[1]["slugs"] == []
    by = stats_by_label()
    assert by["vanilla-sonnet"]["slugs"] == [slug("a"), slug("b")]
    assert by["relay049-sonnet"]["slugs"] == [slug("c"), slug("d")]
    cell = call("m.gridCells(data.runs, data.tasks, data.experiment).cells[0]",
                {"runs": RUNS, "tasks": TASKS, "experiment": EXPERIMENT})
    assert cell["slugs"] == [slug("a")]


def test_a_card_is_preliminary_when_the_experiment_is_preliminary():
    assert all(c["preliminary"] for c in call("m.questionCards(data.runs, data.experiment)", PAYLOAD))


# PRPs/prds/mvp-dashboard.prd.md AC-4 and AC-13 A link to exactly the runs behind a number
ROWS = [{"slug": "j--a", "label": "vanilla-sonnet", "task": "T1"},
        {"slug": "j--b", "label": "relay049-sonnet", "task": "T1"},
        {"slug": "j--c", "label": "relay049-sonnet", "task": "T2"}]


def test_filter_with_an_empty_query_keeps_every_row():
    assert call("m.filterRuns(data, {})", ROWS) == ROWS
    assert call("m.filterRuns(data, {config: null, task: null, ids: null})", ROWS) == ROWS


def test_filter_by_configuration_task_and_both_narrows_the_rows():
    assert [r["slug"] for r in call("m.filterRuns(data, {config: 'relay049-sonnet'})", ROWS)] == ["j--b", "j--c"]
    assert [r["slug"] for r in call("m.filterRuns(data, {task: 'T1'})", ROWS)] == ["j--a", "j--b"]
    assert [r["slug"] for r in call("m.filterRuns(data, {config: 'relay049-sonnet', task: 'T2'})", ROWS)] == ["j--c"]


def test_filter_by_identifiers_lists_exactly_those_runs():
    assert [r["slug"] for r in call("m.filterRuns(data, {ids: 'j--c,j--a'})", ROWS)] == ["j--a", "j--c"]
    assert call("m.filterRuns(data, {ids: 'j--nope'})", ROWS) == []


# PRPs/prds/mvp-dashboard.prd.md AC-12 Definitions one click away
METRIC_IDS = ["task-success", "success-rate", "false-completion", "criteria-satisfied", "cost-per-run",
              "cost-per-successful-task", "cost-source", "wall-clock-time", "outcome", "review-status",
              "sample-size", "preliminary", "wilson-interval", "pareto-frontier"]


def methodology_anchors() -> list[str]:
    text = (SRC / "methodology.md").read_text(encoding="utf-8")
    return re.findall(r'<h[2-4] id="([a-z-]+)"', text)


def test_every_metric_has_a_display_name_and_one_anchor_on_the_methodology_page():
    metrics = call("m.METRICS")
    assert sorted(metrics) == sorted(METRIC_IDS)
    assert all(metrics[i]["name"] for i in METRIC_IDS)
    anchors = methodology_anchors()
    assert sorted(anchors) == sorted(METRIC_IDS)
    assert len(set(anchors)) == len(anchors)


def links_to_methodology(page: str) -> set[str]:
    text = (SRC / page).read_text(encoding="utf-8")
    return set(re.findall(r"\(\./methodology#([a-z-]+)\)", text))


@pytest.mark.parametrize("page, expected", [
    ("index.md", {"cost-per-run", "success-rate", "pareto-frontier", "false-completion",
                  "cost-per-successful-task", "cost-source", "sample-size", "preliminary", "wilson-interval"}),
    ("grid.md", {"success-rate", "cost-per-run", "cost-source", "sample-size", "preliminary", "wilson-interval"}),
])
def test_metric_names_on_the_home_and_grid_pages_link_to_anchors_that_exist(page, expected):
    linked = links_to_methodology(page)
    assert expected <= linked
    assert linked <= set(methodology_anchors())


def test_task_success_is_defined_as_a_reward_of_exactly_one():
    text = (SRC / "methodology.md").read_text(encoding="utf-8")
    section = text.split('id="task-success"', 1)[1].split("<h3", 1)[0]
    assert "exactly 1.0" in section
