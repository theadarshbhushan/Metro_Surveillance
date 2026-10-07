# SmartMetro — Intelligent Metro Crowd Management System

A crowd-management prototype for metro coaches. It has three parts that work together:

1. **Flask backend** — rule-based crowd distribution engine + REST API.
2. **React dashboard** — live coach occupancy, recommendations, alerts and camera view.
3. **Computer-vision edge node** — YOLO person detection + seat-polygon mapping that feeds *real* passenger counts and seat states into the backend (runs on a laptop or Raspberry Pi).

---

## What has been built

| Area | Status |
|---|---|
| Flask REST API, CSV simulation, rule-based recommendation engine | Done (original prototype, unchanged) |
| React + Vite + Tailwind dashboard (train view, density map, analytics, recommendations) | Done |
| Vision package `vision/` (YOLOv8 person detection, ByteTrack tracking, centroid-tracker fallback) | Done |
| Seat Polygon Mapping + temporal confirmation (SEATED / STANDING / UNKNOWN, seat OCCUPIED / EMPTY / UNCERTAIN) | Done |
| Telemetry client (edge → backend, newest-only retry) + annotated JPEG snapshots | Done |
| Backend vision API (`/api/vision/*`), validation, alerts with cooldown, data-source merge (`DATA_SOURCE`) | Done |
| Dashboard Live Vision Monitor, Ground Truth & Accuracy panel, Alerts panel | Done |
| Ground-truth evaluation (never fabricates accuracy: `null` until real samples exist) | Done |
| Seat tool `tools/seat_mapper.py`, demo video generator, one-command `run_demo.py` | Done |
| pytest suite — 66 tests, all passing | Done |
| Raspberry Pi deployment instructions | Written, **untested on real Pi hardware** |
| Accuracy on real metro-coach footage | **Not measured** — the sample video is a street photo |

---

## Quick start (Windows, step by step)

You need **Python 3.11+** and **Node.js 18+** (developed with Python 3.12 and Node 22). Open PowerShell in the project folder (`Smart_Metro`, the folder that contains `run_demo.py`).

### Step 1 — Install Python dependencies (once)

```powershell
python -m pip install -r requirements-dev.txt
```
This installs Flask, flask-cors, pandas, OpenCV, numpy, ultralytics (YOLO), lapx, requests and pytest. `ultralytics` pulls in PyTorch, so the first install is large (a few GB, several minutes).

### Step 2 — Install frontend dependencies (once)

```powershell
cd frontend
npm install
cd ..
```

### Step 3 — Check everything works (optional but recommended)

```powershell
python -m pytest tests -q
```
Expected: `66 passed`.

### Step 4 — Run the full system (three terminals, all in `Smart_Metro`)

**Terminal 1 — backend**
```powershell
python backend/app.py
```
Wait for `SmartMetro backend running on http://localhost:5000 (DATA_SOURCE=auto)`. Check it: open http://localhost:5000/api/health — you should see `"status": "ok"`.

**Terminal 2 — dashboard**
```powershell
cd frontend
npm run dev
```
Open **http://localhost:5173**. At this point you see the simulated (CSV) data.

**Terminal 3 — camera / vision node (pick one)**

```powershell
python run_demo.py
```
`run_demo.py` is the easiest option: it generates `videos/demo.mp4` from `videos/bus.jpg` if missing, starts the backend itself if it is not running, and loops the video through YOLO with a preview window. Press `q` in the preview window (or Ctrl+C in the terminal) to stop. Add `--no-window` for headless.

Within a few seconds the dashboard shows coach **C1** marked `LIVE CV` with real people counts, the annotated snapshot in *Live Vision Monitor*, seat states, and alerts if density turns HIGH/CRITICAL. If you stop the vision node, C1 falls back to simulated data after 10 s (`DATA_SOURCE=auto`).

> The first run downloads or loads YOLO weights. `models/yolov8n.pt` is already in the repo folder and is used automatically by `run_demo.py`. The sample video is a **street photo, not a metro coach** — it only demonstrates the pipeline.

### Step 5 — Use your own video or camera

```powershell
python run_vision.py --source videos\coach.mp4 --show --loop --realtime   # your recording
python run_vision.py --source 0                                           # USB webcam
python run_vision.py --source rtsp://user:pass@host/stream                # CCTV stream
```
Before trusting numbers from your own footage, **map the seats** (Step 6).

### Step 6 — Map seats for your camera view

```powershell
python tools\seat_mapper.py --source videos\coach.mp4 --coach-id C1            # draw polygons
python tools\seat_mapper.py --source videos\coach.mp4 --coach-id C1 --verify   # check them
```
Click the corners of each seat in the image, press **Enter** to finish a seat, **s** to save. Polygons are written to `backend/data/seat_config.json`. Restart `run_vision.py` afterwards. Without polygons every person is counted as STANDING/UNKNOWN.

### Step 7 — Measure accuracy (optional)

In the dashboard's **Ground Truth & Accuracy** panel type the real number of people while the video plays, or run a hand-annotated video:
```powershell
python run_vision.py --source videos\coach.mp4 --ground-truth gt.json --no-send
```
(`gt.json` = `{"<frame number>": actual_people, ...}`; use `--frame-skip 1`.)

### Choosing the data source

Set `DATA_SOURCE` **before** starting the backend:
```powershell
$env:DATA_SOURCE = "simulation"   # CSV only (original prototype)
$env:DATA_SOURCE = "vision"       # only coaches reported by the camera
$env:DATA_SOURCE = "auto"         # default: CSV + live vision overrides
python backend/app.py
```
Other useful variables: `PORT` (backend port), `VITE_API_BASE_URL` (frontend → backend URL, default `http://localhost:5000`), `BACKEND_URL`, `COACH_ID`, `FRAME_SKIP`, `INFERENCE_SIZE`, `CONFIDENCE_THRESHOLD`, `MAX_PASSENGERS_PER_COACH`.

### Run only the original simulation (no camera, no YOLO)

```powershell
pip install -r backend/requirements.txt
python backend/app.py        # then, in another terminal: cd frontend; npm run dev
```
In the dashboard use the simulation controls to step through the 8 stations (`POST /api/simulation/next`).

### If something goes wrong

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | Re-run Step 1 with the same Python you run the scripts with. |
| Port 5000 already in use | `$env:PORT = 5001; python backend/app.py`, and start the frontend with `$env:VITE_API_BASE_URL = "http://localhost:5001"`. |
| Dashboard shows an error banner | Backend not running or wrong URL; check http://localhost:5000/api/health. |
| No `LIVE CV` on the dashboard | Vision node not running, or `DATA_SOURCE=simulation`. Check `http://localhost:5000/api/vision/state`. |
| `videos/demo.mp4` missing | `python tools\make_demo_video.py` (it is git-ignored; `run_demo.py` also regenerates it). |
| Preview window does not open | Run without `--show` / use `--no-window`; OpenCV GUI needs `opencv-python`, not the headless build. |
| Slow detection | Lower `--imgsz` (e.g. 320) and raise `--frame-skip` (e.g. 3). |

More detail is in sections 9–15 below.

---

## Architecture Overview

### Current (Review 1 — Flask + CSV Simulation)

```
stations.csv  (simulated load data)
      ↓
simulation.py  (StationSimulator — data source layer)
      ↓
metro.py       (Coach domain model — occupancy, density, movement)
      ↓
logic.py       (Rule-Based Crowd Distribution Engine)
      ↓
services/metro_service.py  (single source of truth — state assembly)
      ↓
routes/simulation_routes.py  (REST API layer)
      ↓
Flask  →  REST API on localhost:5000
      ↓
[Future React Dashboard]
```

### Future (Phase 3 — Hardware / YOLO)

```
Load Cells / YOLO Passenger Detection
      ↓
simulation.py  ← swap ONLY this layer
      ↓
Same metro.py + logic.py + services + routes
      ↓
Same Flask REST API
      ↓
React Dashboard
```

> The separation of the **data source layer** (`simulation.py`) from the **business logic layer** (`metro.py` + `logic.py`) is intentional. Integrating real sensors in Phase 3 requires changing only `simulation.py`.

---

## Folder Structure

```
Smart_Metro/
├── backend/
│   ├── app.py                      # Flask entry point + CORS + blueprint registration
│   ├── config.py                   # Constants: capacity, density thresholds, DATA_SOURCE, alert/stale timings
│   ├── metro.py                    # Coach domain model (Coach + VisionCoach)
│   ├── simulation.py               # Data source: reads stations.csv, tracks position
│   ├── logic.py                    # Rule-Based Crowd Distribution Engine (pure functions)
│   ├── data/
│   │   ├── stations.csv            # 8 simulated stations
│   │   └── seat_config.json        # Seat polygons per coach (C1 sample)
│   ├── routes/
│   │   ├── simulation_routes.py    # /api/simulation/*
│   │   └── vision_routes.py        # /api/vision/*
│   ├── services/
│   │   ├── metro_service.py        # Assembles state, merges vision per DATA_SOURCE
│   │   └── vision_service.py       # Telemetry validation, live state, alerts, evaluation
│   └── requirements.txt
├── vision/                         # Edge CV package (camera, detector, tracker, seats, occupancy, density, overlay, pipeline)
├── frontend/                       # React + Vite + Tailwind dashboard (src/components, hooks, services)
├── tools/                          # seat_mapper.py, make_demo_video.py
├── tests/                          # pytest suite (66 tests)
├── models/yolov8n.pt               # YOLO weights (git-ignored)
├── videos/                         # bus.jpg sample, demo.mp4 (generated, git-ignored)
├── run_demo.py                     # One-command demo
├── run_vision.py                   # Edge node entry point
├── requirements-vision.txt  requirements-dev.txt
├── prompts.md
└── README.md
```

---

## Backend Setup

### Prerequisites
- Python 3.11+
- pip

### Install dependencies

```bash
cd SmartMetro/backend
pip install -r requirements.txt
```

`requirements.txt` contains:
```
Flask>=3.0.0
flask-cors>=4.0.0
pandas>=2.0.0
```

### Run the Flask server

```bash
python app.py
```

The server starts on **http://localhost:5000** with hot-reload (debug mode).

---

## API Endpoints

### `GET /api/health`
Liveness check.

**Response:**
```json
{
  "status": "ok",
  "system": "SmartMetro"
}
```

---

### `GET /api/simulation/state`
Returns the complete current simulation state (coaches, occupancy, recommendation) without advancing.

**Response:**
```json
{
  "station": {
    "current": "Andheri",
    "previous": null,
    "next": "Vile Parle",
    "index": 0,
    "total": 8,
    "at_final_station": false
  },
  "coaches": [
    {
      "id": 1,
      "current_load": 30.0,
      "capacity": 100,
      "occupancy_percentage": 30.0,
      "available_capacity": 70.0,
      "density_status": "LOW",
      "movement": 0.0
    },
    {
      "id": 4,
      "current_load": 55.0,
      "capacity": 100,
      "occupancy_percentage": 55.0,
      "available_capacity": 45.0,
      "density_status": "MODERATE",
      "movement": 0.0
    }
  ],
  "recommendation": {
    "coach_id": 2,
    "occupancy_percentage": 25.0,
    "available_capacity": 75.0,
    "density_status": "LOW",
    "reason": "Coach 2 currently has the highest available capacity (75.0 kg free, 25.0% occupied) and provides the best option for balanced passenger distribution."
  }
}
```

---

### `POST /api/simulation/next`
Advances the simulation to the next station. Returns the full updated state with movement values (passengers entering/leaving each coach).

At the **final station**, returns the same state with:
```json
{ "message": "Already at the final station (Masjid). Reset to return to the beginning." }
```

---

### `POST /api/simulation/reset`
Resets the simulation to Station 1 (Andheri). Returns the initial state.

---

## Simulation Flow

1. **Start** — Simulator loads `stations.csv` (8 stations) and initialises at index 0.
2. **`GET /state`** — Returns current station data. Movement = 0 at start (no previous station).
3. **`POST /next`** — Advances index, stores previous loads, computes per-coach movement (±), recalculates occupancy and density, runs recommendation engine, returns full state.
4. **Recommendation engine** — Selects the coach with the lowest occupancy percentage. Returns coach ID, occupancy %, available capacity, density level, and a human-readable reason.
5. **`POST /reset`** — Returns to index 0; previous state cleared.

---

## Density Thresholds

Configured in `backend/config.py`:

| Level      | Occupancy Range |
|------------|----------------|
| LOW        | 0 – 40%        |
| MODERATE   | 41 – 65%       |
| HIGH       | 66 – 85%       |
| CRITICAL   | > 85%          |

---

## Simulated Stations

Coach 4 is consistently higher-loaded (represents coach nearest elevator/escalator access). Passengers enter **and** leave between stations, producing both positive and negative movement values.

| Station    | Coach 1 | Coach 2 | Coach 3 | Coach 4 |
|------------|---------|---------|---------|---------|
| Andheri    | 30      | 25      | 35      | 55      |
| Vile Parle | 42      | 38      | 50      | 68      |
| Santacruz  | 55      | 44      | 62      | 78      |
| Bandra     | 48      | 52      | 70      | 88      |
| Mahim      | 62      | 39      | 58      | 82      |
| Dadar      | 75      | 65      | 72      | 91      |
| Parel      | 58      | 70      | 64      | 79      |
| Masjid     | 40      | 35      | 45      | 60      |

---

## Future Integration Architecture

| Phase | Data Source | Change Required |
|-------|------------|-----------------|
| 1 (current) | `stations.csv` | — |
| 2 | React/Vite dashboard | Add `frontend/` app |
| 3 | Raspberry Pi load cells | Replace `simulation.py` data read |
| 4 | YOLO passenger detection | Replace `simulation.py` data read |

The recommendation engine in `logic.py` and the domain model in `metro.py` require **zero changes** across all future phases.


---

# Real Computer-Vision Mode (Raspberry Pi Edge AI)

The original CSV simulation above still works unchanged. On top of it, a camera can now supply **real passenger counts and seat states**. Two modes exist, chosen by the backend environment variable `DATA_SOURCE`:

| `DATA_SOURCE` | Behaviour |
|---|---|
| `simulation` | CSV data only (original prototype). |
| `vision` | Only coaches reported by the camera edge node are shown; "waiting for telemetry" until one reports. |
| `auto` (default) | CSV coaches, but any coach with **live** vision telemetry is replaced by it. If the edge node goes silent for `VISION_STALE_SECONDS` (10 s) the coach falls back to simulation. |

## 1. System architecture

```
CCTV / Pi camera -> Raspberry Pi (edge) -> JSON telemetry -> Flask -> React dashboard
```

Raw video never goes to Flask. The edge node sends only metadata (about 1 message/s) and one small *annotated* JPEG snapshot per second for the Surveillance view.

## 2. Software architecture

```
vision/                      edge package (no Flask dependency)
  camera.py                  FrameSource -> VideoFileSource | LiveSource (USB / RTSP / Pi camera)
  detector.py                pretrained YOLO (person class only) + Ultralytics ByteTrack tracking
  tracker.py                 tiny centroid tracker, used only if ByteTrack fails
  seat_mapper.py             Seat Polygon Mapping (point-in-polygon, overlap, config I/O)
  occupancy.py               temporal seat state + SEATED/STANDING/UNKNOWN classification
  density.py                 statistics + LOW/MODERATE/HIGH/CRITICAL
  ground_truth.py            evaluation samples + metrics (shared with the backend)
  overlay.py  pipeline.py  telemetry_client.py  settings.py  types.py
tools/seat_mapper.py         click-to-define seat polygons
tools/make_demo_video.py     builds videos/demo.mp4 from videos/bus.jpg
run_vision.py  run_demo.py   entry points
backend/
  services/vision_service.py VisionStateService: validation, live state, alerts, evaluation
  routes/vision_routes.py    /api/vision/*
  services/metro_service.py  merges vision coaches (metro.VisionCoach) per DATA_SOURCE
  data/seat_config.json      seat polygons per coach
frontend/src/
  hooks/useLiveData.js       polls /api/vision/*
  components/VisionSection, SurveillanceView, SeatGrid, GroundTruthPanel, AlertsPanel
tests/                       pytest suite (66 tests)
```

The original layering is preserved: data source -> `metro.py` -> `logic.py` -> `metro_service.py` -> routes -> React. The vision data source plugs in as `VisionCoach`.

## 3. Computer-vision pipeline

frame capture -> (`FRAME_SKIP`) -> YOLO person detection (`CONFIDENCE_THRESHOLD`, `INFERENCE_SIZE`) -> ByteTrack IDs -> seat mapping -> temporal verification -> SEATED/STANDING/UNKNOWN -> statistics -> telemetry. YOLO only finds people; "seated"/"standing" is decided by seat geometry plus temporal consistency.

## 4. Seat Polygon Mapping Algorithm

Seats are fixed polygons in the fixed camera's image (`backend/data/seat_config.json`). For each person the **bottom-centre of the bounding box** `((x1+x2)/2, y2)` is tested with `cv2.pointPolygonTest`; bbox/polygon overlap is a secondary score. Each person gets at most one seat and each seat at most one person (greedy best score; the current stable holder wins conflicts, losers become UNKNOWN). A seat becomes OCCUPIED after `OCCUPANCY_CONFIRM_FRAMES` candidate frames (UNCERTAIN while pending) and EMPTY only after `EMPTY_CONFIRM_FRAMES` frames without a candidate, so it does not flicker.

* **SEATED**: holds a confirmed OCCUPIED seat. **STANDING**: stable, confident track with no seat. **UNKNOWN**: new/unstable track, low confidence (< `STANDING_MIN_CONFIDENCE`), cut off at the frame bottom, pending seat, or seat conflict loser.
* `total_people = seated + standing + unknown`, `occupied_seats = seated_people` (a confirmed seat counts as one seated passenger during a short detection dropout), so nobody is double counted.
* `occupancy_percentage = total_people / MAX_PASSENGERS_PER_COACH * 100` (clamped). Seat usage (`seat_occupancy_percentage`) is reported separately.

Seat configuration tool:
```
python tools/seat_mapper.py --source videos/coach.mp4 --coach-id C1            # click corners, Enter = finish seat, s = save
python tools/seat_mapper.py --source videos/coach.mp4 --coach-id C1 --verify   # view saved polygons
```

## 5. Data flow

`run_vision.py` -> `POST /api/vision/telemetry` (+ `POST /api/vision/frame`) -> `VisionStateService` (in memory) -> `GET /api/simulation/state` and `GET /api/vision/state` -> React polls every 1.5-2 s.

## 6. Backend APIs

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | status, `data_source`, `vision_live` |
| POST | `/api/vision/telemetry` | edge node pushes telemetry (validated, 400 on errors) |
| GET | `/api/vision/state` | latest state of all coaches + recent alerts |
| GET | `/api/vision/coach/<id>` | one coach (404 until telemetry arrives) |
| GET | `/api/vision/alerts` | alert history |
| POST | `/api/vision/ground-truth` | evaluator enters actual values |
| GET / DELETE | `/api/vision/evaluation` | metrics from real ground truth / clear samples |
| GET / POST | `/api/vision/seat-config/<id>` | read / write seat polygons |
| POST / GET | `/api/vision/frame?coach_id=C1` | latest annotated JPEG snapshot |
| GET | `/api/simulation/state` (+ `/next`, `/reset`) | original endpoints, now data-source aware |

```
curl localhost:5000/api/health
curl -X POST localhost:5000/api/vision/telemetry -H "Content-Type: application/json" -d '{
 "coach_id":"C1","timestamp":"2026-10-05T20:30:00","total_people":18,"seated_people":12,
 "standing_people":5,"unknown_people":1,"occupied_seats":12,"empty_seats":8,"uncertain_seats":0,
 "occupancy_percentage":45.0,"density_status":"MODERATE"}'
curl localhost:5000/api/vision/coach/C1
curl -X POST localhost:5000/api/vision/ground-truth -H "Content-Type: application/json" -d '{"coach_id":"C1","actual_people":18}'
curl localhost:5000/api/vision/evaluation
```

The backend recomputes `occupancy_percentage` and `density_status` from its own config (single source of truth), validates that `total = seated + standing + unknown`, and creates alerts: one warning when a coach becomes HIGH, one critical alert on CRITICAL, no repeats while it stays there, a cooldown (`ALERT_COOLDOWN_SECONDS`) against flapping, and a "resolved" event on recovery.

## 7. Frontend integration

The existing dashboard is unchanged apart from: coaches with live camera data show `LIVE CV` and people units, plus a new **Live Vision Monitor** section (annotated camera snapshot, people / occupancy / density, seated/standing/unknown, per-seat OCCUPIED/EMPTY/UNCERTAIN with temporary tracking IDs, FPS), a **Ground Truth & Accuracy** panel and an **Alerts** panel.

## 8. Ground-truth evaluation

Accuracy is never fabricated: with no samples every metric is `null` and the UI says **"Ground truth not available"**.

* **Mode A (live)**: type the real number of people into the panel while the system runs; optionally seated/standing counts and per-seat labels. The sample compares your number to the system's latest telemetry.
* **Mode B (annotated video)**: `python run_vision.py --source videos/coach.mp4 --ground-truth gt.json --no-send` where `gt.json` is `{"<frame number>": actual_people, ...}`; metrics are logged at the end. Use `FRAME_SKIP=1` (or annotate only processed frames).
* **Mode C**: `POST /api/vision/ground-truth` with `detected_people`, `frame` for selected test frames.

Sample: `actual_people, detected_people, actual_density, predicted_density, absolute_error, percentage_error, density_match`. Metrics: count MAE, mean % error, count accuracy (1 - sum|err| / sum actual), density accuracy, seat accuracy, seated/standing accuracy (count-based).

## 9. Installation

```
python -m pip install -r requirements-dev.txt          # backend + vision + pytest
cd frontend && npm install
```
YOLO weights (`yolov8n.pt`) download automatically on first use, or put them in `models/` and pass `--model models/yolov8n.pt` / `MODEL_PATH`.

## 10. Running locally

```
python backend/app.py                      # terminal 1  (DATA_SOURCE=auto|vision|simulation)
cd frontend && npm run dev                 # terminal 2  -> http://localhost:5173
python run_demo.py                         # terminal 3  (or run_vision.py below)
```

## 11. Running with recorded video

```
python run_vision.py --source videos/coach.mp4 --show --loop --realtime
```
`run_demo.py` starts the backend if needed and loops `videos/demo.mp4` (generated from `videos/bus.jpg`). **That sample is a street photo, not a metro coach**: it only demonstrates the pipeline and the sample seat polygons in `seat_config.json` are placed on it. Map your own coach video with the seat tool before trusting any numbers.

## 12. Running with a camera

```
python run_vision.py --source camera       # Pi camera (picamera2) or CAMERA_SOURCE
python run_vision.py --source 0            # USB webcam
python run_vision.py --source rtsp://user:pass@host/stream
```

## 13. Raspberry Pi deployment

Develop and map seats on a laptop first, then on the Pi:
```
sudo apt update && sudo apt install -y python3-venv python3-picamera2 python3-opencv
python3 -m venv --system-site-packages venv && source venv/bin/activate
pip install ultralytics lapx requests
export BACKEND_URL=http://SERVER_IP:5000 COACH_ID=C1 MODEL_PATH=yolov8n.pt
export INFERENCE_SIZE=320 FRAME_SKIP=3 CONFIDENCE_THRESHOLD=0.4
python run_vision.py --source camera
```
Copy `backend/data/seat_config.json` to the Pi (or set `SEAT_CONFIG_PATH`). Configuration variables: `BACKEND_URL, COACH_ID, CAMERA_SOURCE, MODEL_PATH, CONFIDENCE_THRESHOLD, INFERENCE_SIZE, FRAME_SKIP, OCCUPANCY_CONFIRM_FRAMES, EMPTY_CONFIRM_FRAMES, MAX_PASSENGERS_PER_COACH, LOW/MODERATE/HIGH_THRESHOLD, TELEMETRY_INTERVAL`. Use `--debug` to print measured capture/inference/telemetry rates; no FPS is promised: measure on your hardware and lower `INFERENCE_SIZE` / raise `FRAME_SKIP` if needed. The Pi was **not** available during development, so Pi speed is untested.

## 14. Testing

```
python -m pytest tests -q
```
Covers point-in-polygon, assignment, seat conflicts, temporal confirmation, seat release, standing/unknown classification, density, telemetry validation, API, alerts, ground truth, and an integration chain video -> detector -> occupancy -> telemetry -> Flask (including a real-YOLO test when `models/yolov8n.pt` and `videos/demo.mp4` exist).

## 15. Troubleshooting

* *Nothing appears in the dashboard*: check `curl localhost:5000/api/vision/state`; make sure `DATA_SOURCE` is not `simulation`.
* *Python is slow to reach `localhost` on Windows*: the client already maps `localhost` to `127.0.0.1`.
* *"YOLO model could not be loaded"*: no weights / no internet; the pipeline retries every `MODEL_RETRY_SECONDS` and sends nothing meanwhile.
* *Everyone is STANDING/UNKNOWN*: no polygons for this `COACH_ID` (see the startup warning) or polygons do not cover where people's feet land; re-run `tools/seat_mapper.py --verify`.
* *Tracker errors*: install `lapx`; otherwise the detector falls back to a centroid tracker automatically.
* *Backend down*: the edge node keeps only the newest telemetry and retries.

## 16. Limitations

* One camera per coach; seat polygons must be drawn per camera view, and a moved camera needs re-mapping.
* "Seated" is inferred from where a person's feet/bottom-centre fall, so heavy occlusion or unusual postures can give UNKNOWN or errors; accuracy has **not** been measured on real coach footage. Use the ground-truth panel.
* Seated/standing accuracy compares counts, not per-person identities.
* State is in memory (restart clears live state; evaluation samples are logged to `backend/data/evaluation_log.json`).
* Tracking IDs are temporary and reset when the process restarts.
* Frames are annotated snapshots (about 1 per second), not a video stream.
