"""November electrochemistry: one particle per electrode, and a 0 V plating rule.

PyBaMM's Doyle–Fuller–Newman model is the cross-check in ``pybamm_check``.
The ageing layer can hand this package a cell whose inventory and film
resistance have already changed. It does not otherwise alter these equations.
"""

from lunar_power.electrochemistry.cell import Cell, cell_from_params
from lunar_power.electrochemistry.spm import (
    discharged_state,
    lithium_inventory_mol,
    simulate,
)

__all__ = [
    "Cell",
    "cell_from_params",
    "discharged_state",
    "lithium_inventory_mol",
    "simulate",
]
