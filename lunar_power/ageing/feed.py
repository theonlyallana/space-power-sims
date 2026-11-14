"""Turn an aged film into the capacity and resistance the cold model uses.

The November cell has no separate film resistance and its initial concentrations
are a formed cell. This function subtracts only the lithium consumed after
t = 0, and adds only the resistance of the film that grew after t = 0. A state
with zero growth returns the same numbers the November cell already had.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from common.constants import FARADAY
from common.params import Entry, require
from lunar_power.ageing.fade import FadeResult, duty_from_params, fade_history
from lunar_power.ageing.sei import SeiKnobs, knobs_from_params
from lunar_power.electrochemistry.cell import Cell


@dataclass(frozen=True)
class AgeingState:
    """What the cold model is allowed to see from the ageing layer."""

    time_s: float
    thickness_m: float
    thickness_grown_m: float
    lithium_lost_mol: float
    capacity_lost_Ah: float
    remaining_fraction: float
    resistivity_ohm_m: float
    depth_of_discharge: float
    diffusivity_multiplier: float


def state_at(result: FadeResult, knobs: SeiKnobs, index: int = -1) -> AgeingState:
    """One sample of a fade history, as lithium and a film thickness."""
    thickness = float(result.thickness_m[index])
    grown = max(0.0, thickness - knobs.initial_thickness_m)
    lost_Ah = float(result.loss_Ah[index])
    # Faraday is already inside loss_Ah. Moles are recovered so the
    # concentration shift can be checked. remaining_fraction is on nameplate.
    moles = lost_Ah * 3600.0 / FARADAY
    return AgeingState(
        time_s=float(result.time_s[index]),
        thickness_m=thickness,
        thickness_grown_m=grown,
        lithium_lost_mol=moles,
        capacity_lost_Ah=lost_Ah,
        remaining_fraction=float(result.remaining_fraction[index]),
        resistivity_ohm_m=knobs.resistivity_ohm_m,
        depth_of_discharge=result.depth_of_discharge,
        diffusivity_multiplier=result.diffusivity_multiplier,
    )


def apply_fade(cell: Cell, state: AgeingState) -> Cell:
    """Copy the cell with a smaller graphite inventory and a thicker film.

    Nameplate capacity is left alone. A 1-hour discharge is still 5 A. The
    aged cell runs out of lithium sooner, and the extra film resistance sags
    the terminal voltage. Both are what a cold discharge then sees.
    """
    if state.lithium_lost_mol < 0.0 or state.thickness_grown_m < 0.0:
        raise ValueError("ageing state cannot grow lithium or a negative film")
    volume_m3 = cell.negative_active_fraction * cell.negative_thickness_m * cell.area_m2
    removed = state.lithium_lost_mol / volume_m3
    if removed >= cell.initial_negative:
        raise ValueError("the film has consumed the whole negative inventory")
    return replace(
        cell,
        initial_negative=cell.initial_negative - removed,
        sei_thickness_grown_m=state.thickness_grown_m,
        sei_resistivity_ohm_m=state.resistivity_ohm_m,
        lithium_lost_to_sei_mol=state.lithium_lost_mol,
    )


def aged_state_from_params(book: dict[str, Entry], cell: Cell) -> AgeingState:
    """The feed used by the scenario runner.

    LEO cadence, the LEO depth of discharge, at the reference temperature, for
    the age in ``feed_age_years``. The diffusivity multiplier is 1: radiation
    is not in this feed.
    """
    knobs = knobs_from_params(book)
    duty = duty_from_params(book)
    years = float(require(book, "feed_age_years").value)
    period = duty["leo_period_s"]
    duration = years * 365.25 * 24.0 * 3600.0
    # One sample at the requested age. The history steps whole cycles up to it.
    history = fade_history(
        knobs,
        time_s=np.array([duration]),
        period_s=period,
        depth_of_discharge=duty["dod_leo"],
        volume_change_full=duty["volume_change"],
        fraction_at_full_expansion=duty["fraction_full"],
        interfacial_area_m2=cell.negative_surface_area_m2,
        nominal_capacity_Ah=cell.nominal_capacity_Ah,
        temperature_K=duty["temperature_K"],
        diffusivity_multiplier=1.0,
    )
    return state_at(history, knobs, index=-1)
