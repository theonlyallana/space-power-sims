"""One scenario runner. Layers are switches, not separate projects.

``thermal`` and ``electrochemistry`` are the November model. ``ageing`` feeds
both when it is on: the cell handed to a cold discharge has lost lithium and
gained film resistance, and the night's stored watt-hours are scaled by the
capacity that remains.

``safety``, ``pack``, ``variation`` and ``mission`` are named so the later
months have a place to land. Switching one on raises NotImplementedError.
That is the unfinished layer, not a silent no-op.
"""

from __future__ import annotations

from dataclasses import dataclass

from common.params import Entry, require
from common.units import celsius_to_kelvin, watt_hours_to_joules
from lunar_power.ageing.feed import AgeingState, aged_state_from_params, apply_fade
from lunar_power.ageing.radiation import FADE_DIFFUSIVITY_MULTIPLIER
from lunar_power.electrochemistry.cell import Cell, cell_from_params
from lunar_power.electrochemistry.spm import simulate
from lunar_power.thermal.night import ingenuity_specific_energy_Wh_per_kg, simulate_night

FUTURE_LAYERS = ("safety", "pack", "variation", "mission")
LAYER_NAMES = ("thermal", "electrochemistry", "ageing", *FUTURE_LAYERS)


@dataclass(frozen=True)
class Layers:
    """Which pieces of the one model this scenario runs."""

    thermal: bool = False
    electrochemistry: bool = False
    ageing: bool = False
    safety: bool = False
    pack: bool = False
    variation: bool = False
    mission: bool = False

    def enabled(self) -> tuple[str, ...]:
        return tuple(name for name in LAYER_NAMES if getattr(self, name))


def parse_layers(text: str) -> Layers:
    """``"thermal,electrochemistry"`` switches those two on and the rest off."""
    names = [part.strip().lower() for part in text.split(",") if part.strip()]
    unknown = [name for name in names if name not in LAYER_NAMES]
    if unknown:
        raise ValueError(f"unknown layer {unknown}. Known layers: {', '.join(LAYER_NAMES)}")
    flags = {name: name in names for name in LAYER_NAMES}
    layers = Layers(**flags)
    pending = [name for name in FUTURE_LAYERS if getattr(layers, name)]
    if pending:
        raise NotImplementedError(
            f"{', '.join(pending)} is a later layer of this same model. "
            "The switch is here so the architecture can turn it on. There is no physics for it yet."
        )
    if not layers.enabled():
        raise ValueError("choose at least one layer")
    return layers


def run_scenario(book: dict[str, Entry], layers: Layers) -> dict:
    """Run the switched-on layers. Ageing, if on, is applied before the others.

    Electrochemistry here is one warm and one cold discharge of whatever cell
    the switches produced. It is the feed check, not charts A and B. Those
    charts are always the fresh cell, drawn by ``charts.november``.
    """
    ageing_state: AgeingState | None = None
    cell: Cell | None = None
    if layers.electrochemistry or layers.ageing:
        cell = cell_from_params(book)
    if layers.ageing:
        if cell is None:
            cell = cell_from_params(book)
        ageing_state = aged_state_from_params(book, cell)
        if ageing_state.diffusivity_multiplier != FADE_DIFFUSIVITY_MULTIPLIER:
            raise RuntimeError("the cold-model feed must not apply the radiation sweep")
        if layers.electrochemistry:
            cell = apply_fade(cell, ageing_state)

    discharges = {}
    if layers.electrochemistry and cell is not None:
        rate = float(require(book, "discharge_c_rate").value)
        for temperature_C in (25.0, 0.0):
            result = simulate(
                cell,
                celsius_to_kelvin(temperature_C),
                rate,
                "discharge",
                cell.initial_negative,
                cell.initial_positive,
            )
            discharges[str(temperature_C)] = {
                "energy_Wh": result.energy_Wh,
                "capacity_Ah": float(result.throughput_Ah[-1]),
                "ohmic_ohm": cell.ohmic_resistance(celsius_to_kelvin(temperature_C)),
            }

    night = None
    if layers.thermal:
        mass_kg = float(require(book, "chart_d_pack_mass_kg").value)
        specific = ingenuity_specific_energy_Wh_per_kg(
            float(require(book, "ingenuity_energy_0C_Wh").value),
            float(require(book, "ingenuity_cell_mass_g").value),
            int(require(book, "ingenuity_cell_count").value),
        )
        remaining = 1.0 if ageing_state is None else ageing_state.remaining_fraction
        stored_Wh = mass_kg * specific * remaining
        result = simulate_night(
            strategy="keep_warm",
            mass_kg=mass_kg,
            specific_heat_J_per_kg_K=float(require(book, "pack_specific_heat_J_per_kg_K").value),
            conductance_W_per_K=float(require(book, "chart_d_conductance_W_per_K").value),
            sink_K=float(require(book, "equator_predawn_temperature_K").value),
            setpoint_K=celsius_to_kelvin(float(require(book, "keep_warm_setpoint_C").value)),
            start_K=celsius_to_kelvin(float(require(book, "night_start_temperature_C").value)),
            stored_energy_J=watt_hours_to_joules(stored_Wh),
            radioisotope_power_W=0.0,
            duration_s=float(require(book, "lunar_night_duration_h").value) * 3600.0,
        )
        night = {
            "stored_Wh": stored_Wh,
            "remaining_fraction": remaining,
            "heater_Wh": result.heater_energy_Wh,
            "final_soc": float(result.state_of_charge[-1]),
        }

    return {
        "layers": list(layers.enabled()),
        "ageing": None
        if ageing_state is None
        else {
            "time_s": ageing_state.time_s,
            "thickness_grown_m": ageing_state.thickness_grown_m,
            "capacity_lost_Ah": ageing_state.capacity_lost_Ah,
            "remaining_fraction": ageing_state.remaining_fraction,
            "lithium_lost_mol": ageing_state.lithium_lost_mol,
            "diffusivity_multiplier": ageing_state.diffusivity_multiplier,
            "depth_of_discharge": ageing_state.depth_of_discharge,
        },
        "discharges": discharges,
        "night": night,
        "initial_negative_mol_m3": None if cell is None else cell.initial_negative,
    }


def fresh_discharge_energy_Wh(book: dict[str, Entry], temperature_C: float) -> float:
    """The November discharge, ageing forced off. Used by the regression test."""
    cell = cell_from_params(book)
    result = simulate(
        cell,
        celsius_to_kelvin(temperature_C),
        float(require(book, "discharge_c_rate").value),
        "discharge",
        cell.initial_negative,
        cell.initial_positive,
    )
    return result.energy_Wh
