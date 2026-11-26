"""
AeroTouch Minecraft & First-Person Sandbox Game Profile
Spatial dual-hand controller for Minecraft, Roblox, and FPS sandbox games:
  - 🎯 Right Hand: Aim / Crosshair look (cursor mapping)
  - ⛏️ Right Index Pinch: Mine / Attack (Left Mouse Click / Hold)
  - 🧱 Right Middle Pinch: Place Block / Interact (Right Mouse Click)
  - 🕹️ Left Hand Position: WASD movement (Forward, Backward, Strafe Left/Right)
  - 🦘 Left Hand Fist: Jump (Spacebar)
  - 🤫 Left Hand Peace Sign: Sneak / Crouch (Shift)
  - 🎒 Left Pinky Pinch: Open Inventory (E)
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple
from src.gestures.engine import HandLandmarks, GestureMath
from src.os_bridge.win32_kernel import VirtualKey
from src.games.base_profile import BaseGameProfile


class MinecraftProfile(BaseGameProfile):
    """
    Minecraft and first-person voxel sandbox spatial controller.
    """

    def __init__(
        self,
        aim_smoothing: float = 0.40,
        move_deadband: float = 0.12,
        action_cooldown: float = 0.10,
    ):
        super().__init__(
            game_id="minecraft",
            game_name="Minecraft & FPS Sandbox",
            description="FPS Sandbox: Right Hand=Aim & Mine/Place, Left Hand=WASD walk, Fist=Jump, Peace=Sneak"
        )
        self.aim_smoothing = aim_smoothing
        self.move_deadband = move_deadband
        self.action_cooldown = action_cooldown

        # Cursor tracking
        self._filtered_cursor: Optional[Tuple[float, float]] = None
        self._is_left_down: bool = False
        self._is_right_down: bool = False

        # Timers
        self._last_move_time: float = 0.0
        self._last_jump_time: float = 0.0
        self._last_sneak_time: float = 0.0
        self._last_inv_time: float = 0.0
        self._last_mine_time: float = 0.0
        self._last_place_time: float = 0.0

        # State tracking
        self.current_movement: List[str] = []
        self.last_action: Optional[str] = None

    def on_enter(self, kernel) -> None:
        super().on_enter(kernel)
        self._filtered_cursor = None
        self._is_left_down = False
        self._is_right_down = False
        self.current_movement = []
        self.last_action = None

    def on_exit(self, kernel) -> None:
        super().on_exit(kernel)
        if kernel:
            if self._is_left_down:
                kernel.mouse_up(left=True)
                self._is_left_down = False
            if self._is_right_down:
                kernel.mouse_up(left=False)
                self._is_right_down = False
        self._filtered_cursor = None
        self.current_movement = []

    def process_frame(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        kernel,
        timestamp: float
    ) -> Dict[str, Any]:
        executed = []

        # 1. Right Hand: Aiming & Mining / Placing
        if right_hand is not None:
            # Tip of index finger (landmark 8) or palm center (landmark 9)
            norm_x = right_hand.points[8][0]
            norm_y = right_hand.points[8][1]

            if kernel:
                res_w, res_h = kernel.get_screen_resolution()
                target_x = norm_x * res_w
                target_y = norm_y * res_h

                if self._filtered_cursor is None:
                    self._filtered_cursor = (target_x, target_y)
                else:
                    fx, fy = self._filtered_cursor
                    smooth = self.aim_smoothing
                    target_x = fx * (1.0 - smooth) + target_x * smooth
                    target_y = fy * (1.0 - smooth) + target_y * smooth
                    self._filtered_cursor = (target_x, target_y)

                kernel.move_cursor(int(target_x), int(target_y))

            # Mine / Attack: Index pinch (thumb 4 to index 8)
            dist_index = math.dist(right_hand.points[4], right_hand.points[8])
            if dist_index < 0.055:
                if not self._is_left_down and kernel:
                    kernel.mouse_down(left=True)
                    self._is_left_down = True
                if (timestamp - self._last_mine_time) > self.action_cooldown:
                    executed.append("MINE/ATTACK (Left Click)")
                    self._last_mine_time = timestamp
            else:
                if self._is_left_down and kernel:
                    kernel.mouse_up(left=True)
                    self._is_left_down = False

            # Place Block / Interact: Middle pinch (thumb 4 to middle 12)
            dist_middle = math.dist(right_hand.points[4], right_hand.points[12])
            if dist_middle < 0.055:
                if (timestamp - self._last_place_time) > 0.18:
                    if kernel:
                        kernel.click(left=False)
                    executed.append("PLACE/USE (Right Click)")
                    self._last_place_time = timestamp
        else:
            if self._is_left_down and kernel:
                kernel.mouse_up(left=True)
                self._is_left_down = False

        # 2. Left Hand: WASD Movement & Jump / Sneak / Inventory
        self.current_movement = []
        if left_hand is not None:
            wrist = left_hand.points[0]
            palm_x, palm_y = left_hand.points[9][0], left_hand.points[9][1]

            # Neutral baseline for left hand is approx (x=0.5, y=0.5) in left ROI
            dx = palm_x - 0.5
            dy = palm_y - 0.5

            if (timestamp - self._last_move_time) > self.action_cooldown:
                # Forward (dy < -move_deadband)
                if dy < -self.move_deadband:
                    if kernel:
                        kernel.tap_key(ord('W'), hold_seconds=0.06)
                    self.current_movement.append("FORWARD (W)")
                # Backward (dy > move_deadband)
                elif dy > self.move_deadband:
                    if kernel:
                        kernel.tap_key(ord('S'), hold_seconds=0.06)
                    self.current_movement.append("BACKWARD (S)")

                # Strafe Left (dx < -move_deadband)
                if dx < -self.move_deadband:
                    if kernel:
                        kernel.tap_key(ord('A'), hold_seconds=0.06)
                    self.current_movement.append("STRAFE_LEFT (A)")
                # Strafe Right (dx > move_deadband)
                elif dx > self.move_deadband:
                    if kernel:
                        kernel.tap_key(ord('D'), hold_seconds=0.06)
                    self.current_movement.append("STRAFE_RIGHT (D)")

                if self.current_movement:
                    self._last_move_time = timestamp
                    executed.extend(self.current_movement)

            # Left Hand Fist: Jump (Space)
            if GestureMath.is_fist(left_hand):
                if (timestamp - self._last_jump_time) > 0.22:
                    if kernel:
                        kernel.tap_key(VirtualKey.VK_SPACE, hold_seconds=0.06)
                    executed.append("JUMP (Space)")
                    self._last_jump_time = timestamp

            # Left Hand Peace Sign: Sneak (Shift)
            elif GestureMath.is_peace(left_hand):
                if (timestamp - self._last_sneak_time) > 0.25:
                    if kernel:
                        kernel.tap_key(VirtualKey.VK_SHIFT, hold_seconds=0.10)
                    executed.append("SNEAK (Shift)")
                    self._last_sneak_time = timestamp

            # Left Hand Pinky Pinch (thumb 4 to pinky 20): Inventory (E)
            dist_pinky = math.dist(left_hand.points[4], left_hand.points[20])
            if dist_pinky < 0.055:
                if (timestamp - self._last_inv_time) > 0.40:
                    if kernel:
                        kernel.tap_key(ord('E'))
                    executed.append("INVENTORY (E)")
                    self._last_inv_time = timestamp

        if executed:
            self.last_action = executed[0]

        return {
            "game_id": self.game_id,
            "actions": executed,
            "movement": self.current_movement,
            "last_action": self.last_action or "IDLE",
            "is_gaming": True
        }
