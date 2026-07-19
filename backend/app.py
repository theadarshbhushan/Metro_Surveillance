# app.py — Flask application entry point.
# Registers blueprints, configures CORS, holds the shared simulator instance.

import sys
import os

# Ensure backend/ is on the path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, g
from flask_cors import CORS

from simulation import StationSimulator
from routes.simulation_routes import simulation_bp


def create_app() -> Flask:
    app = Flask(__name__)

    # Allow all origins in development so Vite (localhost:5173) can reach us.
    # Restrict to specific origins in production.
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # One shared simulator instance for the lifetime of the process.
    # FUTURE: Replace with a session store if multi-user support is needed.
    simulator = StationSimulator()

    # Attach the simulator to the request context before every request.
    # Routes read it from flask.g — no global variable, cleanly testable.
    @app.before_request
    def attach_simulator():
        g.simulator = simulator

    app.register_blueprint(simulation_bp)

    # ------------------------------------------------------------------
    # Health check — confirms the server is alive
    # ------------------------------------------------------------------
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "system": "SmartMetro"})

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
    print("SmartMetro backend running on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
