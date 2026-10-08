import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scoring import (  # noqa: E402
    LEFT_EYE,
    RIGHT_EYE,
    ScoreSmoother,
    calculate_ear,
    estimate_yaw,
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
