"""November thermal layer: one battery mass through a lunar night.

The energy balance does not know about electrochemistry. The scenario runner
is what scales the stored watt-hours by the capacity the ageing layer has left.
"""

from lunar_power.thermal.night import (
    battery_mass_kg,
    conservation_residual_J,
    ingenuity_specific_energy_Wh_per_kg,
    radiative_conductance_W_per_K,
    simulate_night,
    steady_heater_energy_Wh,
    steady_heater_power_W,
)

__all__ = [
    "battery_mass_kg",
    "conservation_residual_J",
    "ingenuity_specific_energy_Wh_per_kg",
    "radiative_conductance_W_per_K",
    "simulate_night",
    "steady_heater_energy_Wh",
    "steady_heater_power_W",
]
