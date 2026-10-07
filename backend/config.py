# config.py — All tunable constants live here.
# Change values here; nothing else needs to change.

# Coach capacity in kg (simulation units)
COACH_CAPACITY_KG = 100

# Number of coaches per train
NUM_COACHES = 4

# -------------------------------------------------------
# Density thresholds (occupancy %)
# These drive density_status classifications.
# -------------------------------------------------------
THRESHOLD_MODERATE = 40   # >40% → MODERATE
THRESHOLD_HIGH = 65       # >65% → HIGH
THRESHOLD_CRITICAL = 85   # >85% → CRITICAL

# Density labels (kept central so logic.py never hardcodes strings)
DENSITY_LOW = "LOW"
DENSITY_MODERATE = "MODERATE"
DENSITY_HIGH = "HIGH"
DENSITY_CRITICAL = "CRITICAL"

# -------------------------------------------------------
# Real computer-vision data source (Raspberry Pi edge node)
# Every value can be overridden with an environment variable.
# -------------------------------------------------------
import os as _os

# "simulation" -> CSV only | "vision" -> camera telemetry only | "auto" -> vision when live, else CSV
DATA_SOURCE = _os.environ.get("DATA_SOURCE", "auto").strip().lower()
if DATA_SOURCE not in ("simulation", "vision", "auto"):
    DATA_SOURCE = "auto"

# Crowd capacity used for vision coaches: occupancy % = people / MAX_PASSENGERS_PER_COACH
MAX_PASSENGERS_PER_COACH = int(_os.environ.get("MAX_PASSENGERS_PER_COACH", 40))

# Telemetry older than this is considered "not live" (edge node stopped / network lost)
VISION_STALE_SECONDS = float(_os.environ.get("VISION_STALE_SECONDS", 10))

# Alerting: a HIGH/CRITICAL alert for a coach is not repeated within this window
ALERT_COOLDOWN_SECONDS = float(_os.environ.get("ALERT_COOLDOWN_SECONDS", 60))
MAX_ALERTS = 100

# "Movement" of a vision coach = change in people vs. this many seconds ago
MOVEMENT_WINDOW_SECONDS = float(_os.environ.get("MOVEMENT_WINDOW_SECONDS", 10))

_BACKEND_DIR = _os.path.dirname(_os.path.abspath(__file__))
SEAT_CONFIG_PATH = _os.environ.get("SEAT_CONFIG_PATH", _os.path.join(_BACKEND_DIR, "data", "seat_config.json"))
EVAL_LOG_PATH = _os.environ.get("EVAL_LOG_PATH", _os.path.join(_BACKEND_DIR, "data", "evaluation_log.json"))
MAX_FRAME_BYTES = 2 * 1024 * 1024

# If True, POST /next at the final station cycles back to Station 1.
# If False, it stays at the final station and returns at_final_station=True.
LOOP_AT_FINAL_STATION = False
