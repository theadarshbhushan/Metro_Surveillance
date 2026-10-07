import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.environ.setdefault("DATA_SOURCE", "auto")

import pytest  # noqa: E402

from vision.seat_mapper import SeatMapper  # noqa: E402
from vision.types import Detection  # noqa: E402

SEATS = {
    "S1": [[100, 300], [180, 300], [190, 380], [95, 380]],
    "S2": [[180, 300], [260, 300], [270, 380], [190, 380]],
    "S3": [[300, 300], [380, 300], [380, 380], [300, 380]],
}


@pytest.fixture
def mapper():
    return SeatMapper(SEATS)


def person(tid, cx, bottom_y, w=40, h=120, conf=0.9):
    """A detection whose bottom-centre is (cx, bottom_y)."""
    return Detection(bbox=(cx - w / 2, bottom_y - h, cx + w / 2, bottom_y), confidence=conf, track_id=tid)


@pytest.fixture
def make_person():
    return person
