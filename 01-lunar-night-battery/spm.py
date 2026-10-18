"""A single-particle cell with a 0 V plating criterion.

This is the model we can derive on a whiteboard. PyBaMM's Doyle-Fuller-Newman
model is the cross-check, not the thing we ask a reader to trust unseen.

State
-----
* Concentration in each spherical shell of one graphite particle.
* The same for one NMC particle.
* Moles of metallic lithium plated on the graphite.

Why one particle per electrode: if the solid conducts well and the electrolyte
concentration stays roughly uniform, every particle in an electrode sees the
same surroundings. The Doyle-Fuller-Newman model drops both of those
assumptions. We keep them, and we show PyBaMM beside us so the cost of the
shortcut is visible.

Sign convention
---------------
Positive current means the cell is discharging: lithium leaves the graphite
and enters the NMC. Charging is a negative discharge current.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from cell import Cell
from common.constants import FARADAY, GAS
from common.units import trapz


@dataclass
class Trajectory:
    """One constant-current charge or discharge."""

    time_s: np.ndarray
    voltage_V: np.ndarray
    current_A: float
    throughput_Ah: np.ndarray
    plated_Ah: np.ndarray
    anode_potential_V: np.ndarray
    energy_Wh: float
    negative_average_mol_m3: float
    positive_average_mol_m3: float
    plated_mol: float
    message: str


@dataclass
class _Shells:
    centers: np.ndarray
    volumes: np.ndarray
    face_areas: np.ndarray


def _shells(radius_m: float, count: int) -> _Shells:
    """Equal radial shells. The outer shell is the one the reaction sees."""
    edges = np.linspace(0.0, radius_m, count + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    volumes = (4.0 / 3.0) * np.pi * (edges[1:] ** 3 - edges[:-1] ** 3)
    face_areas = 4.0 * np.pi * edges**2
    return _Shells(centers=centers, volumes=volumes, face_areas=face_areas)


def _exp_clip(value: float) -> float:
    """The Butler-Volmer exponential overflows long before it matters.

    40 is about exp(40) ~ 2.6e17, already far past any current this cell can
    pass. Clipping keeps a wild Newton step from producing NaN.
    """
    return float(np.exp(np.clip(value, -40.0, 40.0)))


def _butler_volmer(overpotential_V: float, exchange_current: float, alpha: float, temperature_K: float) -> tuple[float, float]:
    """Interfacial current and its derivative with respect to potential.

    j = j0 * (exp(alpha F eta / RT) - exp(-(1-alpha) F eta / RT)).
    Positive j is anodic: lithium leaving the particle.
    """
    factor = FARADAY / (GAS * temperature_K)
    anodic = alpha * factor * overpotential_V
    cathodic = -(1.0 - alpha) * factor * overpotential_V
    forward = _exp_clip(anodic)
    backward = _exp_clip(cathodic)
    current = exchange_current * (forward - backward)
    derivative = exchange_current * (
        alpha * factor * forward + (1.0 - alpha) * factor * backward
    )
    return current, derivative


def _solve_intercalation_potential(
    applied_A_m2: float,
    open_circuit_V: float,
    exchange_current: float,
    alpha: float,
    temperature_K: float,
    guess_V: float,
) -> float:
    """Find the solid-vs-electrolyte potential that passes a set current.

    Newton is enough because Butler-Volmer current rises monotonically with
    potential, so there is one root. The step is capped so a bad guess cannot
    jump into the exponential overflow.
    """
    potential = guess_V
    for _ in range(20):
        overpotential = potential - open_circuit_V
        current, derivative = _butler_volmer(
            overpotential, exchange_current, alpha, temperature_K
        )
        residual = current - applied_A_m2
        if abs(residual) < 1e-8 * max(1.0, abs(applied_A_m2)):
            return potential
        step = residual / max(derivative, 1e-16)
        potential -= float(np.clip(step, -0.25, 0.25))
    return potential


def _anode_split(
    applied_A_m2: float,
    open_circuit_V: float,
    exchange_current: float,
    alpha: float,
    temperature_K: float,
    guess_V: float,
) -> tuple[float, float, float]:
    """Split the anode current into intercalation and plating.

    First ask what potential intercalation alone would need. If that potential
    is still above 0 V vs Li/Li+, no metal is deposited: the ions fit into the
    graphite. If intercalation alone would need a potential below 0 V, we pin
    the surface at 0 V and send the leftover current into plating. That is a
    switch, not a second Butler-Volmer reaction. PyBaMM integrates the
    plating kinetics properly and will not match this milliamps-for-milliamps.
    The switch is here because it makes the 0 V criterion obvious.
    """
    potential = _solve_intercalation_potential(
        applied_A_m2, open_circuit_V, exchange_current, alpha, temperature_K, guess_V
    )
    if potential >= 0.0:
        return potential, applied_A_m2, 0.0

    intercalation, _ = _butler_volmer(
        0.0 - open_circuit_V, exchange_current, alpha, temperature_K
    )
    plated = applied_A_m2 - intercalation
    # Plating is a reduction. A positive leftover would mean the surface at
    # 0 V already wants to give lithium up, which is not plating.
    if plated > 0.0:
        return potential, applied_A_m2, 0.0
    return 0.0, intercalation, plated


def _particle_rates(
    concentration: np.ndarray,
    shells: _Shells,
    diffusivity: float,
    surface_current_A_m2: float,
) -> np.ndarray:
    """Fick's law on the shells. The surface flux is the reaction, not a ghost.

    Moles in a shell change because of what diffuses through its two faces.
    The outer face of the outer shell is the reaction: molar flux out of the
    particle is j/F. A negative (charging) current on the anode pushes lithium
    in.
    """
    count = len(concentration)
    outward = np.empty(count)
    for index in range(count - 1):
        gap = shells.centers[index + 1] - shells.centers[index]
        outward[index] = -diffusivity * (concentration[index + 1] - concentration[index]) / gap
    outward[-1] = surface_current_A_m2 / FARADAY

    rates = np.empty(count)
    for index in range(count):
        inward_flux = 0.0 if index == 0 else outward[index - 1]
        inward_area = 0.0 if index == 0 else shells.face_areas[index]
        outward_area = shells.face_areas[index + 1]
        rates[index] = (inward_area * inward_flux - outward_area * outward[index]) / shells.volumes[index]
    return rates


def _volume_average(concentration: np.ndarray, shells: _Shells) -> float:
    """Outer shells hold more material. An unweighted mean would bias the surface."""
    return float(np.sum(concentration * shells.volumes) / np.sum(shells.volumes))


def simulate(
    cell: Cell,
    temperature_K: float,
    c_rate: float,
    direction: str,
    negative_concentration: float,
    positive_concentration: float,
    duration_s: float | None = None,
) -> Trajectory:
    """Constant-current run until a voltage limit or ``duration_s``.

    ``direction`` is ``"discharge"`` or ``"charge"``. The C-rate is always
    positive and is defined on the nameplate capacity.
    """
    if direction not in ("discharge", "charge"):
        raise ValueError("direction must be 'discharge' or 'charge'")
    sign = 1.0 if direction == "discharge" else -1.0
    current_A = sign * c_rate * cell.nominal_capacity_Ah
    if duration_s is None:
        # A little longer than a full nameplate swing, so the voltage limit
        # is what actually stops a healthy cell.
        duration_s = 1.25 * 3600.0 / c_rate

    negative_shells = _shells(cell.negative_radius_m, cell.shell_count)
    positive_shells = _shells(cell.positive_radius_m, cell.shell_count)
    count = cell.shell_count
    guess = {
        "negative": cell.open_circuit_negative(negative_concentration / cell.cmax_negative),
        "positive": cell.open_circuit_positive(positive_concentration / cell.cmax_positive),
    }

    def split(negative: np.ndarray, positive: np.ndarray) -> tuple[float, float, float, float]:
        applied_negative = current_A / cell.negative_surface_area_m2
        applied_positive = -current_A / cell.positive_surface_area_m2
        surface_negative = float(negative[-1])
        surface_positive = float(positive[-1])
        open_negative = cell.open_circuit_negative(surface_negative / cell.cmax_negative)
        open_positive = cell.open_circuit_positive(surface_positive / cell.cmax_positive)
        phi_n, intercalation, plated = _anode_split(
            applied_negative,
            open_negative,
            cell.exchange_current_negative(surface_negative, temperature_K),
            cell.alpha,
            temperature_K,
            guess["negative"],
        )
        phi_p = _solve_intercalation_potential(
            applied_positive,
            open_positive,
            cell.exchange_current_positive(surface_positive, temperature_K),
            cell.alpha,
            temperature_K,
            guess["positive"],
        )
        guess["negative"] = phi_n
        guess["positive"] = phi_p
        # phi is solid minus local electrolyte. Electrolyte ohmic drop makes
        # the positive end of the cell lower during discharge.
        voltage = phi_p - phi_n - current_A * cell.ohmic_resistance(temperature_K)
        return voltage, phi_n, intercalation, plated

    def rhs(_time: float, state: np.ndarray) -> np.ndarray:
        negative = state[:count]
        positive = state[count : 2 * count]
        _voltage, _phi, intercalation, plated = split(negative, positive)
        d_negative = _particle_rates(
            negative, negative_shells, cell.diffusivity_negative(temperature_K), intercalation
        )
        # The cathode has no plating reaction, so the whole cell current
        # enters or leaves the NMC particle.
        d_positive = _particle_rates(
            positive,
            positive_shells,
            cell.diffusivity_positive(temperature_K),
            -current_A / cell.positive_surface_area_m2,
        )
        # plated current is negative when metal is depositing, so the minus
        # sign stores a positive mole count.
        d_plated_mol = -plated * cell.negative_surface_area_m2 / FARADAY
        return np.concatenate([d_negative, d_positive, [d_plated_mol]])

    def hit_lower(time: float, state: np.ndarray) -> float:
        # A zero at the first instant would stop the run before it starts.
        # The rested empty cell sits near the lower cut-off, so this guard
        # matters for the charge that follows a discharge.
        if time <= 1e-8:
            return 1.0
        voltage, *_rest = split(state[:count], state[count : 2 * count])
        return voltage - cell.voltage_min_V

    def hit_upper(time: float, state: np.ndarray) -> float:
        if time <= 1e-8:
            return 1.0
        voltage, *_rest = split(state[:count], state[count : 2 * count])
        return cell.voltage_max_V - voltage

    hit_lower.terminal = True
    hit_lower.direction = -1
    hit_upper.terminal = True
    hit_upper.direction = -1

    initial = np.concatenate(
        [
            np.full(count, negative_concentration),
            np.full(count, positive_concentration),
            [0.0],
        ]
    )
    solution = solve_ivp(
        rhs,
        (0.0, duration_s),
        initial,
        method="BDF",
        rtol=cell.relative_tolerance,
        atol=cell.absolute_tolerance,
        events=[hit_lower, hit_upper],
        max_step=30.0,
    )

    voltages = []
    anode_potentials = []
    for state in solution.y.T:
        voltage, phi_n, _intercalation, _plated = split(state[:count], state[count : 2 * count])
        voltages.append(voltage)
        anode_potentials.append(phi_n)
    time_s = solution.t
    voltage_V = np.asarray(voltages, dtype=float)
    plated_mol_series = solution.y[-1]
    plated_Ah = plated_mol_series * FARADAY / 3600.0
    throughput_Ah = np.abs(current_A) * time_s / 3600.0
    energy_Wh = trapz(voltage_V * current_A, time_s) / 3600.0 if len(time_s) > 1 else 0.0
    final = solution.y[:, -1]
    return Trajectory(
        time_s=time_s,
        voltage_V=voltage_V,
        current_A=current_A,
        throughput_Ah=throughput_Ah,
        plated_Ah=plated_Ah,
        anode_potential_V=np.asarray(anode_potentials, dtype=float),
        energy_Wh=energy_Wh,
        negative_average_mol_m3=_volume_average(final[:count], negative_shells),
        positive_average_mol_m3=_volume_average(final[count : 2 * count], positive_shells),
        plated_mol=float(final[-1]),
        message=solution.message,
    )


def discharged_state(cell: Cell, c_rate: float, temperature_K: float) -> tuple[float, float]:
    """Uniform concentrations after a slow discharge to the lower cut-off.

    The charge study has to start from the same state at every temperature.
    A slow discharge at 25 C, then replacing the particle profile by its
    volume average, is a rested empty cell. Starting from the published full
    concentrations would be charging a cell that is already full.
    """
    result = simulate(
        cell,
        temperature_K,
        c_rate,
        "discharge",
        cell.initial_negative,
        cell.initial_positive,
    )
    return result.negative_average_mol_m3, result.positive_average_mol_m3


def lithium_inventory_mol(cell: Cell, negative: float, positive: float, plated_mol: float) -> float:
    """Graphite plus NMC plus plated metal. Charge conservation says this is fixed."""
    return (
        cell.electrode_moles(negative, cell.negative_active_fraction, cell.negative_thickness_m)
        + cell.electrode_moles(positive, cell.positive_active_fraction, cell.positive_thickness_m)
        + plated_mol
    )
