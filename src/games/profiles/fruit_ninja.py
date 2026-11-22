"""
AeroTouch Fruit Ninja Game Profile
High-speed spatial blade slicing engine for Fruit Ninja and arcade slashers:
  - 🗡️ Katana Blade Slice: Move index finger / hand rapidly across screen
  - ⚡ Automatic Slice Drag: Left Mouse Down held during fast strokes (>0.30 velocity)
  - 🛑 Clean Cut Off: Left Mouse Up immediately released when stroke slows down
  - ⚔️ Dual Blade Whirlwind: Both hands slicing simultaneously for combo frenzy
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple
from src.gestures.engine import HandLandmarks
from src.games.base_profile import BaseGameProfile


class FruitNinjaProfile(BaseGameProfile):
    """
    Fruit Ninja blade slicing engine with sub-millisecond drag synthesis.
    """

    def __init__(
        self,
        slice_velocity_threshold: float = 0.25,
        min_slice_displacement: float = 0.015,
        cooldown: float = 0.04,
    ):
        super().__init__(
            game_id="fruit_ninja",
            game_name="Fruit Ninja",
            description="Katana Blade: Fast spatial hand motion slices fruit with automatic mouse drag"
        )
        self.slice_velocity_threshold = slice_velocity_threshold
        self.min_slice_displacement = min_slice_displacement
        self.cooldown = cooldown

        # State tracking
        self._last_pos: Optional[Tuple[float, float, float]] = None
        self._is_slicing: bool = False
        self._last_slice_time: float = 0.0
        self.last_action: Optional[str] = None
        self.slice_count: int = 0

    def on_enter(self, kernel) -> None:
        super().on_enter(kernel)
        self._last_pos = None
        self._is_slicing = False
        self.last_action = None
        self.slice_count = 0

    def on_exit(self, kernel) -> None:
        super().on_exit(kernel)
        if self._is_slicing and kernel:
            kernel.mouse_up(left=True)
            self._is_slicing = False
        self._last_pos = None

    def process_frame(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        kernel,
        timestamp: float
    ) -> Dict[str, Any]:
        executed = []

        # Primary slicing hand: prefer right hand, fallback to left hand
        primary_hand = right_hand if right_hand is not None else left_hand

        if primary_hand is not None:
            # Index fingertip (landmark 8) serves as katana blade tip
            cur_x = primary_hand.points[8][0]
            cur_y = primary_hand.points[8][1]

            # Screen resolution
            res_w, res_h = (1920, 1080)
            if kernel:
                res_w, res_h = kernel.get_screen_resolution()

            screen_x = int(cur_x * res_w)
            screen_y = int(cur_y * res_h)

            if self._last_pos is None:
                self._last_pos = (cur_x, cur_y, timestamp)
                if kernel:
                    kernel.move_cursor(screen_x, screen_y)
                return {
                    "game_id": self.game_id,
                    "actions": executed,
                    "is_slicing": False,
                    "slice_count": self.slice_count,
                    "last_action": "IDLE",
                    "is_gaming": True
                }

            prev_x, prev_y, prev_t = self._last_pos
            dt = timestamp - prev_t

            if dt > 0.001:
                vx = (cur_x - prev_x) / dt
                vy = (cur_y - prev_y) / dt
                speed = math.sqrt(vx * vx + vy * vy)
                disp = math.dist((cur_x, cur_y), (prev_x, prev_y))

                self._last_pos = (cur_x, cur_y, timestamp)

                # Move cursor to blade position
                if kernel:
                    kernel.move_cursor(screen_x, screen_y)

                # Check if movement exceeds blade velocity threshold
                if speed >= self.slice_velocity_threshold and disp >= self.min_slice_displacement:
                    if not self._is_slicing:
                        if kernel:
                            kernel.mouse_down(left=True)
                        self._is_slicing = True
                        self.slice_count += 1

                    executed.append(f"KATANA_SLICE (speed: {speed:.2f})")
                    self.last_action = "KATANA_SLICE"
                else:
                    # Slow movement: release blade
                    if self._is_slicing:
                        if kernel:
                            kernel.mouse_up(left=True)
                        self._is_slicing = False

        else:
            # No hand detected: ensure mouse button is released
            if self._is_slicing and kernel:
                kernel.mouse_up(left=True)
                self._is_slicing = False
            self._last_pos = None

        # Check secondary hand for dual-blade whirlwind combo
        if right_hand is not None and left_hand is not None and self._is_slicing:
            executed.append("DUAL_BLADE_COMBO")

        return {
            "game_id": self.game_id,
            "actions": executed,
            "is_slicing": self._is_slicing,
            "slice_count": self.slice_count,
            "last_action": self.last_action or ("SLICING" if self._is_slicing else "IDLE"),
            "is_gaming": True
        }
