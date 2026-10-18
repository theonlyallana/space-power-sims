"""The parameter book is the only place model inputs are allowed to live."""

from __future__ import annotations

from pathlib import Path

from common.params import load_params

PARAMS = Path(__file__).resolve().parents[1] / "01-lunar-night-battery" / "params.yaml"


def test_every_input_has_a_source_or_is_an_assumption():
    book = load_params(PARAMS)
    assert len(book) > 20
    for name, entry in book.items():
        assert entry.unit
        assert entry.note
        if entry.is_assumption:
            assert "swept" in entry.note.lower(), name
        else:
            assert entry.source.startswith("https://"), name


def test_no_employer_strings_in_the_parameter_notes():
    text = PARAMS.read_text().lower()
    for banned in ("jlr", "jaguar", "land rover", "employer", "the guide"):
        assert banned not in text
