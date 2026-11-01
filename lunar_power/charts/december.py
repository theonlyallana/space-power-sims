"""December charts. Plain-language labels. Nothing here is hand-edited.

E is the orbit clock, for 7 December.
F is the surface film, for 14 December.
G is the radiation concept diagram, for 21 December.
H is fade at three depths of discharge, for 28 December.

Charts A to D stay in ``november.py`` and are always the fresh cell.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

from common.params import Entry, require
from common.plotting import COLOURS, apply_style, reserve_footer, save_figure
from common.units import celsius_to_kelvin
from lunar_power.ageing.fade import duty_from_params, fade_history, pure_diffusion_thickness_m
from lunar_power.ageing.orbit import profile_from_params
from lunar_power.ageing.pybamm_sei import load_cache
from lunar_power.ageing.radiation import assumption_multipliers, paper_doses_Mrad
from lunar_power.ageing.sei import capacity_loss_Ah, knobs_from_params, lithium_per_area_mol_m2, storage_loss
from lunar_power.electrochemistry.cell import cell_from_params

SECONDS_PER_DAY = 86400.0
DAYS_PER_YEAR = 365.25


def _area(book: dict[str, Entry]) -> float:
    return cell_from_params(book).negative_surface_area_m2


def figure_e(book: dict[str, Entry], out: Path) -> dict:
    """Sixteen cycles a day, from the length of the orbit."""
    profile = profile_from_params(book)
    apply_style()
    figure, axes = plt.subplots(1, 2, figsize=(10.6, 6.4), layout="constrained")

    clock = axes[0]
    clock.barh(
        0,
        profile["charge_min"],
        color=COLOURS["second"],
        height=0.55,
        label=f"{profile['charge_min']:.0f} minute charge",
    )
    clock.barh(
        0,
        profile["discharge_min"],
        left=profile["charge_min"],
        color=COLOURS["mid"],
        height=0.55,
        label=f"{profile['discharge_min']:.0f} minute discharge",
    )
    clock.set_xlim(0, profile["orbit_period_min"])
    clock.set_ylim(-0.7, 1.15)
    clock.set_yticks([])
    clock.set_xlabel("Minutes into one orbit")
    clock.set_title("One low-Earth orbit", fontsize=12)
    clock.legend(frameon=False, loc="upper right", fontsize=9)
    clock.text(
        profile["charge_min"] / 2,
        0,
        f"{profile['charge_current_A']:.1f} A\non this 5 Ah cell",
        ha="center",
        va="center",
        color="white",
        fontsize=9,
    )
    clock.text(
        profile["charge_min"] + profile["discharge_min"] / 2,
        0,
        f"{profile['discharge_current_A']:.1f} A",
        ha="center",
        va="center",
        color="white",
        fontsize=9,
    )

    years = np.linspace(0.0, 6.0, 400)
    per_day = profile["cycles_per_earth_day"]
    leo = years * DAYS_PER_YEAR * per_day
    daily = years * DAYS_PER_YEAR
    lunar = years * DAYS_PER_YEAR / profile["lunar_day_earth_days"]
    growth = axes[1]
    growth.plot(years, leo, color=COLOURS["warm"], label=f"{per_day:.0f} cycles a day (this orbit)")
    growth.plot(years, daily, color=COLOURS["mid"], label="1 cycle a day")
    growth.plot(
        years,
        lunar,
        color=COLOURS["cold"],
        label="1 cycle a lunar day",
    )
    growth.axhline(
        profile["cycle_goal"],
        color=COLOURS["ink"],
        linewidth=1.0,
        linestyle="--",
        label=f"NASA goal: {profile['cycle_goal']:.0f} cycles",
    )
    growth.axhline(
        profile["cycles_reported"],
        color=COLOURS["muted"],
        linewidth=1.0,
        linestyle=":",
        label=f"More than {profile['cycles_reported']:.0f} cycles by 2008",
    )
    growth.set_xlim(0, 6)
    growth.set_ylim(0, 40000)
    growth.set_xlabel("Earth years")
    growth.set_ylabel("Cycles completed")
    growth.set_title("The same goal, on three clocks", fontsize=12)
    growth.legend(frameon=False, fontsize=8, loc="upper left")

    figure.suptitle(
        f"A {profile['orbit_period_min']:.0f} minute orbit is "
        f"{per_day:.0f} cycles in one Earth day\n"
        f"40% of the nameplate each time. "
        f"{profile['cycle_goal']:.0f} cycles is {profile['days_to_cycle_goal']:.0f} days on this clock.",
        fontsize=13,
    )
    reserve_footer(figure)
    save_figure(figure, out / "E_sixteen_cycles_a_day.png")
    return profile


def figure_f(book: dict[str, Entry], out: Path) -> dict:
    """Film thickness. The right-hand panel is thickness squared, which is linear in time."""
    knobs = knobs_from_params(book)
    area = _area(book)
    days = np.linspace(0.0, 120.0, 241)
    apply_style()
    figure, axes = plt.subplots(1, 2, figsize=(10.6, 6.4), layout="constrained")
    series = {}
    for temperature_C, colour, name in (
        (25.0, COLOURS["warm"], "25 °C, the reference temperature"),
        (0.0, COLOURS["mid"], "0 °C, a published LEO test temperature"),
    ):
        temperature_K = celsius_to_kelvin(temperature_C)
        thickness_nm = np.array(
            [
                storage_loss(knobs, day * SECONDS_PER_DAY, temperature_K, area)["thickness_m"] * 1e9
                for day in days
            ]
        )
        # storage_loss rebuilds the dict 241 times. The thickness call is enough;
        # loss at the end is one more call. Kept this way so the plotted thickness
        # and the reported loss use one function.
        axes[0].plot(days, thickness_nm, color=colour, label=name)
        axes[1].plot(days, thickness_nm**2, color=colour, label=name)
        end = storage_loss(knobs, days[-1] * SECONDS_PER_DAY, temperature_K, area)
        series[str(temperature_C)] = {
            "thickness_nm": float(thickness_nm[-1]),
            "loss_mAh": end["loss_Ah"] * 1000.0,
        }

    cache = load_cache()
    for point in cache["points"]:
        day = point["time_s"] / SECONDS_PER_DAY
        if day > days[-1]:
            continue
        colour = COLOURS["warm"] if abs(point["temperature_K"] - 298.15) < 1.0 else COLOURS["mid"]
        thickness_nm = point["thickness_m"] * 1e9
        axes[0].scatter(day, thickness_nm, color=colour, s=28, zorder=4, edgecolor="white", linewidth=0.4)
        axes[1].scatter(day, thickness_nm**2, color=colour, s=28, zorder=4, edgecolor="white", linewidth=0.4)
    axes[0].scatter([], [], color=COLOURS["ink"], s=28, label="PyBaMM rest, same equation")
    axes[0].set_xlabel("Days on open circuit")
    axes[0].set_ylabel("Film thickness (nanometres)")
    axes[0].set_title("The skin thickens, and the thickening slows", fontsize=11)
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].set_xlim(0, 120)
    axes[1].set_xlabel("Days on open circuit")
    axes[1].set_ylabel("Film thickness squared (nm²)")
    axes[1].set_title("A straight line means diffusion through the film", fontsize=11)
    axes[1].set_xlim(0, 120)
    loss_25 = series["25.0"]["loss_mAh"]
    figure.suptitle(
        "The invisible skin that decides how long the cell lives\n"
        f"In 120 days at 25 °C this film consumes {loss_25:.1f} mAh of the 5 Ah nameplate.",
        fontsize=13,
    )
    reserve_footer(figure)
    save_figure(figure, out / "F_sei_growth.png")
    return {"end_of_window": series, "window_days": float(days[-1])}


def _box(axis, x, y, width, height, face, title, lines) -> None:
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        facecolor=face,
        edgecolor=COLOURS["ink"],
        linewidth=0.8,
        transform=axis.transAxes,
        mutation_aspect=0.6,
    )
    axis.add_patch(patch)
    axis.text(
        x + width / 2,
        y + height - 0.06,
        title,
        transform=axis.transAxes,
        ha="center",
        va="top",
        fontsize=10,
        color=COLOURS["ink"],
        fontweight="medium",
    )
    axis.text(
        x + 0.03,
        y + height - 0.12,
        "\n".join(lines),
        transform=axis.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        color=COLOURS["ink"],
        linespacing=1.35,
    )


def figure_g(book: dict[str, Entry], out: Path) -> dict:
    """Concept diagram. The multipliers are drawn and are not in the fade rate."""
    multipliers = assumption_multipliers(book)
    doses = paper_doses_Mrad(book)
    apply_style()
    figure, axis = plt.subplots(figsize=(10.6, 6.6), layout="constrained")
    axis.set_axis_off()
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    _box(
        axis,
        0.03,
        0.38,
        0.44,
        0.48,
        "#F4E7D7",
        "In the rate",
        [
            "Heat. The film's diffusivity",
            "follows the Arrhenius factor.",
            "",
            "Time. Thickness grows with",
            "the square root of time.",
            "",
            "Depth of discharge. A fraction",
            "of the skin is rebuilt each cycle.",
        ],
    )
    multiplier_text = ", ".join(f"×{value:g}" for value in multipliers)
    _box(
        axis,
        0.53,
        0.38,
        0.44,
        0.48,
        "#E5EEF6",
        "Drawn, not in the rate",
        [
            "Radiation. An EV duty does",
            "not include this dose.",
            "",
            f"2004 cells, up to {doses['experiment_upper_Mrad']:.0f} Mrad:",
            "a marginal decline. That study",
            "had no unirradiated control.",
            "",
            f"Jupiter-moon context there: about {doses['mission_context_Mrad']:.0f} Mrad.",
        ],
    )
    axis.text(
        0.5,
        0.24,
        "Assumption, swept, and not applied to the fade curves:\n"
        f"solvent-diffusivity multipliers {multiplier_text}.\n"
        "They are not a dose, and they do not change charts E, F or H.",
        transform=axis.transAxes,
        ha="center",
        va="top",
        fontsize=10,
        color=COLOURS["ink"],
    )
    figure.suptitle(
        "Radiation: the ageing stressor an electric vehicle does not see\n"
        "The box on the right is a label. It is not a fitted fade.",
        fontsize=13,
    )
    reserve_footer(figure)
    save_figure(figure, out / "G_radiation_concept.png")
    return {"multipliers": multipliers, "doses_Mrad": doses, "applied_to_fade": False}


def _history(knobs, area, duty, years, dod, period_s, fraction):
    return fade_history(
        knobs,
        time_s=years * DAYS_PER_YEAR * SECONDS_PER_DAY,
        period_s=period_s,
        depth_of_discharge=dod,
        volume_change_full=duty["volume_change"],
        fraction_at_full_expansion=fraction,
        interfacial_area_m2=area,
        nominal_capacity_Ah=duty["nominal_Ah"],
        temperature_K=duty["temperature_K"],
        diffusivity_multiplier=1.0,
    )


def figure_h(book: dict[str, Entry], out: Path) -> dict:
    """Three depths of discharge, plus the rover's slower clock as a dashed line."""
    knobs = knobs_from_params(book)
    duty = duty_from_params(book)
    area = _area(book)
    profile = profile_from_params(book)
    years = np.linspace(0.0, 15.0, 61)
    leo_period = duty["leo_period_s"]
    sol_s = profile["sol_earth_days"] * SECONDS_PER_DAY
    rover_period = sol_s / duty["rover_cycles_per_sol"]

    curves = {}
    apply_style()
    figure, axis = plt.subplots(figsize=(10.2, 6.5), layout="constrained")
    styles = (
        ("dod_shallow", "20% depth, 16 cycles a day", COLOURS["cold"], 0.20),
        ("dod_leo", "40% depth, 16 cycles a day", COLOURS["mid"], 0.40),
        ("dod_rover", "60% depth, 16 cycles a day", COLOURS["warm"], 0.60),
    )
    # The keys above are names. The values come from the book so a YAML edit moves the curve.
    dod_value = {
        "dod_shallow": duty["dod_shallow"],
        "dod_leo": duty["dod_leo"],
        "dod_rover": duty["dod_rover"],
    }
    for key, label, colour, _approx in styles:
        history = _history(knobs, area, duty, years, dod_value[key], leo_period, duty["fraction_full"])
        axis.plot(years, history.remaining_fraction, color=colour, label=label, zorder=3)
        curves[key] = {
            "depth_of_discharge": dod_value[key],
            "remaining_at_5_years": float(np.interp(5.0, years, history.remaining_fraction)),
            "remaining_at_15_years": float(history.remaining_fraction[-1]),
            "loss_Ah_at_5_years": float(np.interp(5.0, years, history.loss_Ah)),
        }

    low = _history(knobs, area, duty, years, duty["dod_leo"], leo_period, duty["fraction_low"])
    high = _history(knobs, area, duty, years, duty["dod_leo"], leo_period, duty["fraction_high"])
    axis.fill_between(
        years,
        high.remaining_fraction,
        low.remaining_fraction,
        color=COLOURS["mid"],
        alpha=0.18,
        linewidth=0,
        label="40% curve, crack-fraction sweep",
        zorder=0,
    )
    film_nm = pure_diffusion_thickness_m(knobs, years * DAYS_PER_YEAR * SECONDS_PER_DAY, duty["temperature_K"])
    film_loss_Ah = np.array(
        [
            capacity_loss_Ah(lithium_per_area_mol_m2(knobs, max(0.0, metres - knobs.initial_thickness_m)) * area)
            for metres in film_nm
        ]
    )
    axis.plot(
        years,
        np.maximum(0.0, 1.0 - film_loss_Ah / duty["nominal_Ah"]),
        color=COLOURS["muted"],
        linestyle="--",
        label="Film only, no cracking",
        zorder=2,
    )
    rover = _history(knobs, area, duty, years, duty["dod_rover"], rover_period, duty["fraction_full"])
    axis.plot(
        years,
        rover.remaining_fraction,
        color=COLOURS["warm"],
        linestyle=":",
        label="60% depth, one cycle a sol",
        zorder=3,
    )

    design_years = 90.0 * profile["sol_earth_days"] / DAYS_PER_YEAR
    contact_sol = float(require(book, "opportunity_last_contact_sol").value)
    contact_years = contact_sol * profile["sol_earth_days"] / DAYS_PER_YEAR
    lowest = min(
        float(np.min(low.remaining_fraction)),
        float(np.min(high.remaining_fraction)),
        float(np.min(rover.remaining_fraction)),
        float(curves["dod_rover"]["remaining_at_15_years"]),
    )
    axis.axvline(design_years, color=COLOURS["ink"], linewidth=0.8, linestyle="--")
    axis.axvline(contact_years, color=COLOURS["ink"], linewidth=0.8, linestyle=":")
    floor = max(0.0, lowest - 0.04)
    axis.set_xlim(0, 15)
    axis.set_ylim(floor, 1.03)
    axis.text(
        0.55,
        0.12,
        "90 sol\ndesign life",
        fontsize=8,
        color=COLOURS["ink"],
        ha="left",
    )
    axis.text(
        contact_years - 0.2,
        0.18,
        f"sol {contact_sol:.0f}, last contact",
        fontsize=8,
        color=COLOURS["ink"],
        ha="right",
    )
    axis.set_xlabel("Earth years")
    axis.set_ylabel("Capacity remaining (fraction of the 5 Ah nameplate)")
    axis.legend(frameon=False, fontsize=8, loc="upper right")
    figure.suptitle(
        "90 sols were the plan. Last contact was sol 5,111, almost 15 years\n"
        "Deeper cycles rebuild more of the film. A sol is a much slower clock than an orbit.",
        fontsize=12,
    )
    reserve_footer(figure)
    save_figure(figure, out / "H_fade_three_depths.png")
    curves["rover_one_per_sol"] = {
        "remaining_at_contact": float(np.interp(contact_years, years, rover.remaining_fraction)),
        "contact_years": contact_years,
        "design_years": design_years,
    }
    curves["film_only_remaining_at_15_years"] = float(
        np.interp(15.0, years, np.maximum(0.0, 1.0 - film_loss_Ah / duty["nominal_Ah"]))
    )
    curves["diffusivity_multiplier"] = 1.0
    return curves


def generate(book: dict[str, Entry], out: Path) -> dict:
    """Draw E to H. Returns the numbers the write-up quotes."""
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "E": figure_e(book, out),
        "F": figure_f(book, out),
        "G": figure_g(book, out),
        "H": figure_h(book, out),
    }
    return summary


def write_summary(summary: dict, path: Path) -> None:
    path.write_text(json.dumps(summary, indent=2) + "\n")
