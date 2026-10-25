"""Titles, legends and the footer have to land on the canvas.

The November figures are what gets posted. A layout rectangle with the wrong
convention pushes the titles off the top, and a tight save crops the footer
onto the axis label. This draws the smoke figures and checks every text
artist.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from common.params import load_params
from make_figures import generate

BOOK = load_params(
    Path(__file__).resolve().parents[1] / "01-lunar-night-battery" / "params.yaml"
)


def test_smoke_figures_keep_every_label_on_the_canvas(tmp_path):
    # generate() calls save_figure, which raises if any text extent falls
    # outside the figure. Smoke mode still draws all four titles, the
    # legends and the footer. It skips the PyBaMM traces.
    summary = generate(BOOK, tmp_path, smoke=True)
    for name in (
        "A_plated_lithium.png",
        "B_discharge_curves.png",
        "C_heater_energy.png",
        "D_keep_warm_vs_hibernate.png",
    ):
        image = tmp_path / name
        assert image.is_file()
        assert image.stat().st_size > 20_000
    assert "A" in summary and "D" in summary


def test_a_title_does_not_claim_plated_lithium_only_grows_as_it_gets_colder():
    """1C plates more at -10 °C than at -20 °C, because the colder charge is cut off."""
    source = (
        Path(__file__).resolve().parents[1] / "01-lunar-night-battery" / "make_figures.py"
    ).read_text()
    assert "Colder charging deposits more lithium as metal" not in source
    assert "Below 0 °C, charging starts to plate lithium" in source
    assert 'return "1C"' not in source
    assert 'return "C/2"' not in source
    assert "1-hour charge (1C =" in source
    assert "2-hour charge (C/2 =" in source
    assert "C-rate: 1C charges the full" in source
    assert "mAh of charge diverted to plating" in source
    assert "State of charge (1 means full)" in source
    assert "watts per °C" in source
    assert "Full cell model" in source
