"""Front door for the November model.

The template for this repository lists a ``model.py``. The work is split so
each file is one idea, and this module is the map:

* ``cell.py`` holds the published LG M50 numbers and the Arrhenius, Ohm and
  open-circuit functions.
* ``spm.py`` is our single-particle model and the 0 V plating criterion.
* ``thermal.py`` is the lunar-night energy balance.
* ``pybamm_check.py`` runs the Doyle-Fuller-Newman cross-check.
* ``make_figures.py`` draws charts A to D.
* ``run_all.py`` is the command that regenerates the PNGs.

Read ``EXPLAINED.md`` for the derivation. Read ``params.yaml`` for every input.
"""

from cell import Cell, cell_from_params
from spm import discharged_state, lithium_inventory_mol, simulate
from thermal import (
    battery_mass_kg,
    radiative_conductance_W_per_K,
    simulate_night,
    steady_heater_energy_Wh,
    steady_heater_power_W,
)

__all__ = [
    "Cell",
    "battery_mass_kg",
    "cell_from_params",
    "discharged_state",
    "lithium_inventory_mol",
    "radiative_conductance_W_per_K",
    "simulate",
    "simulate_night",
    "steady_heater_energy_Wh",
    "steady_heater_power_W",
]
