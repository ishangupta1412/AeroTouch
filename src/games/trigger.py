"""
AeroTouch Fist Bump (🤜🤛) Game Mode Trigger
Detects dual-hand knuckle collision dwell to toggle Game Mode on/off.
Features:
- Dwell confirmation (default 0.35s) prevents momentary false triggers
- Cooldown refractory period (default 1.5s) avoids bounce re-toggles
- Exposes dwell progress (0.0 - 1.0) for live UI dynamic island feedback
"""

import math
import time
from typing import Optional, Tuple
from src.gestures.engine import GestureMath, HandLandmarks


class FistBumpTrigger:
    """
    Precision dual-hand fist bump detector.
    Fires when both hands form fists and bring their knuckles close together.
    """

    def __init__(
        self,
        bump_distance_threshold: float = 0.16,
        dwell_duration: float = 0.35,
        cooldown: float = 1.5,
    ):
        self.bump_distance_threshold = bump_distance_threshold
        self.dwell_duration = dwell_duration
        self.cooldown = cooldown

        self._bump_start_time: Optional[float] = None
        self._last_trigger_time: float = -999.0
        self.progress: float = 0.0

    def update(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        timestamp: Optional[float] = None,
    ) -> Tuple[bool, float]:
        """
        Evaluates a frame for a dual-hand fist bump.
        Returns:
            (triggered: bool, progress: float)
        """
        now = timestamp if timestamp is not None else time.perf_counter()

        # Cooldown guard: if recently triggered, prevent re-evaluating
        if (now - self._last_trigger_time) < self.cooldown:
            self._bump_start_time = None
            self.progress = 0.0
            return False, 0.0

        # Both hands must be tracked
        if right_hand is None or left_hand is None:
            self._bump_start_time = None
            self.progress = 0.0
            return False, 0.0

        # Both hands must be closed fists
        right_fist = GestureMath.is_fist(right_hand)
        left_fist = GestureMath.is_fist(left_hand)

        if not (right_fist and left_fist):
            self._bump_start_time = None
            self.progress = 0.0
            return False, 0.0

        # Calculate knuckle Euclidean distance (MCP 5 index knuckle & MCP 9 middle knuckle)
        r_knuckle = right_hand.points[5]
        l_knuckle = left_hand.points[5]

        dx = r_knuckle[0] - l_knuckle[0]
        dy = r_knuckle[1] - l_knuckle[1]
        dz = r_knuckle[2] - l_knuckle[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        # Check proximity
        if dist <= self.bump_distance_threshold:
            if self._bump_start_time is None:
                self._bump_start_time = now

            elapsed = now - self._bump_start_time
            self.progress = min(1.0, elapsed / max(self.dwell_duration, 0.001))

            if self.progress >= 1.0:
                self._last_trigger_time = now
                self._bump_start_time = None
                self.progress = 0.0
                return True, 1.0
            return False, self.progress

        # Fists separated
        self._bump_start_time = None
        self.progress = 0.0
        return False, 0.0

    def reset(self) -> None:
        """Resets active dwell state."""
        self._bump_start_time = None
        self.progress = 0.0
