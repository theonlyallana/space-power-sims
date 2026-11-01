"""December ageing layer: orbit clock, surface film, fade, radiation label."""

from lunar_power.ageing.fade import crack_area_fraction, fade_history
from lunar_power.ageing.feed import AgeingState, aged_state_from_params, apply_fade
from lunar_power.ageing.orbit import cycles_per_earth_day, profile_from_params
from lunar_power.ageing.radiation import FADE_DIFFUSIVITY_MULTIPLIER, assumption_multipliers
from lunar_power.ageing.sei import knobs_from_params, storage_loss, thickness_m

__all__ = [
    "FADE_DIFFUSIVITY_MULTIPLIER",
    "AgeingState",
    "aged_state_from_params",
    "apply_fade",
    "assumption_multipliers",
    "crack_area_fraction",
    "cycles_per_earth_day",
    "fade_history",
    "knobs_from_params",
    "profile_from_params",
    "storage_loss",
    "thickness_m",
]
