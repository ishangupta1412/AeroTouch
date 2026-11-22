"""
AeroTouch Temple Run Game Profile
Kinetic swipe & tilt runner controller for Temple Run & Tomb Runner:
  - ⬆️ Swipe Up: Jump (Up Arrow / W)
  - ⬇️ Swipe Down: Slide (Down Arrow / S)
  - ⬅️ Swipe Left: 90-degree Turn Left (Left Arrow / A)
  - ➡️ Swipe Right: 90-degree Turn Right (Right Arrow / D)
  - 🛹 Double Pinch / Palm Push: Stumble Recovery / Powerup (Space)
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple
from src.gestures.engine import HandLandmarks, GestureMath
from src.os_bridge.win32_kernel import VirtualKey
from src.games.base_profile import BaseGameProfile


class TempleRunProfile(BaseGameProfile):
    """
    Temple Run kinetic motion engine with rapid turning and slide detection.
    """

    def __init__(
        self,
        velocity_threshold: float = 0.28,
        min_displacement: float = 0.025,
        swipe_cooldown: float = 0.14,
    ):
        super().__init__(
            game_id="temple_run",
            game_name="Temple Run",
            description="Endless 3D Runner: Up=Jump, Down=Slide, Left/Right=Turn Corner, Pinch=Powerup"
        )
        self.velocity_threshold = velocity_threshold
        self.min_displacement = min_displacement
        self.swipe_cooldown = swipe_cooldown

        self._last_pos: Optional[Tuple[float, float, float]] = None
        self._stroke_start: Optional[Tuple[float, float]] = None
        self._last_swipe_time: float = -999.0
        self._last_powerup_time: float = -999.0
        self.last_action: Optional[str] = None

    def on_enter(self, kernel) -> None:
        super().on_enter(kernel)
        self._last_pos = None
        self._stroke_start = None
        self.last_action = None

    def on_exit(self, kernel) -> None:
        super().on_exit(kernel)
        self._last_pos = None
        self._stroke_start = None

    def _detect_swipe(self, cur_x: float, cur_y: float, timestamp: float) -> Optional[str]:
        if self._last_pos is None:
            self._last_pos = (cur_x, cur_y, timestamp)
            self._stroke_start = (cur_x, cur_y)
            return None

        prev_x, prev_y, prev_t = self._last_pos
        dt = timestamp - prev_t
        if dt <= 0.001:
            return None

        if (timestamp - self._last_swipe_time) < self.swipe_cooldown:
            self._last_pos = (cur_x, cur_y, timestamp)
            self._stroke_start = (cur_x, cur_y)
            return None

        vx = (cur_x - prev_x) / dt
        vy = (cur_y - prev_y) / dt

        if self._stroke_start is None:
            self._stroke_start = (prev_x, prev_y)
        dx = cur_x - self._stroke_start[0]
        dy = cur_y - self._stroke_start[1]

        self._last_pos = (cur_x, cur_y, timestamp)

        speed_sq = vx * vx + vy * vy
        if speed_sq < (self.velocity_threshold * self.velocity_threshold):
            if abs(dx) > 0.08 or abs(dy) > 0.08:
                self._stroke_start = (cur_x, cur_y)
            return None

        abs_dx = abs(dx)
        abs_dy = abs(dy)
        abs_vx = abs(vx)
        abs_vy = abs(vy)

        detected = None
        if abs_vy > abs_vx * 1.15 and abs_dy >= self.min_displacement:
            if vy < 0 and dy < 0:
                detected = "JUMP"
            elif vy > 0 and dy > 0:
                detected = "SLIDE"
        elif abs_vx > abs_vy * 1.15 and abs_dx >= self.min_displacement:
            if vx < 0 and dx < 0:
                detected = "TURN_LEFT"
            elif vx > 0 and dx > 0:
                detected = "TURN_RIGHT"

        if detected:
            self._last_swipe_time = timestamp
            self._stroke_start = (cur_x, cur_y)
            return detected

        return None

    def process_frame(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        kernel,
        timestamp: float
    ) -> Dict[str, Any]:
        executed = []
        active_hand = right_hand if right_hand is not None else left_hand

        if active_hand is not None:
            cur_x = active_hand.points[9][0]
            cur_y = active_hand.points[9][1]
            swipe = self._detect_swipe(cur_x, cur_y, timestamp)

            if swipe:
                if swipe == "JUMP":
                    if kernel:
                        kernel.tap_key(VirtualKey.VK_UP)
                        kernel.tap_key(ord('W'))
                    executed.append("JUMP (Up / W)")
                elif swipe == "SLIDE":
                    if kernel:
                        kernel.tap_key(VirtualKey.VK_DOWN)
                        kernel.tap_key(ord('S'))
                    executed.append("SLIDE (Down / S)")
                elif swipe == "TURN_LEFT":
                    if kernel:
                        kernel.tap_key(VirtualKey.VK_LEFT)
                        kernel.tap_key(ord('A'))
                    executed.append("TURN_LEFT (Left / A)")
                elif swipe == "TURN_RIGHT":
                    if kernel:
                        kernel.tap_key(VirtualKey.VK_RIGHT)
                        kernel.tap_key(ord('D'))
                    executed.append("TURN_RIGHT (Right / D)")

                self.last_action = swipe

        # Powerup (Pinch)
        if (timestamp - self._last_powerup_time) > 0.8:
            for hand in (right_hand, left_hand):
                if hand is not None:
                    p_dist = math.dist(hand.points[4], hand.points[8])
                    if p_dist < 0.07:
                        self._last_powerup_time = timestamp
                        if kernel:
                            kernel.tap_key(VirtualKey.VK_SPACE)
                        executed.append("POWERUP (Space)")
                        self.last_action = "POWERUP"
                        break

        return {
            "game_id": self.game_id,
            "actions": executed,
            "last_action": self.last_action,
            "is_gaming": True
        }
