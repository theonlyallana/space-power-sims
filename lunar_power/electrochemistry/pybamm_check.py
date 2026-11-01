"""PyBaMM as a second opinion, not as the model we derived.

Our single-particle model drops electrolyte diffusion and uses one particle
per electrode, and it plates with a hard 0 V switch. PyBaMM's
Doyle-Fuller-Newman model keeps the electrolyte equation and a
through-the-electrode reaction distribution, and its irreversible plating
model is a Butler-Volmer reaction. Where the two agree, the shortcut was
cheap. Where they do not, the figure shows the gap instead of hiding it.

Telemetry is switched off before PyBaMM is imported. The first import
otherwise asks a question on stdin, which would hang a test run.
"""

from __future__ import annotations

import os

os.environ["PYBAMM_DISABLE_TELEMETRY"] = "1"

from dataclasses import dataclass

import numpy as np

from common.units import trapz


@dataclass
class PybammCurve:
    time_s: np.ndarray
    voltage_V: np.ndarray
    capacity_Ah: np.ndarray
    throughput_Ah: float
    plated_Ah: float
    energy_Wh: float


def _library():
    import pybamm

    return pybamm


def _solve(experiment: str, temperature_K: float, negative_mol_m3: float, positive_mol_m3: float, plating: str) -> PybammCurve:
    pybamm = _library()
    model = pybamm.lithium_ion.DFN(
        {"lithium plating": plating, "thermal": "isothermal"}
    )
    parameters = pybamm.ParameterValues("OKane2022")
    parameters.update(
        {
            "Ambient temperature [K]": temperature_K,
            "Initial temperature [K]": temperature_K,
            "Initial concentration in negative electrode [mol.m-3]": negative_mol_m3,
            "Initial concentration in positive electrode [mol.m-3]": positive_mol_m3,
        }
    )
    simulation = pybamm.Simulation(
        model,
        parameter_values=parameters,
        experiment=pybamm.Experiment([experiment]),
        solver=pybamm.IDAKLUSolver(),
    )
    solution = simulation.solve()
    time_s = np.asarray(solution.t, dtype=float)
    voltage = np.asarray(solution["Terminal voltage [V]"].entries, dtype=float)
    current = np.asarray(solution["Current [A]"].entries, dtype=float)
    plated = 0.0
    if plating != "none":
        plated = float(solution["Loss of capacity to negative lithium plating [A.h]"].entries[-1])
    # Capacity has to follow the clock, not the solver's step index. After the
    # electrolyte empties, IDAKLU takes many tiny steps at nearly constant
    # voltage. Spacing those steps evenly in ampere-hours draws a plateau the
    # cell never had.
    step_ah = 0.5 * np.diff(time_s) * (np.abs(current[1:]) + np.abs(current[:-1])) / 3600.0
    capacity_Ah = np.concatenate([[0.0], np.cumsum(step_ah)])
    throughput = float(capacity_Ah[-1]) if len(capacity_Ah) else 0.0
    # Discharge current is positive in PyBaMM, so this integral is positive
    # for a discharge and negative for a charge. Callers that want delivered
    # energy use the discharge runs.
    energy_Wh = trapz(voltage * current, time_s) / 3600.0
    return PybammCurve(
        time_s=time_s,
        voltage_V=voltage,
        capacity_Ah=capacity_Ah,
        throughput_Ah=throughput,
        plated_Ah=plated,
        energy_Wh=energy_Wh,
    )


def plated_lithium_Ah(
    temperature_K: float,
    c_rate: float,
    negative_mol_m3: float,
    positive_mol_m3: float,
) -> PybammCurve:
    """Constant-current charge to 4.2 V with irreversible plating."""
    rate = _format_rate(c_rate)
    return _solve(
        f"Charge at {rate} until 4.2 V",
        temperature_K,
        negative_mol_m3,
        positive_mol_m3,
        plating="irreversible",
    )


def discharge_curve(
    temperature_K: float,
    c_rate: float,
    negative_mol_m3: float,
    positive_mol_m3: float,
) -> PybammCurve:
    """Isothermal discharge. Plating is off: this chart is about resistance."""
    rate = _format_rate(c_rate)
    return _solve(
        f"Discharge at {rate} until 2.5 V",
        temperature_K,
        negative_mol_m3,
        positive_mol_m3,
        plating="none",
    )


def smoke_solve() -> float:
    """One short solve, so CI knows the library imports and runs.

    Ten seconds of discharge does not produce a chart. It only checks that
    the pinned PyBaMM build can build a model and step it.
    """
    curve = _solve(
        "Discharge at 1C for 10 seconds",
        298.15,
        29866.0,
        17038.0,
        plating="none",
    )
    if len(curve.time_s) < 2:
        raise RuntimeError("PyBaMM smoke solve returned no time steps")
    return float(curve.voltage_V[-1])


def _format_rate(c_rate: float) -> str:
    """PyBaMM accepts '1C' and '0.5C'. Avoid binary-float noise in the string."""
    text = f"{c_rate:.3f}".rstrip("0").rstrip(".")
    return f"{text}C"
