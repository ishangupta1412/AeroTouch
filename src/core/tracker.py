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
    """

    def __init__(
        self,
        num_hands: int = 2,
        min_hand_detection_confidence: float = 0.6,
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

    def process_frame(self, bgr_image) -> Tuple[Optional[HandLandmarks], Optional[HandLandmarks]]:
        """
        Processes BGR OpenCV frame and returns (right_hand, left_hand).
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
            # If only one hand is visible, designate it as the primary pointer hand
            if len(detection_result.hand_landmarks) == 1:
                landmarks = detection_result.hand_landmarks[0]
                pts = [(lm.x, lm.y, lm.z) for lm in landmarks]
                right_hand = HandLandmarks(points=pts, handedness="Right")
            else:
                # Two hands in view: split by MediaPipe handedness
                for idx, handedness_cat in enumerate(detection_result.handedness):
                    label = handedness_cat[0].category_name
                    landmarks = detection_result.hand_landmarks[idx]
                    pts = [(lm.x, lm.y, lm.z) for lm in landmarks]
                    hand_obj = HandLandmarks(points=pts, handedness=label)

                    if label == "Right":
                        right_hand = hand_obj
                    else:
                        left_hand = hand_obj

        return right_hand, left_hand

    def close(self):
        if self.detector:
            self.detector.close()
