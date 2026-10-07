# routes/vision_routes.py — REST endpoints for real computer-vision telemetry.
# Routes only parse/serialise; all logic lives in VisionStateService.

from flask import Blueprint, Response, g, jsonify, request

import config
from services.vision_service import ValidationError, normalize_coach_id

vision_bp = Blueprint("vision", __name__, url_prefix="/api/vision")


def _bad_request(exc: ValidationError):
    return jsonify({"error": "Validation failed", "details": exc.errors}), 400


def _json_body():
    return request.get_json(silent=True)


@vision_bp.route("/state", methods=["GET"])
def get_state():
    """GET /api/vision/state — latest telemetry of every coach + recent alerts."""
    return jsonify(g.vision.state())


@vision_bp.route("/telemetry", methods=["POST"])
def post_telemetry():
    """POST /api/vision/telemetry — edge node pushes one JSON telemetry message."""
    try:
        return jsonify(g.vision.ingest(_json_body())), 200
    except ValidationError as exc:
        return _bad_request(exc)


@vision_bp.route("/coach/<coach_id>", methods=["GET"])
def get_coach(coach_id):
    if normalize_coach_id(coach_id) is None:
        return jsonify({"error": f"Invalid coach id '{coach_id}'"}), 400
    state = g.vision.coach(coach_id)
    if state is None:
        return jsonify({"error": f"No telemetry received for coach {coach_id}"}), 404
    return jsonify(state)


@vision_bp.route("/alerts", methods=["GET"])
def get_alerts():
    return jsonify({"alerts": g.vision.alerts()})


@vision_bp.route("/evaluation", methods=["GET"])
def get_evaluation():
    """GET /api/vision/evaluation[?coach_id=C1] — metrics from real ground truth only."""
    return jsonify(g.vision.evaluation(request.args.get("coach_id")))


@vision_bp.route("/evaluation", methods=["DELETE"])
def clear_evaluation():
    g.vision.clear_evaluation()
    return jsonify({"status": "cleared"})


@vision_bp.route("/ground-truth", methods=["POST"])
def post_ground_truth():
    """POST /api/vision/ground-truth — evaluator enters the actual number of people."""
    try:
        return jsonify(g.vision.add_ground_truth(_json_body())), 201
    except ValidationError as exc:
        return _bad_request(exc)


@vision_bp.route("/seat-config/<coach_id>", methods=["GET"])
def get_seat_config(coach_id):
    cfg = g.vision.get_seat_config(coach_id)
    if cfg is None:
        return jsonify({"error": f"No seat configuration for coach {coach_id}"}), 404
    return jsonify(cfg)


@vision_bp.route("/seat-config/<coach_id>", methods=["POST"])
def post_seat_config(coach_id):
    try:
        return jsonify(g.vision.set_seat_config(coach_id, _json_body())), 200
    except ValidationError as exc:
        return _bad_request(exc)


@vision_bp.route("/frame", methods=["POST"])
def post_frame():
    """POST /api/vision/frame?coach_id=C1 — latest ANNOTATED snapshot (JPEG body), not raw video."""
    data = request.get_data(cache=False)
    if len(data) > config.MAX_FRAME_BYTES:
        return jsonify({"error": "Frame too large"}), 413
    if not g.vision.set_frame(request.args.get("coach_id", "C1"), data):
        return jsonify({"error": "Body must be a JPEG image and coach_id valid"}), 400
    return jsonify({"status": "ok"})


@vision_bp.route("/frame", methods=["GET"])
def get_frame():
    """GET /api/vision/frame?coach_id=C1 — latest annotated snapshot as image/jpeg."""
    item = g.vision.get_frame(request.args.get("coach_id", "C1"))
    if item is None:
        return jsonify({"error": "No frame available"}), 404
    return Response(item[0], mimetype="image/jpeg", headers={"Cache-Control": "no-store"})
