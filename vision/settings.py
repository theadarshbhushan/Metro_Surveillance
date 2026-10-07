# settings.py — every tunable value of the vision pipeline lives here.
# Each value can be overridden with an environment variable (see _env_* helpers),
# and a few can be overridden again on the command line (run_vision.py).

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SEAT_CONFIG = os.path.join(ROOT_DIR, "backend", "data", "seat_config.json")


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    # --- connectivity -------------------------------------------------
    backend_url: str = field(default_factory=lambda: _env_str("BACKEND_URL", "http://localhost:5000"))
    coach_id: str = field(default_factory=lambda: _env_str("COACH_ID", "C1"))
    camera_source: str = field(default_factory=lambda: _env_str("CAMERA_SOURCE", "0"))
    request_timeout: float = field(default_factory=lambda: _env_float("REQUEST_TIMEOUT", 2.0))

    # --- detection ----------------------------------------------------
    model_path: str = field(default_factory=lambda: _env_str("MODEL_PATH", "yolov8n.pt"))
    confidence_threshold: float = field(default_factory=lambda: _env_float("CONFIDENCE_THRESHOLD", 0.4))
    inference_size: int = field(default_factory=lambda: _env_int("INFERENCE_SIZE", 640))
    frame_skip: int = field(default_factory=lambda: _env_int("FRAME_SKIP", 2))
    tracker_config: str = field(default_factory=lambda: _env_str("TRACKER_CONFIG", "bytetrack.yaml"))
    model_retry_seconds: float = field(default_factory=lambda: _env_float("MODEL_RETRY_SECONDS", 30.0))

    # --- seat / temporal logic ---------------------------------------
    seat_config_path: str = field(default_factory=lambda: _env_str("SEAT_CONFIG_PATH", DEFAULT_SEAT_CONFIG))
    occupancy_confirm_frames: int = field(default_factory=lambda: _env_int("OCCUPANCY_CONFIRM_FRAMES", 5))
    empty_confirm_frames: int = field(default_factory=lambda: _env_int("EMPTY_CONFIRM_FRAMES", 5))
    standing_confirm_frames: int = field(default_factory=lambda: _env_int("STANDING_CONFIRM_FRAMES", 3))
    standing_min_confidence: float = field(default_factory=lambda: _env_float("STANDING_MIN_CONFIDENCE", 0.5))
    truncated_bottom_margin: int = field(default_factory=lambda: _env_int("TRUNCATED_BOTTOM_MARGIN", 3))
    # a box cut off by the frame bottom that is taller than this fraction of the frame and outside every
    # seat polygon is a standing person close to the camera (0 = disabled: such boxes stay UNKNOWN)
    truncated_standing_min_height: float = field(default_factory=lambda: _env_float("TRUNCATED_STANDING_MIN_HEIGHT", 0.0))
    stale_track_frames: int = field(default_factory=lambda: _env_int("STALE_TRACK_FRAMES", 60))

    # --- density ------------------------------------------------------
    max_passengers_per_coach: int = field(default_factory=lambda: _env_int("MAX_PASSENGERS_PER_COACH", 40))
    low_threshold: float = field(default_factory=lambda: _env_float("LOW_THRESHOLD", 40.0))
    moderate_threshold: float = field(default_factory=lambda: _env_float("MODERATE_THRESHOLD", 65.0))
    high_threshold: float = field(default_factory=lambda: _env_float("HIGH_THRESHOLD", 85.0))

    # --- telemetry ----------------------------------------------------
    telemetry_interval: float = field(default_factory=lambda: _env_float("TELEMETRY_INTERVAL", 1.0))
    frame_upload_interval: float = field(default_factory=lambda: _env_float("FRAME_UPLOAD_INTERVAL", 1.0))
    frame_upload_width: int = field(default_factory=lambda: _env_int("FRAME_UPLOAD_WIDTH", 640))
    frame_jpeg_quality: int = field(default_factory=lambda: _env_int("FRAME_JPEG_QUALITY", 70))

    def with_overrides(self, **kwargs) -> "Settings":
        """Return a copy with non-None keyword overrides applied (CLI flags)."""
        return replace(self, **{k: v for k, v in kwargs.items() if v is not None})

    @property
    def density_thresholds(self) -> tuple:
        return (self.low_threshold, self.moderate_threshold, self.high_threshold)


def load_settings() -> Settings:
    return Settings()
