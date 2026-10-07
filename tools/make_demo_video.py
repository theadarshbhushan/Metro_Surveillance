"""Create videos/demo.mp4 from a still photo, for demos when no coach recording is available.

The still is shown with tiny per-frame jitter/brightness noise so the tracker sees a live-like
stream. This is a PIPELINE DEMO ONLY - it is not a metro coach and proves nothing about accuracy.

    python tools/make_demo_video.py [--image videos/bus.jpg] [--out videos/demo.mp4] [--frames 150]
"""

import argparse
import os

import cv2
import numpy as np


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="videos/bus.jpg")
    ap.add_argument("--out", default="videos/demo.mp4")
    ap.add_argument("--frames", type=int, default=150)
    ap.add_argument("--fps", type=float, default=15.0)
    args = ap.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        print(f"Cannot read image {args.image}")
        return 1
    h, w = img.shape[:2]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    writer = cv2.VideoWriter(args.out, cv2.VideoWriter_fourcc(*"mp4v"), args.fps, (w, h))
    rng = np.random.default_rng(0)
    for _ in range(args.frames):
        dx, dy = rng.integers(-1, 2, size=2)
        frame = np.roll(img, (int(dy), int(dx)), axis=(0, 1)).astype(np.int16)
        frame += rng.integers(-3, 4, size=frame.shape, dtype=np.int16)
        writer.write(np.clip(frame, 0, 255).astype(np.uint8))
    writer.release()
    print(f"Wrote {args.out} ({w}x{h}, {args.frames} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
