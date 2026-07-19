# services/metro_service.py — Single source of truth for state assembly.
#
# Both GET /state and POST /next call build_state_response().
# No calculation logic lives in the routes.

from metro import build_coaches_from_row
from logic import recommend_coach


def build_state_response(simulator) -> dict:
    """
    Assembles the complete current simulation state into a JSON-ready dict.
    Called after any state change (advance, reset) and on plain state reads.
    """
    current_row = simulator.get_current_row()
    previous_row = simulator.get_previous_row()

    station_name = str(current_row["Station"])
    coaches = build_coaches_from_row(current_row, previous_row)

    # Station context
    prev_name = str(previous_row["Station"]) if previous_row else None
    next_idx = simulator.current_index + 1
    next_name = simulator.get_station_name(next_idx)

    station_info = {
        "current": station_name,
        "previous": prev_name,
        "next": next_name,
        "index": simulator.current_index,
        "total": simulator.total_stations,
        "at_final_station": simulator.at_final_station,
    }

    coaches_data = [c.to_dict() for c in coaches]
    recommendation = recommend_coach(coaches)

    return {
        "station": station_info,
        "coaches": coaches_data,
        "recommendation": recommendation,
    }
