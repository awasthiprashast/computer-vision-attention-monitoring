"""Pure attention-scoring logic, kept free of OpenCV/MediaPipe so it can be unit tested."""
from collections import deque

import numpy as np

# MediaPipe FaceMesh landmark indices for the six EAR points of each eye
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

NOSE_TIP = 1

EAR_SCALE = 250          # eye_score = EAR * EAR_SCALE, clamped to 0-100
YAW_LIMIT = 25           # |yaw| below this counts as facing the screen
HEAD_SCORE_FORWARD = 100
HEAD_SCORE_AWAY = 40
EYE_WEIGHT = 0.7
HEAD_WEIGHT = 0.3
SMOOTHING_WINDOW = 5


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


def raw_attention_score(ear_avg, yaw):
    """Combine eye openness and head direction into a 0-100 score."""
    eye_score = max(0, min(100, int(ear_avg * EAR_SCALE)))
    head_score = HEAD_SCORE_FORWARD if abs(yaw) < YAW_LIMIT else HEAD_SCORE_AWAY
    return int(EYE_WEIGHT * eye_score + HEAD_WEIGHT * head_score)


class ScoreSmoother:
    """Moving average over the last `window` scores."""

    def __init__(self, window=SMOOTHING_WINDOW):
        self._history = deque(maxlen=window)

    def update(self, score):
        self._history.append(score)
        return int(sum(self._history) / len(self._history))

    def reset(self):
        self._history.clear()


def score_frame(landmarks, w, h, smoother):
    """Return (attention_score, ear_avg, yaw) for one detected face."""
    ear_avg = (calculate_ear(landmarks, LEFT_EYE, w, h) + calculate_ear(landmarks, RIGHT_EYE, w, h)) / 2.0
    yaw = estimate_yaw(landmarks)
    return smoother.update(raw_attention_score(ear_avg, yaw)), ear_avg, yaw
