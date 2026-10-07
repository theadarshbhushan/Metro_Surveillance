"""Seat polygon configuration tool - define the FIXED seat polygons of one camera, once.

Define seats (click the 4 corners of a seat, then type its ID in the terminal):
    python tools/seat_mapper.py --source videos/coach.mp4 --coach-id C1
    (--source may also be an image or a webcam index; --points N changes the corners per seat)

Verify (draws every saved polygon on the saved reference frame - no --source needed):
    python tools/seat_mapper.py --config backend/data/seat_config.json [--coach-id C1]
    python tools/seat_mapper.py --config ... --coach-id C1 --output-image check.png --no-gui

Keys:  left-click  add a corner (the seat closes automatically after --points clicks)
       Enter       close a seat that has more/less than --points corners
       u  undo last point / last seat        s  save to JSON        q / Esc  quit
The first save also stores the reference frame next to the config
(backend/data/reference_frames/<coach>.jpg) so verification works from the config alone.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from vision.seat_mapper import (  # noqa: E402
    SeatMapper, find_coach_entry, list_coaches, load_seat_config, save_coach_seats,
)
from vision.settings import DEFAULT_SEAT_CONFIG  # noqa: E402

WINDOW = "Seat mapper"


def grab_reference_frame(source: str, frame_no: int):
    if source.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
        return cv2.imread(source)
    cap = cv2.VideoCapture(int(source) if source.isdigit() else source)
    if frame_no:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def render(base, seats: dict, current: list, next_id: str):
    img = base.copy()
    for sid, poly in seats.items():
        pts = np.array(poly, dtype=np.int32)
        overlay = img.copy()
        cv2.fillPoly(overlay, [pts], (80, 200, 80))
        img = cv2.addWeighted(overlay, 0.25, img, 0.75, 0)
        cv2.polylines(img, [pts], True, (0, 200, 0), 2)
        cv2.putText(img, sid, (int(pts[:, 0].min()), int(pts[:, 1].min()) - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    for i, (x, y) in enumerate(current):
        cv2.circle(img, (x, y), 4, (0, 0, 255), -1)
        if i:
            cv2.line(img, tuple(current[i - 1]), (x, y), (0, 0, 255), 1)
    cv2.putText(img, f"Next seat: {next_id}  points: {len(current)}  seats: {len(seats)}",
                (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
    return img


def reference_path(config_path: str, coach_id: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(config_path)), "reference_frames", f"{coach_id}.jpg")


def verify(args) -> int:
    config = load_seat_config(args.config)
    coaches = [args.coach_id] if args.coach_id else list_coaches(config)
    if not coaches:
        print(f"No coaches in {args.config}")
        return 1
    rc = 0
    for coach in coaches:
        if find_coach_entry(config, coach) is None:
            print(f"No seats saved for {coach} in {args.config}")
            rc = 1
            continue
        mapper = SeatMapper.from_config(config, coach)
        if args.source:
            base = grab_reference_frame(args.source, args.frame)
        else:
            ref = mapper.reference_image or ""
            ref = ref if os.path.isabs(ref) else os.path.join(os.path.dirname(os.path.abspath(args.config)), ref)
            base = cv2.imread(ref) if ref and os.path.isfile(ref) else None
        if base is None:
            print(f"{coach}: no reference frame - pass --source <video/image> to verify")
            rc = 1
            continue
        h, w = base.shape[:2]
        seats = {k: [[int(x), int(y)] for x, y in v] for k, v in mapper.scaled(w, h).seats.items()}
        img = render(base, seats, [], "-")
        cv2.putText(img, f"{coach}: {len(seats)} seats (verify)", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 255, 255), 2, cv2.LINE_AA)
        print(f"{coach}: " + ", ".join(sorted(seats, key=lambda k: (len(k), k))))
        if args.output_image:
            out = args.output_image if len(coaches) == 1 else f"{os.path.splitext(args.output_image)[0]}_{coach}.png"
            cv2.imwrite(out, img)
            print(f"Wrote {out}")
        if not args.no_gui:
            cv2.imshow(WINDOW, img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", help="video file, image, or webcam index (reference frame to draw on)")
    ap.add_argument("--coach-id", default=None, help="coach to define/verify (default C1 when defining)")
    ap.add_argument("--config", default=None, help="seat_config.json; with no --source this selects verify mode")
    ap.add_argument("--frame", type=int, default=0, help="reference frame number")
    ap.add_argument("--points", type=int, default=4, help="corners per seat (default 4)")
    ap.add_argument("--verify", action="store_true", help="only display the saved polygons")
    ap.add_argument("--output-image", help="verify: also write the annotated frame to this file")
    ap.add_argument("--no-gui", action="store_true", help="verify: do not open a window (use with --output-image)")
    args = ap.parse_args()

    if args.verify or (args.config and not args.source):
        args.config = args.config or DEFAULT_SEAT_CONFIG
        return verify(args)
    if not args.source:
        ap.error("--source is required to define seats (or pass --config alone to verify)")
    args.config = args.config or DEFAULT_SEAT_CONFIG
    coach_id = args.coach_id or os.environ.get("COACH_ID", "C1")

    base = grab_reference_frame(args.source, args.frame)
    if base is None:
        print(f"Could not read a frame from {args.source}")
        return 1
    h, w = base.shape[:2]

    mapper = SeatMapper.from_config(load_seat_config(args.config), coach_id)
    seats = {k: [[int(x), int(y)] for x, y in v] for k, v in (mapper.scaled(w, h).seats.items() if mapper else [])}
    current: list = []
    pending = {"close": False}

    def auto_id() -> str:
        n = len(seats) + 1
        while f"S{n}" in seats:
            n += 1
        return f"S{n}"

    def on_mouse(event, x, y, *_):
        if event == cv2.EVENT_LBUTTONDOWN:
            current.append([x, y])
            if len(current) >= args.points:
                pending["close"] = True

    def close_seat():
        suggestion = auto_id()
        typed = input(f"Enter seat ID [{suggestion}]: ").strip() or suggestion
        if typed in seats:
            print(f"{typed} already exists - it will be replaced")
        seats[typed] = list(current)
        current.clear()
        print(f"polygon saved: {typed} ({len(seats)} seats so far, press 's' to write the file)")

    def save():
        if not seats:
            print("Nothing to save")
            return
        ref = reference_path(args.config, coach_id)
        os.makedirs(os.path.dirname(ref), exist_ok=True)
        cv2.imwrite(ref, base)
        save_coach_seats(args.config, coach_id, seats, (w, h),
                         reference_image=os.path.join("reference_frames", f"{coach_id}.jpg").replace("\\", "/"))
        print(f"Saved {len(seats)} seats for {coach_id} to {args.config} (reference frame: {ref})")

    cv2.namedWindow(WINDOW)
    cv2.setMouseCallback(WINDOW, on_mouse)
    print(__doc__)
    while True:
        cv2.imshow(WINDOW, render(base, seats, current, auto_id()))
        key = cv2.waitKey(30) & 0xFF
        if pending["close"]:
            pending["close"] = False
            cv2.imshow(WINDOW, render(base, seats, current, auto_id()))
            cv2.waitKey(1)
            close_seat()
        elif key in (13, ord("n")):
            if len(current) >= 3:
                close_seat()
            else:
                print("A seat needs at least 3 corner points")
        elif key == ord("u"):
            if current:
                current.pop()
            elif seats:
                print(f"removed {list(seats)[-1]}")
                seats.popitem()
        elif key == ord("s"):
            save()
        elif key in (ord("q"), 27):
            break
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
