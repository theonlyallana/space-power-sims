"""Sanity checks for the lunar-night energy balance.

These do not call PyBaMM. They are the checks named in the brief: energy is
conserved, and heater energy scales with conductance.
"""

from __future__ import annotations

from pathlib import Path

from common.params import load_params
from common.units import celsius_to_kelvin, watt_hours_to_joules
from thermal import (
    conservation_residual_J,
    ingenuity_specific_energy_Wh_per_kg,
    radiative_conductance_W_per_K,
    simulate_night,
    steady_heater_energy_Wh,
    steady_heater_power_W,
)

ROOT = Path(__file__).resolve().parents[1]
BOOK = load_params(ROOT / "01-lunar-night-battery" / "params.yaml")


def _night(strategy: str, conductance: float, mass_kg: float = 3.0, radioisotope_W: float = 0.0):
    specific = ingenuity_specific_energy_Wh_per_kg(
        BOOK["ingenuity_energy_0C_Wh"].value,
        BOOK["ingenuity_cell_mass_g"].value,
        int(BOOK["ingenuity_cell_count"].value),
    )
    return simulate_night(
        strategy=strategy,
        mass_kg=mass_kg,
        specific_heat_J_per_kg_K=float(BOOK["pack_specific_heat_J_per_kg_K"].value),
        conductance_W_per_K=conductance,
        sink_K=float(BOOK["equator_predawn_temperature_K"].value),
        setpoint_K=celsius_to_kelvin(float(BOOK["keep_warm_setpoint_C"].value)),
        start_K=celsius_to_kelvin(float(BOOK["night_start_temperature_C"].value)),
        stored_energy_J=watt_hours_to_joules(mass_kg * specific),
        radioisotope_power_W=radioisotope_W,
        duration_s=float(BOOK["lunar_night_duration_h"].value) * 3600.0,
    )


def test_energy_is_conserved_for_keep_warm_and_hibernate():
    heat_capacity = float(BOOK["pack_specific_heat_J_per_kg_K"].value)
    sink = float(BOOK["equator_predawn_temperature_K"].value)
    for strategy in ("keep_warm", "hibernate"):
        result = _night(strategy, conductance=0.02)
        residual = conservation_residual_J(
            result,
            mass_kg=3.0,
            specific_heat=heat_capacity,
            conductance=0.02,
            sink_K=sink,
            radioisotope_power_W=0.0,
        )
        # The thermal mass times a one-degree error is a few kilojoules.
        # The residual has to be far smaller than that.
        assert abs(residual) < 500.0


def test_heater_energy_scales_with_conductance_when_there_is_no_radioisotope():
    setpoint = celsius_to_kelvin(0.0)
    sink = 95.0
    low = steady_heater_energy_Wh(0.01, setpoint, sink, 0.0, 354.0)
    high = steady_heater_energy_Wh(0.02, setpoint, sink, 0.0, 354.0)
    assert high == pytest_approx(2.0 * low)

    # And the dynamic model, started already at the setpoint with plenty of
    # energy, spends twice as much when the leak is twice as large.
    rich = dict(
        mass_kg=50.0,
        specific_heat_J_per_kg_K=900.0,
        sink_K=sink,
        setpoint_K=setpoint,
        start_K=setpoint,
        stored_energy_J=watt_hours_to_joules(50.0 * 140.0),
        radioisotope_power_W=0.0,
        duration_s=10.0 * 3600.0,
    )
    small = simulate_night(strategy="keep_warm", conductance_W_per_K=0.01, **rich)
    large = simulate_night(strategy="keep_warm", conductance_W_per_K=0.02, **rich)
    assert large.heater_energy_Wh == pytest_approx(2.0 * small.heater_energy_Wh, rel=1e-3)


def test_a_radioisotope_unit_cuts_the_heater_by_its_own_energy():
    setpoint = celsius_to_kelvin(0.0)
    bare = steady_heater_power_W(0.05, setpoint, 95.0, 0.0)
    with_unit = steady_heater_power_W(0.05, setpoint, 95.0, 1.0)
    assert bare - with_unit == pytest_approx(1.0)


def test_hibernate_holds_state_of_charge_and_keep_warm_spends_it():
    hibernate = _night("hibernate", conductance=0.02)
    keep = _night("keep_warm", conductance=0.02)
    assert hibernate.state_of_charge[-1] == pytest_approx(1.0)
    assert hibernate.heater_energy_Wh == pytest_approx(0.0, abs=1e-6)
    assert keep.state_of_charge[-1] < 0.5
    assert keep.heater_energy_Wh > 0.0
    assert hibernate.temperature_K[-1] < celsius_to_kelvin(0.0)
    # The equatorial sink is 95 K, so hibernation cannot go below it.
    assert hibernate.temperature_K[-1] > 95.0


def test_radiative_conductance_matches_the_factored_stefan_boltzmann_law():
    from common.constants import STEFAN_BOLTZMANN

    temperature = 273.15
    sink = 95.0
    emissivity = 0.05
    area = 0.001
    expected = (
        STEFAN_BOLTZMANN
        * emissivity
        * area
        * (temperature**2 + sink**2)
        * (temperature + sink)
    )
    assert radiative_conductance_W_per_K(emissivity, area, temperature, sink) == pytest_approx(expected)


def pytest_approx(value, rel=None, abs=None):
    import pytest

    return pytest.approx(value, rel=rel, abs=abs)
