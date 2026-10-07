# seat_mapper.py — Seat Polygon Mapping Algorithm (geometry only, no temporal logic).
#
# The camera is fixed, so seats are fixed polygons in image space. For every
# detected person we test whether the bottom-centre of the bounding box
# (roughly where the body meets the seat/floor) falls inside a seat polygon.
# The overlap between the bounding box and the polygon is used as a secondary
# score to break ties when polygons overlap or several people compete.

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

log = logging.getLogger(__name__)

Point = Tuple[float, float]
Polygon = List[List[float]]


@dataclass
class SeatCandidate:
    seat_id: str
    overlap: float  # fraction of the person's bbox area lying inside the seat polygon


def _contour(poly: Sequence[Sequence[float]]) -> np.ndarray:
    return np.array(poly, dtype=np.float32).reshape(-1, 1, 2)


def point_in_polygon(point: Point, poly: Sequence[Sequence[float]]) -> bool:
    """True if the point is inside or on the border of the polygon."""
    if len(poly) < 3:
        return False
    return cv2.pointPolygonTest(_contour(poly), (float(point[0]), float(point[1])), False) >= 0


def bbox_polygon_overlap(bbox: Sequence[float], poly: Sequence[Sequence[float]]) -> float:
    """Fraction of the bbox area that lies inside the (convex) seat polygon."""
    x1, y1, x2, y2 = bbox
    area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if area <= 0 or len(poly) < 3:
        return 0.0
    box = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
    try:
        inter, _ = cv2.intersectConvexConvex(_contour(poly), box.reshape(-1, 1, 2))
    except cv2.error:
        return 0.0
    return float(min(1.0, max(0.0, inter / area)))


class SeatMapper:
    """Holds the seat polygons of one coach and maps points/boxes to seats."""

    def __init__(self, seats: Dict[str, Polygon], frame_size: Optional[Tuple[int, int]] = None,
                 reference_image: Optional[str] = None):
        self.reference_image = reference_image  # path (relative to the config file) of the frame the polygons were drawn on
        self.seats: Dict[str, Polygon] = {k: [list(map(float, p)) for p in v] for k, v in seats.items()}
        self.frame_size = frame_size  # (w, h) of the reference frame the polygons were drawn on

    @property
    def seat_ids(self) -> List[str]:
        return list(self.seats.keys())

    def scaled(self, width: int, height: int) -> "SeatMapper":
        """Return polygons rescaled when the live frame size differs from the reference frame."""
        if not self.frame_size or (width, height) == tuple(self.frame_size):
            return self
        sx, sy = width / self.frame_size[0], height / self.frame_size[1]
        seats = {sid: [[x * sx, y * sy] for x, y in poly] for sid, poly in self.seats.items()}
        return SeatMapper(seats, (width, height))

    def candidates_for(self, bbox: Sequence[float]) -> List[SeatCandidate]:
        """All seats whose polygon contains the bottom-centre of the bbox, best overlap first."""
        x1, y1, x2, y2 = bbox
        bottom_center = ((x1 + x2) / 2.0, y2)
        found = [
            SeatCandidate(sid, bbox_polygon_overlap(bbox, poly))
            for sid, poly in self.seats.items()
            if point_in_polygon(bottom_center, poly)
        ]
        found.sort(key=lambda c: c.overlap, reverse=True)
        return found

    # ---- persistence -------------------------------------------------
    @classmethod
    def from_config(cls, config: dict, coach_id: str) -> Optional["SeatMapper"]:
        """Parse one coach from a seat_config dict. Accepts 'C1', 'c1' and 'coach_1' keys and
        both {"S1": [...]} and {"frame_size": [w, h], "seats": {...}} layouts."""
        entry = find_coach_entry(config, coach_id)
        if entry is None:
            return None
        frame_size = None
        reference_image = None
        seats = entry
        if isinstance(entry, dict) and "seats" in entry:
            seats = entry["seats"]
            reference_image = entry.get("reference_image")
            fs = entry.get("frame_size")
            if fs and len(fs) == 2:
                frame_size = (int(fs[0]), int(fs[1]))
        return cls(validate_seats(seats), frame_size, reference_image)

    @classmethod
    def from_file(cls, path: str, coach_id: str) -> Optional["SeatMapper"]:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return cls.from_config(json.load(fh), coach_id)
        except FileNotFoundError:
            log.warning("Seat config %s not found - running without seats", path)
        except (ValueError, OSError) as exc:
            log.error("Could not read seat config %s: %s", path, exc)
        return None


def _coach_aliases(coach_id: str) -> List[str]:
    cid = str(coach_id).strip()
    digits = "".join(ch for ch in cid if ch.isdigit())
    aliases = [cid, cid.upper(), cid.lower()]
    if digits:
        aliases += [f"C{digits}", f"c{digits}", f"coach_{digits}", f"coach{digits}", digits]
    return aliases


def find_coach_entry(config: dict, coach_id: str):
    if not isinstance(config, dict):
        return None
    for key in _coach_aliases(coach_id):
        if key in config:
            return config[key]
    return None


def validate_seats(seats) -> Dict[str, Polygon]:
    """Validate a {seat_id: [[x, y], ...]} mapping; raises ValueError on bad input."""
    if not isinstance(seats, dict):
        raise ValueError("seats must be an object mapping seat id to polygon points")
    clean: Dict[str, Polygon] = {}
    for sid, poly in seats.items():
        if isinstance(poly, dict):  # {"S1": {"polygon": [[x, y], ...]}} layout
            poly = poly.get("polygon")
        if not isinstance(poly, (list, tuple)) or len(poly) < 3:
            raise ValueError(f"seat {sid}: polygon needs at least 3 points")
        pts = []
        for pt in poly:
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise ValueError(f"seat {sid}: each point must be [x, y]")
            try:
                pts.append([float(pt[0]), float(pt[1])])
            except (TypeError, ValueError):
                raise ValueError(f"seat {sid}: point coordinates must be numbers")
        clean[str(sid)] = pts
    return clean


def list_coaches(config: dict) -> List[str]:
    return [k for k, v in config.items() if isinstance(v, dict)]


def load_seat_config(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_coach_seats(path: str, coach_id: str, seats: Dict[str, Polygon],
                     frame_size: Optional[Tuple[int, int]] = None, reference_image: Optional[str] = None) -> None:
    """Merge one coach into the seat config file (other coaches are preserved)."""
    clean = validate_seats(seats)
    config = load_seat_config(path)
    entry: dict = {"seats": clean}
    if frame_size:
        entry["frame_size"] = [int(frame_size[0]), int(frame_size[1])]
    if reference_image:
        entry["reference_image"] = reference_image
    config[str(coach_id)] = entry
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
    os.replace(tmp, path)
