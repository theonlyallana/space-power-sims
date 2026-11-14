"""Orbit arithmetic, the film, depth of discharge, and the cold-model feed."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from common.params import load_params
from lunar_power.ageing.fade import crack_area_fraction, duty_from_params, fade_history
from lunar_power.ageing.feed import aged_state_from_params, apply_fade
from lunar_power.ageing.orbit import cycles_per_earth_day, current_A, profile_from_params
from lunar_power.ageing.radiation import FADE_DIFFUSIVITY_MULTIPLIER, assumption_multipliers
from lunar_power.ageing.sei import knobs_from_params, storage_loss, thickness_m
from lunar_power.electrochemistry.cell import cell_from_params
from lunar_power.electrochemistry.spm import simulate
from lunar_power.scenario import parse_layers, run_scenario

BOOK = load_params(Path(__file__).resolve().parents[1] / "lunar_power" / "params.yaml")


def test_a_90_minute_orbit_is_sixteen_cycles_in_an_earth_day():
    profile = profile_from_params(BOOK)
    assert profile["charge_min"] + profile["discharge_min"] == pytest.approx(profile["orbit_period_min"])
    assert cycles_per_earth_day(90) == pytest.approx(16.0)
    assert profile["cycles_per_earth_day"] == pytest.approx(16.0)
    assert profile["days_to_cycle_goal"] == pytest.approx(30000 / 16)


def test_depth_of_discharge_current_is_ampere_hours_over_hours():
    # 40% of 5 Ah in 35 minutes.
    assert current_A(5.0, 0.40, 35.0) == pytest.approx(0.40 * 5.0 / (35.0 / 60.0))


def test_film_thickness_is_the_square_root_closed_form():
    knobs = knobs_from_params(BOOK)
    rate_time = 10.0 * 24.0 * 3600.0
    expected = np.sqrt(
        knobs.initial_thickness_m**2
        + 2.0
        * knobs.partial_molar_volume_m3_mol
        * knobs.solvent_diffusivity_m2_s
        * knobs.solvent_concentration_mol_m3
        / knobs.lithium_per_sei_mole
        * rate_time
    )
    assert thickness_m(knobs, rate_time, knobs.reference_temperature_K) == pytest.approx(expected)


def test_a_colder_film_grows_more_slowly():
    knobs = knobs_from_params(BOOK)
    day = 30.0 * 24.0 * 3600.0
    warm = thickness_m(knobs, day, 298.15)
    cold = thickness_m(knobs, day, 273.15)
    assert warm > cold > knobs.initial_thickness_m


def test_zero_crack_fraction_matches_pure_diffusion():
    knobs = knobs_from_params(BOOK)
    cell = cell_from_params(BOOK)
    period = 90.0 * 60.0
    duration = 20.0 * period
    history = fade_history(
        knobs,
        time_s=np.array([0.0, duration]),
        period_s=period,
        depth_of_discharge=0.4,
        volume_change_full=0.132,
        fraction_at_full_expansion=0.0,
        interfacial_area_m2=cell.negative_surface_area_m2,
        nominal_capacity_Ah=cell.nominal_capacity_Ah,
        temperature_K=knobs.reference_temperature_K,
    )
    assert history.thickness_m[-1] == pytest.approx(
        thickness_m(knobs, duration, knobs.reference_temperature_K), rel=1e-9
    )


def test_a_deeper_cycle_consumes_more_capacity():
    knobs = knobs_from_params(BOOK)
    cell = cell_from_params(BOOK)
    duty = duty_from_params(BOOK)
    duration = 2.0 * 365.25 * 24.0 * 3600.0
    losses = []
    for dod in (duty["dod_shallow"], duty["dod_leo"], duty["dod_rover"]):
        history = fade_history(
            knobs,
            time_s=np.array([duration]),
            period_s=duty["leo_period_s"],
            depth_of_discharge=dod,
            volume_change_full=duty["volume_change"],
            fraction_at_full_expansion=duty["fraction_full"],
            interfacial_area_m2=cell.negative_surface_area_m2,
            nominal_capacity_Ah=cell.nominal_capacity_Ah,
            temperature_K=duty["temperature_K"],
        )
        losses.append(history.loss_Ah[-1])
    assert losses[0] < losses[1] < losses[2]


def test_crack_fraction_scales_with_the_square_of_depth():
    assert crack_area_fraction(0.0, 0.132, 2e-5) == 0.0
    full = crack_area_fraction(1.0, 0.132, 0.02)
    half = crack_area_fraction(0.5, 0.132, 0.02)
    assert full == pytest.approx(0.02)
    assert half == pytest.approx(full / 4.0)


def test_the_default_crack_fraction_sits_inside_the_sweep():
    duty = duty_from_params(BOOK)
    assert duty["fraction_low"] < duty["fraction_full"] < duty["fraction_high"]


def test_radiation_multipliers_are_not_the_fade_multiplier():
    assert FADE_DIFFUSIVITY_MULTIPLIER == 1.0
    assert 1.0 in assumption_multipliers(BOOK)
    assert max(assumption_multipliers(BOOK)) > 1.0


def test_a_higher_diffusivity_multiplier_thickens_the_film_faster():
    knobs = knobs_from_params(BOOK)
    cell = cell_from_params(BOOK)
    day = 10.0 * 24.0 * 3600.0
    plain = storage_loss(knobs, day, knobs.reference_temperature_K, cell.negative_surface_area_m2, 1.0)
    doubled = storage_loss(knobs, day, knobs.reference_temperature_K, cell.negative_surface_area_m2, 2.0)
    assert doubled["thickness_m"] > plain["thickness_m"]
    assert doubled["loss_Ah"] > plain["loss_Ah"]


def test_ageing_off_is_the_november_cell_and_ageing_on_changes_it():
    fresh = cell_from_params(BOOK)
    state = aged_state_from_params(BOOK, fresh)
    assert state.diffusivity_multiplier == 1.0
    assert state.capacity_lost_Ah > 0.0
    assert state.thickness_grown_m > 0.0
    aged = apply_fade(fresh, state)
    assert aged.initial_negative < fresh.initial_negative
    assert aged.nominal_capacity_Ah == fresh.nominal_capacity_Ah
    warm = fresh.reference_temperature_K
    assert aged.ohmic_resistance(warm) > fresh.ohmic_resistance(warm)
    # A zero-growth state must not move the November resistance or inventory.
    from lunar_power.ageing.feed import AgeingState

    untouched = apply_fade(
        fresh,
        AgeingState(
            time_s=0.0,
            thickness_m=state.thickness_m,
            thickness_grown_m=0.0,
            lithium_lost_mol=0.0,
            capacity_lost_Ah=0.0,
            remaining_fraction=1.0,
            resistivity_ohm_m=state.resistivity_ohm_m,
            depth_of_discharge=0.4,
            diffusivity_multiplier=1.0,
        ),
    )
    assert untouched.initial_negative == fresh.initial_negative
    assert untouched.ohmic_resistance(warm) == fresh.ohmic_resistance(warm)


def test_an_aged_cell_returns_less_charge_on_the_cold_model():
    fresh = cell_from_params(BOOK)
    aged = apply_fade(fresh, aged_state_from_params(BOOK, fresh))
    temperature = fresh.reference_temperature_K
    fresh_run = simulate(
        fresh, temperature, 1.0, "discharge", fresh.initial_negative, fresh.initial_positive
    )
    aged_run = simulate(
        aged, temperature, 1.0, "discharge", aged.initial_negative, aged.initial_positive
    )
    assert aged_run.throughput_Ah[-1] < fresh_run.throughput_Ah[-1]
    assert aged_run.energy_Wh < fresh_run.energy_Wh


def test_future_layers_are_switches_that_do_not_silently_run():
    with pytest.raises(NotImplementedError):
        parse_layers("thermal,safety")
    layers = parse_layers("thermal,electrochemistry")
    assert layers.ageing is False
    result = run_scenario(BOOK, layers)
    assert result["ageing"] is None
    assert result["night"]["remaining_fraction"] == 1.0


def test_storage_film_matches_the_cached_pybamm_rests():
    """The cache is a PyBaMM rest with the solvent-diffusion-limited option.

    Relative agreement of a few parts in 10,000 on thickness is the cross-check.
    The cache is not re-solved here. A separate smoke test runs the option live.
    """
    from lunar_power.ageing.pybamm_sei import load_cache

    knobs = knobs_from_params(BOOK)
    cell = cell_from_params(BOOK)
    for point in load_cache()["points"]:
        ours = storage_loss(
            knobs,
            point["time_s"],
            point["temperature_K"],
            cell.negative_surface_area_m2,
        )
        assert ours["thickness_m"] == pytest.approx(point["thickness_m"], rel=2e-3)
        assert ours["loss_Ah"] == pytest.approx(point["loss_Ah"], rel=2e-2)


def test_sei_knobs_match_the_installed_pybamm_parameter_set():
    import pybamm

    knobs = knobs_from_params(BOOK)
    parameters = pybamm.ParameterValues("OKane2022")
    assert knobs.initial_thickness_m == pytest.approx(parameters["Initial SEI thickness [m]"])
    assert knobs.solvent_diffusivity_m2_s == pytest.approx(parameters["SEI solvent diffusivity [m2.s-1]"])
    assert knobs.solvent_concentration_mol_m3 == pytest.approx(
        parameters["Bulk solvent concentration [mol.m-3]"]
    )
    assert knobs.partial_molar_volume_m3_mol == pytest.approx(
        parameters["SEI partial molar volume [m3.mol-1]"]
    )
    assert knobs.lithium_per_sei_mole == pytest.approx(parameters["Ratio of lithium moles to SEI moles"])
    assert knobs.resistivity_ohm_m == pytest.approx(parameters["SEI resistivity [Ohm.m]"])
    assert knobs.activation_energy_J_mol == pytest.approx(
        parameters["SEI growth activation energy [J.mol-1]"]
    )
