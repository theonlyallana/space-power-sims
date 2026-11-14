"""Capacity fade from the film, with a depth-of-discharge crack term.

Between cycles the film thickens by the diffusion law in ``sei.py``. That part
does not know the depth of discharge.

A cycle also strains the graphite. Schweidler et al. (2018) measured a 13.2%
volume change from graphite to LiC6. This file takes the strain on a cycle to
be that full-lithiation strain times the depth of discharge. That linear map
is an assumption. Elastic energy goes as strain squared, so the fraction of
surface that cracks and has to grow a new skin is

    f = f_full * (strain / strain_full)^2 = f_full * (depth of discharge)^2

with f_full an assumption that is swept. The new skin on that fraction is the
initial film thickness: formation up to that thickness is the fast step, and
diffusion limits only the later thickening. Each cycle therefore consumes the
lithium in a film of the initial thickness, on area fraction f, plus the
diffusion increment on the intact film and on the fresh patch.

f = 0 recovers pure square-root growth. A larger depth of discharge cracks
more area and consumes more lithium per cycle.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.params import Entry, require
from lunar_power.ageing.sei import (
    SeiKnobs,
    capacity_loss_Ah,
    growth_constant_m2_s,
    lithium_per_area_mol_m2,
    thickness_m,
)


@dataclass(frozen=True)
class FadeResult:
    """One duty cycle, sampled on the requested clock."""

    time_s: np.ndarray
    cycles: np.ndarray
    thickness_m: np.ndarray
    loss_Ah: np.ndarray
    remaining_fraction: np.ndarray
    depth_of_discharge: float
    period_s: float
    crack_fraction_at_full: float
    diffusivity_multiplier: float


def crack_area_fraction(
    depth_of_discharge: float,
    volume_change_full: float,
    fraction_at_full_expansion: float,
) -> float:
    """Area fraction rebuilt each cycle. Zero depth rebuilds nothing."""
    if not 0.0 <= depth_of_discharge <= 1.0:
        raise ValueError("depth of discharge must sit between 0 and 1")
    if volume_change_full <= 0.0:
        raise ValueError("full-lithiation volume change must be positive")
    strain = volume_change_full * float(depth_of_discharge)
    ratio = strain / volume_change_full
    fraction = float(fraction_at_full_expansion) * ratio**2
    return float(min(1.0, max(0.0, fraction)))


def _step_thickness(
    thickness_m_now: float,
    dt_s: float,
    crack_fraction: float,
    growth_m2_s: float,
    initial_thickness_m: float,
) -> tuple[float, float]:
    """Advance the average thickness by dt and return the new lithium per area.

    The intact fraction keeps its thickness and diffuses. The cracked fraction
    has just been returned to the initial thickness, then diffuses for dt.
    Lithium for the rebuild itself is added by the caller, once per cycle.
    """
    intact = float(np.sqrt(thickness_m_now**2 + 2.0 * growth_m2_s * dt_s))
    patch = float(np.sqrt(initial_thickness_m**2 + 2.0 * growth_m2_s * dt_s))
    updated = (1.0 - crack_fraction) * intact + crack_fraction * patch
    grown_intact = intact - thickness_m_now
    grown_patch = patch - initial_thickness_m
    # The per-area lithium from diffusion is computed by the caller via the
    # thickness change of each population. Return those grown lengths.
    return updated, (1.0 - crack_fraction) * grown_intact + crack_fraction * grown_patch


def fade_history(
    knobs: SeiKnobs,
    *,
    time_s: np.ndarray,
    period_s: float,
    depth_of_discharge: float,
    volume_change_full: float,
    fraction_at_full_expansion: float,
    interfacial_area_m2: float,
    nominal_capacity_Ah: float,
    temperature_K: float,
    diffusivity_multiplier: float = 1.0,
) -> FadeResult:
    """Step one cycle at a time up to the last requested time.

    Output times that fall inside a cycle see diffusion only for the stub, so
    a rebuild is not charged twice. With a zero crack fraction the thickness
    matches the closed form.
    """
    samples = np.asarray(time_s, dtype=float)
    if samples.ndim != 1 or len(samples) == 0:
        raise ValueError("time_s must be a non-empty 1-d array")
    if np.any(np.diff(samples) < 0.0) or samples[0] < 0.0:
        raise ValueError("time samples must be increasing and start at or after 0")
    if period_s <= 0.0:
        raise ValueError("cycle period must be positive")

    fraction = crack_area_fraction(
        depth_of_discharge, volume_change_full, fraction_at_full_expansion
    )
    rate = growth_constant_m2_s(knobs, temperature_K, diffusivity_multiplier)
    rebuild_per_area = lithium_per_area_mol_m2(knobs, knobs.initial_thickness_m) * fraction

    def loss_Ah_from(per_area: float) -> float:
        return capacity_loss_Ah(per_area * float(interfacial_area_m2))

    def diffused_stub(thickness_now: float, dt_s: float) -> tuple[float, float]:
        """Diffusion of the film as it stands. A stub does not open a new crack."""
        updated = float(np.sqrt(thickness_now**2 + 2.0 * rate * dt_s))
        return updated, updated - thickness_now

    thickness = knobs.initial_thickness_m
    lost_per_area = 0.0
    clock = 0.0
    cursor = 0
    out_thickness = np.empty(len(samples))
    out_loss = np.empty(len(samples))

    def record_at(index: int, per_area: float, thickness_now: float) -> None:
        out_thickness[index] = thickness_now
        out_loss[index] = loss_Ah_from(per_area)

    while cursor < len(samples) and samples[cursor] <= 1e-15:
        record_at(cursor, 0.0, knobs.initial_thickness_m)
        cursor += 1

    final = float(samples[-1])
    while clock + period_s <= final + 1e-9:
        cycle_end = clock + period_s
        while cursor < len(samples) and samples[cursor] < cycle_end - 1e-9:
            stub = float(samples[cursor] - clock)
            stub_thickness, grown = diffused_stub(thickness, stub)
            record_at(
                cursor,
                lost_per_area + lithium_per_area_mol_m2(knobs, grown),
                stub_thickness,
            )
            cursor += 1
        thickness, diffused = _step_thickness(
            thickness, period_s, fraction, rate, knobs.initial_thickness_m
        )
        lost_per_area += lithium_per_area_mol_m2(knobs, diffused) + rebuild_per_area
        clock = cycle_end
        while cursor < len(samples) and samples[cursor] <= clock + 1e-9:
            record_at(cursor, lost_per_area, thickness)
            cursor += 1

    while cursor < len(samples):
        stub = float(samples[cursor] - clock)
        stub_thickness, grown = diffused_stub(thickness, stub)
        record_at(
            cursor,
            lost_per_area + lithium_per_area_mol_m2(knobs, grown),
            stub_thickness,
        )
        cursor += 1

    out_cycles = np.floor(samples / period_s + 1e-12)
    remaining = 1.0 - out_loss / float(nominal_capacity_Ah)
    return FadeResult(
        time_s=samples,
        cycles=out_cycles,
        thickness_m=out_thickness,
        loss_Ah=out_loss,
        remaining_fraction=np.maximum(0.0, remaining),
        depth_of_discharge=float(depth_of_discharge),
        period_s=float(period_s),
        crack_fraction_at_full=float(fraction_at_full_expansion),
        diffusivity_multiplier=float(diffusivity_multiplier),
    )


def pure_diffusion_thickness_m(
    knobs: SeiKnobs,
    time_s: np.ndarray,
    temperature_K: float,
    diffusivity_multiplier: float = 1.0,
) -> np.ndarray:
    """Square-root film with no cracking. The reference curve on the fade chart."""
    return np.array(
        [
            thickness_m(knobs, float(t), temperature_K, diffusivity_multiplier)
            for t in np.asarray(time_s, dtype=float)
        ]
    )


def duty_from_params(book: dict[str, Entry]) -> dict[str, float]:
    """Depths, the crack-fraction sweep, and the two cadences."""
    return {
        "dod_shallow": float(require(book, "fade_dod_shallow").value),
        "dod_leo": float(require(book, "fade_dod_leo").value),
        "dod_rover": float(require(book, "fade_dod_rover_early").value),
        "volume_change": float(require(book, "graphite_full_lithiation_volume_change").value),
        "fraction_full": float(require(book, "crack_area_fraction_at_full_expansion").value),
        "fraction_low": float(require(book, "crack_area_fraction_sweep_low").value),
        "fraction_high": float(require(book, "crack_area_fraction_sweep_high").value),
        "temperature_K": float(require(book, "reference_temperature_K").value),
        "leo_period_s": float(require(book, "leo_orbit_period_min").value) * 60.0,
        "rover_cycles_per_sol": float(require(book, "rover_cycles_per_sol").value),
        "nominal_Ah": float(require(book, "nominal_capacity_Ah").value),
    }
