import base64
import io
import tempfile
from typing import Optional

try:
    import cv2
    import mediapipe as mp
    import numpy as np
    # Use the new MediaPipe Tasks API (v0.10+)
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe import Image, ImageFormat
    _POSE_AVAILABLE = True
except ImportError:
    _POSE_AVAILABLE = False
    np = None  # type: ignore


class PoseService:
    """Server-side MediaPipe pose detection with angle-based rep counting.
    
    Rep counting state machine ported from Pushup_counter.py:
        if angle > up_angle:       up_pos = 'Up'
        if angle < down_angle and up_pos == 'Up':  down_pos = 'Down'
        if angle > up_angle and down_pos == 'Down': counter += 1; reset
    """

    # Per-exercise angle thresholds (from Pushup_counter.py)
    EXERCISE_CONFIGS = {
        "pushup": {"up_angle": 160, "down_angle": 110, "joint": "left_elbow"},
        "squat": {"up_angle": 170, "down_angle": 90, "joint": "left_knee"},
        "lunge": {"up_angle": 170, "down_angle": 90, "joint": "left_knee"},
        "situp": {"up_angle": 160, "down_angle": 70, "joint": "left_hip"},
        "pullup": {"up_angle": 170, "down_angle": 90, "joint": "left_elbow"},
        "burpee": {"up_angle": 170, "down_angle": 160, "joint": "left_knee"},
    }

    # MediaPipe Pose landmark indices
    LANDMARK_INDICES = {
        "left_shoulder": 11, "right_shoulder": 12,
        "left_elbow": 13, "right_elbow": 14,
        "left_wrist": 15, "right_wrist": 16,
        "left_hip": 23, "right_hip": 24,
        "left_knee": 25, "right_knee": 26,
        "left_ankle": 27, "right_ankle": 28,
    }

    def __init__(self):
        self.landmarker = None
        self._pose_legacy = None
        # Per-user session state
        self._sessions: dict[str, dict] = {}

        if not _POSE_AVAILABLE:
            return

        try:
            # Try the new Tasks API first (MediaPipe 0.10+)
            # model_asset_path="" is no longer valid — use the legacy API as fallback
            import mediapipe as mp_core
            self._pose_legacy = mp_core.solutions.pose.Pose(
                static_image_mode=True,
                model_complexity=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        except Exception:
            self._pose_legacy = None

    def process_frame(
        self,
        image_base64: str,
        exercise_type: str = "pushup",
        session_id: str = "default",
    ) -> dict:
        """Process a single camera frame and return pose data + rep count."""
        if not _POSE_AVAILABLE or self._pose_legacy is None:
            return {
                "error": "Pose detection not available. Install: pip install opencv-python-headless mediapipe",
                "landmarks": [],
                "angles": {},
                "rep_counted": False,
                "phase": "REST",
                "total_reps": 0,
            }
        # Decode image
        image_data = base64.b64decode(image_base64)
        nparr = np.frombuffer(image_data, np.uint8)
        image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image_bgr is None:
            return {"error": "Could not decode image", "landmarks": [], "angles": {}}

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        image_height, image_width = image_rgb.shape[:2]

        # Run detection using legacy API
        result = self._pose_legacy.process(image_rgb)

        if not result.pose_landmarks:
            return {
                "error": "No pose detected",
                "landmarks": [],
                "angles": {},
                "rep_counted": False,
                "phase": "REST",
                "total_reps": self._get_reps(session_id),
            }

        # Extract landmarks (normalized 0-1)
        raw = result.pose_landmarks.landmark
        landmarks = []
        for lm in raw:
            landmarks.append({
                "x": lm.x,
                "y": lm.y,
                "z": lm.z,
                "visibility": lm.visibility if hasattr(lm, 'visibility') else 0.0,
            })

        # Get joint pixel coordinates
        def get_xy(name: str) -> tuple[float, float]:
            idx = self.LANDMARK_INDICES[name]
            return (raw[idx].x * image_width, raw[idx].y * image_height)

        shoulder_l = get_xy("left_shoulder")
        shoulder_r = get_xy("right_shoulder")
        elbow_l = get_xy("left_elbow")
        elbow_r = get_xy("right_elbow")
        wrist_l = get_xy("left_wrist")
        wrist_r = get_xy("right_wrist")
        hip_l = get_xy("left_hip")
        hip_r = get_xy("right_hip")
        knee_l = get_xy("left_knee")
        knee_r = get_xy("right_knee")
        ankle_l = get_xy("left_ankle")
        ankle_r = get_xy("right_ankle")

        # Calculate angles (from gym_code.py calculate_angle)
        angles = {
            "left_elbow": int(self._calculate_angle(shoulder_l, elbow_l, wrist_l)),
            "right_elbow": int(self._calculate_angle(shoulder_r, elbow_r, wrist_r)),
            "left_knee": int(self._calculate_angle(hip_l, knee_l, ankle_l)),
            "right_knee": int(self._calculate_angle(hip_r, knee_r, ankle_r)),
        }

        # Rep counting (from Pushup_counter.py state machine)
        config = self.EXERCISE_CONFIGS.get(exercise_type, self.EXERCISE_CONFIGS["pushup"])
        joint_name = config["joint"]
        angle = angles.get(joint_name, 180)
        up_angle = config["up_angle"]
        down_angle = config["down_angle"]

        session = self._sessions.get(session_id, {"up_pos": None, "down_pos": None, "reps": 0})
        phase = "REST"
        rep_counted = False

        if angle > up_angle:
            session["up_pos"] = "Up"
            phase = "UP"
        elif angle < down_angle and session["up_pos"] == "Up":
            session["down_pos"] = "Down"
            phase = "DOWN"

        if angle > up_angle and session["down_pos"] == "Down":
            session["reps"] += 1
            rep_counted = True
            session["up_pos"] = None
            session["down_pos"] = None
            phase = "UP"

        self._sessions[session_id] = session

        return {
            "landmarks": landmarks,
            "angles": angles,
            "rep_counted": rep_counted,
            "phase": phase,
            "total_reps": session["reps"],
            "image_width": image_width,
            "image_height": image_height,
        }

    def reset_session(self, session_id: str = "default"):
        if session_id in self._sessions:
            self._sessions[session_id] = {"up_pos": None, "down_pos": None, "reps": 0}

    def _get_reps(self, session_id: str) -> int:
        return self._sessions.get(session_id, {}).get("reps", 0)

    @staticmethod
    def _calculate_angle(a: tuple, b: tuple, c: tuple) -> float:
        """Ported 1:1 from gym_code.py calculate_angle() and Pushup_counter.py."""
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        if angle > 180.0:
            angle = 360 - angle
        return angle
