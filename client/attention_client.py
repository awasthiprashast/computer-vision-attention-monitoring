import os
import time
import uuid

import cv2
import mediapipe as mp
import requests

from scoring import Calibrator, ScoreSmoother, measure, score_frame

# ========================= CONFIG =========================
# Set via environment variables (see .env.example).
STUDENT_ID = os.environ.get("STUDENT_ID", "student_001")
API_URL = os.environ.get("API_URL", "http://localhost:8000/attention")
API_KEY = os.environ.get("API_KEY", "")
SEND_INTERVAL = float(os.environ.get("SEND_INTERVAL", "1.0"))
CALIBRATE = os.environ.get("CALIBRATE", "1") != "0"

mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles


def send_record(payload):
    """POST one reading to the backend. Returns True on success."""
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=2)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[warn] Could not send to backend: {e}")
        return False


def draw_calibration_overlay(frame, progress):
    """Instructions and a progress bar shown while the baseline is being measured."""
    h, w, _ = frame.shape
    cv2.putText(frame, "Calibrating...", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 200, 0), 3)
    cv2.putText(frame, "Look at the screen normally and blink as usual", (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.rectangle(frame, (20, 110), (w - 20, 130), (255, 255, 255), 2)
    cv2.rectangle(frame, (20, 110), (20 + int((w - 40) * progress), 130), (255, 200, 0), -1)


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[error] Could not open webcam")
        return

    cap.set(cv2.CAP_PROP_FPS, 30)
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    session_id = str(uuid.uuid4())
    last_send_time = time.time()
    smoother = ScoreSmoother()
    calibrator = Calibrator() if CALIBRATE else None
    calibration = None

    print(f"[ok] Session started: {session_id}")
    print("Press 'q' to quit, 'c' to recalibrate\n")
    if calibrator:
        print("[calibration] Look at the screen normally for a few seconds...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = frame.shape

        results = face_mesh.process(rgb_frame)

        # No face in frame means no data: nothing is scored or sent.
        attention_score = None
        ear_avg = 0.0
        yaw = 0.0

        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]

            if calibrator:
                ear, raw_yaw = measure(face_landmarks.landmark, w, h)
                calibrator.add(ear, raw_yaw)
                if calibrator.done:
                    calibration = calibrator.result()
                    calibrator = None
                    smoother.reset()
                    if calibration:
                        print(f"[calibration] Done: baseline EAR {calibration.ear_baseline:.3f}, "
                              f"neutral head position {calibration.yaw_offset:.1f}")
                    else:
                        print("[warn] Calibration failed (eyes closed or face not detected well). "
                              "Using the default scale; press 'c' to retry.")
            else:
                attention_score, ear_avg, yaw = score_frame(
                    face_landmarks.landmark, w, h, smoother, calibration)

            mp_drawing.draw_landmarks(
                frame, face_landmarks,
                mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style()
            )
        else:
            smoother.reset()

        # Send to backend
        if attention_score is not None and time.time() - last_send_time >= SEND_INTERVAL:
            payload = {
                "session_id": session_id,
                "student_id": STUDENT_ID,
                "timestamp": time.time(),
                "attention_score": attention_score,
                "ear": round(ear_avg, 4),
                "yaw": round(yaw, 2),
                "pitch": 0.0,
                "roll": 0.0
            }
            if send_record(payload):
                print(f"Sent -> Attention: {attention_score}% | EAR: {ear_avg:.3f} | Yaw: {yaw:.1f}")
            last_send_time = time.time()

        # Display
        if calibrator and results.multi_face_landmarks:
            draw_calibration_overlay(frame, calibrator.progress)
        elif attention_score is None:
            cv2.putText(frame, "No face detected", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 255), 3)
        else:
            color = (0, 255, 0) if attention_score >= 60 else (0, 165, 255)
            cv2.putText(frame, f"Attention: {attention_score}%", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.3, color, 3)
            cv2.putText(frame, f"EAR: {ear_avg:.3f}  |  Yaw: {yaw:.1f}", (20, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        cv2.imshow("Attention Monitoring System", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key == ord('c'):
            calibrator, calibration = Calibrator(), None
            smoother.reset()
            print("[calibration] Restarted: look at the screen normally for a few seconds...")

    cap.release()
    cv2.destroyAllWindows()
    print("Session ended.")


if __name__ == "__main__":
    main()
