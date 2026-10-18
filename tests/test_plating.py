"""The cold-charge check: plating grows as the temperature falls.

This uses our own model, so it does not need PyBaMM. A separate test asks
PyBaMM the same question.
"""

from __future__ import annotations

from pathlib import Path

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


def _plated_ah(cell, empty, temperature_C: float, c_rate: float = 1.0) -> float:
    result = simulate(
        cell,
        celsius_to_kelvin(temperature_C),
        c_rate,
        "charge",
        empty[0],
        empty[1],
    )
    return float(result.plated_Ah[-1])


def test_plating_increases_as_temperature_falls(cell, empty):
    warm = _plated_ah(cell, empty, 25.0)
    freezing = _plated_ah(cell, empty, 0.0)
    colder = _plated_ah(cell, empty, -10.0)
    coldest = _plated_ah(cell, empty, -20.0)
    # At 1C the 0 V criterion stays off at 25 C and at 0 C, then switches on
    # and deposits more metal as the cell gets colder still.
    assert warm == pytest.approx(0.0, abs=1e-6)
    assert freezing == pytest.approx(0.0, abs=1e-6)
    assert coldest > colder > freezing


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
