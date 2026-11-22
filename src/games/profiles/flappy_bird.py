"""
AeroTouch Flappy Bird & Rhythm Jumper Game Profile
Ultra-low latency pulse jumper controller for Flappy Bird, Geometry Dash, and tap games:
  - 🪽 Wing Flap: Fast upward/downward pulse flick OR index pinch OR fist tap
  - 🕹️ Tri-Input Synthesis: Simultaneously dispatches Spacebar, Up Arrow, and Left Click
  - ⚡ Sub-millisecond Response: 0.11s refractory period for rapid rhythmic flapping
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple
from src.gestures.engine import HandLandmarks, GestureMath
from src.os_bridge.win32_kernel import VirtualKey
from src.games.base_profile import BaseGameProfile


class FlappyBirdProfile(BaseGameProfile):
    """
    Rhythmic flap and jump controller for Flappy Bird and arcade runners.
    """

    def __init__(
        self,
        flap_cooldown: float = 0.11,
        pulse_velocity_threshold: float = 0.22,
    ):
        super().__init__(
            game_id="flappy_bird",
            game_name="Flappy Bird & Rhythm Jumpers",
            description="Pulse Flap: Flap hand, pinch, or make fist to jump through pipes (Space / Up / Click)"
        )
        self.flap_cooldown = flap_cooldown
        self.pulse_velocity_threshold = pulse_velocity_threshold

        # Tracking state
        self._last_y: Optional[Tuple[float, float]] = None  # (y, timestamp)
        self._last_flap_time: float = -999.0
        self.flap_count: int = 0
        self.last_action: Optional[str] = None

    def on_enter(self, kernel) -> None:
        super().on_enter(kernel)
        self._last_y = None
        self._last_flap_time = -999.0
        self.flap_count = 0
        self.last_action = None

    def on_exit(self, kernel) -> None:
        super().on_exit(kernel)
        self._last_y = None

    def _trigger_flap(self, kernel, timestamp: float, source: str) -> str:
        """Dispatches multi-channel jump trigger for maximum game compatibility."""
        if kernel:
            kernel.tap_key(VirtualKey.VK_SPACE, hold_seconds=0.03)
            kernel.tap_key(VirtualKey.VK_UP, hold_seconds=0.03)
            kernel.click(left=True)

        self._last_flap_time = timestamp
        self.flap_count += 1
        action_desc = f"FLAP #{self.flap_count} via {source}"
        self.last_action = action_desc
        return action_desc

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
            # 1. Pinch trigger (thumb tip 4 to index tip 8)
            dist_pinch = math.dist(active_hand.points[4], active_hand.points[8])
            is_pinch = dist_pinch < 0.055

            # 2. Fist trigger
            is_fist = GestureMath.is_fist(active_hand)

            # 3. Kinetic vertical pulse flick (wrist landmark 0 or palm landmark 9)
            cur_y = active_hand.points[9][1]
            is_pulse = False

            if self._last_y is not None:
                prev_y, prev_t = self._last_y
                dt = timestamp - prev_t
                if dt > 0.001:
                    vy = (cur_y - prev_y) / dt
                    # Upward or downward sharp flick
                    if abs(vy) > self.pulse_velocity_threshold:
                        is_pulse = True

            self._last_y = (cur_y, timestamp)

            # Check if cooldown has elapsed
            can_flap = (timestamp - self._last_flap_time) >= self.flap_cooldown

            if can_flap:
                if is_pinch:
                    action = self._trigger_flap(kernel, timestamp, "PINCH")
                    executed.append(action)
                elif is_fist:
                    action = self._trigger_flap(kernel, timestamp, "FIST")
                    executed.append(action)
                elif is_pulse:
                    action = self._trigger_flap(kernel, timestamp, "PULSE_FLICK")
                    executed.append(action)

        else:
            self._last_y = None

        return {
            "game_id": self.game_id,
            "actions": executed,
            "flap_count": self.flap_count,
            "last_action": self.last_action or "IDLE",
            "is_gaming": True
        }
