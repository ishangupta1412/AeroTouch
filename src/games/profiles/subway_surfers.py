"""
AeroTouch Subway Surfers Game Profile
Isolated kinetic gesture controller for Subway Surfers:
  - ⬆️ Swipe Up       -> JUMP (Up Arrow / W)
  - ⬇️ Swipe Down     -> ROLL / SLIDE (Down Arrow / S)
  - ⬅️ Swipe Left     -> DODGE LEFT (Left Arrow / A)
  - ➡️ Swipe Right    -> DODGE RIGHT (Right Arrow / D)
  - 🛹 Double Pinch   -> HOVERBOARD (Spacebar)
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple
from src.gestures.engine import HandLandmarks, GestureMath
from src.os_bridge.win32_kernel import VirtualKey
from src.games.base_profile import BaseGameProfile


class SubwaySurfersProfile(BaseGameProfile):
    """
    Subway Surfers real-time spatial motion engine.
    Translates physical hand flicks into high-speed game inputs.
    """

    def __init__(
        self,
        velocity_threshold: float = 0.28,
        min_displacement: float = 0.025,
        swipe_cooldown: float = 0.14,
        hoverboard_cooldown: float = 0.80,
    ):
        super().__init__(
            game_id="subway_surfers",
            game_name="Subway Surfers",
            description="Kinetic swipe runner: Up=Jump, Down=Roll, Left/Right=Dodge, Pinch=Hoverboard"
        )
        self.velocity_threshold = velocity_threshold
        self.min_displacement = min_displacement
        self.swipe_cooldown = swipe_cooldown
        self.hoverboard_cooldown = hoverboard_cooldown

        # Tracking state
        self._last_pos: Optional[Tuple[float, float, float]] = None  # (x, y, timestamp)
        self._stroke_start: Optional[Tuple[float, float]] = None
        self._last_swipe_time: float = -999.0
        self._last_hoverboard_time: float = -999.0

        # Telemetry
        self.last_action: Optional[str] = None
        self.last_action_time: float = 0.0

    def on_enter(self, kernel) -> None:
        super().on_enter(kernel)
        self._last_pos = None
        self._stroke_start = None
        self.last_action = None

    def on_exit(self, kernel) -> None:
        super().on_exit(kernel)
        self._last_pos = None
        self._stroke_start = None

    def _extract_hand_position(self, hand: HandLandmarks) -> Tuple[float, float]:
        """Extracts stable tracking point (Index MCP landmark 5 or mid-palm landmark 9)."""
        pt = hand.points[9]  # Middle knuckle / palm center
        return pt[0], pt[1]

    def _detect_swipe(
        self,
        cur_x: float,
        cur_y: float,
        timestamp: float
    ) -> Optional[str]:
        """
        Calculates instantaneous velocity vector and displacement to detect swipe flick.
        """
        if self._last_pos is None:
            self._last_pos = (cur_x, cur_y, timestamp)
            self._stroke_start = (cur_x, cur_y)
            return None

        prev_x, prev_y, prev_t = self._last_pos
        dt = timestamp - prev_t

        if dt <= 0.001:
            return None

        # Check swipe cooldown
        if (timestamp - self._last_swipe_time) < self.swipe_cooldown:
            self._last_pos = (cur_x, cur_y, timestamp)
            self._stroke_start = (cur_x, cur_y)
            return None

        # Instantaneous velocity
        vx = (cur_x - prev_x) / dt
        vy = (cur_y - prev_y) / dt

        # Total displacement from stroke start
        if self._stroke_start is None:
            self._stroke_start = (prev_x, prev_y)
        dx = cur_x - self._stroke_start[0]
        dy = cur_y - self._stroke_start[1]

        self._last_pos = (cur_x, cur_y, timestamp)

        speed_sq = vx * vx + vy * vy
        if speed_sq < (self.velocity_threshold * self.velocity_threshold):
            # Hand is moving slowly or stopped; reset origin
            if abs(dx) > 0.08 or abs(dy) > 0.08:
                self._stroke_start = (cur_x, cur_y)
            return None

        # Classify dominant direction
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        abs_vx = abs(vx)
        abs_vy = abs(vy)

        detected_direction = None

        # Vertical dominance (Jump or Roll)
        if abs_vy > abs_vx * 1.15 and abs_dy >= self.min_displacement:
            if vy < 0 and dy < 0:
                detected_direction = "JUMP"
            elif vy > 0 and dy > 0:
                detected_direction = "ROLL"

        # Horizontal dominance (Left or Right Dodge)
        elif abs_vx > abs_vy * 1.15 and abs_dx >= self.min_displacement:
            if vx < 0 and dx < 0:
                detected_direction = "MOVE_LEFT"
            elif vx > 0 and dx > 0:
                detected_direction = "MOVE_RIGHT"

        if detected_direction:
            self._last_swipe_time = timestamp
            self._stroke_start = (cur_x, cur_y)
            return detected_direction

        return None

    def process_frame(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        kernel,
        timestamp: float
    ) -> Dict[str, Any]:
        """
        Processes spatial frame, detects swipes, and taps corresponding keys.
        """
        executed_actions = []

        # 1. Primary hand selection (prefer Right Hand, fallback to Left)
        active_hand = right_hand if right_hand is not None else left_hand

        if active_hand is not None:
            cur_x, cur_y = self._extract_hand_position(active_hand)
            swipe = self._detect_swipe(cur_x, cur_y, timestamp)

            if swipe:
                if swipe == "JUMP":
                    if kernel:
                        kernel.tap_key(VirtualKey.VK_UP)
                        kernel.tap_key(ord('W'))
                    executed_actions.append("JUMP (VK_UP / W)")
                elif swipe == "ROLL":
                    if kernel:
                        kernel.tap_key(VirtualKey.VK_DOWN)
                        kernel.tap_key(ord('S'))
                    executed_actions.append("ROLL (VK_DOWN / S)")
                elif swipe == "MOVE_LEFT":
                    if kernel:
                        kernel.tap_key(VirtualKey.VK_LEFT)
                        kernel.tap_key(ord('A'))
                    executed_actions.append("DODGE_LEFT (VK_LEFT / A)")
                elif swipe == "MOVE_RIGHT":
                    if kernel:
                        kernel.tap_key(VirtualKey.VK_RIGHT)
                        kernel.tap_key(ord('D'))
                    executed_actions.append("DODGE_RIGHT (VK_RIGHT / D)")

                self.last_action = swipe
                self.last_action_time = timestamp
        else:
            self._last_pos = None
            self._stroke_start = None

        # 2. Hoverboard Activation (Pinch or Open-Palm Deploy)
        # Check if either hand performs a deliberate thumb-index pinch
        hoverboard_triggered = False
        if (timestamp - self._last_hoverboard_time) >= self.hoverboard_cooldown:
            for hand in [right_hand, left_hand]:
                if hand is not None:
                    # Pinch detection between Thumb Tip (4) and Index Tip (8)
                    t_pt = hand.points[4]
                    i_pt = hand.points[8]
                    pinch_dist = math.dist(t_pt, i_pt)
                    if pinch_dist < 0.07:  # Close pinch
                        hoverboard_triggered = True
                        break

            if hoverboard_triggered:
                self._last_hoverboard_time = timestamp
                if kernel:
                    kernel.tap_key(VirtualKey.VK_SPACE)
                executed_actions.append("HOVERBOARD (VK_SPACE)")
                self.last_action = "HOVERBOARD"
                self.last_action_time = timestamp

        return {
            "game_id": self.game_id,
            "actions": executed_actions,
            "last_action": self.last_action,
            "is_gaming": True
        }
