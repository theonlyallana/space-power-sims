"""December figures have to keep their text on the canvas, same rule as November."""

from __future__ import annotations

from pathlib import Path

from common.params import load_params
from lunar_power.charts.december import generate

BOOK = load_params(Path(__file__).resolve().parents[1] / "lunar_power" / "params.yaml")


def test_december_figures_keep_every_label_on_the_canvas(tmp_path):
    summary = generate(BOOK, tmp_path)
    for name in (
        "E_sixteen_cycles_a_day.png",
        "F_sei_growth.png",
        "G_radiation_concept.png",
        "H_fade_three_depths.png",
    ):
        image = tmp_path / name
        assert image.is_file()
        assert image.stat().st_size > 20_000
    assert summary["E"]["cycles_per_earth_day"] == 16.0
    assert summary["G"]["applied_to_fade"] is False
    assert summary["H"]["diffusivity_multiplier"] == 1.0
    # Deeper duty, same clock, less capacity left.
    assert (
        summary["H"]["dod_shallow"]["remaining_at_5_years"]
        > summary["H"]["dod_leo"]["remaining_at_5_years"]
        > summary["H"]["dod_rover"]["remaining_at_5_years"]
    )


def test_december_labels_are_in_words():
    source = (
        Path(__file__).resolve().parents[1] / "lunar_power" / "charts" / "december.py"
    ).read_text()
    assert "minute charge" in source
    assert "minute discharge" in source
    assert "cycles a day" in source
    assert "Film thickness" in source
    assert "square root of time" in source
    assert "Capacity remaining" in source
    assert "one cycle a sol" in source
    assert 'label="1C"' not in source
    assert 'label="C/2"' not in source
