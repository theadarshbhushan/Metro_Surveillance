# tracker.py — fallback tracker.
#
# The primary tracker is ByteTrack/BoT-SORT running inside Ultralytics (see detector.py).
# If it cannot run (missing dependency, exception), the detector degrades to plain detection
# plus this deliberately tiny nearest-centroid tracker, so IDs stay roughly stable instead
# of the pipeline crashing.

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

from .types import Detection


class CentroidTracker:
    def __init__(self, max_distance: float = 120.0, max_missed: int = 10):
        self.max_distance = max_distance
        self.max_missed = max_missed
        self._next_id = 1
        self._tracks: Dict[int, Tuple[float, float, int]] = {}  # id -> (cx, cy, missed)

    def assign(self, detections: Sequence[Detection]) -> List[Detection]:
        """Sets track_id on each detection (greedy nearest match by bottom-centre)."""
        unmatched_tracks = set(self._tracks)
        pairs = []
        for di, det in enumerate(detections):
            for tid, (cx, cy, _) in self._tracks.items():
                d = math.hypot(det.bottom_center[0] - cx, det.bottom_center[1] - cy)
                if d <= self.max_distance:
                    pairs.append((d, di, tid))
        pairs.sort()
        used_det = set()
        for _, di, tid in pairs:
            if di in used_det or tid not in unmatched_tracks:
                continue
            detections[di].track_id = tid
            used_det.add(di)
            unmatched_tracks.discard(tid)
        for di, det in enumerate(detections):
            if di not in used_det:
                det.track_id = self._next_id
                self._next_id += 1
        for tid in unmatched_tracks:
            cx, cy, missed = self._tracks[tid]
            if missed + 1 > self.max_missed:
                del self._tracks[tid]
            else:
                self._tracks[tid] = (cx, cy, missed + 1)
        for det in detections:
            self._tracks[det.track_id] = (det.bottom_center[0], det.bottom_center[1], 0)
        return list(detections)
