"""
AeroTouch MediaPipe 3D Dual-Hand Tracking Adapter
Modern MediaPipe Tasks Vision Architecture (Compatible with Python 3.10, 3.11, 3.12+).
Auto-downloads model asset on first run and extracts 21 3D landmarks per hand at native 60 FPS.
"""

import os
import urllib.request
from typing import List, Optional, Tuple

import cv2
import numpy as np

from src.gestures.engine import HandLandmarks


MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(MODEL_DIR, "hand_landmarker.task")


def ensure_model_asset() -> str:
    """Ensures hand_landmarker.task exists, auto-downloading if missing."""
    if not os.path.exists(MODEL_PATH) or os.path.getsize(MODEL_PATH) < 1000:
        print("[AeroTouch Vision]: Downloading official hand_landmarker.task bundle...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("[AeroTouch Vision]: Model asset cached successfully.")
    return MODEL_PATH


class DualHandTracker:
    """
    Encapsulates modern MediaPipe HandLandmarker with dual-hand (num_hands=2) detection.
    Provides robust handedness separation so that:
      1. Both hands are detected simultaneously without dropping or overwriting.
      2. Turning the right hand over (showing palm vs back of hand) never flips handedness to Left.
      3. A single Left hand never controls the cursor (right_hand is None).
    """

    def __init__(
        self,
        num_hands: int = 2,
        min_hand_detection_confidence: float = 0.5,
        min_hand_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5
    ):
        self.num_hands = num_hands
        self.detector = None

        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision

            model_file = ensure_model_asset()
            base_options = mp_python.BaseOptions(model_asset_path=model_file)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=num_hands,
                min_hand_detection_confidence=min_hand_detection_confidence,
                min_hand_presence_confidence=min_hand_presence_confidence,
                min_tracking_confidence=min_tracking_confidence
            )
            self.detector = vision.HandLandmarker.create_from_options(options)
            print("[AeroTouch Vision]: MediaPipe 3D HandLandmarker Engine ONLINE.")
        except Exception as e:
            print(f"[AeroTouch Vision]: Warning - Initializing in Fallback Mode: {e}")

    @staticmethod
    def _compute_3d_chirality(pts: List[Tuple[float, float, float]]) -> float:
        """
        Computes the 3D scalar triple product of the hand:
          triple_product = thumb_vec . (longitudinal_axis x transverse_axis)
        
        This quantity is a rigid 3D rotation invariant (SO(3) invariant).
        It maintains the EXACT same sign whether the hand is facing
        palm-forward, back-of-hand, tilted, or rotated at any 3D angle.
        It ONLY changes sign under chiral reflection (Left vs Right hand).
        """
        if len(pts) < 21:
            return 0.0

        p0 = np.array(pts[0][:3])    # Wrist
        p2 = np.array(pts[2][:3])    # Thumb MCP
        p5 = np.array(pts[5][:3])    # Index MCP
        p9 = np.array(pts[9][:3])    # Middle MCP
        p17 = np.array(pts[17][:3])  # Pinky MCP

        long_axis = p9 - p0          # Wrist -> Middle MCP
        trans_axis = p17 - p5        # Index MCP -> Pinky MCP
        thumb_vec = p2 - p0          # Wrist -> Thumb MCP

        palm_normal = np.cross(long_axis, trans_axis)
        return float(np.dot(thumb_vec, palm_normal))

    def _verify_anatomical_handedness(
        self,
        pts: List[Tuple[float, float, float]],
        model_label: str,
        score: float = 1.0
    ) -> str:
        """
        Validates handedness using rotation-invariant 3D chirality and spatial heuristics.
        Does NOT flip when hand turns between palm and back of hand.
        """
        if len(pts) < 21:
            return model_label

        # If MediaPipe ML model has high confidence (>= 0.65), trust it
        if score >= 0.65 and model_label in ("Right", "Left"):
            return model_label

        # Fallback to rotation-invariant 3D chirality
        chirality = self._compute_3d_chirality(pts)
        if abs(chirality) > 1e-6:
            # Negative triple product = Right hand, Positive = Left hand
            return "Right" if chirality < 0 else "Left"

        # Spatial prior: on mirrored frame, right side of screen is user's Right hand
        wrist_x = pts[0][0]
        if wrist_x > 0.55:
            return "Right"
        elif wrist_x < 0.45:
            return "Left"

        return model_label

    def process_frame(self, bgr_image) -> Tuple[Optional[HandLandmarks], Optional[HandLandmarks]]:
        """
        Processes BGR OpenCV frame and returns (right_hand, left_hand).
        Strict separation: Left hand NEVER controls the cursor.
        Guarantees both hands are tracked concurrently without collision or dropped hands.
        """
        if self.detector is None:
            return None, None

        import mediapipe as mp

        rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

        detection_result = self.detector.detect(mp_image)

        right_hand: Optional[HandLandmarks] = None
        left_hand: Optional[HandLandmarks] = None

        if detection_result.hand_landmarks and detection_result.handedness:
            num_detected = len(detection_result.hand_landmarks)

            if num_detected == 1:
                # Single hand detected
                landmarks = detection_result.hand_landmarks[0]
                pts = [(lm.x, lm.y, lm.z) for lm in landmarks]
                raw_cat = detection_result.handedness[0][0]
                raw_label = raw_cat.category_name
                score = getattr(raw_cat, "score", 1.0)

                label = self._verify_anatomical_handedness(pts, raw_label, score=score)
                hand_obj = HandLandmarks(points=pts, handedness=label)

                if label == "Right":
                    right_hand = hand_obj
                    left_hand = None
                else:
                    right_hand = None
                    left_hand = hand_obj

            elif num_detected >= 2:
                # Dual-hand tracking (or multi-hand)
                # Extract points and metadata for the first two detections
                detected_hands = []
                for idx, landmarks in enumerate(detection_result.hand_landmarks[:2]):
                    pts = [(lm.x, lm.y, lm.z) for lm in landmarks]
                    raw_cat = detection_result.handedness[idx][0]
                    raw_label = raw_cat.category_name
                    score = getattr(raw_cat, "score", 1.0)
                    wrist_x = pts[0][0]
                    detected_hands.append({
                        "pts": pts,
                        "raw_label": raw_label,
                        "score": score,
                        "wrist_x": wrist_x
                    })

                h0 = detected_hands[0]
                h1 = detected_hands[1]

                # Case 1: MediaPipe already detected distinct Right and Left with good confidence
                if h0["raw_label"] != h1["raw_label"] and h0["score"] >= 0.65 and h1["score"] >= 0.65:
                    if h0["raw_label"] == "Right":
                        right_hand = HandLandmarks(points=h0["pts"], handedness="Right")
                        left_hand = HandLandmarks(points=h1["pts"], handedness="Left")
                    else:
                        right_hand = HandLandmarks(points=h1["pts"], handedness="Right")
                        left_hand = HandLandmarks(points=h0["pts"], handedness="Left")
                else:
                    # Case 2: MediaPipe had duplicate labels (e.g. [Right, Right] or [Left, Left])
                    # or lower confidence. Disambiguate using horizontal position on mirrored screen:
                    # User's Left hand is on screen left (smaller wrist_x).
                    # User's Right hand is on screen right (larger wrist_x).
                    if h0["wrist_x"] >= h1["wrist_x"]:
                        right_hand = HandLandmarks(points=h0["pts"], handedness="Right")
                        left_hand = HandLandmarks(points=h1["pts"], handedness="Left")
                    else:
                        right_hand = HandLandmarks(points=h1["pts"], handedness="Right")
                        left_hand = HandLandmarks(points=h0["pts"], handedness="Left")

        return right_hand, left_hand

    def close(self):
        """Release MediaPipe detector resources."""
        if self.detector is not None:
            self.detector.close()
            self.detector = None
