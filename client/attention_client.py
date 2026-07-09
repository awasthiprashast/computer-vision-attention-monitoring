import cv2
import mediapipe as mp
import numpy as np
import time
import requests
import uuid

# ========================= CONFIG =========================
STUDENT_ID = "prashast_001"
EC2_API_URL = "http://43.204.22.69:8000/attention"
SEND_INTERVAL = 1.0

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

def euclidean_distance(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))

def calculate_ear(landmarks, eye_indices, w, h):
    points = [(int(landmarks[idx].x * w), int(landmarks[idx].y * h)) for idx in eye_indices]
    A = euclidean_distance(points[1], points[5])
    B = euclidean_distance(points[2], points[4])
    C = euclidean_distance(points[0], points[3])
    ear = (A + B) / (2.0 * C) if C > 0 else 0.0
    return ear

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open webcam")
        return

    cap.set(cv2.CAP_PROP_FPS, 30)
    session_id = str(uuid.uuid4())
    last_send_time = time.time()

    # For smoothing attention score
    attention_history = []

    print(f"✅ Session started: {session_id}")
    print("Press 'q' to quit\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = frame.shape

        results = face_mesh.process(rgb_frame)

        attention_score = 50
        ear_avg = 0.0
        yaw = 0.0

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark

            # EAR Calculation
            left_ear = calculate_ear(landmarks, LEFT_EYE, w, h)
            right_ear = calculate_ear(landmarks, RIGHT_EYE, w, h)
            ear_avg = (left_ear + right_ear) / 2.0

            # Simple Head Pose (Yaw - left/right turn) using nose position
            nose_x = landmarks[1].x
            yaw = (nose_x - 0.5) * 100   # rough yaw estimation

            # Improved Attention Score
            eye_score = max(0, min(100, int(ear_avg * 250)))
            head_score = 100 if abs(yaw) < 25 else 40
            raw_score = int(0.7 * eye_score + 0.3 * head_score)

            # Smoothing (average of last 5 frames)
            attention_history.append(raw_score)
            if len(attention_history) > 5:
                attention_history.pop(0)
            attention_score = int(sum(attention_history) / len(attention_history))

            # Draw face mesh
            mp_drawing.draw_landmarks(
                frame, results.multi_face_landmarks[0],
                mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style()
            )

        # Send to backend
        if time.time() - last_send_time >= SEND_INTERVAL:
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
            try:
                requests.post(EC2_API_URL, json=payload, timeout=2)
                print(f"Sent → Attention: {attention_score}% | EAR: {ear_avg:.3f} | Yaw: {yaw:.1f}")
            except:
                print("⚠️ Could not send to backend")

            last_send_time = time.time()

        # Display
        color = (0, 255, 0) if attention_score >= 60 else (0, 165, 255)
        cv2.putText(frame, f"Attention: {attention_score}%", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.3, color, 3)
        cv2.putText(frame, f"EAR: {ear_avg:.3f}  |  Yaw: {yaw:.1f}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

        cv2.imshow("Attention Monitoring System", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Session ended.")

if __name__ == "__main__":
    main()