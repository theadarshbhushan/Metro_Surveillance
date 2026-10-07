# metro.py — Coach domain model.
# This is the ONLY place where per-coach calculations live.
# Swap the data source (CSV → load-cell → YOLO) without touching this file.

from config import COACH_CAPACITY_KG, NUM_COACHES
from logic import get_density_status


class Coach:
    """Represents a single metro coach with its current load."""

    def __init__(self, coach_id: int, current_load: float, previous_load: float = None):
        self.id = coach_id
        self.current_load = float(current_load)
        self.capacity = COACH_CAPACITY_KG
        # previous_load used to compute passenger movement (+/-)
        self._previous_load = float(previous_load) if previous_load is not None else float(current_load)

    @property
    def occupancy_percentage(self) -> float:
        """Occupancy as a rounded percentage (0–100+)."""
        if self.capacity == 0:
            return 0.0
        return round((self.current_load / self.capacity) * 100, 1)

    @property
    def available_capacity(self) -> float:
        """Remaining capacity in kg. Never goes below 0."""
        return max(0.0, round(self.capacity - self.current_load, 1))

    @property
    def density_status(self) -> str:
        """Human-readable density level based on thresholds in config.py."""
        return get_density_status(self.occupancy_percentage)

    @property
    def movement(self) -> float:
        """Passenger movement since last station (positive = boarded, negative = alighted)."""
        return round(self.current_load - self._previous_load, 1)

    unit = "kg"
    source = "simulation"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "current_load": self.current_load,
            "capacity": self.capacity,
            "occupancy_percentage": self.occupancy_percentage,
            "available_capacity": self.available_capacity,
            "density_status": self.density_status,
            "movement": self.movement,
            "source": self.source,
        }


class VisionCoach(Coach):
    """A coach whose load comes from the camera: load = people, capacity = max passengers.
    Percentage/density are the values computed from the vision telemetry (people / capacity)."""

    unit = "people"
    source = "vision"

    def __init__(self, row: dict):
        super().__init__(row["id"], row["current_load"], row["current_load"] - row.get("movement", 0))
        self.capacity = row["capacity"]
        self._pct = row["occupancy_percentage"]
        self._density = row["density_status"]
        self.vision = row.get("vision", {})

    @property
    def occupancy_percentage(self) -> float:
        return self._pct

    @property
    def density_status(self) -> str:
        return self._density

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["current_load"] = int(self.current_load)
        d["movement"] = int(self.movement)
        d["available_capacity"] = int(self.available_capacity)
        d["unit"] = self.unit
        d["vision"] = self.vision
        return d


def build_coaches_from_row(row: dict, previous_row: dict = None) -> list:
    """
    Turn a CSV row dict into a list of Coach objects.
    row keys: Station, Coach1, Coach2, Coach3, Coach4
    previous_row: the prior station's row (for movement calculation)
    """
    coaches = []
    for i in range(1, NUM_COACHES + 1):
        key = f"Coach{i}"
        if key not in row:
            continue
        prev_load = float(previous_row[key]) if previous_row and key in previous_row else None
        coaches.append(Coach(i, float(row[key]), prev_load))
    return coaches
