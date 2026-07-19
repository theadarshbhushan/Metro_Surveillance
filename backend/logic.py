# logic.py — Core decision engine.
# Contains ONLY pure functions; no Flask, no Streamlit, no I/O.
# Swap the recommendation algorithm here without touching routes or services.

from config import (
    THRESHOLD_MODERATE, THRESHOLD_HIGH, THRESHOLD_CRITICAL,
    DENSITY_LOW, DENSITY_MODERATE, DENSITY_HIGH, DENSITY_CRITICAL,
)


def get_density_status(occupancy_percentage: float) -> str:
    """
    Classify occupancy into one of four density levels.
    Thresholds are defined centrally in config.py.
    """
    if occupancy_percentage <= THRESHOLD_MODERATE:
        return DENSITY_LOW
    elif occupancy_percentage <= THRESHOLD_HIGH:
        return DENSITY_MODERATE
    elif occupancy_percentage <= THRESHOLD_CRITICAL:
        return DENSITY_HIGH
    else:
        return DENSITY_CRITICAL


def recommend_coach(coaches: list) -> dict:
    """
    Rule-Based Crowd Distribution Engine.
    Selects the coach with the highest available capacity (= lowest occupancy).
    Returns a recommendation dict ready for JSON serialization.
    """
    if not coaches:
        return {}

    best = min(coaches, key=lambda c: c.occupancy_percentage)

    reason = (
        f"Coach {best.id} currently has the highest available capacity "
        f"({best.available_capacity} kg free, {best.occupancy_percentage}% occupied) "
        f"and provides the best option for balanced passenger distribution."
    )

    return {
        "coach_id": best.id,
        "occupancy_percentage": best.occupancy_percentage,
        "available_capacity": best.available_capacity,
        "density_status": best.density_status,
        "reason": reason,
    }
