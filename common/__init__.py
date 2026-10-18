"""Shared pieces for the space-power simulations.

The months share three things: physical constants, a reader for ``params.yaml``,
and a plotting style. Electrochemistry for a particular month stays in that
month's folder. Nothing in here is specific to an employer or a programme.
"""

from common.constants import BOLTZMANN, FARADAY, GAS, STEFAN_BOLTZMANN
from common.params import Entry, load_params

__all__ = [
    "BOLTZMANN",
    "Entry",
    "FARADAY",
    "GAS",
    "STEFAN_BOLTZMANN",
    "load_params",
]
