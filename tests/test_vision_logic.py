import json

import pytest

from conftest import person
from vision import density
from vision.ground_truth import compute_metrics, load_frame_annotations, make_sample
from vision.occupancy import OccupancyEngine
from vision.seat_mapper import SeatMapper, point_in_polygon, save_coach_seats
from vision.types import (
    PERSON_SEATED, PERSON_STANDING, PERSON_UNKNOWN,
    SEAT_EMPTY, SEAT_OCCUPIED, SEAT_UNCERTAIN,
)

FRAME = (640, 480)


def engine(mapper, **kw):
    return OccupancyEngine(mapper, occupancy_confirm_frames=kw.get("n", 5), empty_confirm_frames=kw.get("e", 5),
                           standing_confirm_frames=kw.get("s", 3))


# 1/2 geometry ---------------------------------------------------------
def test_point_inside_polygon(mapper):
    assert point_in_polygon((140, 340), mapper.seats["S1"])


def test_point_outside_polygon(mapper):
    assert not point_in_polygon((50, 50), mapper.seats["S1"])
    assert not point_in_polygon((140, 390), mapper.seats["S1"])


# 3 person-seat assignment ---------------------------------------------
def test_person_assignment_uses_bottom_center(mapper):
    cands = mapper.candidates_for(person(1, 140, 350).bbox)
    assert [c.seat_id for c in cands] == ["S1"]
    assert mapper.candidates_for(person(1, 140, 200).bbox) == []  # feet above the polygon


def test_polygons_scale_with_frame_size():
    m = SeatMapper({"S1": [[0, 0], [10, 0], [10, 10], [0, 10]]}, frame_size=(100, 100))
    assert m.scaled(200, 200).seats["S1"][2] == [20.0, 20.0]


# 4 conflicts -----------------------------------------------------------
def test_two_people_one_seat_only_one_seat_and_no_double_count(mapper):
    eng = engine(mapper)
    for _ in range(6):
        res = eng.update([person(1, 140, 350), person(2, 142, 352)], FRAME)
    states = sorted(p.state for p in res.persons)
    assert states == [PERSON_SEATED, PERSON_UNKNOWN]
    c = res.counts()
    assert c["occupied_seats"] == 1 and c["seated"] == 1
    assert c["seated"] + c["standing"] + c["unknown"] == len(res.persons)


def test_stable_holder_wins_conflict(mapper):
    eng = engine(mapper)
    for _ in range(6):
        res = eng.update([person(1, 140, 350)], FRAME)
    res = eng.update([person(1, 140, 350), person(9, 140, 350)], FRAME)
    seated = [p for p in res.persons if p.state == PERSON_SEATED]
    assert [p.detection.track_id for p in seated] == [1]


# 5 temporal confirmation ---------------------------------------------
def test_occupancy_needs_confirm_frames(mapper):
    eng = engine(mapper)
    statuses = []
    for _ in range(5):
        res = eng.update([person(1, 140, 350)], FRAME)
        statuses.append(res.seats["S1"].status)
    assert statuses == [SEAT_UNCERTAIN] * 4 + [SEAT_OCCUPIED]
    assert res.persons[0].state == PERSON_SEATED and res.persons[0].seat_id == "S1"


def test_passer_by_does_not_occupy_seat(mapper):
    eng = engine(mapper)
    for _ in range(2):
        eng.update([person(1, 140, 350)], FRAME)
    for _ in range(6):
        res = eng.update([], FRAME)
    assert res.seats["S1"].status == SEAT_EMPTY


# 6 becoming empty ----------------------------------------------------
def test_seat_becomes_empty_only_after_empty_confirm(mapper):
    eng = engine(mapper)
    for _ in range(6):
        eng.update([person(1, 140, 350)], FRAME)
    for i in range(4):  # person vanishes for a few frames: still occupied (and counted as seated)
        res = eng.update([], FRAME)
        assert res.seats["S1"].status == SEAT_OCCUPIED
        assert res.counts()["seated"] == 1
    res = eng.update([], FRAME)
    assert res.seats["S1"].status == SEAT_EMPTY
    assert res.counts()["seated"] == 0


# 7 standing ----------------------------------------------------------
def test_standing_classification(mapper):
    eng = engine(mapper)
    for _ in range(4):
        res = eng.update([person(7, 500, 400)], FRAME)
    assert res.persons[0].state == PERSON_STANDING and res.persons[0].seat_id is None
    assert res.counts()["standing"] == 1 and res.counts()["occupied_seats"] == 0


def test_new_track_and_low_confidence_are_unknown(mapper):
    eng = engine(mapper)
    res = eng.update([person(7, 500, 400)], FRAME)
    assert res.persons[0].state == PERSON_UNKNOWN  # track too young
    for _ in range(5):
        res = eng.update([person(8, 500, 400, conf=0.45)], FRAME)
    assert res.persons[0].state == PERSON_UNKNOWN  # below standing confidence


def test_person_cut_off_at_frame_bottom_is_unknown(mapper):
    eng = engine(mapper)
    for _ in range(5):
        res = eng.update([person(7, 500, 480)], FRAME)
    assert res.persons[0].state == PERSON_UNKNOWN


def test_total_is_sum_of_parts_and_seated_never_double_counted(mapper):
    eng = engine(mapper)
    dets = [person(1, 140, 350), person(2, 225, 350), person(3, 500, 400), person(4, 600, 400)]
    for _ in range(6):
        res = eng.update(dets, FRAME)
    c = res.counts()
    assert (c["seated"], c["standing"], c["unknown"]) == (2, 2, 0)
    stats = density.compute_stats(c["seated"], c["standing"], c["unknown"], c["occupied_seats"],
                                  c["empty_seats"], c["uncertain_seats"], 40)
    assert stats["total_people"] == 4 and stats["occupied_seats"] == 2 and stats["empty_seats"] == 1


def test_no_seat_config_does_not_crash():
    eng = OccupancyEngine(None)
    for _ in range(4):
        res = eng.update([person(1, 100, 100)], FRAME)
    assert res.seats == {} and res.persons[0].state == PERSON_STANDING


# 8 density -----------------------------------------------------------
@pytest.mark.parametrize("pct,label", [(0, "LOW"), (40, "LOW"), (40.1, "MODERATE"), (65, "MODERATE"),
                                       (65.1, "HIGH"), (85, "HIGH"), (85.1, "CRITICAL"), (100, "CRITICAL")])
def test_density_thresholds(pct, label):
    assert density.density_status(pct) == label


def test_occupancy_percentage_is_people_over_capacity_and_clamped():
    assert density.occupancy_percentage(18, 40) == 45.0
    assert density.occupancy_percentage(80, 40) == 100.0
    assert density.occupancy_percentage(5, 0) == 0.0


def test_seat_occupancy_is_separate_from_crowd_density():
    s = density.compute_stats(2, 18, 0, 2, 8, 0, 40)
    assert s["occupancy_percentage"] == 50.0 and s["seat_occupancy_percentage"] == 20.0


# 11 ground truth ------------------------------------------------------
def test_ground_truth_sample_matches_spec_example():
    s = make_sample(18, 17, 40, frame=1520)
    assert s["absolute_error"] == 1 and s["percentage_error"] == 5.56
    assert s["actual_density"] == "MODERATE" and s["predicted_density"] == "MODERATE" and s["density_match"] is True


def test_metrics_none_without_samples():
    m = compute_metrics([])
    assert m["available"] is False and m["person_count_mae"] is None and m["density_accuracy_percent"] is None


def test_metrics_values():
    samples = [make_sample(18, 17, 40), make_sample(30, 20, 40),
               make_sample(10, 10, 40, actual_seats={"S1": "OCCUPIED", "S2": "EMPTY"},
                           detected_seats={"S1": "OCCUPIED", "S2": "OCCUPIED"})]
    m = compute_metrics(samples)
    assert m["person_count_mae"] == pytest.approx((1 + 10 + 0) / 3, abs=1e-3)
    assert m["density_accuracy_percent"] == pytest.approx(66.7, abs=0.1)  # 30 actual=HIGH, 20 detected=MODERATE
    assert m["seat_accuracy_percent"] == 50.0
    assert m["seated_standing_accuracy_percent"] is None  # nothing labelled -> no fake number


def test_zero_actual_percentage_error():
    assert make_sample(0, 0, 40)["percentage_error"] == 0.0
    assert make_sample(0, 2, 40)["percentage_error"] is None


def test_annotation_file_validation(tmp_path):
    p = tmp_path / "gt.json"
    p.write_text(json.dumps({"10": 3, "20": 4}))
    assert load_frame_annotations(str(p)) == {10: 3, 20: 4}
    p.write_text(json.dumps({"10": -1}))
    with pytest.raises(ValueError):
        load_frame_annotations(str(p))


def test_seat_config_save_and_load_roundtrip(tmp_path):
    path = str(tmp_path / "seats.json")
    save_coach_seats(path, "C1", {"S1": [[0, 0], [10, 0], [10, 10]]}, (640, 480))
    save_coach_seats(path, "C2", {"A": [[0, 0], [5, 0], [5, 5]]})
    m = SeatMapper.from_file(path, "C1")
    assert m.seat_ids == ["S1"] and m.frame_size == (640, 480)
    assert SeatMapper.from_file(path, "C2").seat_ids == ["A"]
    assert SeatMapper.from_file(path, "C3") is None
    assert SeatMapper.from_file(str(tmp_path / "missing.json"), "C1") is None
    with pytest.raises(ValueError):
        save_coach_seats(path, "C1", {"S1": [[0, 0], [1, 1]]})


def test_prompt_style_seat_config_layout():
    cfg = {"coach_1": {"S1": [[100, 300], [180, 300], [190, 380], [95, 380]]}}
    assert SeatMapper.from_config(cfg, "C1").seat_ids == ["S1"]


def test_polygon_dict_seat_config_layout():
    cfg = {"C1": {"S1": {"polygon": [[100, 300], [180, 300], [190, 380], [95, 380]]},
                  "S2": {"polygon": [[180, 300], [260, 300], [270, 380], [190, 380]]}}}
    m = SeatMapper.from_config(cfg, "C1")
    assert m.seat_ids == ["S1", "S2"]
    assert point_in_polygon((145, 350), m.seats["S1"]) and not point_in_polygon((145, 350), m.seats["S2"])


def test_reference_image_roundtrip(tmp_path):
    path = str(tmp_path / "seats.json")
    save_coach_seats(path, "C1", {"S1": [[0, 0], [10, 0], [10, 10]]}, (640, 480), reference_image="reference_frames/C1.jpg")
    assert SeatMapper.from_file(path, "C1").reference_image == "reference_frames/C1.jpg"


def test_nested_fragment_boxes_are_suppressed():
    from vision.detector import PersonDetector
    from vision.types import Detection
    full = Detection((100, 100, 300, 500), 0.9, 1)
    fragment = Detection((120, 100, 280, 300), 0.5, 2)          # upper body nested in the full box
    twin = Detection((100, 105, 296, 500), 0.4, 3)              # same person, same feet
    neighbour = Detection((280, 150, 400, 500), 0.6, 4)         # genuinely different person
    kept = {d.track_id for d in PersonDetector.suppress_fragments([full, fragment, twin, neighbour])}
    assert kept == {1, 4}


def test_tall_truncated_box_outside_seats_is_standing_only_when_enabled(mapper):
    tall = person(1, 450, 480, w=100, h=380)  # bottom edge == frame height (480), outside every seat
    for _ in range(5):
        r = engine(mapper).update([tall], FRAME)
    assert r.persons[0].state == PERSON_UNKNOWN
    e = OccupancyEngine(mapper, standing_confirm_frames=3, truncated_standing_min_height=0.5)
    for _ in range(5):
        r = e.update([tall], FRAME)
    assert r.persons[0].state == PERSON_STANDING


def test_seated_needs_consecutive_frames_then_survives_one_missed_frame(mapper):
    """Section 9: one frame in a seat polygon is never SEATED; a single missed detection does not free the seat."""
    e = engine(mapper, n=5, e=5)
    sitter = person(1, 145, 350)
    assert e.update([sitter], FRAME).persons[0].state == PERSON_UNKNOWN
    for _ in range(5):
        r = e.update([sitter], FRAME)
    assert r.persons[0].state == PERSON_SEATED and r.persons[0].seat_id == "S1"
    assert e.update([], FRAME).seats["S1"].status == SEAT_OCCUPIED
