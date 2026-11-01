"""Lumped thermal model of a battery sitting out a lunar night.

The electrochemical model answers what the cell does at a given temperature.
This file answers a different question: what does it cost, in stored
watt-hours, to stay at that temperature until sunrise?

Control volume: the cells and a heater bonded to them, inside the insulation.
Radioisotope heater units, if any, also dump their heat inside that volume.
Vacuum outside means the leak is conduction through the insulation and
radiation, not air.

Energy balance, with mass and specific heat taken as constant::

    m c dT/dt = P_heater + P_RHU - G (T - T_env)

The heater is inside the insulation, so the electrical energy it draws from
the cells comes back as heat in the same control volume. Adding I^2 R on top
would count that heat twice. I^2 R matters in the cell model, where the
question is the voltage under load. It is not a second source here.

Hibernation, as NASA Glenn describes it, opens the battery and leaves it
alone. Then P_heater is zero and the state of charge does not move.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from common.constants import STEFAN_BOLTZMANN
from common.units import celsius_to_kelvin, joules_to_watt_hours, kelvin_to_celsius, trapz


@dataclass
class NightResult:
    """Temperature and state of charge through one night."""

    time_s: np.ndarray
    temperature_K: np.ndarray
    stored_energy_J: np.ndarray
    heater_power_W: np.ndarray
    strategy: str

    @property
    def time_h(self) -> np.ndarray:
        return self.time_s / 3600.0

    @property
    def temperature_C(self) -> np.ndarray:
        return self.temperature_K - 273.15

    @property
    def state_of_charge(self) -> np.ndarray:
        initial = self.stored_energy_J[0]
        if initial <= 0.0:
            return np.zeros_like(self.stored_energy_J)
        return self.stored_energy_J / initial

    @property
    def heater_energy_Wh(self) -> float:
        return joules_to_watt_hours(trapz(self.heater_power_W, self.time_s))


def steady_heater_power_W(
    conductance_W_per_K: float,
    setpoint_K: float,
    sink_K: float,
    radioisotope_power_W: float,
) -> float:
    """Power that holds the setpoint forever.

    At steady state the time derivative is zero, so the heater makes up the
    difference between the leak and any radioisotope heat. Below a small
    enough conductance the radioisotope unit covers the leak and the heater
    is off. Halving the conductance halves this power when the radioisotope
    term is zero, which is the chart C statement.
    """
    leak = conductance_W_per_K * (setpoint_K - sink_K)
    return float(max(0.0, leak - radioisotope_power_W))


def steady_heater_energy_Wh(
    conductance_W_per_K: float,
    setpoint_K: float,
    sink_K: float,
    radioisotope_power_W: float,
    duration_h: float,
) -> float:
    """Hold the setpoint for the whole night. This ignores the free cooldown.

    Chart C uses this on purpose. It is heat leak times time, which is the
    scaling the post wants to show. Chart D integrates the transient, including
    the hours spent cooling from the sunset temperature down to the setpoint.
    """
    return steady_heater_power_W(
        conductance_W_per_K, setpoint_K, sink_K, radioisotope_power_W
    ) * duration_h


def radiative_conductance_W_per_K(
    emissivity: float,
    area_m2: float,
    temperature_K: float,
    sink_K: float,
) -> float:
    """Linear conductance that matches Stefan-Boltzmann at one temperature.

    sigma epsilon A (T^4 - T_sink^4) = G (T - T_sink), with
    G = sigma epsilon A (T^2 + T_sink^2) (T + T_sink).
    G is not a property of the insulation alone: it depends on the two
    temperatures. The sweep on chart C treats G as constant, which is the
    right picture for conduction through a blanket and only an approximation
    for radiation.
    """
    return float(
        STEFAN_BOLTZMANN
        * emissivity
        * area_m2
        * (temperature_K**2 + sink_K**2)
        * (temperature_K + sink_K)
    )


def battery_mass_kg(heater_energy_Wh: float, specific_energy_Wh_per_kg: float) -> float:
    """Cell mass whose stored energy equals the heater energy.

    This is cell mass, not a packaged battery. Structure, a management system
    and the insulation itself are extra, and they do not appear in this number.
    """
    if specific_energy_Wh_per_kg <= 0.0:
        raise ValueError("specific energy must be positive")
    return float(heater_energy_Wh / specific_energy_Wh_per_kg)


def ingenuity_specific_energy_Wh_per_kg(pack_energy_Wh: float, cell_mass_g: float, cell_count: int) -> float:
    """Divide two published Ingenuity numbers. NASA does not quote Wh/kg."""
    mass_kg = cell_count * cell_mass_g / 1000.0
    return float(pack_energy_Wh / mass_kg)


def _sample(solution, count: int = 240) -> tuple[np.ndarray, np.ndarray]:
    start, end = float(solution.t[0]), float(solution.t[-1])
    if end <= start:
        return solution.t, solution.y
    times = np.linspace(start, end, count)
    return times, solution.sol(times)


def simulate_night(
    *,
    strategy: str,
    mass_kg: float,
    specific_heat_J_per_kg_K: float,
    conductance_W_per_K: float,
    sink_K: float,
    setpoint_K: float,
    start_K: float,
    stored_energy_J: float,
    radioisotope_power_W: float,
    duration_s: float,
) -> NightResult:
    """Integrate one night.

    Keep-warm has three pieces, because an ideal thermostat is a switch and
    switches make an adaptive solver take tiny steps if you leave them inside
    one right-hand side:

    1. Heater off, cool from the sunset temperature down to the setpoint.
    2. Heater on at exactly the balance power, temperature pinned, stored
       energy falling in a straight line, until the energy is gone or the
       Sun is back.
    3. Heater off again, cool towards the sink.

    Hibernate is only piece 1, run all the way to sunrise. NASA's description
    is that the battery is disconnected, so piece 2 never happens.
    """
    if strategy not in ("keep_warm", "hibernate"):
        raise ValueError("strategy must be 'keep_warm' or 'hibernate'")
    thermal_mass = mass_kg * specific_heat_J_per_kg_K
    if thermal_mass <= 0.0:
        raise ValueError("thermal mass must be positive")

    def cooling(_time: float, state: np.ndarray) -> list[float]:
        temperature = state[0]
        leak = conductance_W_per_K * (temperature - sink_K)
        return [(radioisotope_power_W - leak) / thermal_mass, 0.0]

    def holding(_time: float, state: np.ndarray) -> list[float]:
        # Temperature is pinned by the caller (the derivative is zero). The
        # power is the steady balance, and it stops being available the
        # instant the stored energy hits zero.
        balance = steady_heater_power_W(
            conductance_W_per_K, setpoint_K, sink_K, radioisotope_power_W
        )
        power = balance if state[1] > 0.0 else 0.0
        return [0.0, -power]

    pieces_t: list[np.ndarray] = []
    pieces_T: list[np.ndarray] = []
    pieces_E: list[np.ndarray] = []
    pieces_P: list[np.ndarray] = []

    def append(times, temperatures, energies, powers) -> None:
        # Keep the shared timestamp. Dropping it would make the trapezium
        # rule average the heater power across the switch, and the integral
        # would miss about half of the first hold step. A repeated time
        # contributes nothing to the integral and records the switch cleanly.
        if len(times) == 0:
            return
        pieces_t.append(np.asarray(times, dtype=float))
        pieces_T.append(np.asarray(temperatures, dtype=float))
        pieces_E.append(np.asarray(energies, dtype=float))
        pieces_P.append(np.asarray(powers, dtype=float))

    time = 0.0
    temperature = start_K
    energy = stored_energy_J

    def reached_setpoint(_time: float, state: np.ndarray) -> float:
        return state[0] - setpoint_K

    reached_setpoint.terminal = True
    reached_setpoint.direction = -1.0

    def energy_gone(_time: float, state: np.ndarray) -> float:
        return state[1]

    energy_gone.terminal = True
    energy_gone.direction = -1.0

    if strategy == "keep_warm" and temperature > setpoint_K and time < duration_s:
        solution = solve_ivp(
            cooling,
            (time, duration_s),
            [temperature, energy],
            method="RK45",
            rtol=1e-7,
            atol=1e-8,
            events=[reached_setpoint],
            dense_output=True,
        )
        times, values = _sample(solution)
        append(times, values[0], values[1], np.zeros_like(times))
        time = float(solution.t[-1])
        temperature = float(solution.y[0, -1])
        energy = float(solution.y[1, -1])

    if strategy == "keep_warm" and temperature <= setpoint_K + 1e-6 and energy > 0.0 and time < duration_s:
        balance = steady_heater_power_W(
            conductance_W_per_K, setpoint_K, sink_K, radioisotope_power_W
        )
        if balance > 0.0:
            solution = solve_ivp(
                holding,
                (time, duration_s),
                [setpoint_K, energy],
                method="RK45",
                rtol=1e-7,
                atol=1e-6,
                events=[energy_gone],
                dense_output=True,
            )
            times, values = _sample(solution, count=80)
            append(times, np.full_like(times, setpoint_K), values[1], np.full_like(times, balance))
            time = float(solution.t[-1])
            temperature = setpoint_K
            energy = max(0.0, float(solution.y[1, -1]))

    if time < duration_s - 1.0:
        solution = solve_ivp(
            cooling,
            (time, duration_s),
            [temperature, energy],
            method="RK45",
            rtol=1e-7,
            atol=1e-8,
            dense_output=True,
        )
        times, values = _sample(solution)
        append(times, values[0], values[1], np.zeros_like(times))

    return NightResult(
        time_s=np.concatenate(pieces_t),
        temperature_K=np.concatenate(pieces_T),
        stored_energy_J=np.concatenate(pieces_E),
        heater_power_W=np.concatenate(pieces_P),
        strategy=strategy,
    )


def conservation_residual_J(result: NightResult, *, mass_kg: float, specific_heat: float, conductance: float, sink_K: float, radioisotope_power_W: float) -> float:
    """Left-hand side minus right-hand side of the energy balance, in joules.

    Integrated over the night, m c (T_end - T_start) should equal the integral
    of heater power plus radioisotope power minus the leak. A small residual
    is the integrator's tolerance plus the trapezium rule on the samples.
    """
    thermal_mass = mass_kg * specific_heat
    stored = thermal_mass * (result.temperature_K[-1] - result.temperature_K[0])
    leak = conductance * (result.temperature_K - sink_K)
    supplied = trapz(result.heater_power_W + radioisotope_power_W - leak, result.time_s)
    return float(stored - supplied)


def setpoint_kelvin(setpoint_C: float) -> float:
    return celsius_to_kelvin(setpoint_C)


def temperature_celsius(temperature_K: float) -> float:
    return kelvin_to_celsius(temperature_K)
