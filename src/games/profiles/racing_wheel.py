"""
AeroTouch Racing & Hill Climb Game Profile
Dual-hand virtual steering wheel and kinetic pedals for racing games,
including Hill Climb Racing, Asphalt, TrackMania, and browser arcade racers:
  - 🔄 Dual-Hand Steering Wheel Tilt: Left/Right turning (A/D or Arrow Keys)
  - 🟢 Right Hand Fist/Pinch: Gas / Accelerate (W or Up Arrow)
  - 🔴 Left Hand Fist/Pinch: Brake / Reverse (S or Down Arrow)
  - 🚀 Space / Nitro: Double hand pinch or quick high-five
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple
from src.gestures.engine import HandLandmarks, GestureMath
from src.os_bridge.win32_kernel import VirtualKey
from src.games.base_profile import BaseGameProfile


class RacingWheelProfile(BaseGameProfile):
    """
    Virtual steering wheel and gas/brake pedal controller.
    """

    def __init__(
        self,
        steer_deadband: float = 0.06,
        steer_cooldown: float = 0.08,
    ):
        super().__init__(
            game_id="racing",
            game_name="Racing & Hill Climb",
            description="Virtual Steering Wheel: Tilt hands to steer, Right hand=Gas, Left hand=Brake, Pinch=Nitro"
        )
        self.steer_deadband = steer_deadband
        self.steer_cooldown = steer_cooldown

        self._last_steer_time: float = 0.0
        self._last_gas_time: float = 0.0
        self._last_brake_time: float = 0.0
        self._last_nitro_time: float = 0.0
        self.current_steer: str = "CENTER"

    def on_enter(self, kernel) -> None:
        super().on_enter(kernel)
        self.current_steer = "CENTER"

    def on_exit(self, kernel) -> None:
        super().on_exit(kernel)
        self.current_steer = "CENTER"

    def process_frame(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        kernel,
        timestamp: float
    ) -> Dict[str, Any]:
        executed = []

        # 1. Dual-Hand Virtual Steering Wheel Tilt
        if right_hand is not None and left_hand is not None:
            # Normalized Y of wrists (landmark 0) or mid-palm (landmark 9)
            r_y = right_hand.points[9][1]
            l_y = left_hand.points[9][1]

            # In mirrored view: if Right hand is lower (larger y) and Left is higher -> steer Right
            # If Right hand is higher (smaller y) and Left is lower -> steer Left
            tilt = r_y - l_y

            if tilt > self.steer_deadband:
                # Steer Right
                self.current_steer = "RIGHT"
                if kernel and (timestamp - self._last_steer_time) > self.steer_cooldown:
                    kernel.tap_key(VirtualKey.VK_RIGHT)
                    kernel.tap_key(ord('D'))
                    self._last_steer_time = timestamp
                executed.append("STEER_RIGHT")
            elif tilt < -self.steer_deadband:
                # Steer Left
                self.current_steer = "LEFT"
                if kernel and (timestamp - self._last_steer_time) > self.steer_cooldown:
                    kernel.tap_key(VirtualKey.VK_LEFT)
                    kernel.tap_key(ord('A'))
                    self._last_steer_time = timestamp
                executed.append("STEER_LEFT")
            else:
                self.current_steer = "CENTER"

        # 2. Right Hand: Gas / Accelerate (Fist or Pinch)
        if right_hand is not None:
            is_r_fist = GestureMath.is_fist(right_hand)
            r_pinch = math.dist(right_hand.points[4], right_hand.points[8]) < 0.06
            if is_r_fist or r_pinch:
                if kernel and (timestamp - self._last_gas_time) > 0.08:
                    kernel.tap_key(VirtualKey.VK_UP)
                    kernel.tap_key(ord('W'))
                    self._last_gas_time = timestamp
                executed.append("GAS (W / Up)")

        # 3. Left Hand: Brake / Reverse (Fist or Pinch)
        if left_hand is not None:
            is_l_fist = GestureMath.is_fist(left_hand)
            l_pinch = math.dist(left_hand.points[4], left_hand.points[8]) < 0.06
            if is_l_fist or l_pinch:
                if kernel and (timestamp - self._last_brake_time) > 0.08:
                    kernel.tap_key(VirtualKey.VK_DOWN)
                    kernel.tap_key(ord('S'))
                    self._last_brake_time = timestamp
                executed.append("BRAKE (S / Down)")

        # 4. Nitro / Boost: Dual hand pinch or space
        if right_hand is not None and left_hand is not None:
            r_pinch = math.dist(right_hand.points[4], right_hand.points[8]) < 0.06
            l_pinch = math.dist(left_hand.points[4], left_hand.points[8]) < 0.06
            if r_pinch and l_pinch:
                if kernel and (timestamp - self._last_nitro_time) > 0.5:
                    kernel.tap_key(VirtualKey.VK_SPACE)
                    self._last_nitro_time = timestamp
                executed.append("NITRO (Space)")

        return {
            "game_id": self.game_id,
            "actions": executed,
            "steer": self.current_steer,
            "last_action": executed[0] if executed else self.current_steer,
            "is_gaming": True
        }
