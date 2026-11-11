"""The exporter's experiment description (PRD mvp-dashboard AC-1, and the parts of AC-6 and AC-13 phase 1 delivers)."""

import hashlib
import json
import sys
from pathlib import Path

import duckdb
import pytest

from atr.store import export as exporter
from atr.store.export import RUN_FIELDS, check_configurations, load_experiment

# PRPs/prds/mvp-dashboard.prd.md AC-1 Experiment description in the export
REAL_FILE = Path(__file__).resolve().parents[2] / "experiments" / "mvp.toml"

MINIMAL = """\
preliminary = true
planned_repetitions = 3

[[configurations]]
label = "alpha"
name = "Alpha"
workflow = "wf"
workflow_version = "1.0.0"
model = "model-a"
question = "Q1"

[[configurations]]
label = "beta"
name = "Beta"
workflow = "plain"
model = "model-a"
question = "Q2"

[[questions]]
id = "Q1"
text = "First question?"
status = "answered"
answer = "Yes."

[[questions]]
id = "Q2"
text = "Second question?"
status = "not_yet_answered"
reason = "Pending."

[[hypotheses]]
id = "H1"
text = "A hypothesis"
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "experiment-input.toml"
    path.write_text(text)
    return path


def fails_with(tmp_path: Path, text: str, *fragments: str) -> None:
    with pytest.raises(SystemExit) as error:
        load_experiment(write(tmp_path, text))
    message = str(error.value)
    for fragment in fragments:
        assert fragment in message


# AC-1: the export lists configurations, questions, hypotheses, repetitions, preliminary flag


def test_declared_content_is_loaded_in_the_documented_shape(tmp_path):
    experiment = load_experiment(write(tmp_path, MINIMAL))
    assert experiment["preliminary"] is True
    assert experiment["planned_repetitions"] == 3
    assert experiment["configurations"] == [
        {"label": "alpha", "name": "Alpha", "workflow": "wf", "workflow_version": "1.0.0",
         "model": "model-a", "question": "Q1"},
        {"label": "beta", "name": "Beta", "workflow": "plain", "workflow_version": None,
         "model": "model-a", "question": "Q2"},
    ]
    assert experiment["hypotheses"] == [{"id": "H1", "text": "A hypothesis"}]
    assert set(experiment) == {"preliminary", "planned_repetitions", "configurations",
                               "questions", "hypotheses"}


def test_the_experiment_is_plain_json(tmp_path):
    experiment = load_experiment(write(tmp_path, MINIMAL))
    assert json.loads(json.dumps(experiment)) == experiment


def test_the_public_mvp_file_declares_the_mvp_experiment():
    experiment = load_experiment(REAL_FILE)
    assert [c["label"] for c in experiment["configurations"]] == [
        "relay049-sonnet", "relay049-haiku", "relay049-opus", "vanilla-sonnet", "relay047-sonnet"]
    assert [h["id"] for h in experiment["hypotheses"]] == ["H1", "H2", "H3", "H4", "H5"]
    assert experiment["planned_repetitions"] == 3
    assert experiment["preliminary"] is True
    vanilla = next(c for c in experiment["configurations"] if c["label"] == "vanilla-sonnet")
    assert vanilla["workflow_version"] is None


# AC-6 / AC-13: questions in declared order, status, reason, null answer; nothing declared is omitted


def test_questions_keep_declared_order_status_reason_and_null_answer(tmp_path):
    questions = load_experiment(write(tmp_path, MINIMAL))["questions"]
    assert [q["id"] for q in questions] == ["Q1", "Q2"]
    assert questions[0] == {"id": "Q1", "text": "First question?", "status": "answered",
                            "reason": None, "answer": "Yes."}
    assert questions[1] == {"id": "Q2", "text": "Second question?", "status": "not_yet_answered",
                            "reason": "Pending.", "answer": None}


def test_the_public_mvp_questions_are_unanswered_with_a_reason_and_in_order():
    questions = load_experiment(REAL_FILE)["questions"]
    assert [q["text"] for q in questions] == [
        "Is a workflow worth it?", "Did a new workflow version help?",
        "How much does the model tier matter?", "How often do agents claim false success?",
        "What does a working feature cost?"]
    assert all(q["status"] == "not_yet_answered" and q["answer"] is None and q["reason"]
               for q in questions)
    version = next(q for q in questions if q["text"] == "Did a new workflow version help?")
    assert "earlier-release" in version["reason"]


def test_the_earlier_release_configuration_is_declared_although_it_has_no_runs():
    experiment = load_experiment(REAL_FILE)
    earlier = [c for c in experiment["configurations"] if c["label"] == "relay047-sonnet"]
    assert len(earlier) == 1 and earlier[0]["workflow_version"] == "0.47.0"


# AC-1 / AC-4: strict validation, with a message naming the problem


def test_an_unreadable_file_fails_naming_it(tmp_path):
    missing = tmp_path / "absent-file.toml"
    with pytest.raises(SystemExit) as error:
        load_experiment(missing)
    assert "absent-file.toml" in str(error.value)


def test_malformed_toml_fails_naming_the_file(tmp_path):
    path = write(tmp_path, "preliminary = = true")
    with pytest.raises(SystemExit) as error:
        load_experiment(path)
    assert "experiment-input.toml" in str(error.value)


@pytest.mark.parametrize("key", ["preliminary", "planned_repetitions", "configurations",
                                 "questions", "hypotheses"])
def test_a_missing_top_level_key_fails_naming_it(tmp_path, key):
    import tomllib

    data = tomllib.loads(MINIMAL)
    del data[key]
    lines = []
    for k in ("preliminary", "planned_repetitions"):
        if k in data:
            lines.append(f"{k} = {json.dumps(data[k])}")
    text = "\n".join(lines) + "\n"
    for table in ("configurations", "questions", "hypotheses"):
        for item in data.get(table, []):
            text += f"\n[[{table}]]\n" + "".join(f"{k} = {json.dumps(v)}\n" for k, v in item.items())
    fails_with(tmp_path, text, key)


def test_an_unknown_top_level_key_fails_instead_of_being_dropped(tmp_path):
    fails_with(tmp_path, "surprise = 1\n" + MINIMAL, "surprise")


def test_an_unknown_key_in_a_configuration_fails_naming_it(tmp_path):
    text = MINIMAL.replace('model = "model-a"\nquestion = "Q1"', 'model = "model-a"\nquestion = "Q1"\nextra = "x"')
    fails_with(tmp_path, text, "extra")


def test_an_unknown_key_in_a_question_fails_naming_it(tmp_path):
    text = MINIMAL.replace('text = "First question?"', 'text = "First question?"\nsurprise = "x"')
    fails_with(tmp_path, text, "surprise")


def test_a_missing_required_configuration_key_fails_naming_it(tmp_path):
    text = MINIMAL.replace('workflow = "plain"\n', "")
    fails_with(tmp_path, text, "workflow")


def test_an_unknown_question_status_fails_naming_it(tmp_path):
    text = MINIMAL.replace('status = "answered"', 'status = "maybe"')
    fails_with(tmp_path, text, "maybe")


def test_a_non_boolean_preliminary_flag_fails(tmp_path):
    fails_with(tmp_path, MINIMAL.replace("preliminary = true", 'preliminary = "yes"'), "preliminary")


def test_a_non_integer_repetition_count_fails(tmp_path):
    fails_with(tmp_path, MINIMAL.replace("planned_repetitions = 3", 'planned_repetitions = "3"'),
               "planned_repetitions")


def test_duplicate_configuration_labels_fail_naming_the_label(tmp_path):
    fails_with(tmp_path, MINIMAL.replace('label = "beta"', 'label = "alpha"'), "alpha")


def test_duplicate_question_ids_fail_naming_the_id(tmp_path):
    fails_with(tmp_path, MINIMAL.replace('id = "Q2"', 'id = "Q1"'), "Q1")


def test_a_configuration_naming_an_undeclared_question_fails(tmp_path):
    fails_with(tmp_path, MINIMAL.replace('question = "Q2"', 'question = "Q9"'), "Q9")


# AC-1: an exported run whose config is not declared fails the export and names the label


def test_an_undeclared_run_config_is_named_in_the_failure(tmp_path):
    experiment = load_experiment(write(tmp_path, MINIMAL))
    runs = [{"config": "alpha"}, {"config": "ghost-config"}]
    with pytest.raises(SystemExit) as error:
        check_configurations(experiment, runs)
    assert "ghost-config" in str(error.value)


def test_declared_run_configs_pass_even_when_other_declared_configs_have_no_runs(tmp_path):
    experiment = load_experiment(write(tmp_path, MINIMAL))
    check_configurations(experiment, [{"config": "alpha"}])


# End to end through the command, on a synthetic store


def seed(path: Path, configs: list[tuple[str, str]], create: bool = True) -> None:
    extra = ("visibility", "category", "difficulty", "target_description", "task_title")
    cols = list(dict.fromkeys(RUN_FIELDS + extra))
    con = duckdb.connect(str(path))
    if create:
        con.execute("CREATE TABLE trials (" + ", ".join(f"{c} VARCHAR" for c in cols) + ")")
        con.execute("CREATE TABLE model_usage (job VARCHAR, trial VARCHAR, input_tokens BIGINT, "
                    "output_tokens BIGINT, cache_read_tokens BIGINT, cache_creation_tokens BIGINT)")
        con.execute("CREATE TABLE review_findings (job VARCHAR, trial VARCHAR, category VARCHAR, "
                    "verdict VARCHAR)")
    for trial, config in configs:
        row = {c: "x" for c in cols}
        row |= {"job": "job-1", "trial": trial, "codename": "synthetic", "task_id": "task-1",
                "config": config, "route": "api", "visibility": "public", "model": "model-a",
                "category": "feature", "difficulty": "easy",
                "target_description": "A synthetic target", "task_title": "A synthetic task"}
        con.execute(f"INSERT INTO trials VALUES ({', '.join('?' * len(cols))})",
                    [row[c] for c in cols])
    con.close()


def run_export(monkeypatch, tmp_path: Path, out: Path, *extra: str) -> None:
    argv = ["export", str(out), "job-1", "--data-dir", str(tmp_path),
            "--db", str(tmp_path / "atr.duckdb"), *extra]
    monkeypatch.setattr(sys, "argv", argv)
    exporter.main()


def test_export_with_an_experiment_writes_it_and_records_its_digest(monkeypatch, tmp_path):
    seed(tmp_path / "atr.duckdb", [("t1", "alpha"), ("t2", "beta")])
    experiment_file = write(tmp_path, MINIMAL)
    out = tmp_path / "out"
    run_export(monkeypatch, tmp_path, out, "--experiment", str(experiment_file))

    data = (out / "experiment.json").read_bytes()
    published = json.loads(data)
    assert published == load_experiment(experiment_file)
    record = json.loads((tmp_path / "publications.jsonl").read_text().splitlines()[-1])
    assert record["sha256"]["experiment.json"] == hashlib.sha256(data).hexdigest()
    assert set(record["sha256"]) >= {"runs.json", "tasks.json", "targets.json",
                                     "publication.json", "experiment.json"}


def test_export_with_the_public_mvp_file_passes_the_leak_check(monkeypatch, tmp_path):
    seed(tmp_path / "atr.duckdb", [("t1", "relay049-sonnet"), ("t2", "vanilla-sonnet")])
    out = tmp_path / "out"
    run_export(monkeypatch, tmp_path, out, "--experiment", str(REAL_FILE))
    published = json.loads((out / "experiment.json").read_text())
    assert "relay047-sonnet" in [c["label"] for c in published["configurations"]]
    assert len(published["questions"]) == 5
    assert all(q["answer"] is None for q in published["questions"])


def test_export_blocks_when_the_experiment_text_trips_the_leak_check(monkeypatch, tmp_path, capsys):
    seed(tmp_path / "atr.duckdb", [("t1", "alpha")])
    leaky = MINIMAL.replace("A hypothesis", "see notes/plan.md for details")
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as error:
        run_export(monkeypatch, tmp_path, out, "--experiment", str(write(tmp_path, leaky)))
    assert error.value.code == 2
    assert "experiment.json" in capsys.readouterr().out
    assert not out.exists()
    assert not (tmp_path / "publications.jsonl").exists()


def test_export_with_an_undeclared_config_fails_naming_it_and_writes_nothing(monkeypatch, tmp_path):
    seed(tmp_path / "atr.duckdb", [("t1", "alpha"), ("t2", "undeclared-config-x")])
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as error:
        run_export(monkeypatch, tmp_path, out, "--experiment", str(write(tmp_path, MINIMAL)))
    assert "undeclared-config-x" in str(error.value)
    assert not out.exists()
    assert not (tmp_path / "publications.jsonl").exists()


def test_export_with_an_invalid_experiment_fails_and_writes_nothing(monkeypatch, tmp_path):
    seed(tmp_path / "atr.duckdb", [("t1", "alpha")])
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as error:
        run_export(monkeypatch, tmp_path, out, "--experiment",
                   str(write(tmp_path, "surprise = 1\n" + MINIMAL)))
    assert "surprise" in str(error.value)
    assert not out.exists()
    assert not (tmp_path / "publications.jsonl").exists()


def test_export_without_an_experiment_is_unchanged(monkeypatch, tmp_path):
    seed(tmp_path / "atr.duckdb", [("t1", "anything-at-all")])
    out = tmp_path / "out"
    run_export(monkeypatch, tmp_path, out)
    assert not (out / "experiment.json").exists()
    assert sorted(p.name for p in out.iterdir()) == [
        "publication.json", "runs.json", "targets.json", "tasks.json"]
    record = json.loads((tmp_path / "publications.jsonl").read_text().splitlines()[-1])
    assert "experiment.json" not in record["sha256"]
