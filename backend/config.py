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

# If True, POST /next at the final station cycles back to Station 1.
# If False, it stays at the final station and returns at_final_station=True.
LOOP_AT_FINAL_STATION = False
