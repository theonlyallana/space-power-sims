"""Low-Earth-orbit cycle counting. Arithmetic, not a fitted life model.

NASA's description of an LEO battery test is a 90 minute orbit: about 55
minutes of charge in sunlight and 35 minutes of discharge in eclipse, to 40%
depth of discharge. Dividing a civil day by that orbit is 16 cycles. That
division is the whole of the "sixteen cycles a day" result.
"""

from __future__ import annotations

from common.params import Entry, require

MINUTES_PER_EARTH_DAY = 24 * 60


def cycles_per_earth_day(orbit_period_min: float) -> float:
    """How many orbits fit in 24 hours. 1440 / 90 is exactly 16."""
    if orbit_period_min <= 0.0:
        raise ValueError("orbit period must be positive")
    return MINUTES_PER_EARTH_DAY / float(orbit_period_min)


def earth_days_for_cycles(cycle_count: float, orbit_period_min: float) -> float:
    """Calendar days to accumulate ``cycle_count`` orbits."""
    return float(cycle_count) / cycles_per_earth_day(orbit_period_min)


def current_A(capacity_Ah: float, depth_of_discharge: float, duration_min: float) -> float:
    """Current that moves ``depth_of_discharge`` of the nameplate in ``duration_min``.

    Ampere-hours divided by hours. A 40% swing of a 5 Ah cell in 35 minutes
    is 0.4 * 5 / (35/60) amperes. The function does not invent a mission current.
    """
    hours = float(duration_min) / 60.0
    if hours <= 0.0:
        raise ValueError("duration must be positive")
    return float(depth_of_discharge) * float(capacity_Ah) / hours


def lunar_day_hours(night_hours: float, day_to_night_ratio: float) -> float:
    """Sunlit hours plus night, with the sunlit part as a ratio of the night.

    A ratio of 1 doubles the cited night. That is an assumption about the
    site, recorded in the parameter note, not a second measurement.
    """
    return float(night_hours) * (1.0 + float(day_to_night_ratio))


def sol_seconds(hours: float, minutes: float, seconds: float) -> float:
    """Length of one Martian solar day from the three published parts."""
    return float(hours) * 3600.0 + float(minutes) * 60.0 + float(seconds)


def sol_in_earth_days(hours: float, minutes: float, seconds: float) -> float:
    return sol_seconds(hours, minutes, seconds) / (24.0 * 3600.0)


def profile_from_params(book: dict[str, Entry]) -> dict[str, float]:
    """The LEO clock, the lunar-day comparison, and the currents on this cell."""
    period = float(require(book, "leo_orbit_period_min").value)
    charge_min = float(require(book, "leo_sunlight_charge_min").value)
    discharge_min = float(require(book, "leo_eclipse_discharge_min").value)
    dod = float(require(book, "leo_depth_of_discharge").value)
    capacity = float(require(book, "nominal_capacity_Ah").value)
    night_h = float(require(book, "lunar_night_duration_h").value)
    ratio = float(require(book, "nonpolar_day_to_night_ratio").value)
    per_day = cycles_per_earth_day(period)
    goal = float(require(book, "leo_cycle_goal").value)
    sol_days = sol_in_earth_days(
        float(require(book, "mars_sol_hours").value),
        float(require(book, "mars_sol_minutes").value),
        float(require(book, "mars_sol_seconds").value),
    )
    return {
        "orbit_period_min": period,
        "charge_min": charge_min,
        "discharge_min": discharge_min,
        "depth_of_discharge": dod,
        "cycles_per_earth_day": per_day,
        "days_to_cycle_goal": earth_days_for_cycles(goal, period),
        "cycle_goal": goal,
        "cycles_reported": float(require(book, "leo_cycles_reported").value),
        "charge_current_A": current_A(capacity, dod, charge_min),
        "discharge_current_A": current_A(capacity, dod, discharge_min),
        "capacity_Ah": capacity,
        "lunar_day_h": lunar_day_hours(night_h, ratio),
        "lunar_day_earth_days": lunar_day_hours(night_h, ratio) / 24.0,
        "sol_earth_days": sol_days,
        "cycles_per_earth_day_once": 1.0,
    }
