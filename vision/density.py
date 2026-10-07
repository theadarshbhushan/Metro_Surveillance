# density.py — passenger statistics and density classification (pure functions).
#
# Two different percentages are deliberately kept apart:
#   occupancy_percentage       = total_people / MAX_PASSENGERS_PER_COACH   (crowd density)
#   seat_occupancy_percentage  = occupied_seats / total_seats              (seat usage)
# The density label (LOW/MODERATE/HIGH/CRITICAL) is driven by the crowd density.

from __future__ import annotations

from typing import Optional, Sequence

LOW, MODERATE, HIGH, CRITICAL = "LOW", "MODERATE", "HIGH", "CRITICAL"
DEFAULT_THRESHOLDS = (40.0, 65.0, 85.0)  # same values as backend/config.py


def occupancy_percentage(total_people: int, max_passengers: int) -> float:
    """People / capacity as a percentage, clamped to [0, 100]."""
    if max_passengers <= 0:
        return 0.0
    return round(max(0.0, min(100.0, total_people / max_passengers * 100.0)), 1)


def density_status(pct: float, thresholds: Sequence[float] = DEFAULT_THRESHOLDS) -> str:
    """LOW <= t0 < MODERATE <= t1 < HIGH <= t2 < CRITICAL (matches backend logic.py)."""
    t_mod, t_high, t_crit = thresholds
    if pct <= t_mod:
        return LOW
    if pct <= t_high:
        return MODERATE
    if pct <= t_crit:
        return HIGH
    return CRITICAL


def seat_occupancy_percentage(occupied_seats: int, total_seats: int) -> Optional[float]:
    if total_seats <= 0:
        return None
    return round(occupied_seats / total_seats * 100.0, 1)


def compute_stats(
    seated: int,
    standing: int,
    unknown: int,
    occupied_seats: int,
    empty_seats: int,
    uncertain_seats: int,
    max_passengers: int,
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
) -> dict:
    """Build the statistics block of a telemetry message."""
    total_people = seated + standing + unknown  # no double counting by construction
    pct = occupancy_percentage(total_people, max_passengers)
    return {
        "total_people": total_people,
        "seated_people": seated,
        "standing_people": standing,
        "unknown_people": unknown,
        "occupied_seats": occupied_seats,
        "empty_seats": empty_seats,
        "uncertain_seats": uncertain_seats,
        "max_passengers": max_passengers,
        "occupancy_percentage": pct,
        "seat_occupancy_percentage": seat_occupancy_percentage(
            occupied_seats, occupied_seats + empty_seats + uncertain_seats
        ),
        "density_status": density_status(pct, thresholds),
    }
