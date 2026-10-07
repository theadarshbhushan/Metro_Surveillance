# pipeline.py — glue: frame source -> detector -> occupancy -> density -> telemetry.
#
# The same Pipeline runs for recorded video and live cameras. It never raises on
# runtime problems (model missing, camera drop, backend down): it logs and carries on.

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

import cv2

from .camera import FrameSource
from .density import compute_stats
from .ground_truth import make_sample
from .occupancy import OccupancyEngine
from .overlay import draw_overlay
from .seat_mapper import SeatMapper
from .settings import Settings
from .types import Detection, FrameResult

log = logging.getLogger(__name__)


class _RateMeter:
    """Events per second over a sliding window."""

    def __init__(self, window: float = 3.0):
        self.window = window
        self._times: List[float] = []

    def tick(self) -> None:
        now = time.time()
        self._times = [t for t in self._times if now - t < self.window] + [now]

    @property
    def rate(self) -> float:
        now = time.time()
        times = [t for t in self._times if now - t < self.window]
        if len(times) < 2:
            return 0.0
        return (len(times) - 1) / max(1e-6, times[-1] - times[0])


class Pipeline:
    def __init__(
        self,
        settings: Settings,
        source: FrameSource,
        detector=None,
        detector_factory: Optional[Callable[[], object]] = None,
        mapper: Optional[SeatMapper] = None,
        client=None,
        annotations: Optional[Dict[int, int]] = None,
    ):
        self.s = settings
        self.source = source
        self.detector = detector
        self._detector_factory = detector_factory
        self._next_model_try = 0.0
        self.mapper = mapper
        self.engine = OccupancyEngine(
            mapper,
            occupancy_confirm_frames=settings.occupancy_confirm_frames,
            empty_confirm_frames=settings.empty_confirm_frames,
            standing_confirm_frames=settings.standing_confirm_frames,
            standing_min_confidence=settings.standing_min_confidence,
            truncated_bottom_margin=settings.truncated_bottom_margin,
            truncated_standing_min_height=settings.truncated_standing_min_height,
            stale_track_frames=settings.stale_track_frames,
        )
        self.client = client
        self.annotations = annotations or {}
        self.capture_meter, self.infer_meter, self.telemetry_meter = _RateMeter(), _RateMeter(), _RateMeter()
        self._last_telemetry = 0.0
        self._last_frame_upload = 0.0
        self.processed_frames = 0
        self.last_result: Optional[FrameResult] = None
        self.last_stats: Optional[dict] = None
        self.local_samples: List[dict] = []  # ground-truth samples from an annotation file (mode B)

    # ------------------------------------------------------------------
    def _ensure_detector(self) -> bool:
        if self.detector is not None:
            return True
        if self._detector_factory is None or time.time() < self._next_model_try:
            return False
        try:
            self.detector = self._detector_factory()
            return True
        except Exception as exc:  # noqa: BLE001 - missing weights, no network, bad install...
            log.error("YOLO model could not be loaded (%s). Retrying in %.0fs; no telemetry is sent meanwhile.",
                      exc, self.s.model_retry_seconds)
            self._next_model_try = time.time() + self.s.model_retry_seconds
            return False

    def fps_info(self) -> dict:
        return {
            "capture": round(self.capture_meter.rate, 2),
            "inference": round(self.infer_meter.rate, 2),
            "telemetry": round(self.telemetry_meter.rate, 3),
        }

    def build_telemetry(self, result: FrameResult, frame_index: int) -> dict:
        counts = result.counts()
        stats = compute_stats(
            counts["seated"], counts["standing"], counts["unknown"],
            counts["occupied_seats"], counts["empty_seats"], counts["uncertain_seats"],
            self.s.max_passengers_per_coach, self.s.density_thresholds,
        )
        payload = {
            "coach_id": self.s.coach_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "frame": frame_index,
            **stats,
            "seats": {sid: {"status": st.status, "track_id": st.track_id} for sid, st in result.seats.items()},
            "fps": self.fps_info(),
        }
        return payload

    # ------------------------------------------------------------------
    def process_frame(self, frame, frame_index: int = 0) -> Optional[dict]:
        """Run one frame through detection and occupancy. Returns the telemetry dict (or None
        when no detector is available — in that case nothing is fabricated)."""
        if not self._ensure_detector():
            return None
        try:
            detections: List[Detection] = self.detector.detect(frame)
        except Exception as exc:  # noqa: BLE001
            log.error("Inference failed on frame %s: %s", frame_index, exc)
            return None
        self.infer_meter.tick()
        h, w = frame.shape[:2]
        result = self.engine.update(detections, (w, h))
        self.processed_frames += 1
        payload = self.build_telemetry(result, frame_index)
        self.last_result, self.last_stats = result, payload

        if frame_index in self.annotations:  # mode B: hand-annotated reference video
            self.local_samples.append(make_sample(
                self.annotations[frame_index], payload["total_people"], self.s.max_passengers_per_coach,
                self.s.density_thresholds, frame=frame_index, coach_id=self.s.coach_id,
            ))
        return payload

    def annotate(self, frame, scale: float = 1.0):
        if self.last_result is None or self.last_stats is None:
            return frame
        return draw_overlay(frame, self.last_result, self.mapper, self.last_stats, self.fps_info(), scale=scale)

    def _maybe_send(self, frame, payload: dict) -> None:
        if self.client is None:
            return
        now = time.time()
        if now - self._last_telemetry >= self.s.telemetry_interval:
            self._last_telemetry = now
            self.telemetry_meter.tick()
            self.client.submit_telemetry(payload)
        if self.s.frame_upload_interval > 0 and now - self._last_frame_upload >= self.s.frame_upload_interval:
            self._last_frame_upload = now
            self.client.submit_frame(self._encode(self.annotate(frame)))

    def _encode(self, img) -> bytes:
        h, w = img.shape[:2]
        if w > self.s.frame_upload_width:
            img = cv2.resize(img, (self.s.frame_upload_width, int(h * self.s.frame_upload_width / w)))
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, self.s.frame_jpeg_quality])
        return buf.tobytes() if ok else b""

    # ------------------------------------------------------------------
    def run(self, show: bool = False, max_frames: Optional[int] = None, debug: bool = False,
            writer=None, realtime: bool = False) -> None:
        """Main loop. Stops at end of a video file, on 'q' in the preview window, or Ctrl+C."""
        misses = 0
        loop_count = 0
        last_debug = 0.0
        frame_period = (1.0 / self.source.fps) if (realtime and self.source.fps > 0) else 0.0
        try:
            while max_frames is None or self.processed_frames < max_frames:
                t0 = time.time()
                ok, frame = self.source.read()
                if not ok:
                    if self.source.is_live:
                        misses += 1
                        if misses % 5 == 1:
                            log.warning("No frame from camera (%d consecutive misses)", misses)
                        continue
                    log.info("End of video")
                    break
                misses = 0
                loop_count += 1
                self.capture_meter.tick()
                frame_index = self.source.frame_index or loop_count

                if (loop_count - 1) % max(1, self.s.frame_skip) == 0:
                    payload = self.process_frame(frame, frame_index)
                    if payload is not None:
                        self._maybe_send(frame, payload)

                if show or writer is not None:
                    vis = self.annotate(frame)
                    if writer is not None:
                        writer.write(vis)
                    if show:
                        cv2.imshow("Smart Metro vision (q to quit)", vis)
                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            break
                if debug and time.time() - last_debug > 2.0:
                    last_debug = time.time()
                    log.info("FPS %s | people %s", self.fps_info(),
                             self.last_stats["total_people"] if self.last_stats else "-")
                if frame_period:
                    time.sleep(max(0.0, frame_period - (time.time() - t0)))
        except KeyboardInterrupt:
            log.info("Interrupted")
        finally:
            self.source.release()
            if self.client is not None:
                if self.last_stats is not None:
                    self.client.submit_telemetry(self.last_stats)  # flush the final state
                time.sleep(0.5)  # let the sender thread flush the last payload
                self.client.close()
            if show:
                cv2.destroyAllWindows()
