"""The cold-charge check.

This uses our own model, so it does not need PyBaMM. A separate test asks
PyBaMM the same question.

Absolute plated milliampere-hours at the 4.2 V cutoff are not a temperature
ranking. A colder charge hits the cutoff sooner, so it can deposit less metal
in total even though plating started earlier. The tests check the onset.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cell import cell_from_params
from common.params import load_params
from common.units import celsius_to_kelvin
from spm import discharged_state, lithium_inventory_mol, simulate

BOOK = load_params(
    Path(__file__).resolve().parents[1] / "01-lunar-night-battery" / "params.yaml"
)


@pytest.fixture(scope="module")
def cell():
    return cell_from_params(BOOK)


@pytest.fixture(scope="module")
def empty(cell):
    return discharged_state(cell, 0.2, cell.reference_temperature_K)


def _charge(cell, empty, temperature_C: float, c_rate: float):
    return simulate(
        cell,
        celsius_to_kelvin(temperature_C),
        c_rate,
        "charge",
        empty[0],
        empty[1],
    )


def _onset_Ah(result) -> float:
    """Throughput at which plated lithium first exceeds 0.1 mAh."""
    hit = np.where(result.plated_Ah > 1e-4)[0]
    assert len(hit), "expected the 0 V switch to trip"
    return float(result.throughput_Ah[hit[0]])


def test_plating_starts_earlier_as_temperature_falls(cell, empty):
    warm = _charge(cell, empty, 25.0, 1.0)
    freezing = _charge(cell, empty, 0.0, 1.0)
    colder = _charge(cell, empty, -10.0, 1.0)
    coldest = _charge(cell, empty, -20.0, 1.0)
    # At 1C the switch stays off at 25 C and at 0 C.
    assert warm.plated_Ah[-1] == pytest.approx(0.0, abs=1e-6)
    assert freezing.plated_Ah[-1] == pytest.approx(0.0, abs=1e-4)
    # Both cold charges plate, and the colder one reaches 0 V after less
    # charge has gone in. The totals themselves need not be in that order:
    # the -20 C charge is cut off by 4.2 V before it can match the -10 C total.
    assert colder.plated_Ah[-1] > 0.05
    assert coldest.plated_Ah[-1] > 0.02
    assert _onset_Ah(coldest) < _onset_Ah(colder)


def test_half_c_does_not_false_plate_above_minus_20(cell, empty):
    """Eight equal shells plated ~9.5 mAh at 0 C and ~1.5 mAh at -10 C.

    That dip was the outer bin, not the threshold. The graded mesh leaves
    both of those charges on the intercalation side of 0 V, and still plates
    at -20 C.
    """
    for temperature_C in (0.0, -10.0):
        result = _charge(cell, empty, temperature_C, 0.5)
        assert result.plated_Ah[-1] < 1e-3
        assert result.anode_potential_V.min() > 0.0
    cold = _charge(cell, empty, -20.0, 0.5)
    assert cold.plated_Ah[-1] > 0.05
    assert cold.anode_potential_V.min() == pytest.approx(0.0, abs=1e-6)


def test_lithium_inventory_is_conserved_during_a_plating_charge(cell, empty):
    result = simulate(
        cell,
        celsius_to_kelvin(-20.0),
        1.0,
        "charge",
        empty[0],
        empty[1],
    )
    before = lithium_inventory_mol(cell, empty[0], empty[1], 0.0)
    after = lithium_inventory_mol(
        cell,
        result.negative_average_mol_m3,
        result.positive_average_mol_m3,
        result.plated_mol,
    )
    assert after == pytest.approx(before, rel=1e-3)


def test_a_warm_slow_discharge_returns_about_the_nameplate_capacity(cell):
    result = simulate(
        cell,
        cell.reference_temperature_K,
        0.2,
        "discharge",
        cell.initial_negative,
        cell.initial_positive,
    )
    assert result.throughput_Ah[-1] == pytest.approx(cell.nominal_capacity_Ah, rel=0.1)
    assert result.voltage_V[-1] == pytest.approx(cell.voltage_min_V, abs=0.05)


def test_cold_discharge_returns_less_energy_than_a_warm_one(cell):
    warm = simulate(
        cell, celsius_to_kelvin(25.0), 1.0, "discharge", cell.initial_negative, cell.initial_positive
    )
    cold = simulate(
        cell, celsius_to_kelvin(0.0), 1.0, "discharge", cell.initial_negative, cell.initial_positive
    )
    colder = simulate(
        cell, celsius_to_kelvin(-20.0), 1.0, "discharge", cell.initial_negative, cell.initial_positive
    )
    assert warm.energy_Wh > cold.energy_Wh > colder.energy_Wh
    assert warm.energy_Wh > 10.0
