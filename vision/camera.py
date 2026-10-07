# camera.py — frame sources. The pipeline only sees FrameSource.read(), so a video
# file on a laptop and a live camera on a Raspberry Pi run the identical code.
#
#   FrameSource
#     ├── VideoFileSource   recorded video (development / tests)
#     └── LiveSource        USB webcam index, RTSP/HTTP URL, or Pi camera (picamera2 if present)

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np

log = logging.getLogger(__name__)

Frame = np.ndarray


class FrameSource:
    is_live = False

    def read(self) -> Tuple[bool, Optional[Frame]]:
        raise NotImplementedError

    def skip(self, n: int) -> None:
        """Discard n frames cheaply (default: read and drop)."""
        for _ in range(n):
            self.read()

    @property
    def fps(self) -> float:
        return 0.0

    @property
    def frame_index(self) -> int:
        return 0

    def release(self) -> None:
        pass


class VideoFileSource(FrameSource):
    def __init__(self, path: str, loop: bool = False):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Video file not found: {path}")
        self.path = path
        self.loop = loop
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            raise IOError(f"Could not open video file: {path}")
        self._index = 0

    def read(self):
        ok, frame = self._cap.read()
        if not ok and self.loop:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._index = 0
            ok, frame = self._cap.read()
        if not ok:
            return False, None
        self._index += 1
        return True, frame

    def skip(self, n: int) -> None:
        for _ in range(n):
            if not self._cap.grab():
                break
            self._index += 1

    @property
    def fps(self) -> float:
        return float(self._cap.get(cv2.CAP_PROP_FPS) or 0.0)

    @property
    def frame_index(self) -> int:
        return self._index

    def release(self) -> None:
        self._cap.release()


class LiveSource(FrameSource):
    """Live camera with a background grabber thread that always keeps the NEWEST frame
    (so slow inference never builds up latency) and reconnects after a disconnect."""

    is_live = True

    def __init__(self, source: str = "0", reconnect_seconds: float = 3.0):
        self.source = source
        self.reconnect_seconds = reconnect_seconds
        self._lock = threading.Lock()
        self._frame: Optional[Frame] = None
        self._frame_id = 0
        self._last_read_id = 0
        self._stop = threading.Event()
        self._fps_est = 0.0
        self._thread = threading.Thread(target=self._grab_loop, name="camera-grabber", daemon=True)
        self._thread.start()

    # -- opening ---------------------------------------------------------
    def _open(self):
        src = self.source
        if src.lower() in ("camera", "picamera", "pi"):
            pi = self._open_picamera()
            if pi is not None:
                return pi
            src = os.environ.get("CAMERA_SOURCE", "0")
            if src.lower() in ("camera", "picamera", "pi"):
                src = "0"
        target = int(src) if str(src).isdigit() else src
        cap = cv2.VideoCapture(target)
        return cap if cap.isOpened() else None

    @staticmethod
    def _open_picamera():
        try:
            from picamera2 import Picamera2  # only available on Raspberry Pi OS
        except ImportError:
            return None
        try:
            cam = Picamera2()
            cam.configure(cam.create_video_configuration(main={"size": (1280, 720), "format": "RGB888"}))
            cam.start()
            return _PiCameraAdapter(cam)
        except Exception as exc:  # noqa: BLE001 - hardware errors are many and varied
            log.warning("picamera2 unavailable (%s); falling back to OpenCV capture", exc)
            return None

    # -- background loop ---------------------------------------------------
    def _grab_loop(self):
        cap = None
        times = []
        while not self._stop.is_set():
            if cap is None:
                cap = self._open()
                if cap is None:
                    log.warning("Camera '%s' not available, retrying in %.0fs", self.source, self.reconnect_seconds)
                    self._stop.wait(self.reconnect_seconds)
                    continue
                log.info("Camera '%s' connected", self.source)
            ok, frame = cap.read()
            if not ok or frame is None:
                log.warning("Camera '%s' lost; reconnecting", self.source)
                cap.release()
                cap = None
                continue
            now = time.time()
            times = [t for t in times if now - t < 2.0] + [now]
            with self._lock:
                self._frame = frame
                self._frame_id += 1
                self._fps_est = (len(times) - 1) / max(1e-6, times[-1] - times[0]) if len(times) > 1 else 0.0
        if cap is not None:
            cap.release()

    def read(self):
        """Blocks (up to 2 s) for a frame newer than the last one returned."""
        deadline = time.time() + 2.0
        while time.time() < deadline and not self._stop.is_set():
            with self._lock:
                if self._frame is not None and self._frame_id != self._last_read_id:
                    self._last_read_id = self._frame_id
                    return True, self._frame.copy()
            time.sleep(0.005)
        return False, None

    def skip(self, n: int) -> None:
        pass  # a live source already drops old frames

    @property
    def fps(self) -> float:
        return self._fps_est

    @property
    def frame_index(self) -> int:
        return self._frame_id

    def release(self) -> None:
        self._stop.set()


class _PiCameraAdapter:
    """Gives picamera2 the tiny subset of the cv2.VideoCapture API used above."""

    def __init__(self, cam):
        self._cam = cam

    def read(self):
        try:
            arr = self._cam.capture_array()
            return True, cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        except Exception:  # noqa: BLE001
            return False, None

    def release(self):
        try:
            self._cam.stop()
            self._cam.close()
        except Exception:  # noqa: BLE001
            pass


def open_source(spec: str, loop: bool = False) -> FrameSource:
    """`videos/coach.mp4` -> VideoFileSource; `camera`, `0`, `rtsp://...` -> LiveSource."""
    s = str(spec).strip()
    if s.lower() in ("camera", "picamera", "pi") or s.isdigit() or "://" in s:
        return LiveSource(s)
    return VideoFileSource(s, loop=loop)
