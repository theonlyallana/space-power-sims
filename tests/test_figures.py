"""The four November PNGs are produced by code and committed with it."""

from pathlib import Path

FIGURES = Path(__file__).resolve().parents[1] / "01-lunar-night-battery" / "figures"
EXPECTED = (
    "A_plated_lithium.png",
    "B_discharge_curves.png",
    "C_heater_energy.png",
    "D_keep_warm_vs_hibernate.png",
)


def test_four_charts_are_real_pngs():
    for name in EXPECTED:
        path = FIGURES / name
        assert path.is_file(), name
        # A real chart is tens of kilobytes. An empty placeholder is not.
        assert path.stat().st_size > 20_000, name
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
