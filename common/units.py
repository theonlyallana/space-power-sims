"""Unit conversions used by more than one month.

Keeping these in one place means a watt-hour is the same number of joules in
the thermal model and in the discharge-energy integral.
"""

from __future__ import annotations

import numpy as np

# The thermal model integrates in seconds and joules. Posts quote hours and
# watt-hours, which are the units NASA uses for the lunar night and for
# Ingenuity's battery energy.
JOULES_PER_WATT_HOUR = 3600.0
SECONDS_PER_HOUR = 3600.0


def celsius_to_kelvin(temperature_C: float) -> float:
    """Absolute temperature. Electrochemical rates use kelvin, not Celsius."""
    return float(temperature_C) + 273.15


def kelvin_to_celsius(temperature_K: float) -> float:
    return float(temperature_K) - 273.15


def hours_to_seconds(hours: float) -> float:
    return float(hours) * SECONDS_PER_HOUR


def watt_hours_to_joules(energy_Wh: float) -> float:
    return float(energy_Wh) * JOULES_PER_WATT_HOUR


def joules_to_watt_hours(energy_J: float) -> float:
    return float(energy_J) / JOULES_PER_WATT_HOUR


def trapz(y, x) -> float:
    """Integral of y dx.

    NumPy 2 renamed ``trapz`` to ``trapezoid``. PyBaMM 25.8 requires NumPy 1.x,
    where only ``trapz`` exists. Using whichever is present keeps the integral
    the same if the pin is ever relaxed.
    """
    function = getattr(np, "trapezoid", None) or getattr(np, "trapz")
    return float(function(np.asarray(y, dtype=float), np.asarray(x, dtype=float)))
