"""The exporter's leak check (PUB-03): any finding blocks a publication."""

from atr.store.export import leak_check

PRIVATE = {"Target A"}
CLEAN_RUN = {"trial": "task-01__abc", "codename": "Target A", "outcome": "completed", "cost_usd": 0.45}


def export_with(run: dict) -> dict:
    return {"runs.json": [run], "tasks.json": [], "targets.json": []}


def test_clean_export_has_no_findings():
    assert leak_check(export_with(CLEAN_RUN), ["secretproduct"], PRIVATE) == []


def test_private_term_is_found_whatever_its_case():
    run = CLEAN_RUN | {"native_outcome": "halted in SecretProduct billing"}
    findings = leak_check(export_with(run), ["secretproduct"], PRIVATE)
    assert any("private term" in finding for finding in findings)


def test_absolute_paths_and_email_addresses_are_found():
    run = CLEAN_RUN | {"native_outcome": "see /home/op/notes and op@example.com"}
    findings = leak_check(export_with(run), [], set())
    assert any("absolute path" in finding for finding in findings)
    assert any("e-mail address" in finding for finding in findings)


def test_long_text_is_found_only_in_private_runs():
    run = CLEAN_RUN | {"native_outcome": "x" * 65}
    assert any("long text" in finding for finding in leak_check(export_with(run), [], PRIVATE))
    assert not any("long text" in finding for finding in leak_check(export_with(run), [], set()))
