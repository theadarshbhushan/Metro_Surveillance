# routes/simulation_routes.py — REST endpoints for the simulation.
# Routes delegate ALL business logic to metro_service; no calculations here.

from flask import Blueprint, jsonify, g
from services.metro_service import build_state_response

simulation_bp = Blueprint("simulation", __name__, url_prefix="/api/simulation")


def _state():
    return build_state_response(g.simulator, g.vision)


@simulation_bp.route("/state", methods=["GET"])
def get_state():
    """
    GET /api/simulation/state
    Returns the complete current state without advancing. Coach values come from the
    simulation CSV and/or live vision telemetry depending on DATA_SOURCE.
    """
    return jsonify(_state())


@simulation_bp.route("/next", methods=["POST"])
def next_station():
    """
    POST /api/simulation/next
    Advances to the next station and returns the updated state.
    At the final station (with LOOP_AT_FINAL_STATION=False), stays put and
    includes a message field in the response.
    """
    advanced = g.simulator.advance()
    state = _state()

    if not advanced:
        state["message"] = (
            f"Already at the final station ({state['station']['current']}). "
            "Reset to return to the beginning."
        )

    return jsonify(state)


@simulation_bp.route("/reset", methods=["POST"])
def reset_simulation():
    """
    POST /api/simulation/reset
    Resets simulation to Station 1 and returns the initial state.
    """
    g.simulator.reset()
    state = _state()
    state["message"] = "Simulation reset to the first station."
    return jsonify(state)
