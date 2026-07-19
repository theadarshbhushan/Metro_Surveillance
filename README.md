# SmartMetro — Intelligent Metro Crowd Management System

A rule-based crowd distribution prototype for metro coaches. Phase 1 is a fully verified Flask REST backend with CSV-based simulation. Phase 2 will add a React dashboard; Phase 3 will swap the data source for real hardware (load cells / YOLO passenger detection).

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
SmartMetro/
├── backend/
│   ├── app.py                      # Flask entry point + CORS + blueprint registration
│   ├── config.py                   # All constants: capacity, density thresholds, loop flag
│   ├── metro.py                    # Coach domain model (occupancy, density, movement)
│   ├── simulation.py               # Data source: reads stations.csv, tracks position
│   ├── logic.py                    # Rule-Based Crowd Distribution Engine (pure functions)
│   ├── data/
│   │   └── stations.csv            # 8 realistic simulated stations (Mumbai metro-inspired)
│   ├── routes/
│   │   ├── __init__.py
│   │   └── simulation_routes.py    # /api/simulation/* endpoint definitions
│   ├── services/
│   │   ├── __init__.py
│   │   └── metro_service.py        # Assembles complete state; called by all routes
│   └── requirements.txt
├── frontend/
│   └── .gitkeep                    # React/Vite dashboard — Phase 2
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
