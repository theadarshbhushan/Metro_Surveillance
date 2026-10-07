# ground_truth.py — evaluation of system output against HUMAN-entered ground truth.
#
# Nothing here ever derives "actual" values from the detector. If no ground truth
# exists every metric is None, and the UI must say "Ground truth not available".

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Sequence

from .density import DEFAULT_THRESHOLDS, density_status, occupancy_percentage


def make_sample(
    actual_people: int,
    detected_people: int,
    max_passengers: int,
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
    frame: Optional[int] = None,
    timestamp: Optional[str] = None,
    coach_id: Optional[str] = None,
    actual_seated: Optional[int] = None,
    actual_standing: Optional[int] = None,
    detected_seated: Optional[int] = None,
    detected_standing: Optional[int] = None,
    actual_seats: Optional[Dict[str, str]] = None,
    detected_seats: Optional[Dict[str, str]] = None,
    note: Optional[str] = None,
) -> dict:
    """Build one evaluation sample comparing actual vs detected."""
    actual_density = density_status(occupancy_percentage(actual_people, max_passengers), thresholds)
    predicted_density = density_status(occupancy_percentage(detected_people, max_passengers), thresholds)
    abs_error = abs(actual_people - detected_people)
    if actual_people > 0:
        pct_error: Optional[float] = round(abs_error / actual_people * 100.0, 2)
    else:
        pct_error = 0.0 if detected_people == 0 else None  # undefined relative to zero

    sample = {
        "coach_id": coach_id,
        "frame": frame,
        "timestamp": timestamp,
        "actual_people": actual_people,
        "detected_people": detected_people,
        "actual_density": actual_density,
        "predicted_density": predicted_density,
        "absolute_error": abs_error,
        "percentage_error": pct_error,
        "density_match": actual_density == predicted_density,
        "note": note,
    }

    # Seat accuracy: only over seats the evaluator labelled that the system also reports.
    if actual_seats and detected_seats:
        compared = [sid for sid in actual_seats if sid in detected_seats]
        if compared:
            correct = sum(1 for sid in compared if actual_seats[sid] == detected_seats[sid])
            sample["seats_evaluated"] = len(compared)
            sample["seats_correct"] = correct

    # Seated/standing: compares counts, as a person-level match needs per-person labels.
    if actual_seated is not None and actual_standing is not None \
            and detected_seated is not None and detected_standing is not None:
        sample["actual_seated"] = actual_seated
        sample["actual_standing"] = actual_standing
        sample["detected_seated"] = detected_seated
        sample["detected_standing"] = detected_standing
        # People correctly attributed to a posture = overlap of the two count vectors.
        sample["posture_correct"] = min(actual_seated, detected_seated) + min(actual_standing, detected_standing)
        sample["posture_total"] = actual_seated + actual_standing
    return sample


def compute_metrics(samples: Sequence[dict]) -> dict:
    """Aggregate metrics. Every metric is None when it cannot be computed from real samples."""
    n = len(samples)
    metrics: dict = {
        "samples": n,
        "person_count_mae": None,
        "person_count_mean_percentage_error": None,
        "person_count_accuracy_percent": None,
        "density_accuracy_percent": None,
        "seat_accuracy_percent": None,
        "seated_standing_accuracy_percent": None,
        "available": n > 0,
    }
    if n == 0:
        return metrics

    metrics["person_count_mae"] = round(sum(s["absolute_error"] for s in samples) / n, 3)

    pct_errors = [s["percentage_error"] for s in samples if s.get("percentage_error") is not None]
    if pct_errors:
        metrics["person_count_mean_percentage_error"] = round(sum(pct_errors) / len(pct_errors), 2)

    total_actual = sum(s["actual_people"] for s in samples)
    if total_actual > 0:
        wape = sum(s["absolute_error"] for s in samples) / total_actual * 100.0
        metrics["person_count_accuracy_percent"] = round(max(0.0, 100.0 - wape), 1)

    metrics["density_accuracy_percent"] = round(sum(1 for s in samples if s["density_match"]) / n * 100.0, 1)

    seat_total = sum(s.get("seats_evaluated", 0) for s in samples)
    if seat_total > 0:
        metrics["seat_accuracy_percent"] = round(sum(s.get("seats_correct", 0) for s in samples) / seat_total * 100.0, 1)

    posture_total = sum(s.get("posture_total", 0) for s in samples)
    if posture_total > 0:
        metrics["seated_standing_accuracy_percent"] = round(
            sum(s.get("posture_correct", 0) for s in samples) / posture_total * 100.0, 1)
    return metrics


def load_frame_annotations(path: str) -> Dict[int, int]:
    """Mode B: a hand-annotated video. JSON {"<frame>": actual_people, ...}."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError("annotation file must be a JSON object mapping frame number to people count")
    out: Dict[int, int] = {}
    for k, v in raw.items():
        if not (isinstance(v, int) and not isinstance(v, bool) and v >= 0):
            raise ValueError(f"frame {k}: actual people must be a non-negative integer")
        out[int(k)] = v
    return out


class SampleLog:
    """Append-only list of evaluation samples, optionally persisted as JSON."""

    def __init__(self, path: Optional[str] = None, max_samples: int = 5000):
        self.path = path
        self.max_samples = max_samples
        self.samples: List[dict] = []
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, list):
                    self.samples = data[-max_samples:]
            except (ValueError, OSError):
                self.samples = []

    def add(self, sample: dict) -> None:
        self.samples.append(sample)
        del self.samples[:-self.max_samples]
        self._save()

    def clear(self) -> None:
        self.samples = []
        self._save()

    def _save(self) -> None:
        if not self.path:
            return
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.samples, fh)
            os.replace(tmp, self.path)
        except OSError:
            pass  # evaluation persistence is best-effort, never fatal
