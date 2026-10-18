"""Draw the four November charts from the models. Nothing here is hand-edited.

Chart A is plating, for the 2 November post.
Chart B is cold discharge energy, for 9 November.
Chart C is heater energy against insulation, for 16 November.
Chart D is keep-warm against hibernation, for 23 November.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from cell import Cell, cell_from_params
from common.constants import STEFAN_BOLTZMANN
from common.params import Entry, require
from common.plotting import COLOURS, DISCLAIMER, apply_style, save_figure
from common.units import celsius_to_kelvin, watt_hours_to_joules
from spm import discharged_state, simulate
from thermal import (
    battery_mass_kg,
    ingenuity_specific_energy_Wh_per_kg,
    radiative_conductance_W_per_K,
    simulate_night,
    steady_heater_energy_Wh,
)

TEMPERATURE_COLOURS = {
    25.0: COLOURS["warm"],
    10.0: COLOURS["second"],
    0.0: COLOURS["mid"],
    -10.0: "#56B4E9",
    -20.0: COLOURS["cold"],
}


def _footer(figure: plt.Figure) -> None:
    figure.text(0.01, 0.01, DISCLAIMER, fontsize=7, color=COLOURS["muted"])


def _rate_label(c_rate: float) -> str:
    if abs(c_rate - 0.5) < 1e-9:
        return "C/2"
    if abs(c_rate - 1.0) < 1e-9:
        return "1C"
    return f"{c_rate:g}C"


def figure_a(cell: Cell, book: dict[str, Entry], out: Path, smoke: bool) -> dict:
    """Plated lithium against charge temperature, our criterion and PyBaMM."""
    temperatures = [float(t) for t in require(book, "plating_temperatures_C").value]
    rates = [float(r) for r in require(book, "plating_c_rates").value]
    if smoke:
        temperatures = [temperatures[0], temperatures[-1]]
        rates = rates[-1:]

    empty_negative, empty_positive = discharged_state(
        cell,
        float(require(book, "precondition_c_rate").value),
        cell.reference_temperature_K,
    )
    ours = []
    for rate in rates:
        for temperature_C in temperatures:
            result = simulate(
                cell,
                celsius_to_kelvin(temperature_C),
                rate,
                "charge",
                empty_negative,
                empty_positive,
            )
            ours.append(
                {
                    "rate": rate,
                    "temperature_C": temperature_C,
                    "plated_mAh": float(result.plated_Ah[-1] * 1000.0),
                    "throughput_Ah": float(result.throughput_Ah[-1]),
                    "anode_min_V": float(np.min(result.anode_potential_V)),
                }
            )

    pybamm_rows = []
    if not smoke:
        from pybamm_check import plated_lithium_Ah

        for rate in rates:
            for temperature_C in temperatures:
                curve = plated_lithium_Ah(
                    celsius_to_kelvin(temperature_C),
                    rate,
                    empty_negative,
                    empty_positive,
                )
                pybamm_rows.append(
                    {
                        "rate": rate,
                        "temperature_C": temperature_C,
                        "plated_mAh": curve.plated_Ah * 1000.0,
                        "throughput_Ah": curve.throughput_Ah,
                    }
                )

    rate_colours = {0.5: COLOURS["mid"], 1.0: COLOURS["warm"]}
    apply_style()
    figure, axes = plt.subplots(1, 2, figsize=(10.2, 4.8), sharey=True)
    for axis, rows, title in (
        (axes[0], ours, "Our model: plate only below 0 V vs Li"),
        (axes[1], pybamm_rows or ours, "PyBaMM DFN, irreversible Butler-Volmer"),
    ):
        if axis is axes[1] and smoke:
            axis.set_title("PyBaMM cross-check skipped in smoke mode")
            axis.text(0.5, 0.5, "smoke mode", ha="center", va="center", transform=axis.transAxes)
            continue
        for rate in rates:
            subset = [row for row in rows if row["rate"] == rate]
            axis.plot(
                [row["temperature_C"] for row in subset],
                [row["plated_mAh"] for row in subset],
                marker="o",
                color=rate_colours.get(rate, COLOURS["ink"]),
                label=_rate_label(rate),
            )
        axis.set_xlabel("Charging temperature (°C)")
        axis.set_title(title, fontsize=11)
        axis.legend(frameon=False)
        axis.set_ylim(bottom=0.0)
    axes[0].set_ylabel("Plated lithium at 4.2 V (mAh)")
    figure.suptitle(
        "Colder charging deposits more lithium as metal",
        fontsize=14,
        y=1.02,
    )
    _footer(figure)
    save_figure(figure, out / "A_plated_lithium.png")
    return {
        "empty_negative_mol_m3": empty_negative,
        "empty_positive_mol_m3": empty_positive,
        "ours": ours,
        "pybamm": pybamm_rows,
    }


def figure_b(cell: Cell, book: dict[str, Entry], out: Path, smoke: bool) -> dict:
    """Discharge curves at three temperatures, with Ingenuity as a relative check."""
    temperatures = [float(t) for t in require(book, "discharge_temperatures_C").value]
    rate = float(require(book, "discharge_c_rate").value)
    if smoke:
        temperatures = [25.0, 0.0]

    ours = []
    apply_style()
    figure, axis = plt.subplots(figsize=(7.4, 5.0))
    for temperature_C in temperatures:
        result = simulate(
            cell,
            celsius_to_kelvin(temperature_C),
            rate,
            "discharge",
            cell.initial_negative,
            cell.initial_positive,
        )
        axis.plot(
            result.throughput_Ah,
            result.voltage_V,
            color=TEMPERATURE_COLOURS.get(temperature_C, COLOURS["ink"]),
            label=f"Our model, {temperature_C:.0f} °C",
        )
        ours.append(
            {
                "temperature_C": temperature_C,
                "energy_Wh": result.energy_Wh,
                "capacity_Ah": float(result.throughput_Ah[-1]),
            }
        )

    pybamm_rows = []
    if not smoke:
        from pybamm_check import discharge_curve

        for temperature_C in temperatures:
            curve = discharge_curve(
                celsius_to_kelvin(temperature_C),
                rate,
                cell.initial_negative,
                cell.initial_positive,
            )
            # Spread the integrated ampere-hours along the trace. PyBaMM's
            # current is constant, so this is the same shape as time times current.
            capacity = np.linspace(0.0, curve.throughput_Ah, len(curve.voltage_V))
            axis.plot(
                capacity,
                curve.voltage_V,
                color=TEMPERATURE_COLOURS.get(temperature_C, COLOURS["ink"]),
                linestyle="--",
                label=f"PyBaMM DFN, {temperature_C:.0f} °C",
            )
            pybamm_rows.append(
                {
                    "temperature_C": temperature_C,
                    "energy_Wh": curve.energy_Wh,
                    "capacity_Ah": curve.throughput_Ah,
                }
            )

    warm = next(row["energy_Wh"] for row in ours if row["temperature_C"] == 25.0)
    cold = next(row["energy_Wh"] for row in ours if row["temperature_C"] == 0.0)
    drop = (warm - cold) / warm
    ingenuity_warm = float(require(book, "ingenuity_energy_25C_Wh").value)
    ingenuity_cold = float(require(book, "ingenuity_energy_0C_Wh").value)
    ingenuity_drop = (ingenuity_warm - ingenuity_cold) / ingenuity_warm
    axis.set_xlabel("Capacity discharged (Ah)")
    axis.set_ylabel("Cell voltage (V)")
    axis.set_title("Same charge, less energy back when the cell is cold")
    axis.legend(frameon=False, fontsize=8, loc="lower left")
    pybamm_drop = None
    if pybamm_rows:
        py_warm = next(row["energy_Wh"] for row in pybamm_rows if row["temperature_C"] == 25.0)
        py_cold = next(row["energy_Wh"] for row in pybamm_rows if row["temperature_C"] == 0.0)
        pybamm_drop = (py_warm - py_cold) / py_warm
    drop_line = f"Our model, 1C: {drop * 100:.1f}% less at 0 °C than at 25 °C"
    if pybamm_drop is not None:
        drop_line += f"\nPyBaMM DFN: {pybamm_drop * 100:.1f}% less over the same step"
    axis.text(
        0.98,
        0.98,
        (
            f"{drop_line}\n"
            f"Ingenuity's pack, a different cell: {ingenuity_drop * 100:.1f}% "
            f"({ingenuity_cold:.1f} / {ingenuity_warm:.1f} Wh)\n"
            "Compare the percentage, not the watt-hours."
        ),
        transform=axis.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        color=COLOURS["ink"],
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": "#dddddd"},
    )
    _footer(figure)
    save_figure(figure, out / "B_discharge_curves.png")
    return {
        "ours": ours,
        "pybamm": pybamm_rows,
        "relative_drop": drop,
        "pybamm_relative_drop": pybamm_drop,
        "ingenuity_relative_drop": ingenuity_drop,
    }


def figure_c(book: dict[str, Entry], out: Path) -> dict:
    """Heater energy and the cell mass that stores it, against conductance."""
    g_min = float(require(book, "conductance_min_W_per_K").value)
    g_max = float(require(book, "conductance_max_W_per_K").value)
    conductances = np.logspace(np.log10(g_min), np.log10(g_max), 40)
    setpoint = celsius_to_kelvin(float(require(book, "keep_warm_setpoint_C").value))
    equator = float(require(book, "equator_predawn_temperature_K").value)
    psr = float(require(book, "psr_sink_temperature_K").value)
    night = float(require(book, "lunar_night_duration_h").value)
    psr_hours = float(require(book, "psr_night_duration_h").value)
    rhu = float(require(book, "radioisotope_heater_power_W").value)
    specific = ingenuity_specific_energy_Wh_per_kg(
        float(require(book, "ingenuity_energy_0C_Wh").value),
        float(require(book, "ingenuity_cell_mass_g").value),
        int(require(book, "ingenuity_cell_count").value),
    )
    cases = (
        ("354 h night, no RHU", equator, night, 0.0, COLOURS["ink"], "-"),
        ("354 h night, one 1 W RHU", equator, night, rhu, COLOURS["ink"], "--"),
        ("125 h PSR night, no RHU", psr, psr_hours, 0.0, COLOURS["cold"], "-"),
        ("125 h PSR night, one 1 W RHU", psr, psr_hours, rhu, COLOURS["cold"], "--"),
    )
    series = {}
    apply_style()
    # Two panels because a 1 W radioisotope unit is invisible on a plot that
    # runs up to tens of watts of leak. The left panel is the scaling. The
    # right panel is the corner where that one watt actually covers the leak.
    figure, axes = plt.subplots(1, 2, figsize=(10.6, 4.8))
    for label, sink, hours, radioisotope, colour, style in cases:
        energy = np.array(
            [
                steady_heater_energy_Wh(g, setpoint, sink, radioisotope, hours)
                for g in conductances
            ]
        )
        series[label] = {
            "conductance_W_per_K": conductances.tolist(),
            "heater_Wh": energy.tolist(),
        }
        if radioisotope == 0.0:
            axes[0].plot(conductances, energy, color=colour, linestyle=style, label=label)
        axes[1].plot(conductances, energy, color=colour, linestyle=style, label=label)
    example_g = radiative_conductance_W_per_K(
        float(require(book, "example_emissivity").value),
        float(require(book, "example_radiating_area_m2").value),
        setpoint,
        equator,
    )
    axes[0].axvline(
        example_g,
        color=COLOURS["second"],
        linewidth=1.2,
        label="Example radiation (assumption)",
    )
    axes[0].set_xlabel("Insulation conductance G (W/K)")
    axes[0].set_ylabel("Heater energy over the night (Wh)")
    axes[0].set_title("Energy tracks the leak")
    mass_axis = axes[0].twinx()
    mass_axis.set_ylabel("Cell mass to store it (kg)")
    y_low, y_high = axes[0].get_ylim()
    mass_axis.set_ylim(battery_mass_kg(max(y_low, 0.0), specific), battery_mass_kg(y_high, specific))
    mass_axis.spines["top"].set_visible(False)
    axes[0].legend(frameon=False, fontsize=7, loc="upper left")
    zoom_index = int(np.argmax(conductances >= 0.04))
    axes[1].set_xlim(float(conductances[0]), 0.04)
    axes[1].set_ylim(0.0, series["354 h night, no RHU"]["heater_Wh"][zoom_index] * 1.15)
    axes[1].set_xlabel("Insulation conductance G (W/K)")
    axes[1].set_ylabel("Heater energy over the night (Wh)")
    axes[1].set_title("Where one 1 W RHU is enough")
    axes[1].legend(frameon=False, fontsize=7, loc="upper left")
    figure.suptitle("Halve the heat leak and you roughly halve the battery", fontsize=14)
    _footer(figure)
    save_figure(figure, out / "C_heater_energy.png")
    return {
        "specific_energy_Wh_per_kg": specific,
        "example_radiative_conductance_W_per_K": example_g,
        "stefan_boltzmann": STEFAN_BOLTZMANN,
        "series_endpoints": {
            label: {
                "heater_Wh_at_min_G": values["heater_Wh"][0],
                "heater_Wh_at_max_G": values["heater_Wh"][-1],
            }
            for label, values in series.items()
        },
    }


def figure_d(book: dict[str, Entry], out: Path, specific_energy: float) -> dict:
    """State of charge and temperature, keep-warm against hibernate."""
    mass = float(require(book, "chart_d_pack_mass_kg").value)
    heat_capacity = float(require(book, "pack_specific_heat_J_per_kg_K").value)
    conductance = float(require(book, "chart_d_conductance_W_per_K").value)
    sink = float(require(book, "equator_predawn_temperature_K").value)
    setpoint = celsius_to_kelvin(float(require(book, "keep_warm_setpoint_C").value))
    start = celsius_to_kelvin(float(require(book, "night_start_temperature_C").value))
    duration_h = float(require(book, "lunar_night_duration_h").value)
    stored_Wh = mass * specific_energy * float(require(book, "night_start_state_of_charge").value)
    common = dict(
        mass_kg=mass,
        specific_heat_J_per_kg_K=heat_capacity,
        conductance_W_per_K=conductance,
        sink_K=sink,
        setpoint_K=setpoint,
        start_K=start,
        stored_energy_J=watt_hours_to_joules(stored_Wh),
        radioisotope_power_W=0.0,
        duration_s=duration_h * 3600.0,
    )
    keep = simulate_night(strategy="keep_warm", **common)
    hibernate = simulate_night(strategy="hibernate", **common)

    apply_style()
    figure, axes = plt.subplots(2, 1, figsize=(7.6, 6.2), sharex=True)
    axes[0].plot(keep.time_h, keep.temperature_C, color=COLOURS["warm"], label="Keep warm")
    axes[0].plot(hibernate.time_h, hibernate.temperature_C, color=COLOURS["mid"], label="Hibernate")
    axes[0].axhline(0.0, color=COLOURS["muted"], linewidth=0.8, linestyle=":")
    axes[0].set_ylabel("Pack temperature (°C)")
    axes[0].legend(frameon=False, loc="upper right")
    axes[0].set_title("A small pack that heats itself can still freeze")
    axes[1].plot(keep.time_h, keep.state_of_charge, color=COLOURS["warm"], label="Keep warm")
    axes[1].plot(hibernate.time_h, hibernate.state_of_charge, color=COLOURS["mid"], label="Hibernate")
    axes[1].set_ylabel("State of charge")
    axes[1].set_xlabel("Hours into a 354 h lunar night")
    axes[1].set_ylim(-0.05, 1.05)
    axes[1].legend(frameon=False, loc="center right")
    empty_index = int(np.argmax(keep.state_of_charge <= 1e-3))
    empty_hour = float(keep.time_h[empty_index])
    axes[0].annotate(
        f"heater stops\n{empty_hour:.0f} h",
        xy=(empty_hour, 0.0),
        xytext=(empty_hour + 25, 40),
        fontsize=8,
        color=COLOURS["warm"],
        arrowprops={"arrowstyle": "->", "color": COLOURS["warm"]},
    )
    sink_C = sink - 273.15
    axes[0].axhline(sink_C, color=COLOURS["muted"], linewidth=0.7, linestyle=":")
    axes[0].text(
        354,
        sink_C + 8,
        "sink, 95 K",
        ha="right",
        va="bottom",
        fontsize=8,
        color=COLOURS["muted"],
    )
    _footer(figure)
    save_figure(figure, out / "D_keep_warm_vs_hibernate.png")

    empty = None
    if np.any(keep.state_of_charge <= 1e-3):
        empty = float(keep.time_h[np.argmax(keep.state_of_charge <= 1e-3)])
    return {
        "stored_Wh": stored_Wh,
        "keep_warm_heater_Wh": keep.heater_energy_Wh,
        "keep_warm_final_soc": float(keep.state_of_charge[-1]),
        "keep_warm_final_C": float(keep.temperature_C[-1]),
        "hibernate_final_soc": float(hibernate.state_of_charge[-1]),
        "hibernate_final_C": float(hibernate.temperature_C[-1]),
        "keep_warm_empty_h": empty,
        "conductance_W_per_K": conductance,
        "mass_kg": mass,
    }


def generate(book: dict[str, Entry], out: Path, smoke: bool = False) -> dict:
    """Regenerate every November figure. Returns the numbers the write-up quotes."""
    cell = cell_from_params(book)
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "A": figure_a(cell, book, out, smoke),
        "B": figure_b(cell, book, out, smoke),
    }
    thermal_summary = figure_c(book, out)
    summary["C"] = thermal_summary
    summary["D"] = figure_d(book, out, thermal_summary["specific_energy_Wh_per_kg"])
    if not smoke:
        (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary
