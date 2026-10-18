"""PyBaMM imports, steps, and shows the same plating trend.

Two full charges is enough. The figure script runs the rest.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cell import cell_from_params
from common.params import load_params
from common.units import celsius_to_kelvin
from pybamm_check import plated_lithium_Ah, smoke_solve
from spm import discharged_state

BOOK = load_params(
    Path(__file__).resolve().parents[1] / "01-lunar-night-battery" / "params.yaml"
)


def test_smoke_solve_returns_a_sensible_voltage():
    voltage = smoke_solve()
    assert 2.5 < voltage < 4.2


def test_pybamm_plating_increases_as_temperature_falls():
    cell = cell_from_params(BOOK)
    empty_negative, empty_positive = discharged_state(cell, 0.2, cell.reference_temperature_K)
    warm = plated_lithium_Ah(
        celsius_to_kelvin(25.0), 1.0, empty_negative, empty_positive
    )
    cold = plated_lithium_Ah(
        celsius_to_kelvin(-20.0), 1.0, empty_negative, empty_positive
    )
    assert cold.plated_Ah > warm.plated_Ah


def test_our_arrhenius_matches_the_pybamm_parameter_functions():
    """Catch a typo in the copied activation energies.

    The comparison is against PyBaMM 25.8's own functions, which is where the
    digits were taken from. It does not re-derive Ecker or Cabanero.
    """
    import pybamm

    cell = cell_from_params(BOOK)
    parameters = pybamm.ParameterValues("OKane2022")
    for temperature in (253.15, 298.15):
        theirs = float(
            parameters.evaluate(
                parameters["Negative particle diffusivity [m2.s-1]"](0.5, temperature)
            )
        )
        assert cell.diffusivity_negative(temperature) == pytest.approx(theirs, rel=1e-6)
        theirs_positive = float(
            parameters.evaluate(
                parameters["Positive particle diffusivity [m2.s-1]"](0.5, temperature)
            )
        )
        assert cell.diffusivity_positive(temperature) == pytest.approx(theirs_positive, rel=1e-6)
