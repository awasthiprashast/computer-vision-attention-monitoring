import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scoring import (  # noqa: E402
    LEFT_EYE,
    RIGHT_EYE,
    Calibration,
    Calibrator,
    ScoreSmoother,
    calculate_ear,
    estimate_yaw,
    eye_score,
    measure,
    raw_attention_score,
    score_frame,
)


def face(eye_open=0.1, nose_x=0.5):
    """Fake 468-point landmark list with both eyes `eye_open` tall (as a fraction of frame)."""
    pts = [SimpleNamespace(x=0.5, y=0.5) for _ in range(478)]
    for idx_list, cx in ((LEFT_EYE, 0.6), (RIGHT_EYE, 0.4)):
        p1, p2, p3, p4, p5, p6 = idx_list
        pts[p1] = SimpleNamespace(x=cx - 0.05, y=0.4)
        pts[p4] = SimpleNamespace(x=cx + 0.05, y=0.4)
        pts[p2] = SimpleNamespace(x=cx - 0.02, y=0.4 - eye_open / 2)
        pts[p6] = SimpleNamespace(x=cx - 0.02, y=0.4 + eye_open / 2)
        pts[p3] = SimpleNamespace(x=cx + 0.02, y=0.4 - eye_open / 2)
        pts[p5] = SimpleNamespace(x=cx + 0.02, y=0.4 + eye_open / 2)
    pts[1] = SimpleNamespace(x=nose_x, y=0.5)
    return pts


def test_ear_open_greater_than_closed():
    open_ear = calculate_ear(face(eye_open=0.06), LEFT_EYE, 1000, 1000)
    closed_ear = calculate_ear(face(eye_open=0.0), LEFT_EYE, 1000, 1000)
    assert open_ear == pytest.approx(0.6, abs=0.01)
    assert closed_ear == 0.0


def test_ear_handles_zero_eye_width():
    pts = [SimpleNamespace(x=0.5, y=0.5) for _ in range(478)]
    assert calculate_ear(pts, LEFT_EYE, 100, 100) == 0.0


def test_yaw_centred_and_offset():
    assert estimate_yaw(face(nose_x=0.5)) == 0.0
    assert estimate_yaw(face(nose_x=0.8)) == pytest.approx(30)


@pytest.mark.parametrize(
    "ear,yaw,expected",
    [
        (0.4, 0, 100),    # eyes saturate at 100, facing forward
        (0.2, 0, 65),     # 0.7*50 + 0.3*100
        (0.0, 0, 30),     # eyes closed, facing forward
        (0.4, 40, 82),    # eyes open, looking away: 70 + 12
        (0.0, 40, 12),
    ],
)
def test_raw_attention_score(ear, yaw, expected):
    assert raw_attention_score(ear, yaw) == expected


def test_smoother_averages_last_five():
    s = ScoreSmoother()
    for v in (100, 100, 100, 100, 100):
        s.update(v)
    assert s.update(0) == 80  # window now 100,100,100,100,0


def test_smoother_reset():
    s = ScoreSmoother()
    s.update(100)
    s.reset()
    assert s.update(20) == 20


def test_score_frame_end_to_end():
    score, ear, yaw = score_frame(face(eye_open=0.06), 1000, 1000, ScoreSmoother())
    assert 0 <= score <= 100
    assert ear == pytest.approx(0.6, abs=0.01)
    assert yaw == 0.0


# ---- calibration ----


def test_calibrator_not_done_until_enough_frames():
    c = Calibrator(frames=10)
    for _ in range(9):
        c.add(0.14, 0.0)
    assert not c.done and c.result() is None
    assert c.progress == pytest.approx(0.9)
    c.add(0.14, 0.0)
    assert c.done and c.progress == 1.0


def test_calibrator_median_ignores_blinks_and_glances():
    c = Calibrator(frames=11)
    for ear in [0.30] * 8 + [0.02, 0.03, 0.02]:      # three blink frames
        c.add(ear, 0.0)
    result = c.result()
    assert result.ear_baseline == pytest.approx(0.30)


def test_calibrator_records_neutral_head_position():
    c = Calibrator(frames=5)
    for yaw in (8.0, 8.5, 9.0, 8.0, 40.0):           # one glance away
        c.add(0.28, yaw)
    assert c.result().yaw_offset == pytest.approx(8.5)


@pytest.mark.parametrize("ear", [0.02, 0.9])
def test_calibrator_rejects_implausible_baseline(ear):
    c = Calibrator(frames=5)
    for _ in range(5):
        c.add(ear, 0.0)
    assert c.done and c.result() is None


def test_calibrator_ignores_extra_samples_once_done():
    c = Calibrator(frames=3)
    for ear in (0.3, 0.3, 0.3, 0.05, 0.05):
        c.add(ear, 0.0)
    assert c.result().ear_baseline == pytest.approx(0.3)


def test_eye_score_is_relative_to_baseline():
    cal = Calibration(ear_baseline=0.14, yaw_offset=0.0)
    assert eye_score(0.14, cal) == 100            # your normal open eyes
    assert eye_score(0.07, cal) == 50             # half closed
    assert eye_score(0.30, cal) == 100            # clamped
    assert eye_score(0.0, cal) == 0
    assert eye_score(0.14) == 35                  # without calibration the same eyes score low


def test_calibrated_score_for_a_low_ear_user():
    cal = Calibration(ear_baseline=0.14, yaw_offset=0.0)
    assert raw_attention_score(0.14, 0, cal) == 100
    assert raw_attention_score(0.14, 0) == 54     # uncalibrated: the same eyes score about half


def test_yaw_is_measured_from_calibrated_neutral():
    cal = Calibration(ear_baseline=0.3, yaw_offset=20.0)   # sits well off-centre
    _, yaw = measure(face(nose_x=0.7), 1000, 1000, cal)
    assert yaw == pytest.approx(0.0)
    _, uncalibrated = measure(face(nose_x=0.7), 1000, 1000)
    assert uncalibrated == pytest.approx(20.0)


def test_score_frame_uses_calibration():
    cal = Calibration(ear_baseline=0.6, yaw_offset=0.0)
    score, _, _ = score_frame(face(eye_open=0.06), 1000, 1000, ScoreSmoother(), cal)
    assert score == 100
