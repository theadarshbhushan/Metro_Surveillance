# telemetry_client.py — sends telemetry (and optionally annotated JPEG snapshots) to Flask.
#
# Runs in a background thread so a slow/unreachable server never stalls inference.
# Only the LATEST telemetry and the LATEST frame are kept (one slot each): when the
# backend is down nothing accumulates, and the newest data is retried on the next cycle.

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Optional

import requests

log = logging.getLogger(__name__)


class TelemetryClient:
    def __init__(self, backend_url: str, coach_id: str, timeout: float = 2.0, retry_seconds: float = 2.0):
        # On Windows "localhost" tries IPv6 first and costs ~2 s per request against an IPv4-only
        # Flask server, so resolve it to the IPv4 loopback address.
        self.base = re.sub(r"^(https?://)localhost(?=[:/]|$)", r"\g<1>127.0.0.1", backend_url.rstrip("/"))
        self._http = requests.Session()  # keep-alive connection
        self.coach_id = coach_id
        self.timeout = timeout
        self.retry_seconds = retry_seconds
        self._lock = threading.Lock()
        self._telemetry: Optional[dict] = None
        self._frame: Optional[bytes] = None
        self._wake = threading.Event()
        self._stop = threading.Event()
        self.sent_count = 0
        self.failed_count = 0
        self._connected: Optional[bool] = None
        self._thread = threading.Thread(target=self._run, name="telemetry-sender", daemon=True)
        self._thread.start()

    def submit_telemetry(self, payload: dict) -> None:
        with self._lock:
            self._telemetry = payload  # overwrites any unsent older payload
        self._wake.set()

    def submit_frame(self, jpeg: bytes) -> None:
        with self._lock:
            self._frame = jpeg
        self._wake.set()

    def close(self) -> None:
        self._stop.set()
        self._wake.set()

    # ------------------------------------------------------------------
    def _take(self):
        with self._lock:
            t, f = self._telemetry, self._frame
            self._telemetry = self._frame = None
        return t, f

    def _run(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(timeout=1.0)
            self._wake.clear()
            telemetry, frame = self._take()
            if telemetry is None and frame is None:
                continue
            ok = True
            if telemetry is not None:
                ok = self._post_json(telemetry) and ok
            if frame is not None:
                ok = self._post_frame(frame) and ok
            if not ok:
                # put the newest data back only if nothing newer arrived meanwhile
                with self._lock:
                    if telemetry is not None and self._telemetry is None:
                        self._telemetry = telemetry
                self._stop.wait(self.retry_seconds)

    def _mark(self, ok: bool, err: str = "") -> None:
        if ok:
            self.sent_count += 1
            if self._connected is False:
                log.info("Backend connection restored")
        else:
            self.failed_count += 1
            if self._connected is not False:
                log.warning("Backend unreachable or rejected data (%s); will retry", err)
        self._connected = ok

    def _post_json(self, payload: dict) -> bool:
        try:
            r = self._http.post(f"{self.base}/api/vision/telemetry", json=payload, timeout=self.timeout)
            if r.status_code >= 400:
                self._mark(False, f"HTTP {r.status_code}: {r.text[:200]}")
                # a 4xx means our payload is bad; retrying the same payload is pointless
                return r.status_code < 500
            self._mark(True)
            return True
        except requests.RequestException as exc:
            self._mark(False, str(exc))
            return False

    def _post_frame(self, jpeg: bytes) -> bool:
        try:
            r = self._http.post(
                f"{self.base}/api/vision/frame", params={"coach_id": self.coach_id}, data=jpeg,
                headers={"Content-Type": "image/jpeg"}, timeout=self.timeout,
            )
            return r.status_code < 500
        except requests.RequestException:
            return False
