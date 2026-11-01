"""PyBaMM's solvent-diffusion-limited film, as a cross-check and a cache.

Our film model is the closed form of the same rate PyBaMM integrates on a
rest. The cache holds a handful of rests so the figure can mark those points
without solving again. A one-hour rest is cheap enough that a test solves it
live and compares.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("PYBAMM_DISABLE_TELEMETRY", "1")

CACHE_PATH = Path(__file__).resolve().parent / "sei_cache.json"


def _solve_rest(temperature_K: float, hours: float) -> dict[str, float]:
    import pybamm

    model = pybamm.lithium_ion.SPM({"SEI": "solvent-diffusion limited"})
    parameters = pybamm.ParameterValues("OKane2022")
    parameters.update(
        {
            "Ambient temperature [K]": temperature_K,
            "Initial temperature [K]": temperature_K,
        }
    )
    # Integer hours keep the experiment string free of binary-float noise.
    experiment = pybamm.Experiment([f"Rest for {hours:g} hours"])
    simulation = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment)
    solution = simulation.solve()
    thickness = solution["X-averaged negative SEI thickness [m]"].entries
    loss_mol = solution["Loss of lithium to negative SEI [mol]"].entries
    loss_Ah = solution["Loss of capacity to negative SEI [A.h]"].entries
    return {
        "temperature_K": float(temperature_K),
        "hours": float(hours),
        "time_s": float(solution.t[-1]),
        "thickness_m": float(thickness[-1]),
        "loss_mol": float(loss_mol[-1]),
        "loss_Ah": float(loss_Ah[-1]),
    }


def smoke_thickness_m() -> float:
    """Ten minutes of rest. CI uses this to see that the SEI option runs."""
    import pybamm

    model = pybamm.lithium_ion.SPM({"SEI": "solvent-diffusion limited"})
    parameters = pybamm.ParameterValues("OKane2022")
    parameters.update({"Ambient temperature [K]": 298.15, "Initial temperature [K]": 298.15})
    simulation = pybamm.Simulation(
        model,
        parameter_values=parameters,
        experiment=pybamm.Experiment(["Rest for 10 minutes"]),
    )
    solution = simulation.solve()
    thickness = float(solution["X-averaged negative SEI thickness [m]"].entries[-1])
    if thickness <= 0.0:
        raise RuntimeError("PyBaMM SEI smoke solve returned no thickness")
    return thickness


def build_cache(path: Path = CACHE_PATH) -> dict:
    """Rests used as markers on the film-growth chart. Not a mission profile."""
    points = []
    for temperature_K in (273.15, 298.15):
        for hours in (1.0, 4.0, 24.0, 72.0):
            points.append(_solve_rest(temperature_K, hours))
    payload = {
        "model": "SPM",
        "sei_option": "solvent-diffusion limited",
        "parameter_set": "OKane2022",
        "pybamm": "25.8.0",
        "experiment": "Rest",
        "points": points,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def load_cache(path: Path = CACHE_PATH) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} is missing. Regenerate it with lunar_power.ageing.pybamm_sei.build_cache"
        )
    return json.loads(path.read_text())
