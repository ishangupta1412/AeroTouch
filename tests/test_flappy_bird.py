"""
Unit tests for AeroTouch Flappy Bird Profile.
Tests pulse flick flapping, pinch/fist triggers, multi-input key/click dispatch, and refractory cooldown.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gestures.engine import HandLandmarks
from src.games.profiles.flappy_bird import FlappyBirdProfile
from src.os_bridge.win32_kernel import VirtualKey


def make_flappy_hand(
    y: float = 0.5,
    is_pinch: bool = False,
    is_fist: bool = False
) -> HandLandmarks:
    # Wrist at y = 0.85
    points = [(0.5, y, 0.0)] * 21
    points[0] = (0.5, 0.85, 0.0)
    points[9] = (0.5, y, 0.0)

    if is_pinch:
        for tip, pip in [(12, 10), (16, 14), (20, 18)]:
            points[pip] = (0.5, 0.4, 0.0)
            points[tip] = (0.5, 0.2, 0.0)
        points[4] = (0.5, y, 0.0)
        points[8] = (0.5, y + 0.02, 0.0)
    elif is_fist:
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            points[pip] = (0.5, 0.4, 0.0)
            points[tip] = (0.5, 0.5, 0.0)
        points[4] = (0.5, y, 0.0)
    else:
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            points[pip] = (0.5, 0.4, 0.0)
            points[tip] = (0.5, 0.2, 0.0)
        points[4] = (0.2, y, 0.0)
        points[8] = (0.5, 0.2, 0.0)

    return HandLandmarks(points=points, handedness="Right")


class TestFlappyBirdProfile(unittest.TestCase):
    def setUp(self):
        self.profile = FlappyBirdProfile(
            flap_cooldown=0.10,
            pulse_velocity_threshold=0.20
        )
        self.kernel = MagicMock()

    def test_pinch_flap_dispatch(self):
        h = make_flappy_hand(y=0.5, is_pinch=True)
        res = self.profile.process_frame(h, None, self.kernel, timestamp=1.0)

        self.assertEqual(res["flap_count"], 1)
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_SPACE, hold_seconds=0.03)
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_UP, hold_seconds=0.03)
        self.kernel.click.assert_called_with(left=True)

    def test_fist_flap_dispatch(self):
        h = make_flappy_hand(y=0.5, is_fist=True)
        res = self.profile.process_frame(h, None, self.kernel, timestamp=1.0)

        self.assertEqual(res["flap_count"], 1)
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_SPACE, hold_seconds=0.03)

    def test_pulse_flick_flap(self):
        # Frame 1
        h1 = make_flappy_hand(y=0.60)
        self.profile.process_frame(h1, None, self.kernel, timestamp=1.0)

        # Frame 2: sharp upward pulse (y decreases from 0.60 to 0.45 in 0.05s -> vy = -3.0)
        h2 = make_flappy_hand(y=0.45)
        res = self.profile.process_frame(h2, None, self.kernel, timestamp=1.05)

        self.assertEqual(res["flap_count"], 1)
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_SPACE, hold_seconds=0.03)

    def test_cooldown_prevents_immediate_double_flap(self):
        h = make_flappy_hand(y=0.5, is_pinch=True)
        res1 = self.profile.process_frame(h, None, self.kernel, timestamp=1.0)
        self.assertEqual(res1["flap_count"], 1)

        # Immediate frame at 1.05s (< cooldown 0.10s)
        res2 = self.profile.process_frame(h, None, self.kernel, timestamp=1.05)
        self.assertEqual(res2["flap_count"], 1)
        self.assertEqual(len(res2["actions"]), 0)

        # Frame after cooldown at 1.15s
        res3 = self.profile.process_frame(h, None, self.kernel, timestamp=1.15)
        self.assertEqual(res3["flap_count"], 2)


if __name__ == "__main__":
    unittest.main()
