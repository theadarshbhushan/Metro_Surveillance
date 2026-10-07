# services/vision_service.py — VisionStateService: live telemetry from the edge CV node.
#
# Responsibilities: validate telemetry, keep the latest state per coach in memory, derive
# crowd density with the backend's own thresholds (single source of truth), raise
# debounced HIGH/CRITICAL alerts, hold the latest annotated frame, and run the
# ground-truth evaluation. No database: state is in memory (evaluation samples are
# additionally logged to a JSON file so they survive restarts).

import json
import os
import re
import threading
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import config
from vision.density import compute_stats, density_status, occupancy_percentage
from vision.ground_truth import SampleLog, compute_metrics, make_sample
from vision.seat_mapper import find_coach_entry, validate_seats

SEAT_STATUSES = ("OCCUPIED", "EMPTY", "UNCERTAIN")
_COACH_RE = re.compile(r"^[Cc]?(\d+)$")
_INT_FIELDS = (
    "total_people", "seated_people", "standing_people", "unknown_people",
    "occupied_seats", "empty_seats", "uncertain_seats",
)


class ValidationError(Exception):
    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def normalize_coach_id(value) -> Optional[str]:
    """'C1', 'c1', '1', 1 -> 'C1'; None if invalid or outside 1..NUM_COACHES."""
    if isinstance(value, bool):
        return None
    m = _COACH_RE.match(str(value).strip())
    if not m:
        return None
    n = int(m.group(1))
    return f"C{n}" if 1 <= n <= config.NUM_COACHES else None


def coach_number(coach_id: str) -> int:
    return int(coach_id[1:])


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


class VisionStateService:
    def __init__(self, seat_config_path: Optional[str] = None, eval_log_path: Optional[str] = None,
                 stale_seconds: Optional[float] = None, alert_cooldown: Optional[float] = None,
                 clock=time.time):
        self._lock = threading.RLock()
        self._clock = clock
        self.seat_config_path = seat_config_path or config.SEAT_CONFIG_PATH
        self.stale_seconds = config.VISION_STALE_SECONDS if stale_seconds is None else stale_seconds
        self.alert_cooldown = config.ALERT_COOLDOWN_SECONDS if alert_cooldown is None else alert_cooldown
        self._coaches: Dict[str, dict] = {}
        self._history: Dict[str, deque] = {}
        self._frames: Dict[str, Tuple[bytes, float]] = {}
        self._alerts: deque = deque(maxlen=config.MAX_ALERTS)
        self._alert_seq = 0
        self._alert_state: Dict[str, dict] = {}  # coach -> {"level": str|None, "last": {level: ts}}
        self._samples = SampleLog(eval_log_path)

    # ------------------------------------------------------------------ telemetry
    def validate(self, payload) -> dict:
        """Return a clean telemetry dict or raise ValidationError."""
        if not isinstance(payload, dict):
            raise ValidationError(["body must be a JSON object"])
        errors: List[str] = []

        coach_id = normalize_coach_id(payload.get("coach_id"))
        if coach_id is None:
            errors.append(f"coach_id must look like C1..C{config.NUM_COACHES}")

        values = {}
        for f in _INT_FIELDS:
            v = payload.get(f)
            if not _is_int(v) or v < 0:
                errors.append(f"{f} must be a non-negative integer")
            else:
                values[f] = v

        if not errors:
            if values["total_people"] != values["seated_people"] + values["standing_people"] + values["unknown_people"]:
                errors.append("total_people must equal seated + standing + unknown")
            if values["occupied_seats"] != values["seated_people"]:
                errors.append("occupied_seats must equal seated_people (one person per seat)")

        seats = payload.get("seats")
        clean_seats = None
        if seats is not None:
            if not isinstance(seats, dict):
                errors.append("seats must be an object")
            else:
                clean_seats = {}
                for sid, info in seats.items():
                    status = info.get("status") if isinstance(info, dict) else info
                    if status not in SEAT_STATUSES:
                        errors.append(f"seat {sid}: status must be one of {SEAT_STATUSES}")
                        continue
                    tid = info.get("track_id") if isinstance(info, dict) else None
                    if tid is not None and not _is_int(tid):
                        errors.append(f"seat {sid}: track_id must be an integer or null")
                        continue
                    clean_seats[str(sid)] = {"status": status, "track_id": tid}
                if not errors:
                    counted = {s: sum(1 for v in clean_seats.values() if v["status"] == s) for s in SEAT_STATUSES}
                    if clean_seats and (counted["OCCUPIED"], counted["EMPTY"], counted["UNCERTAIN"]) != (
                            values["occupied_seats"], values["empty_seats"], values["uncertain_seats"]):
                        errors.append("seat counts do not match the per-seat states")

        ts = payload.get("timestamp")
        if ts is not None:
            try:
                datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except ValueError:
                errors.append("timestamp must be ISO-8601")

        fps = payload.get("fps")
        if fps is not None and not isinstance(fps, dict):
            errors.append("fps must be an object")
        frame = payload.get("frame")
        if frame is not None and not _is_int(frame):
            errors.append("frame must be an integer")

        if errors:
            raise ValidationError(errors)
        return {"coach_id": coach_id, "timestamp": ts, "values": values, "seats": clean_seats,
                "fps": fps, "frame": frame}

    def ingest(self, payload) -> dict:
        """Validate + store telemetry. Derived fields are recomputed from the backend config."""
        clean = self.validate(payload)
        v = clean["values"]
        stats = compute_stats(
            v["seated_people"], v["standing_people"], v["unknown_people"], v["occupied_seats"],
            v["empty_seats"], v["uncertain_seats"], config.MAX_PASSENGERS_PER_COACH,
            (config.THRESHOLD_MODERATE, config.THRESHOLD_HIGH, config.THRESHOLD_CRITICAL),
        )
        now = self._clock()
        state = {
            "coach_id": clean["coach_id"],
            "timestamp": clean["timestamp"] or datetime.now().isoformat(timespec="seconds"),
            "received_at": now,
            "frame": clean["frame"],
            "fps": clean["fps"],
            "seats": clean["seats"] or {},
            **stats,
        }
        reported = payload.get("density_status")
        if reported and reported != stats["density_status"]:
            state["edge_density_status"] = reported  # edge used different thresholds; backend value wins
        with self._lock:
            cid = clean["coach_id"]
            self._coaches[cid] = state
            hist = self._history.setdefault(cid, deque())
            hist.append((now, stats["total_people"]))
            while hist and now - hist[0][0] > config.MOVEMENT_WINDOW_SECONDS * 3:
                hist.popleft()
            self._update_alerts(cid, stats["density_status"], stats["total_people"], now)
        return self._public(state)

    # ------------------------------------------------------------------ views
    def _is_live(self, state: dict) -> bool:
        return self._clock() - state["received_at"] <= self.stale_seconds

    def _movement(self, cid: str) -> int:
        """People change versus ~MOVEMENT_WINDOW_SECONDS ago (0 until enough history exists)."""
        hist = self._history.get(cid)
        if not hist:
            return 0
        now, current = hist[-1]
        past = [c for t, c in hist if now - t >= config.MOVEMENT_WINDOW_SECONDS]
        return current - past[-1] if past else 0

    def _public(self, state: dict) -> dict:
        out = {k: v for k, v in state.items() if k != "received_at"}
        out["live"] = self._is_live(state)
        out["age_seconds"] = round(self._clock() - state["received_at"], 1)
        out["has_frame"] = state["coach_id"] in self._frames
        return out

    def coach(self, coach_id: str) -> Optional[dict]:
        cid = normalize_coach_id(coach_id)
        with self._lock:
            st = self._coaches.get(cid) if cid else None
            return self._public(st) if st else None

    def state(self) -> dict:
        with self._lock:
            coaches = {cid: self._public(st) for cid, st in sorted(self._coaches.items())}
            return {
                "data_source": config.DATA_SOURCE,
                "any_live": any(c["live"] for c in coaches.values()),
                "max_passengers": config.MAX_PASSENGERS_PER_COACH,
                "coaches": coaches,
                "alerts": list(self._alerts)[-20:][::-1],
            }

    def coach_rows(self, only_live: bool) -> List[dict]:
        """Coach dicts shaped like metro.Coach.to_dict() plus a 'vision' block (for metro_service)."""
        rows = []
        with self._lock:
            for cid, st in sorted(self._coaches.items()):
                live = self._is_live(st)
                if only_live and not live:
                    continue
                cap = st["max_passengers"]
                people = st["total_people"]
                rows.append({
                    "id": coach_number(cid),
                    "current_load": people,
                    "capacity": cap,
                    "occupancy_percentage": st["occupancy_percentage"],
                    "available_capacity": max(0, cap - people),
                    "density_status": st["density_status"],
                    "movement": self._movement(cid),
                    "source": "vision",
                    "vision": {
                        "live": live,
                        "timestamp": st["timestamp"],
                        "seated_people": st["seated_people"],
                        "standing_people": st["standing_people"],
                        "unknown_people": st["unknown_people"],
                        "occupied_seats": st["occupied_seats"],
                        "empty_seats": st["empty_seats"],
                        "uncertain_seats": st["uncertain_seats"],
                        "seat_occupancy_percentage": st["seat_occupancy_percentage"],
                        "seats": st["seats"],
                    },
                })
        return rows

    # ------------------------------------------------------------------ alerts
    def _update_alerts(self, cid: str, level: str, people: int, now: float) -> None:
        """One alert per escalation; a repeat of the same level inside the cooldown is suppressed,
        and staying HIGH/CRITICAL never re-alerts. A 'resolved' event is logged on recovery."""
        st = self._alert_state.setdefault(cid, {"level": "LOW", "last": {}})
        prev = st["level"]
        if level == prev:
            return
        st["level"] = level
        severe = ("HIGH", "CRITICAL")
        if level in severe:
            if prev == "CRITICAL" and level == "HIGH":
                return  # de-escalation inside the overcrowded range: no new alert
            if now - st["last"].get(level, -1e18) < self.alert_cooldown:
                return
            st["last"][level] = now
            self._push_alert(cid, "critical" if level == "CRITICAL" else "warning", level, people, now,
                             f"Coach {cid} is {level} ({people}/{config.MAX_PASSENGERS_PER_COACH} passengers)"
                             + (" - critical overcrowding" if level == "CRITICAL" else ""))
        elif prev in severe:
            self._push_alert(cid, "resolved", level, people, now, f"Coach {cid} density back to {level}")

    def _push_alert(self, cid, kind, level, people, now, message) -> None:
        self._alert_seq += 1
        self._alerts.append({
            "id": self._alert_seq, "coach_id": cid, "type": kind, "density_status": level,
            "total_people": people, "message": message,
            "timestamp": datetime.fromtimestamp(now).isoformat(timespec="seconds"),
        })

    def alerts(self) -> List[dict]:
        with self._lock:
            return list(self._alerts)[::-1]

    # ------------------------------------------------------------------ frames
    def set_frame(self, coach_id, jpeg: bytes) -> bool:
        cid = normalize_coach_id(coach_id)
        if cid is None or not jpeg or not jpeg.startswith(b"\xff\xd8"):
            return False
        with self._lock:
            self._frames[cid] = (jpeg, self._clock())
        return True

    def get_frame(self, coach_id) -> Optional[Tuple[bytes, float]]:
        cid = normalize_coach_id(coach_id)
        with self._lock:
            return self._frames.get(cid) if cid else None

    # ------------------------------------------------------------------ ground truth
    def add_ground_truth(self, payload) -> dict:
        """Compare human-entered actual values with the system's detected values.

        'detected_*' may be supplied (offline/annotated-video evaluation); otherwise they are
        taken from the latest live telemetry of the coach. Never uses detector output as truth."""
        if not isinstance(payload, dict):
            raise ValidationError(["body must be a JSON object"])
        errors = []
        cid = normalize_coach_id(payload.get("coach_id", "C1"))
        if cid is None:
            errors.append("coach_id invalid")
        actual = payload.get("actual_people")
        if not _is_int(actual) or actual < 0:
            errors.append("actual_people must be a non-negative integer")
        for f in ("actual_seated", "actual_standing", "detected_people", "detected_seated", "detected_standing"):
            v = payload.get(f)
            if v is not None and (not _is_int(v) or v < 0):
                errors.append(f"{f} must be a non-negative integer")
        actual_seats = payload.get("actual_seats")
        if actual_seats is not None:
            if not isinstance(actual_seats, dict) or any(s not in SEAT_STATUSES for s in actual_seats.values()):
                errors.append(f"actual_seats must map seat id to one of {SEAT_STATUSES}")
        if errors:
            raise ValidationError(errors)

        with self._lock:
            live = self._coaches.get(cid)
            detected = payload.get("detected_people")
            if detected is None:
                if live is None:
                    raise ValidationError(["no telemetry received for this coach yet; supply detected_people"])
                detected = live["total_people"]
                det_seated, det_standing = live["seated_people"], live["standing_people"]
                det_seats = {sid: s["status"] for sid, s in live["seats"].items()}
                frame, ts = live.get("frame"), live["timestamp"]
            else:
                det_seated, det_standing = payload.get("detected_seated"), payload.get("detected_standing")
                det_seats = payload.get("detected_seats")
                frame, ts = payload.get("frame"), payload.get("timestamp") or datetime.now().isoformat(timespec="seconds")
            sample = make_sample(
                actual, detected, config.MAX_PASSENGERS_PER_COACH,
                (config.THRESHOLD_MODERATE, config.THRESHOLD_HIGH, config.THRESHOLD_CRITICAL),
                frame=payload.get("frame", frame), timestamp=ts, coach_id=cid,
                actual_seated=payload.get("actual_seated"), actual_standing=payload.get("actual_standing"),
                detected_seated=det_seated, detected_standing=det_standing,
                actual_seats=actual_seats, detected_seats=det_seats, note=payload.get("note"),
            )
            self._samples.add(sample)
            return sample

    def evaluation(self, coach_id: Optional[str] = None) -> dict:
        with self._lock:
            cid = normalize_coach_id(coach_id) if coach_id else None
            samples = [s for s in self._samples.samples if cid is None or s.get("coach_id") == cid]
            metrics = compute_metrics(samples)
            return {
                "metrics": metrics,
                "latest": samples[-1] if samples else None,
                "recent": samples[-20:][::-1],
                "message": None if samples else "Ground truth not available",
            }

    def clear_evaluation(self) -> None:
        with self._lock:
            self._samples.clear()

    # ------------------------------------------------------------------ seat config
    def get_seat_config(self, coach_id) -> Optional[dict]:
        cid = normalize_coach_id(coach_id)
        if cid is None:
            return None
        try:
            with open(self.seat_config_path, "r", encoding="utf-8") as fh:
                entry = find_coach_entry(json.load(fh), cid)
        except (OSError, ValueError):
            return None
        if entry is None:
            return None
        if isinstance(entry, dict) and "seats" in entry:
            return {"coach_id": cid, "frame_size": entry.get("frame_size"), "seats": entry["seats"]}
        return {"coach_id": cid, "frame_size": None, "seats": entry}

    def set_seat_config(self, coach_id, payload) -> dict:
        cid = normalize_coach_id(coach_id)
        if cid is None:
            raise ValidationError(["coach_id invalid"])
        if not isinstance(payload, dict):
            raise ValidationError(["body must be a JSON object"])
        seats = payload.get("seats", payload)
        try:
            clean = validate_seats(seats)
        except ValueError as exc:
            raise ValidationError([str(exc)])
        entry = {"seats": clean}
        fs = payload.get("frame_size")
        if fs is not None:
            if not (isinstance(fs, list) and len(fs) == 2 and all(_is_int(x) and x > 0 for x in fs)):
                raise ValidationError(["frame_size must be [width, height]"])
            entry["frame_size"] = fs
        with self._lock:
            try:
                with open(self.seat_config_path, "r", encoding="utf-8") as fh:
                    full = json.load(fh)
            except (OSError, ValueError):
                full = {}
            full[cid] = entry
            os.makedirs(os.path.dirname(os.path.abspath(self.seat_config_path)), exist_ok=True)
            tmp = self.seat_config_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(full, fh, indent=2)
            os.replace(tmp, self.seat_config_path)
        return {"coach_id": cid, "frame_size": entry.get("frame_size"), "seats": clean}
