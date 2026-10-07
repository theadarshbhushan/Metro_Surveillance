# SmartMetro – seat-polygon correction: what changed

Implements `prompts.md` ("IMPORTANT CORRECTION"): seats are **fixed, manually defined polygons** in the
fixed camera's image. YOLO only detects people, the tracker only tracks them, and the SmartMetro logic
alone decides **SEATED / STANDING / UNKNOWN**, seat occupancy and density. No existing work was deleted.

## How the prompt maps to the code

| Prompt section | Where it lives |
|---|---|
| 1, 5 Fixed seat polygons, never recomputed, never inferred from people | `backend/data/seat_config*.json` (data only, no coordinates in Python); `vision/seat_mapper.py` |
| 2 YOLO = detection only | `vision/detector.py` (class `person` only; no seated/standing claim) |
| 3 Config file, any number of seats, simple format | both `{"C1": {"S1": [[x,y]...]}}` and `{"S1": {"polygon": [...]}}` accepted; optional `frame_size`, `reference_image` |
| 4 Seat-mapping tool + verification mode | `tools/seat_mapper.py` (see below) |
| 6, 7 Bottom-centre -> candidate seat | `SeatMapper.candidates_for` (bottom-centre in polygon, bbox overlap as tie-break) |
| 8 SEATED / STANDING / UNKNOWN rules | `vision/occupancy.py` |
| 9 Temporal verification | `vision/occupancy.py` (`OCCUPANCY_CONFIRM_FRAMES`, `EMPTY_CONFIRM_FRAMES`, `STANDING_CONFIRM_FRAMES`) |

Seated needs the seat polygon to hold the same stable track for N consecutive frames (default 5) and the
seat not to be claimed by a stronger person; a seat is only freed after M frames without a candidate
(a single missed detection never frees it). Standing needs a confident, stable track outside every
polygon. UNKNOWN = low confidence, unstable track, seat conflict, or box cut off by the frame bottom.

## Changes in this round

1. **Fragment/duplicate suppression** (`vision/detector.py::suppress_fragments`). In crowded coaches YOLO
   returns half-body boxes nested in a neighbour's box, or two boxes for one person (same feet). Those
   created phantom people and phantom seat conflicts. A box >= 85 % inside a higher-confidence box is
   dropped; a larger box whose contents are a same-feet duplicate is dropped too.
2. **Opt-in tall-truncated rule** (`TRUNCATED_STANDING_MIN_HEIGHT`, default `0` = off). A box cut off by
   the frame bottom is normally UNKNOWN (its bottom-centre is not a foot). If enabled, a truncated box
   that is at least that fraction of the frame tall **and outside every seat polygon** is STANDING: a
   seated person near the camera would sit inside a seat polygon that reaches the frame bottom.
3. **Seat mapper tool rewritten to the prompt** (`tools/seat_mapper.py`):
   * click the corners (4 by default, `--points N`), the seat closes itself, then **type the seat ID in
     the terminal** (Enter accepts the suggested `S<n>`), repeat, press `s` to save;
   * saving also stores the reference frame (`backend/data/reference_frames/<coach>.jpg`) and records it
     in the config as `reference_image`;
   * **verify with the config alone**: `python tools/seat_mapper.py --config backend/data/seat_config.json`
     draws every saved polygon on the saved reference frame (`--coach-id`, `--output-image`, `--no-gui`
     for headless use; `--source` overrides the frame).
4. **Overlay** (`vision/overlay.py`): optional `scale` for small stills; labels are shortened and placed at
   the person's feet so they stop overlapping (live behaviour at `scale=1` is unchanged).
5. **Demo configuration** (`backend/data/seat_config_demo.json`): hand-drawn polygons for the three photos
   in `backend/demo_img` (coaches `D1`, `D2`, `D3`), each photo being a different camera.
6. **Demo runner** (`tools/demo_images.py`): feeds each photo for 12 frames (so temporal verification
   really runs), prints a per-person table, writes annotated PNGs + `results.json` to
   `backend/demo_output/` and checks them against the hand-counted expectations.
7. **Tests**: 5 new tests (polygon-dict config, reference image round trip, fragment suppression,
   tall-truncated rule, consecutive-frame confirmation). Full suite: **71 passed**.

## Demo results (`python tools/demo_images.py`)

Model `yolov8x` at 1280 px for these stills (accuracy over speed; the edge default stays `yolov8n`).
Per-camera tuning, as a real deployment would do:

| Camera | Photo | conf | extra |
|---|---|---|---|
| D1 | image 1 (crowded) | 0.40 | `standing_min_confidence` 0.40, `truncated_standing_min_height` 0.45 |
| D2 | image 2 | 0.40 | – |
| D3 | image 3 | 0.30 | `standing_min_confidence` 0.30 |

| Photo | Seated | Standing | Unknown | Occupied seats |
|---|---|---|---|---|
| image 1 | 5 | 8 | 0 | S1-S5 |
| image 2 | 8 | 0 | 0 | S1-S8 (all 8 seated passengers, 3 left bench + 5 right bench) |
| image 3 | 10 | 1 | 0 | S1-S10 (the 1 standing person is far down the aisle) |

Outputs: `backend/demo_output/image{1,2,3}_result.png`, `results.json`, and
`seat_map_check_D{1,2,3}.png` (verify mode).

## Honest limits

* The expected counts were fixed by me looking at the photos **together with** the detector output, so
  this is a consistency/regression check, not an independent accuracy measurement.
* Image 1 is a dense, blurry crowd. Standing people are classified by "confident, stable, outside every
  polygon"; a few seated people at the right edge are not separately detected by the model, so no seat is
  defined for them.
* Seat polygons here are drawn by eye from one still each. For a real coach draw them with
  `tools/seat_mapper.py` on a frame from the actual camera; the polygon must cover where a seated
  person's *bottom-centre* (feet/knees) lands, not only the cushion.
* Windows reflections or posters showing people would be detected as people; only the polygons and
  confidence thresholds guard against that.

## Run it

```
python tools/demo_images.py                                   # the three demo photos
python tools/seat_mapper.py --config backend/data/seat_config_demo.json --no-gui --output-image out.png
python tools/seat_mapper.py --source videos/coach.mp4 --coach-id C1   # define seats for a real camera
python -m pytest -q
```

`models/yolov8m.pt` and `models/yolov8x.pt` were downloaded for the demo (git-ignored like all `*.pt`).
