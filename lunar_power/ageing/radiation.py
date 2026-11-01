"""Radiation is a label on the concept chart, not a term in the fade rate.

Ratnakumar et al. (J. Electrochem. Soc., 2004) irradiated aerospace lithium-ion
cells to cumulative doses up to 25 Mrad. Their abstract reports only a
marginal capacity decline and no significant change in the later fade rate,
and they note that study had no unirradiated control. An electric vehicle does
not see that dose. This module does not turn grays into a capacity loss.

The assumption sweep is a set of solvent-diffusivity multipliers. They are
drawn on the concept chart so the range is visible. The fade curves and the
feed into the cold model call the film model with multiplier 1.
"""

from __future__ import annotations

from common.params import Entry, require

# The fade charts and the cold-model feed use this. It is not a dose.
FADE_DIFFUSIVITY_MULTIPLIER = 1.0


def assumption_multipliers(book: dict[str, Entry]) -> list[float]:
    """The swept 'what if the film's diffusivity were scaled' factors."""
    values = [float(item) for item in require(book, "radiation_diffusivity_multipliers").value]
    if not values or any(item <= 0.0 for item in values):
        raise ValueError("radiation multipliers must be positive")
    return values


def paper_doses_Mrad(book: dict[str, Entry]) -> dict[str, float]:
    """Doses quoted from the 2004 paper, for the diagram, not for a rate."""
    return {
        "mission_context_Mrad": float(require(book, "radiation_paper_mission_dose_Mrad").value),
        "experiment_upper_Mrad": float(require(book, "radiation_paper_upper_dose_Mrad").value),
    }
