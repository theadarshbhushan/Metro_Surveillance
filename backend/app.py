# app.py — Flask application entry point.
# Registers blueprints, configures CORS, holds the shared simulator instance.

import sys
import os

# Ensure backend/ is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# The repo root holds the shared `vision` package (density + ground-truth logic).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, g
from flask_cors import CORS

import config
from simulation import StationSimulator
from routes.simulation_routes import simulation_bp
from routes.vision_routes import vision_bp
from services.vision_service import VisionStateService


def create_app(vision_service: VisionStateService = None) -> Flask:
    app = Flask(__name__)

    # Allow all origins in development so Vite (localhost:5173) can reach us.
    # Restrict to specific origins in production.
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # One shared simulator instance for the lifetime of the process.
    # FUTURE: Replace with a session store if multi-user support is needed.
    simulator = StationSimulator()

    # Live telemetry from the Raspberry Pi / vision process (in-memory state).
    vision = vision_service or VisionStateService()

    # Attach the data sources to the request context before every request.
    # Routes read them from flask.g — no global variable, cleanly testable.
    @app.before_request
    def attach_sources():
        g.simulator = simulator
        g.vision = vision

    app.register_blueprint(simulation_bp)
    app.register_blueprint(vision_bp)

    # ------------------------------------------------------------------
    # Health check — confirms the server is alive
    # ------------------------------------------------------------------
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "ok",
            "system": "SmartMetro",
            "data_source": config.DATA_SOURCE,
            "vision_live": vision.state()["any_live"],
        })

    # ------------------------------------------------------------------
    # Generic error handlers
    # ------------------------------------------------------------------
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    print(f"SmartMetro backend running on http://localhost:5000 (DATA_SOURCE={config.DATA_SOURCE})")
    # use_reloader=False: the reloader would restart the in-memory vision state on file changes
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True, use_reloader=False)
