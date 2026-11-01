"""Diffusion-limited growth of the anode surface film.

The film is the solid-electrolyte interphase. Solvent diffuses across it and
is reduced at the graphite, so the film gets thicker and cyclable lithium is
consumed. Fick's law with a fast reaction at the inner face gives a flux that
falls as 1/thickness, and integrating that rate gives thickness proportional
to the square root of time.

The algebra is the one PyBaMM integrates for the option
``"SEI": "solvent-diffusion limited"`` (Marquis, as coded in v25.8, which is
the single-layer form O'Kane et al. 2022 use). A rest in that model is the
cross-check. Ploehn, Ramadass and White (2004) are the continuum paper that
showed the square-root result against storage data.

Stoichiometry follows the parameter set: ``z`` is "lithium moles per SEI mole"
and is 1 in OKane2022. Ploehn describe a two-electron reduction. This file does
not silently insert that extra factor of two, because then it would no longer
be the equation the cross-check solves.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.constants import FARADAY, GAS
from common.params import Entry, require


@dataclass(frozen=True)
class SeiKnobs:
    """Digits from the parameter book. No defaults."""

    initial_thickness_m: float
    solvent_diffusivity_m2_s: float
    solvent_concentration_mol_m3: float
    partial_molar_volume_m3_mol: float
    lithium_per_sei_mole: float
    resistivity_ohm_m: float
    activation_energy_J_mol: float
    reference_temperature_K: float


def knobs_from_params(book: dict[str, Entry]) -> SeiKnobs:
    return SeiKnobs(
        initial_thickness_m=float(require(book, "sei_initial_thickness_m").value),
        solvent_diffusivity_m2_s=float(require(book, "sei_solvent_diffusivity_m2_s").value),
        solvent_concentration_mol_m3=float(require(book, "sei_bulk_solvent_concentration_mol_m3").value),
        partial_molar_volume_m3_mol=float(require(book, "sei_partial_molar_volume_m3_mol").value),
        lithium_per_sei_mole=float(require(book, "sei_lithium_per_mole").value),
        resistivity_ohm_m=float(require(book, "sei_resistivity_ohm_m").value),
        activation_energy_J_mol=float(require(book, "sei_growth_activation_energy_J_mol").value),
        reference_temperature_K=float(require(book, "reference_temperature_K").value),
    )


def arrhenius_factor(knobs: SeiKnobs, temperature_K: float) -> float:
    """k(T) / k(T_ref) = exp[(Ea/R) (1/T_ref - 1/T)].

    The same quotient the November cell uses for diffusion and kinetics.
    A colder film lets less solvent through.
    """
    return float(
        np.exp(
            knobs.activation_energy_J_mol
            / GAS
            * (1.0 / knobs.reference_temperature_K - 1.0 / float(temperature_K))
        )
    )


def growth_constant_m2_s(
    knobs: SeiKnobs,
    temperature_K: float,
    diffusivity_multiplier: float = 1.0,
) -> float:
    """k in ``L dL = k dt``.

    PyBaMM's interfacial current for this option is

        j = - D c F / L * Arrhenius

    and the thickness rate is

        dL/dt = - V_bar * j / (F z) = V_bar * D * c * Arrhenius / (L z)

    so k = V_bar * D * c * Arrhenius / z. ``diffusivity_multiplier`` scales D.
    The fade curves leave it at 1. The radiation chart's assumption sweep is
    the only caller that passes anything else, and it does not feed the fade.
    """
    if diffusivity_multiplier <= 0.0:
        raise ValueError("diffusivity multiplier must be positive")
    return (
        knobs.partial_molar_volume_m3_mol
        * knobs.solvent_diffusivity_m2_s
        * float(diffusivity_multiplier)
        * arrhenius_factor(knobs, temperature_K)
        * knobs.solvent_concentration_mol_m3
        / knobs.lithium_per_sei_mole
    )


def thickness_m(
    knobs: SeiKnobs,
    time_s: float,
    temperature_K: float,
    diffusivity_multiplier: float = 1.0,
    initial_thickness_m: float | None = None,
) -> float:
    """Closed form of L dL = k dt. L = sqrt(L_start^2 + 2 k t)."""
    start = knobs.initial_thickness_m if initial_thickness_m is None else float(initial_thickness_m)
    rate = growth_constant_m2_s(knobs, temperature_K, diffusivity_multiplier)
    return float(np.sqrt(start**2 + 2.0 * rate * float(time_s)))


def lithium_per_area_mol_m2(knobs: SeiKnobs, grown_thickness_m: float) -> float:
    """Lithium locked in the film that grew past the initial thickness.

    integral of (-j / F) dt = z * (L - L_start) / V_bar.
    The initial film is already in the formed cell. Only the growth after
    t = 0 is new loss.
    """
    if grown_thickness_m < 0.0:
        raise ValueError("grown thickness cannot be negative")
    return (
        knobs.lithium_per_sei_mole
        * float(grown_thickness_m)
        / knobs.partial_molar_volume_m3_mol
    )


def capacity_loss_Ah(lithium_mol: float) -> float:
    """Faraday's law: ampere-hours are moles times F, per 3600 seconds."""
    return float(lithium_mol) * FARADAY / 3600.0


def storage_loss(
    knobs: SeiKnobs,
    time_s: float,
    temperature_K: float,
    interfacial_area_m2: float,
    diffusivity_multiplier: float = 1.0,
) -> dict[str, float]:
    """Film on open circuit. No cycling, so the closed form is the whole model."""
    thickness = thickness_m(knobs, time_s, temperature_K, diffusivity_multiplier)
    grown = thickness - knobs.initial_thickness_m
    per_area = lithium_per_area_mol_m2(knobs, grown)
    moles = per_area * float(interfacial_area_m2)
    return {
        "thickness_m": thickness,
        "grown_m": grown,
        "lithium_mol": moles,
        "loss_Ah": capacity_loss_Ah(moles),
    }
