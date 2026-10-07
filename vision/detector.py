# detector.py — pretrained YOLO person detection + tracking (Ultralytics).
#
# Only the COCO "person" class (id 0) is requested. Tracking uses Ultralytics' built-in
# ByteTrack/BoT-SORT. YOLO never decides "seated"/"standing" — that comes from seat geometry.

from __future__ import annotations

import logging
from typing import List

import numpy as np

from .settings import Settings
from .tracker import CentroidTracker
from .types import Detection

log = logging.getLogger(__name__)

PERSON_CLASS_ID = 0


class PersonDetector:
    def __init__(self, settings: Settings):
        from ultralytics import YOLO  # imported lazily: heavy, and may be missing

        self.settings = settings
        self.model = YOLO(settings.model_path)
        self._use_tracker = True
        self._fallback = CentroidTracker()
        log.info("YOLO model loaded: %s", settings.model_path)

    def detect(self, frame: np.ndarray) -> List[Detection]:
        s = self.settings
        if self._use_tracker:
            try:
                results = self.model.track(
                    frame, persist=True, classes=[PERSON_CLASS_ID], conf=s.confidence_threshold,
                    imgsz=s.inference_size, tracker=s.tracker_config, verbose=False,
                )
                return self._parse(results[0])
            except Exception as exc:  # noqa: BLE001 - e.g. tracker dependency problems
                log.warning("Tracking failed (%s); falling back to detection + centroid tracker", exc)
                self._use_tracker = False
        results = self.model.predict(
            frame, classes=[PERSON_CLASS_ID], conf=s.confidence_threshold,
            imgsz=s.inference_size, verbose=False,
        )
        return self._fallback.assign(self._parse(results[0]))

    @staticmethod
    def suppress_fragments(dets: List[Detection], containment: float = 0.85) -> List[Detection]:
        """Remove duplicate/partial person boxes (common in crowded coaches).

        * a box almost entirely inside a higher-confidence box is a body fragment -> dropped
        * two boxes that share (almost) the same feet position and where one is mostly inside the
          other describe the same person -> the lower-confidence one is dropped
        Counting either would create a phantom person and a phantom seat conflict."""
        keep: List[Detection] = []
        for d in sorted(dets, key=lambda d: d.confidence, reverse=True):
            x1, y1, x2, y2 = d.bbox
            area = max(1e-6, (x2 - x1) * (y2 - y1))
            drop = False
            for k in keep:
                kx1, ky1, kx2, ky2 = k.bbox
                ix = max(0.0, min(x2, kx2) - max(x1, kx1))
                iy = max(0.0, min(y2, ky2) - max(y1, ky1))
                inter = ix * iy
                karea = max(1e-6, (kx2 - kx1) * (ky2 - ky1))
                if inter / area >= containment:
                    drop = True
                elif inter / karea >= containment:  # k nested in d: same person only if feet coincide
                    feet = abs(d.bottom_center[1] - k.bottom_center[1]) <= 0.06 * (y2 - y1)
                    drop = feet and abs(d.bottom_center[0] - k.bottom_center[0]) <= 0.25 * (x2 - x1)
                if drop:
                    break
            if not drop:
                keep.append(d)
        return keep

    @staticmethod
    def _parse(result) -> List[Detection]:
        out: List[Detection] = []
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return out
        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else [None] * len(xyxy)
        for box, conf, tid in zip(xyxy, confs, ids):
            out.append(Detection(
                bbox=tuple(float(v) for v in box),
                confidence=float(conf),
                track_id=int(tid) if tid is not None else None,
            ))
        return PersonDetector.suppress_fragments(out)
