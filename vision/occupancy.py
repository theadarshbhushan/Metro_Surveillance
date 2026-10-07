# occupancy.py — seat occupancy + seated/standing/unknown classification.
#
# Per processed frame:
#   1. every tracked person is mapped to candidate seat polygons (SeatMapper)
#   2. each person gets AT MOST ONE seat and each seat AT MOST ONE person
#      (greedy best-score assignment; stable holders win conflicts)
#   3. a per-seat counter confirms OCCUPIED only after OCCUPANCY_CONFIRM_FRAMES
#      consecutive-ish candidate frames and releases it only after
#      EMPTY_CONFIRM_FRAMES frames without a candidate (temporal verification)
#   4. persons are classified from the *confirmed* seat state, never from one frame

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from .seat_mapper import SeatMapper
from .types import (
    Detection, FrameResult, PersonState, SeatState,
    PERSON_SEATED, PERSON_STANDING, PERSON_UNKNOWN,
    SEAT_EMPTY, SEAT_OCCUPIED, SEAT_UNCERTAIN,
)


class _SeatTracker:
    """Temporal state of one seat."""

    def __init__(self, seat_id: str):
        self.seat_id = seat_id
        self.status = SEAT_EMPTY
        self.holder: Optional[int] = None  # track id of the person holding the seat
        self.has_holder_track = False
        self.candidate_streak = 0
        self.empty_streak = 0


class OccupancyEngine:
    def __init__(
        self,
        mapper: Optional[SeatMapper],
        occupancy_confirm_frames: int = 5,
        empty_confirm_frames: int = 5,
        standing_confirm_frames: int = 3,
        standing_min_confidence: float = 0.5,
        truncated_bottom_margin: int = 3,
        truncated_standing_min_height: float = 0.0,
        stale_track_frames: int = 60,
    ):
        self.mapper = mapper
        self.occupancy_confirm_frames = max(1, occupancy_confirm_frames)
        self.empty_confirm_frames = max(1, empty_confirm_frames)
        self.standing_confirm_frames = max(1, standing_confirm_frames)
        self.standing_min_confidence = standing_min_confidence
        self.truncated_bottom_margin = truncated_bottom_margin
        self.truncated_standing_min_height = truncated_standing_min_height
        self.stale_track_frames = stale_track_frames
        self._seats: Dict[str, _SeatTracker] = {}
        self._track_seen: Dict[int, List[int]] = {}  # track_id -> [frames_seen, last_frame]
        self._frame_index = 0
        self.set_mapper(mapper)

    def set_mapper(self, mapper: Optional[SeatMapper]) -> None:
        self.mapper = mapper
        ids = mapper.seat_ids if mapper else []
        self._seats = {sid: self._seats.get(sid) or _SeatTracker(sid) for sid in ids}

    # ------------------------------------------------------------------
    def update(self, detections: Sequence[Detection], frame_size: Optional[Tuple[int, int]] = None) -> FrameResult:
        """Process one frame of detections. frame_size = (width, height) of that frame."""
        self._frame_index += 1
        mapper = self.mapper
        if mapper is not None and frame_size is not None:
            mapper = mapper.scaled(*frame_size)

        seen_counts = self._update_track_ages(detections)

        # --- 1/2: person -> seat candidates and conflict-free assignment ---
        candidates: List[List] = []  # per detection: list of SeatCandidate
        pairs: List[Tuple[float, int, str]] = []
        for di, det in enumerate(detections):
            cands = mapper.candidates_for(det.bbox) if mapper else []
            candidates.append(cands)
            for c in cands:
                holder_bonus = 1.0 if (det.track_id is not None and self._seats[c.seat_id].holder == det.track_id
                                       and self._seats[c.seat_id].status == SEAT_OCCUPIED) else 0.0
                stability = min(seen_counts[di], 50) / 50.0 * 0.5
                pairs.append((holder_bonus + stability + c.overlap + 0.1 * det.confidence, di, c.seat_id))
        pairs.sort(key=lambda p: p[0], reverse=True)

        seat_to_det: Dict[str, int] = {}
        det_to_seat: Dict[int, str] = {}
        for _, di, sid in pairs:
            if sid in seat_to_det or di in det_to_seat:
                continue
            seat_to_det[sid] = di
            det_to_seat[di] = sid

        # --- 3: temporal verification per seat ---
        for sid, st in self._seats.items():
            di = seat_to_det.get(sid)
            if di is not None:
                st.candidate_streak += 1
                st.empty_streak = 0
                tid = detections[di].track_id
                st.holder = tid
            else:
                st.empty_streak += 1
                st.candidate_streak = max(0, st.candidate_streak - 1)

            if st.status == SEAT_OCCUPIED:
                if st.empty_streak >= self.empty_confirm_frames:
                    st.status, st.holder, st.candidate_streak = SEAT_EMPTY, None, 0
            elif st.candidate_streak >= self.occupancy_confirm_frames:
                st.status = SEAT_OCCUPIED
            elif st.candidate_streak > 0:
                st.status = SEAT_UNCERTAIN  # someone is there but not yet confirmed
            else:
                st.status, st.holder = SEAT_EMPTY, None

        # --- 4: person classification ---
        frame_h = frame_size[1] if frame_size else None
        persons: List[PersonState] = []
        for di, det in enumerate(detections):
            sid = det_to_seat.get(di)
            if sid is not None:
                if self._seats[sid].status == SEAT_OCCUPIED:
                    persons.append(PersonState(det, PERSON_SEATED, sid, "confirmed seat"))
                else:
                    persons.append(PersonState(det, PERSON_UNKNOWN, sid, "seat not yet confirmed"))
            elif candidates[di]:
                persons.append(PersonState(det, PERSON_UNKNOWN, None, "seat conflict"))
            else:
                persons.append(self._classify_unseated(det, seen_counts[di], frame_h))

        result = FrameResult(
            seats={sid: SeatState(sid, st.status, st.holder if st.status == SEAT_OCCUPIED else None)
                   for sid, st in self._seats.items()},
            persons=persons,
        )
        return result

    # ------------------------------------------------------------------
    def _classify_unseated(self, det: Detection, seen: int, frame_h: Optional[int]) -> PersonState:
        if det.confidence < self.standing_min_confidence:
            return PersonState(det, PERSON_UNKNOWN, None, "low confidence")
        if frame_h is not None and det.bbox[3] >= frame_h - self.truncated_bottom_margin:
            tall = (det.bbox[3] - det.bbox[1]) / frame_h
            if self.truncated_standing_min_height > 0 and tall >= self.truncated_standing_min_height:
                if det.track_id is None or seen >= self.standing_confirm_frames:
                    return PersonState(det, PERSON_STANDING, None, "tall, outside every seat")
                return PersonState(det, PERSON_UNKNOWN, None, "track not yet stable")
            return PersonState(det, PERSON_UNKNOWN, None, "cut off at frame bottom")
        if det.track_id is not None and seen < self.standing_confirm_frames:
            return PersonState(det, PERSON_UNKNOWN, None, "track not yet stable")
        return PersonState(det, PERSON_STANDING, None, "no seat")

    def _update_track_ages(self, detections: Sequence[Detection]) -> List[int]:
        """Returns frames-seen for every detection; detections without a track id count as stable."""
        counts: List[int] = []
        for det in detections:
            if det.track_id is None:
                counts.append(self.standing_confirm_frames)
                continue
            rec = self._track_seen.setdefault(det.track_id, [0, self._frame_index])
            rec[0] += 1
            rec[1] = self._frame_index
            counts.append(rec[0])
        stale = [t for t, (_, last) in self._track_seen.items() if self._frame_index - last > self.stale_track_frames]
        for t in stale:
            del self._track_seen[t]
        return counts
