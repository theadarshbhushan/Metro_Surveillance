# types.py — small shared data structures (no heavy imports).

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Seat states
SEAT_OCCUPIED, SEAT_EMPTY, SEAT_UNCERTAIN = "OCCUPIED", "EMPTY", "UNCERTAIN"
# Person states
PERSON_SEATED, PERSON_STANDING, PERSON_UNKNOWN = "SEATED", "STANDING", "UNKNOWN"


@dataclass
class Detection:
    """One tracked person in one frame."""
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float
    track_id: Optional[int] = None  # None when the tracker could not provide an ID
    cls: str = "person"

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def bottom_center(self) -> Tuple[float, float]:
        x1, _, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, y2)

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "bbox": [round(v, 1) for v in self.bbox],
            "confidence": round(self.confidence, 3),
            "class": self.cls,
            "center": [round(v, 1) for v in self.center],
            "bottom_center": [round(v, 1) for v in self.bottom_center],
        }


@dataclass
class PersonState:
    detection: Detection
    state: str  # SEATED / STANDING / UNKNOWN
    seat_id: Optional[str] = None
    reason: str = ""


@dataclass
class SeatState:
    seat_id: str
    status: str = SEAT_EMPTY
    track_id: Optional[int] = None  # current/last holder track (temporary ID, not personal data)


@dataclass
class FrameResult:
    seats: Dict[str, SeatState] = field(default_factory=dict)
    persons: List[PersonState] = field(default_factory=list)

    def counts(self) -> dict:
        """Counts guaranteeing total = seated + standing + unknown and occupied_seats = seated.

        A confirmed OCCUPIED seat is one seated passenger even if that person is briefly not
        detected (temporal grace period), so seated_people is derived from seats."""
        occupied = sum(1 for s in self.seats.values() if s.status == SEAT_OCCUPIED)
        empty = sum(1 for s in self.seats.values() if s.status == SEAT_EMPTY)
        uncertain = sum(1 for s in self.seats.values() if s.status == SEAT_UNCERTAIN)
        standing = sum(1 for p in self.persons if p.state == PERSON_STANDING)
        unknown = sum(1 for p in self.persons if p.state == PERSON_UNKNOWN)
        return {
            "seated": occupied,
            "standing": standing,
            "unknown": unknown,
            "occupied_seats": occupied,
            "empty_seats": empty,
            "uncertain_seats": uncertain,
        }
