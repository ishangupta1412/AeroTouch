"""
AeroTouch Gaze + Hand Hybrid Targeting ("Look + Pinch" Paradigm)
Uses MediaPipe FaceLandmarker iris landmarks (when model asset is present) to estimate
coarse eye gaze direction on screen, accelerating large cross-screen jumps while leaving
sub-pixel precision to the hand pointer. Gracefully stays inactive if no face model is cached.
"""

import os
import time
from typing import Optional, Tuple

import cv2


MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_landmarker.task")


class GazeHybridTracker:
    """
    Lightweight optional Iris Gaze estimator for Look+Pinch coarse cursor warping.
    Only activates if `face_landmarker.task` is present locally (never stalls startup).
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.detector = None
        self._last_ts_ms: int = 0
        self.last_gaze_norm: Optional[Tuple[float, float]] = None
        self._prev_gaze: Optional[Tuple[float, float]] = None

        if enabled and os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 1000:
            try:
                from mediapipe.tasks import python as mp_python
                from mediapipe.tasks.python import vision

                base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.VIDEO,
                    num_faces=1,
                )
                self.detector = vision.FaceLandmarker.create_from_options(options)
            except Exception:
                self.detector = None

    @property
    def available(self) -> bool:
        return self.detector is not None

    def process_frame(self, bgr_image) -> Optional[Tuple[float, float]]:
        """Extracts smoothed normalized iris gaze (gx, gy) in [0.0, 1.0]."""
        if self.detector is None:
            return None
        try:
            import mediapipe as mp
            rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms = int(time.perf_counter() * 1000)
            if ts_ms <= self._last_ts_ms:
                ts_ms = self._last_ts_ms + 1
            self._last_ts_ms = ts_ms
            res = self.detector.detect_for_video(mp_image, ts_ms)
            if res.face_landmarks:
                lms = res.face_landmarks[0]
                if len(lms) > 473:
                    # Average left (468) and right (473) iris centers
                    gx = (lms[468].x + lms[473].x) * 0.5
                    gy = (lms[468].y + lms[473].y) * 0.5
                    # Amplify subtle iris travel around center [0.5, 0.5]
                    gx = max(0.0, min(1.0, 0.5 + (gx - 0.5) * 3.2))
                    gy = max(0.0, min(1.0, 0.5 + (gy - 0.5) * 3.2))
                    self._prev_gaze = self.last_gaze_norm
                    self.last_gaze_norm = (gx, gy)
                    return self.last_gaze_norm
        except Exception:
            pass
        return None

    def blend_with_hand(
        self,
        hand_x: float,
        hand_y: float,
        gaze_weight: float = 0.25,
        jump_threshold: float = 0.30,
    ) -> Tuple[float, float]:
        """
        Coarse gaze bias: only assists when gaze & hand are far apart (> jump_threshold),
        keeping fine sub-pixel hand control completely dominant near targets.
        """
        if self.last_gaze_norm is None:
            return hand_x, hand_y
        gx, gy = self.last_gaze_norm
        dist = ((gx - hand_x) ** 2 + (gy - hand_y) ** 2) ** 0.5
        if dist < jump_threshold:
            return hand_x, hand_y
        bx = hand_x + (gx - hand_x) * gaze_weight
        by = hand_y + (gy - hand_y) * gaze_weight
        return max(0.0, min(1.0, bx)), max(0.0, min(1.0, by))

    def close(self) -> None:
        if self.detector is not None:
            try:
                self.detector.close()
            except Exception:
                pass
            self.detector = None
