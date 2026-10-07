# overlay.py — debug / surveillance overlay drawn on the frame with OpenCV.

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from .seat_mapper import SeatMapper
from .types import (
    FrameResult, PERSON_SEATED, PERSON_STANDING,
    SEAT_EMPTY, SEAT_OCCUPIED,
)

SEAT_COLORS = {SEAT_OCCUPIED: (60, 60, 230), SEAT_EMPTY: (80, 200, 80)}  # BGR; default = UNCERTAIN
UNCERTAIN_COLOR = (0, 190, 255)
PERSON_COLORS = {PERSON_SEATED: (230, 120, 40), PERSON_STANDING: (200, 60, 200)}
UNKNOWN_COLOR = (150, 150, 150)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def _label(img, text, org, color, scale=0.5):
    (w, h), base = cv2.getTextSize(text, FONT, scale, 1)
    x, y = int(org[0]), int(org[1])
    cv2.rectangle(img, (x, y - h - base), (x + w + 2, y + base), color, -1)
    cv2.putText(img, text, (x + 1, y), FONT, scale, (255, 255, 255), 1, cv2.LINE_AA)


def draw_overlay(frame: np.ndarray, result: FrameResult, mapper: Optional[SeatMapper],
                 stats: dict, fps: Optional[dict] = None, scale: float = 1.0) -> np.ndarray:
    """Return a copy of `frame` annotated with seats, people and summary statistics.

    scale > 1 enlarges the output (for small stills) so labels stay readable; labels are then
    shortened (no confidence) and placed at the person's feet to avoid overlapping each other."""
    h, w = frame.shape[:2]
    if mapper is not None:
        mapper = mapper.scaled(w, h)
    img = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC) if scale != 1.0 else frame.copy()
    fs = 0.45 * max(1.0, scale * 0.8)
    th = max(2, int(round(2 * scale * 0.7)))

    def sc(v):
        return int(round(v * scale))

    # seat polygons (translucent fill + border + id/status)
    if mapper is not None:
        fill = img.copy()
        for sid, poly in mapper.seats.items():
            st = result.seats.get(sid)
            color = SEAT_COLORS.get(st.status, UNCERTAIN_COLOR) if st else UNCERTAIN_COLOR
            cv2.fillPoly(fill, [np.array([[sc(x), sc(y)] for x, y in poly], dtype=np.int32)], color)
        img = cv2.addWeighted(fill, 0.25, img, 0.75, 0)
        for sid, poly in mapper.seats.items():
            st = result.seats.get(sid)
            color = SEAT_COLORS.get(st.status, UNCERTAIN_COLOR) if st else UNCERTAIN_COLOR
            pts = np.array([[sc(x), sc(y)] for x, y in poly], dtype=np.int32)
            cv2.polylines(img, [pts], True, color, th)
            _label(img, sid if scale != 1.0 else f"{sid} {st.status if st else ''}".strip(),
                   (pts[:, 0].min() + 2, pts[:, 1].min() + int(14 * max(1.0, scale * 0.8))), color, fs)

    # people
    for p in result.persons:
        x1, y1, x2, y2 = [sc(v) for v in p.detection.bbox]
        color = PERSON_COLORS.get(p.state, UNKNOWN_COLOR)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, th)
        tid = p.detection.track_id
        text = f"P{tid if tid is not None else '?'} {p.state}"
        if p.seat_id:
            text += f" {p.seat_id}"
        if scale == 1.0:
            text += f" {p.detection.confidence:.2f}"
            _label(img, text, (x1, max(14, y1)), color, fs)
        else:
            _label(img, text, (x1 + 2, max(18, min(y2 - 4, img.shape[0] - 6))), color, fs)
        bx, by = [sc(v) for v in p.detection.bottom_center]
        cv2.circle(img, (bx, by), max(4, int(4 * scale * 0.8)), (0, 255, 255), -1)

    # summary panel
    lines = [
        f"People: {stats['total_people']} / {stats['max_passengers']}",
        f"Seated: {stats['seated_people']}  Standing: {stats['standing_people']}  Unknown: {stats['unknown_people']}",
        f"Seats  occ: {stats['occupied_seats']}  empty: {stats['empty_seats']}  uncertain: {stats['uncertain_seats']}",
        f"Density: {stats['density_status']} ({stats['occupancy_percentage']}%)",
    ]
    if fps and scale == 1.0:
        lines.append(f"FPS capture {fps.get('capture', 0):.1f} | infer {fps.get('inference', 0):.1f}"
                     f" | telemetry {fps.get('telemetry', 0):.2f}/s")
    ps = max(1.0, scale * 0.8)
    lh = int(18 * ps)
    cv2.rectangle(img, (6, 6), (min(img.shape[1] - 6, int(470 * ps)), 6 + 8 + lh * len(lines)), (30, 30, 30), -1)
    for i, line in enumerate(lines):
        cv2.putText(img, line, (12, 6 + int(16 * ps) + lh * i), FONT, 0.5 * ps, (255, 255, 255), 1, cv2.LINE_AA)
    return img
