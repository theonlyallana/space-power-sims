"""November numbers still come out of the moved code.

The committed summary.json is the baseline from before this layer. Thermal
results are algebraic or a short ODE and should match closely. One plating
charge and one warm discharge guard the electrochemical solver.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.params import load_params
from common.units import celsius_to_kelvin
from lunar_power.electrochemistry.cell import cell_from_params
from lunar_power.electrochemistry.spm import discharged_state, simulate
from lunar_power.scenario import fresh_discharge_energy_Wh
from lunar_power.thermal.night import steady_heater_energy_Wh

ROOT = Path(__file__).resolve().parents[1]
BOOK = load_params(ROOT / "lunar_power" / "params.yaml")
# Digits from the November summary, copied here so rewriting summary.json
# cannot move the baseline. Chart B at 25 °C and the C/2 plating charge at
# −20 °C are the two electrochemical anchors. Chart C's ends are algebraic.
NOVEMBER_DISCHARGE_25C_Wh = 17.299517309904623
NOVEMBER_PLATED_MAh_MINUS20_HALF_C = 125.07550214526323
NOVEMBER_HEATER_Wh_MIN_G = 315.3254999999999
NOVEMBER_HEATER_Wh_MAX_G = 12613.019999999999


def test_heater_energy_matches_the_november_baseline():
    low_g = float(BOOK["conductance_min_W_per_K"].value)
    high_g = float(BOOK["conductance_max_W_per_K"].value)
    hours = float(BOOK["lunar_night_duration_h"].value)
    setpoint = celsius_to_kelvin(float(BOOK["keep_warm_setpoint_C"].value))
    sink = float(BOOK["equator_predawn_temperature_K"].value)
    low = steady_heater_energy_Wh(low_g, setpoint, sink, 0.0, hours)
    high = steady_heater_energy_Wh(high_g, setpoint, sink, 0.0, hours)
    assert low == pytest.approx(NOVEMBER_HEATER_Wh_MIN_G, rel=1e-9)
    assert high == pytest.approx(NOVEMBER_HEATER_Wh_MAX_G, rel=1e-9)


def test_warm_discharge_energy_matches_the_november_baseline():
    energy = fresh_discharge_energy_Wh(BOOK, 25.0)
    assert energy == pytest.approx(NOVEMBER_DISCHARGE_25C_Wh, rel=1e-6)


def test_plated_lithium_at_minus_20_matches_the_november_baseline():
    cell = cell_from_params(BOOK)
    empty_negative, empty_positive = discharged_state(cell, 0.2, cell.reference_temperature_K)
    result = simulate(
        cell,
        celsius_to_kelvin(-20.0),
        0.5,
        "charge",
        empty_negative,
        empty_positive,
    )
    assert result.plated_Ah[-1] * 1000.0 == pytest.approx(NOVEMBER_PLATED_MAh_MINUS20_HALF_C, rel=1e-4)


def test_committed_summary_still_carries_the_november_anchors():
    """Charts A to D in the written summary are the fresh cell, ageing off."""
    summary = json.loads((ROOT / "lunar_power" / "figures" / "summary.json").read_text())
    warm = next(row for row in summary["B"]["ours"] if row["temperature_C"] == 25.0)
    plated = next(
        row for row in summary["A"]["ours"] if row["temperature_C"] == -20.0 and row["rate"] == 0.5
    )
    assert warm["energy_Wh"] == pytest.approx(NOVEMBER_DISCHARGE_25C_Wh, rel=1e-6)
    assert plated["plated_mAh"] == pytest.approx(NOVEMBER_PLATED_MAh_MINUS20_HALF_C, rel=1e-4)
    assert summary["D"]["hibernate_final_soc"] == pytest.approx(1.0)
    assert "scenario" in summary
    assert "ageing" in summary["scenario"]["layers"]
