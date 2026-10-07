# services/metro_service.py — Single source of truth for state assembly.
#
# Both GET /state and POST /next call build_state_response().
# No calculation logic lives in the routes.
#
# DATA_SOURCE (config.py / env):
#   simulation -> CSV coaches only (original behaviour)
#   vision     -> only coaches reported by the camera edge node
#   auto       -> CSV coaches, with every coach that has LIVE vision telemetry replaced by it

import config
from metro import VisionCoach, build_coaches_from_row
from logic import recommend_coach


def build_state_response(simulator, vision_service=None) -> dict:
    """
    Assembles the complete current state into a JSON-ready dict.
    Called after any state change (advance, reset) and on plain state reads.
    """
    current_row = simulator.get_current_row()
    previous_row = simulator.get_previous_row()

    station_name = str(current_row["Station"])
    sim_coaches = build_coaches_from_row(current_row, previous_row)

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

    mode = config.DATA_SOURCE
    vision_live = False
    coaches = sim_coaches
    if vision_service is not None and mode != "simulation":
        rows = vision_service.coach_rows(only_live=(mode == "auto"))
        vision_live = any(r["vision"]["live"] for r in rows)
        vision_by_id = {r["id"]: VisionCoach(r) for r in rows}
        if mode == "vision":
            coaches = list(vision_by_id.values())
        else:
            coaches = [vision_by_id.get(c.id, c) for c in sim_coaches]

    coaches_data = [c.to_dict() for c in coaches]
    recommendation = recommend_coach(coaches)

    state = {
        "station": station_info,
        "coaches": coaches_data,
        "recommendation": recommendation,
        "data_source": mode,
        "vision_live": vision_live,
    }
    if mode == "vision" and not coaches:
        state["message"] = "Waiting for vision telemetry from the edge node."
    return state
