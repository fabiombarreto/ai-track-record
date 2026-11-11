"""The leak helpers the exporter shares with the site check (PUB-03).

PRPs/prds/mvp-dashboard.prd.md AC-11 (one leak-check implementation, finding strings unchanged).
"""

from pathlib import Path

from atr.store.export import read_leak_terms, text_findings


def test_leak_terms_skip_blank_lines_and_comments(tmp_path: Path):
    terms = tmp_path / "leak-terms.txt"
    terms.write_text("# synthetic\n\n  zzterm  \n   \nother term\n", encoding="utf-8")
    assert read_leak_terms(terms) == ["zzterm", "other term"]


def test_a_missing_terms_file_means_no_terms(tmp_path: Path):
    assert read_leak_terms(tmp_path / "absent.txt") == []


def test_term_findings_come_before_pattern_findings():
    assert text_findings("f", "zzterm and a@b.co", ["zzterm"], ("e-mail address",)) == [
        "f: private term 'zzterm'", "f: e-mail address 'a@b.co'"]


def test_only_the_requested_labels_are_applied():
    assert text_findings("f", "a@b.co", [], ("absolute path",)) == []


def test_all_labels_apply_by_default():
    findings = text_findings("f", "see /home/u/x and a@b.co and x.py", [])
    assert any("absolute path" in f for f in findings)
    assert any("e-mail address" in f for f in findings)
    assert any("source file name" in f for f in findings)


def test_a_term_matches_whole_words_in_any_case():
    assert text_findings("f", "the ZzTerm here", ["zzterm"], ()) == ["f: private term 'zzterm'"]
    assert text_findings("f", "zztermination", ["zzterm"], ()) == []


def test_at_most_five_distinct_matches_per_label():
    text = " ".join(f"u{i}@example.com" for i in range(9))
    assert len(text_findings("f", text, [], ("e-mail address",))) == 5
