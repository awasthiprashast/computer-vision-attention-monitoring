"""Pure attention-scoring logic, kept free of OpenCV/MediaPipe so it can be unit tested."""
from collections import deque
from dataclasses import dataclass
from statistics import median

import numpy as np

# MediaPipe FaceMesh landmark indices for the six EAR points of each eye
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

NOSE_TIP = 1

EAR_SCALE = 250          # uncalibrated: eye_score = EAR * EAR_SCALE, clamped to 0-100
YAW_LIMIT = 25           # |yaw| below this counts as facing the screen
HEAD_SCORE_FORWARD = 100
HEAD_SCORE_AWAY = 40
EYE_WEIGHT = 0.7
HEAD_WEIGHT = 0.3
SMOOTHING_WINDOW = 5

CALIBRATION_FRAMES = 90  # face-visible frames to collect (about 3 seconds at 30 fps)
MIN_EAR_BASELINE = 0.10  # outside this range the calibration is rejected (eyes shut, bad detection)
MAX_EAR_BASELINE = 0.50


def euclidean_distance(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))


def calculate_ear(landmarks, eye_indices, w, h):
    """Eye Aspect Ratio for one eye. `landmarks` need `.x` / `.y` in 0-1 coordinates."""
    points = [(int(landmarks[idx].x * w), int(landmarks[idx].y * h)) for idx in eye_indices]
    A = euclidean_distance(points[1], points[5])
    B = euclidean_distance(points[2], points[4])
    C = euclidean_distance(points[0], points[3])
    return (A + B) / (2.0 * C) if C > 0 else 0.0


def estimate_yaw(landmarks):
    """Rough left/right turn estimate from the nose position (0 = centred in frame)."""
    return (landmarks[NOSE_TIP].x - 0.5) * 100


@dataclass(frozen=True)
class Calibration:
    """A person's own reference values, measured while looking at the screen normally."""

    ear_baseline: float   # typical EAR with eyes open
    yaw_offset: float     # nose position that counts as "facing the screen"


class Calibrator:
    """Collects EAR and yaw samples and turns them into a Calibration.

    The median is used so that blinks and brief glances away do not skew the result.
    """

    def __init__(self, frames=CALIBRATION_FRAMES):
        self.frames = frames
        self._ears = []
        self._yaws = []

    def add(self, ear, yaw):
        if not self.done:
            self._ears.append(ear)
            self._yaws.append(yaw)

    @property
    def progress(self):
        return min(1.0, len(self._ears) / self.frames)

    @property
    def done(self):
        return len(self._ears) >= self.frames

    def result(self):
        """The Calibration, or None if not finished or the measured baseline is implausible."""
        if not self.done:
            return None
        baseline = median(self._ears)
        if not MIN_EAR_BASELINE <= baseline <= MAX_EAR_BASELINE:
            return None
        return Calibration(ear_baseline=baseline, yaw_offset=median(self._yaws))


def eye_score(ear_avg, calibration=None):
    """0-100 eye-openness score. Calibrated: your baseline EAR scores 100."""
    if calibration is not None:
        return max(0, min(100, round(ear_avg / calibration.ear_baseline * 100)))
    return max(0, min(100, int(ear_avg * EAR_SCALE)))


def measure(landmarks, w, h, calibration=None):
    """Return (ear_avg, yaw) for one face. Yaw is relative to the calibrated neutral position, if any."""
    ear_avg = (calculate_ear(landmarks, LEFT_EYE, w, h) + calculate_ear(landmarks, RIGHT_EYE, w, h)) / 2.0
    yaw = estimate_yaw(landmarks)
    if calibration is not None:
        yaw -= calibration.yaw_offset
    return ear_avg, yaw


def raw_attention_score(ear_avg, yaw, calibration=None):
    """Combine eye openness and head direction into a 0-100 score.

    `yaw` must already be relative to the neutral position (see `measure`).
    """
    head_score = HEAD_SCORE_FORWARD if abs(yaw) < YAW_LIMIT else HEAD_SCORE_AWAY
    return int(EYE_WEIGHT * eye_score(ear_avg, calibration) + HEAD_WEIGHT * head_score)


class ScoreSmoother:
    """Moving average over the last `window` scores."""

    def __init__(self, window=SMOOTHING_WINDOW):
        self._history = deque(maxlen=window)

    def update(self, score):
        self._history.append(score)
        return int(sum(self._history) / len(self._history))

    def reset(self):
        self._history.clear()


def score_frame(landmarks, w, h, smoother, calibration=None):
    """Return (attention_score, ear_avg, yaw) for one detected face."""
    ear_avg, yaw = measure(landmarks, w, h, calibration)
    return smoother.update(raw_attention_score(ear_avg, yaw, calibration)), ear_avg, yaw
