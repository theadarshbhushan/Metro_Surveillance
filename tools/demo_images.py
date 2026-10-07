"""Run the full SmartMetro pipeline on the still photos in backend/demo_img.

Each photo is a different camera, so each has its own hand-drawn seat polygons in
backend/data/seat_config_demo.json (D1..D3). A still is fed for N frames so the temporal
verification (seat confirmation, track stability) runs exactly as on video.

    python tools/demo_images.py [--frames 12]

Writes annotated PNGs + a results.json to backend/demo_output/ and checks the result against
hand-counted expectations (EXPECTED).
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cv2  # noqa: E402

from vision.detector import PersonDetector  # noqa: E402
from vision.pipeline import Pipeline  # noqa: E402
from vision.seat_mapper import SeatMapper  # noqa: E402
from vision.settings import load_settings  # noqa: E402

IMG_DIR = os.path.join(ROOT, "backend", "demo_img")
OUT_DIR = os.path.join(ROOT, "backend", "demo_output")
CONFIG = os.path.join(ROOT, "backend", "data", "seat_config_demo.json")

# Per-camera tuning (a real deployment also tunes the model/threshold per camera). yolov8x@1280 is used
# for these stills because accuracy matters more than speed here; the edge default stays yolov8n.
MODEL = os.path.join(ROOT, "models", "yolov8x.pt")
CAMERAS = {
    "D1": {"file": "image 1.jpeg", "conf": 0.4, "standing_min_confidence": 0.4, "truncated_standing_min_height": 0.45},
    "D2": {"file": "image 2.jpeg", "conf": 0.4},
    "D3": {"file": "image 3.jpeg", "conf": 0.3, "standing_min_confidence": 0.3},
}
# Hand-counted from the photos (see docs/CHANGES.md for the per-person reasoning).
EXPECTED = {
    "D1": {"seated": 5, "standing": 8, "unknown": 0, "occupied": ["S1", "S2", "S3", "S4", "S5"]},
    "D2": {"seated": 8, "standing": 0, "unknown": 0, "occupied": ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]},
    "D3": {"seated": 10, "standing": 1, "unknown": 0,
           "occupied": ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"]},
}


class _StillSource:
    is_live = False

    def read(self):
        return False, None

    def release(self):
        pass

    fps = 0.0
    frame_index = 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=12)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)

    summary, failures = {}, 0
    for coach, cam in CAMERAS.items():
        settings = load_settings().with_overrides(
            model_path=MODEL, inference_size=1280, coach_id=coach,
            confidence_threshold=cam["conf"], standing_min_confidence=cam.get("standing_min_confidence"),
            truncated_standing_min_height=cam.get("truncated_standing_min_height"))
        frame = cv2.imread(os.path.join(IMG_DIR, cam["file"]))
        mapper = SeatMapper.from_file(CONFIG, coach)
        pipe = Pipeline(settings, _StillSource(), detector=PersonDetector(settings), mapper=mapper)
        for i in range(1, args.frames + 1):
            pipe.process_frame(frame, i)
        res, stats = pipe.last_result, pipe.last_stats
        cv2.imwrite(os.path.join(OUT_DIR, f"{os.path.splitext(cam['file'])[0].replace(' ', '')}_result.png"),
                    pipe.annotate(frame, scale=2.5))

        occ = sorted((s for s, st in res.seats.items() if st.status == "OCCUPIED"), key=lambda x: int(x[1:]))
        got = {"seated": stats["seated_people"], "standing": stats["standing_people"],
               "unknown": stats["unknown_people"], "occupied": occ}
        exp = EXPECTED.get(coach)
        ok = exp is not None and all(got[k] == exp[k] for k in got)
        failures += 0 if ok else 1
        print(f"\n{coach} ({cam['file']})  {'PASS' if ok else 'FAIL'}")
        print(f"  expected: {exp}")
        print(f"  got:      {got}")
        for p in sorted(res.persons, key=lambda p: p.detection.bbox[0]):
            d = p.detection
            print(f"    track {d.track_id}: bottom-centre=({d.bottom_center[0]:.0f},{d.bottom_center[1]:.0f}) "
                  f"conf={d.confidence:.2f} -> {p.state}" + (f" {p.seat_id}" if p.seat_id else "") + f"  [{p.reason}]")
        summary[coach] = {"expected": exp, "got": got, "pass": ok, "telemetry": stats}
    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\n{len(CAMERAS) - failures}/{len(CAMERAS)} images match expectations")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
