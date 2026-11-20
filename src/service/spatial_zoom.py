"""
AeroTouch Bimanual Spatial Zoom Controller
Enables two-hand pinch-to-zoom and canvas expansion in CAD, Figma, Maps, and Browser.
When both hands are engaged in pinch mode:
  - Moving hands apart (expanding distance) -> Zoom In (Ctrl + Wheel Up)
  - Moving hands closer (contracting distance) -> Zoom Out (Ctrl + Wheel Down)
"""

import math
import time
from typing import Optional, Tuple

from src.gestures.engine import HandLandmarks, GestureMath


class BimanualZoomController:
    """
    Translates inter-hand spatial distance changes into smooth kinetic Ctrl+Wheel zoom steps.
    """

    def __init__(
        self,
        step_threshold: float = 0.022,   # Normalized distance change needed per zoom step
        debounce_seconds: float = 0.08   # Throttling rate between zoom increments
    ):
        self.step_threshold = step_threshold
        self.debounce_seconds = debounce_seconds

        self.is_active: bool = False
        self.last_distance: Optional[float] = None
        self.last_step_time: float = 0.0

    @staticmethod
    def _is_zoom_pose(hand: HandLandmarks) -> bool:
        """
        True when hand is either pinching (Thumb + Index close)
        or index pointing forward with other fingers curled.
        """
        norm_pinch = GestureMath.normalized_pinch_distance(hand, finger_idx=8)
        if norm_pinch < 0.38:
            return True
        # Index extended, other fingers curled
        index_ext = GestureMath.is_finger_extended(hand, 8, 6)
        middle_ext = GestureMath.is_finger_extended(hand, 12, 10)
        ring_ext = GestureMath.is_finger_extended(hand, 16, 14)
        pinky_ext = GestureMath.is_finger_extended(hand, 20, 18)
        return index_ext and not middle_ext and not ring_ext and not pinky_ext

    def update(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        timestamp: Optional[float] = None
    ) -> int:
        """
        Updates two-hand distance and returns zoom steps:
        > 0 : Zoom In (Ctrl + Scroll Up)
        < 0 : Zoom Out (Ctrl + Scroll Down)
        0   : No zoom step this frame
        """
        if timestamp is None:
            timestamp = time.perf_counter()

        # Both hands must be present and in valid zoom pose
        if right_hand is None or left_hand is None:
            self.reset()
            return 0

        if not self._is_zoom_pose(right_hand) or not self._is_zoom_pose(left_hand):
            self.reset()
            return 0

        # Compute Euclidean distance between index fingertips (3D)
        p_r = right_hand.index_tip
        p_l = left_hand.index_tip
        current_dist = math.sqrt(
            (p_r[0] - p_l[0]) ** 2 +
            (p_r[1] - p_l[1]) ** 2 +
            (p_r[2] - p_l[2]) ** 2
        )

        if not self.is_active or self.last_distance is None:
            self.is_active = True
            self.last_distance = current_dist
            self.last_step_time = timestamp
            return 0

        delta_d = current_dist - self.last_distance

        if abs(delta_d) >= self.step_threshold:
            if (timestamp - self.last_step_time) >= self.debounce_seconds:
                # Determine step count proportional to delta
                steps = int(delta_d / self.step_threshold)
                if steps == 0:
                    steps = 1 if delta_d > 0 else -1

                # Advance anchor
                self.last_distance += steps * self.step_threshold
                self.last_step_time = timestamp
                return steps

        return 0

    def reset(self):
        """Resets bimanual zoom tracking state."""
        self.is_active = False
        self.last_distance = None
