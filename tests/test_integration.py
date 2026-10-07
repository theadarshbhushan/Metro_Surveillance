"""video -> detector -> occupancy -> telemetry -> Flask -> API.

Part 1 uses a scripted detector (always runs). Part 2 runs the REAL YOLO model on
videos/demo.mp4 and is skipped when the weights/video are not present."""

import os

import numpy as np
import pytest

import config
from app import create_app
from conftest import ROOT, person
from services.vision_service import VisionStateService
from vision.camera import FrameSource, VideoFileSource
from vision.pipeline import Pipeline
from vision.seat_mapper import SeatMapper
from vision.settings import load_settings


class ListSource(FrameSource):
    def __init__(self, n, size=(480, 640)):
        self.n, self.i, self.size = n, 0, size

    def read(self):
        if self.i >= self.n:
            return False, None
        self.i += 1
        return True, np.zeros((*self.size, 3), np.uint8)

    @property
    def frame_index(self):
        return self.i


class FlaskClient:
    """Stands in for TelemetryClient: posts straight into the Flask test client."""

    def __init__(self, http):
        self.http, self.responses = http, []

    def submit_telemetry(self, payload):
        self.responses.append(self.http.post("/api/vision/telemetry", json=payload))

    def submit_frame(self, jpeg):
        self.http.post("/api/vision/frame?coach_id=C1", data=jpeg, content_type="image/jpeg")

    def close(self):
        pass


class ScriptedDetector:
    def __init__(self, script):
        self.script, self.i = script, 0

    def detect(self, frame):
        dets = self.script[min(self.i, len(self.script) - 1)]
        self.i += 1
        return dets


@pytest.fixture
def http(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_SOURCE", "auto")
    svc = VisionStateService(seat_config_path=str(tmp_path / "s.json"), eval_log_path=str(tmp_path / "e.json"))
    return create_app(svc).test_client()


def settings(**kw):
    return load_settings().with_overrides(frame_skip=1, telemetry_interval=0.0, frame_upload_interval=0.001, **kw)


def test_scripted_pipeline_reaches_dashboard_api(http, mapper):
    people = [person(1, 140, 350), person(2, 225, 350), person(3, 340, 340), person(4, 500, 430)]
    pipe = Pipeline(settings(), ListSource(12), detector=ScriptedDetector([people]), mapper=mapper,
                    client=FlaskClient(http))
    pipe.run()
    assert all(r.status_code == 200 for r in pipe.client.responses), pipe.client.responses[-1].json
    state = http.get("/api/vision/coach/C1").json
    assert (state["seated_people"], state["standing_people"], state["total_people"]) == (3, 1, 4)
    assert state["occupied_seats"] == 3 and state["empty_seats"] == 0
    assert set(state["seats"]) == {"S1", "S2", "S3"}
    dash = http.get("/api/simulation/state").json
    assert dash["coaches"][0]["source"] == "vision" and dash["coaches"][0]["current_load"] == 4
    assert dash["coaches"][0]["vision"]["seats"]["S1"]["status"] == "OCCUPIED"
    assert http.get("/api/vision/frame?coach_id=C1").mimetype == "image/jpeg"


def test_pipeline_survives_detector_failure_and_backend_down(mapper):
    class Boom:
        def detect(self, frame):
            raise RuntimeError("cuda exploded")

    class Down:
        def submit_telemetry(self, p):
            raise AssertionError("must not be called when inference failed")

        submit_frame = submit_telemetry

        def close(self):
            pass

    Pipeline(settings(), ListSource(3), detector=Boom(), mapper=mapper, client=Down()).run()  # no exception


def test_model_load_failure_does_not_crash_and_sends_nothing(mapper):
    def factory():
        raise FileNotFoundError("weights missing")

    pipe = Pipeline(settings(), ListSource(3), detector_factory=factory, mapper=mapper, client=None)
    pipe.run()
    assert pipe.processed_frames == 0


def test_annotated_video_ground_truth_mode(mapper):
    people = [person(1, 140, 350), person(2, 500, 430)]
    pipe = Pipeline(settings(), ListSource(8), detector=ScriptedDetector([people]), mapper=mapper,
                    annotations={5: 2, 6: 3})
    pipe.run()
    assert [s["frame"] for s in pipe.local_samples] == [5, 6]
    assert pipe.local_samples[0]["absolute_error"] == 0 and pipe.local_samples[1]["absolute_error"] == 1


DEMO_VIDEO = os.path.join(ROOT, "videos", "demo.mp4")
MODEL = os.path.join(ROOT, "models", "yolov8n.pt")


@pytest.mark.skipif(not (os.path.exists(DEMO_VIDEO) and os.path.exists(MODEL)), reason="demo video / weights missing")
def test_real_yolo_on_demo_video(http):
    from vision.detector import PersonDetector
    s = settings(model_path=MODEL)
    mapper = SeatMapper.from_file(os.path.join(ROOT, "backend", "data", "seat_config.json"), "C1")
    pipe = Pipeline(s, VideoFileSource(DEMO_VIDEO), detector=PersonDetector(s), mapper=mapper,
                    client=FlaskClient(http))
    pipe.run(max_frames=25)
    state = http.get("/api/vision/coach/C1").json
    assert state["total_people"] >= 2
    assert state["seated_people"] + state["standing_people"] + state["unknown_people"] == state["total_people"]
    tracked = [p.detection.track_id for p in pipe.last_result.persons]
    assert all(t is not None for t in tracked)
