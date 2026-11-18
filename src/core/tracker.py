"""
AeroTouch MediaPipe 3D Dual-Hand Tracking Adapter
Extracts 21 3D coordinates per hand at native webcam frame rate with fallback resiliency.
"""

from typing import List, Optional, Tuple
from src.gestures.engine import HandLandmarks


class DualHandTracker:
    """
    Encapsulates MediaPipe Hands solution with dual-hand (num_hands=2) detection.
    """

    def __init__(
        self,
        static_image_mode: bool = False,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5
    ):
        self.max_num_hands = max_num_hands
        self.mp_hands = None
        self.hands_detector = None

        try:
            import mediapipe as mp
            self.mp_hands = mp.solutions.hands
            self.hands_detector = self.mp_hands.Hands(
                static_image_mode=static_image_mode,
                max_num_hands=max_num_hands,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence
            )
            print("[AeroTouch Vision]: MediaPipe Native 3D Hands Engine Initialized.")
        except ImportError:
            print("[AeroTouch Vision]: Running in Headless/Synthetic Simulation Mode.")

    def process_frame(self, bgr_image) -> Tuple[Optional[HandLandmarks], Optional[HandLandmarks]]:
        """
        Processes BGR image and returns (right_hand, left_hand).
        """
        if self.hands_detector is None:
            return None, None

        import cv2

        rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        rgb_image.flags.writeable = False
        results = self.hands_detector.process(rgb_image)

        right_hand: Optional[HandLandmarks] = None
        left_hand: Optional[HandLandmarks] = None

        if results.multi_hand_landmarks and results.multi_handedness:
            for idx, handedness_info in enumerate(results.multi_handedness):
                label = handedness_info.classification[0].label  # 'Left' or 'Right'
                landmarks = results.multi_hand_landmarks[idx]

                pts = [(lm.x, lm.y, lm.z) for lm in landmarks.landmark]
                hand_obj = HandLandmarks(points=pts, handedness=label)

                # Camera mirror logic: MediaPipe 'Right' is user's physical right hand in selfie mode
                if label == "Right":
                    right_hand = hand_obj
                else:
                    left_hand = hand_obj

        return right_hand, left_hand

    def close(self):
        if self.hands_detector:
            self.hands_detector.close()
