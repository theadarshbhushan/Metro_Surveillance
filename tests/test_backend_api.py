import copy

import pytest

import config
from app import create_app
from services.vision_service import VisionStateService


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def client(tmp_path, clock, monkeypatch):
    monkeypatch.setattr(config, "DATA_SOURCE", "auto")
    svc = VisionStateService(seat_config_path=str(tmp_path / "seats.json"),
                             eval_log_path=str(tmp_path / "eval.json"), clock=clock)
    return create_app(svc).test_client()


def telemetry(people=18, seated=12, standing=5, unknown=1, coach="C1", **extra):
    t = {"coach_id": coach, "timestamp": "2026-10-05T20:30:00", "total_people": people,
         "seated_people": seated, "standing_people": standing, "unknown_people": unknown,
         "occupied_seats": seated, "empty_seats": 8, "uncertain_seats": 0,
         "occupancy_percentage": 45.0, "density_status": "MODERATE"}
    t.update(extra)
    return t


def test_health_reports_data_source(client):
    r = client.get("/api/health").json
    assert r["status"] == "ok" and r["data_source"] == "auto" and r["vision_live"] is False


def test_simulation_endpoints_still_work(client):
    r = client.get("/api/simulation/state").json
    assert len(r["coaches"]) == 4 and all(c["source"] == "simulation" for c in r["coaches"])
    assert client.post("/api/simulation/next").json["station"]["index"] == 1
    assert client.post("/api/simulation/reset").json["station"]["index"] == 0


def test_telemetry_roundtrip(client):
    r = client.post("/api/vision/telemetry", json=telemetry())
    assert r.status_code == 200
    body = r.json
    assert body["occupancy_percentage"] == 45.0 and body["density_status"] == "MODERATE" and body["live"] is True
    assert client.get("/api/vision/coach/C1").json["total_people"] == 18
    assert client.get("/api/vision/state").json["any_live"] is True


def test_backend_recomputes_density_itself(client):
    r = client.post("/api/vision/telemetry", json=telemetry(people=38, seated=12, standing=25, unknown=1,
                                                            density_status="LOW", occupancy_percentage=1.0))
    assert r.json["density_status"] == "CRITICAL" and r.json["occupancy_percentage"] == 95.0
    assert r.json["edge_density_status"] == "LOW"


@pytest.mark.parametrize("mutate", [
    lambda t: t.pop("coach_id"),
    lambda t: t.update(coach_id="C9"),
    lambda t: t.update(total_people=-1),
    lambda t: t.update(total_people="18"),
    lambda t: t.update(total_people=99),                 # != seated + standing + unknown
    lambda t: t.update(occupied_seats=3),                # != seated_people
    lambda t: t.update(timestamp="yesterday"),
    lambda t: t.update(seats={"S1": {"status": "BROKEN"}}),
    lambda t: t.update(seats={"S1": {"status": "EMPTY"}}),  # seat counts mismatch
])
def test_malformed_telemetry_rejected(client, mutate):
    t = telemetry()
    mutate(t)
    r = client.post("/api/vision/telemetry", json=t)
    assert r.status_code == 400 and r.json["details"]


def test_non_json_body_rejected(client):
    r = client.post("/api/vision/telemetry", data="not json", content_type="text/plain")
    assert r.status_code == 400


def test_unknown_coach_404(client):
    assert client.get("/api/vision/coach/C1").status_code == 404
    assert client.get("/api/vision/coach/xyz").status_code == 400


def test_auto_mode_replaces_only_live_coach(client, clock):
    client.post("/api/vision/telemetry", json=telemetry())
    coaches = client.get("/api/simulation/state").json["coaches"]
    c1, c2 = coaches[0], coaches[1]
    assert c1["source"] == "vision" and c1["current_load"] == 18 and c1["capacity"] == 40
    assert c1["vision"]["seated_people"] == 12 and c2["source"] == "simulation"
    clock.t += config.VISION_STALE_SECONDS + 1  # edge node went silent -> falls back to simulation
    assert client.get("/api/simulation/state").json["coaches"][0]["source"] == "simulation"


def test_vision_mode_only_shows_vision_coaches(client, monkeypatch):
    monkeypatch.setattr(config, "DATA_SOURCE", "vision")
    r = client.get("/api/simulation/state").json
    assert r["coaches"] == [] and "Waiting" in r["message"]
    client.post("/api/vision/telemetry", json=telemetry())
    r = client.get("/api/simulation/state").json
    assert [c["id"] for c in r["coaches"]] == [1] and r["recommendation"]["coach_id"] == 1


def test_simulation_mode_ignores_vision(client, monkeypatch):
    monkeypatch.setattr(config, "DATA_SOURCE", "simulation")
    client.post("/api/vision/telemetry", json=telemetry())
    assert all(c["source"] == "simulation" for c in client.get("/api/simulation/state").json["coaches"])


# alerts ------------------------------------------------------------------
def _level(client, people, clock, dt=1.0):
    clock.t += dt
    return client.post("/api/vision/telemetry", json=telemetry(people=people, seated=0, standing=people, unknown=0,
                                                              occupied_seats=0))


def test_alert_debounce_and_resolution(client, clock):
    _level(client, 30, clock)       # 75% HIGH -> one warning
    for _ in range(5):
        _level(client, 30, clock)   # stays HIGH -> no repeats
    assert [a["type"] for a in client.get("/api/vision/alerts").json["alerts"]] == ["warning"]
    _level(client, 38, clock)       # CRITICAL -> one critical
    _level(client, 38, clock)
    _level(client, 30, clock)       # back to HIGH: no new alert
    assert [a["type"] for a in client.get("/api/vision/alerts").json["alerts"]] == ["critical", "warning"]
    _level(client, 5, clock)        # LOW -> resolved event
    assert client.get("/api/vision/alerts").json["alerts"][0]["type"] == "resolved"


def test_alert_cooldown_suppresses_flapping(client, clock):
    _level(client, 30, clock)
    _level(client, 5, clock)
    _level(client, 30, clock)       # HIGH again within the cooldown -> suppressed
    kinds = [a["type"] for a in client.get("/api/vision/alerts").json["alerts"]]
    assert kinds.count("warning") == 1
    _level(client, 5, clock)
    _level(client, 30, clock, dt=config.ALERT_COOLDOWN_SECONDS + 1)
    kinds = [a["type"] for a in client.get("/api/vision/alerts").json["alerts"]]
    assert kinds.count("warning") == 2


# ground truth --------------------------------------------------------------
def test_evaluation_empty_says_not_available(client):
    r = client.get("/api/vision/evaluation").json
    assert r["metrics"]["available"] is False and r["metrics"]["person_count_mae"] is None
    assert r["message"] == "Ground truth not available"


def test_ground_truth_requires_telemetry_or_detected_value(client):
    r = client.post("/api/vision/ground-truth", json={"coach_id": "C1", "actual_people": 18})
    assert r.status_code == 400


def test_ground_truth_flow(client):
    client.post("/api/vision/telemetry", json=telemetry(people=17, seated=12, standing=5, unknown=0))
    r = client.post("/api/vision/ground-truth", json={"coach_id": "C1", "actual_people": 18})
    assert r.status_code == 201
    s = r.json
    assert (s["actual_people"], s["detected_people"], s["absolute_error"]) == (18, 17, 1)
    assert s["percentage_error"] == 5.56 and s["density_match"] is True
    m = client.get("/api/vision/evaluation").json["metrics"]
    assert m["samples"] == 1 and m["person_count_mae"] == 1 and m["density_accuracy_percent"] == 100.0
    assert m["seat_accuracy_percent"] is None


def test_ground_truth_with_offline_detected_values(client):
    r = client.post("/api/vision/ground-truth", json={"coach_id": "C1", "actual_people": 20, "detected_people": 10,
                                                      "frame": 1520})
    assert r.status_code == 201 and r.json["frame"] == 1520 and r.json["density_match"] is False


@pytest.mark.parametrize("body", [{"actual_people": -1}, {"actual_people": "x"}, {}, {"coach_id": "Z", "actual_people": 1}])
def test_ground_truth_validation(client, body):
    assert client.post("/api/vision/ground-truth", json=body).status_code == 400


# seat config + frame ---------------------------------------------------------
def test_seat_config_api(client):
    assert client.get("/api/vision/seat-config/C1").status_code == 404
    seats = {"seats": {"S1": [[0, 0], [10, 0], [10, 10]]}, "frame_size": [640, 480]}
    assert client.post("/api/vision/seat-config/C1", json=seats).status_code == 200
    got = client.get("/api/vision/seat-config/C1").json
    assert got["seats"]["S1"][1] == [10.0, 0.0] and got["frame_size"] == [640, 480]
    assert client.post("/api/vision/seat-config/C1", json={"seats": {"S1": [[0, 0]]}}).status_code == 400


def test_frame_upload_and_download(client):
    jpeg = b"\xff\xd8\xff\xe0" + b"0" * 100
    assert client.get("/api/vision/frame?coach_id=C1").status_code == 404
    assert client.post("/api/vision/frame?coach_id=C1", data=jpeg, content_type="image/jpeg").status_code == 200
    r = client.get("/api/vision/frame?coach_id=C1")
    assert r.status_code == 200 and r.mimetype == "image/jpeg" and r.data == jpeg
    assert client.post("/api/vision/frame?coach_id=C1", data=b"nope").status_code == 400
