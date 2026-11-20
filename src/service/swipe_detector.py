"""
AeroTouch Fluid 3-Finger Desktop & Mission Control Swipe Engine
Tracks 3-finger pose dynamics (Index + Middle + Ring extended, Pinky curled)
and detects directional velocity vectors to trigger Windows OS gestures:
  - Swipe UP:    Task View (Win + Tab)
  - Swipe DOWN:  Show / Peek Desktop (Win + D)
  - Swipe LEFT:  Previous Virtual Desktop (Win + Ctrl + Left)
  - Swipe RIGHT: Next Virtual Desktop (Win + Ctrl + Right)
"""

import collections
import math
import time
from typing import Deque, Optional, Tuple

from src.gestures.engine import HandLandmarks, GestureMath


class FluidSwipeDetector:
    """
    Directional kinematic swipe recognizer with momentum filtering and debounce.
    """

    def __init__(
        self,
        velocity_threshold: float = 0.55,    # Normalized units per second
        min_displacement: float = 0.06,      # Minimum travel distance
        max_duration: float = 0.35,          # Maximum swipe gesture duration in seconds
        cooldown: float = 0.65               # Cooldown between consecutive swipes
    ):
        self.velocity_threshold = velocity_threshold
        self.min_displacement = min_displacement
        self.max_duration = max_duration
        self.cooldown = cooldown

        self.last_swipe_time: float = 0.0
        # History queue stores (x, y, timestamp)
        self._history: Deque[Tuple[float, float, float]] = collections.deque(maxlen=16)

    @classmethod
    def is_three_finger_pose(cls, hand: HandLandmarks) -> bool:
        """
        True when Index (8), Middle (12), and Ring (16) are extended,
        and Pinky (20) is curled into palm.
        """
        # Index, Middle, Ring MUST be extended
        if not GestureMath.is_finger_extended(hand, tip_idx=8, pip_idx=6):
            return False
        if not GestureMath.is_finger_extended(hand, tip_idx=12, pip_idx=10):
            return False
        if not GestureMath.is_finger_extended(hand, tip_idx=16, pip_idx=14):
            return False

        # Pinky MUST be curled
        if GestureMath.is_finger_extended(hand, tip_idx=20, pip_idx=18):
            return False

        return True

    def update(self, hand: Optional[HandLandmarks], timestamp: Optional[float] = None) -> Optional[str]:
        """
        Updates kinematic history and returns swipe action string if detected:
        'SWIPE_UP', 'SWIPE_DOWN', 'SWIPE_LEFT', 'SWIPE_RIGHT', or None.
        """
        if timestamp is None:
            timestamp = time.perf_counter()

        if hand is None or not self.is_three_finger_pose(hand):
            self._history.clear()
            return None

        # Cooldown guard
        if (timestamp - self.last_swipe_time) < self.cooldown:
            return None

        # Compute centroid of Index, Middle, and Ring fingertips
        p8 = hand.points[8]
        p12 = hand.points[12]
        p16 = hand.points[16]
        cx = (p8[0] + p12[0] + p16[0]) / 3.0
        cy = (p8[1] + p12[1] + p16[1]) / 3.0

        self._history.append((cx, cy, timestamp))

        if len(self._history) < 4:
            return None

        # Window analysis
        start_x, start_y, start_t = self._history[0]
        dt = timestamp - start_t

        if dt > self.max_duration:
            # Prune old samples
            while len(self._history) > 1 and (timestamp - self._history[0][2]) > self.max_duration:
                self._history.popleft()
            if len(self._history) < 4:
                return None
            start_x, start_y, start_t = self._history[0]
            dt = timestamp - start_t

        if dt <= 0.02:
            return None

        dx = cx - start_x
        dy = cy - start_y  # In camera coords: cy increases downward, decreases upward
        dist = math.hypot(dx, dy)
        vel = dist / dt

        if dist >= self.min_displacement and vel >= self.velocity_threshold:
            # Check axis dominance
            abs_x = abs(dx)
            abs_y = abs(dy)

            detected_swipe = None
            if abs_y > abs_x * 1.25:
                # Vertical swipe dominant
                detected_swipe = "SWIPE_UP" if dy < 0 else "SWIPE_DOWN"
            elif abs_x > abs_y * 1.25:
                # Horizontal swipe dominant
                detected_swipe = "SWIPE_LEFT" if dx < 0 else "SWIPE_RIGHT"

            if detected_swipe:
                self.last_swipe_time = timestamp
                self._history.clear()
                return detected_swipe

        return None

    def reset(self):
        """Clears tracking history."""
        self._history.clear()
