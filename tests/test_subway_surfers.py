"""
Unit tests for AeroTouch Subway Surfers Game Profile.
Tests Jump (VK_UP), Roll (VK_DOWN), Dodge Left/Right (VK_LEFT/VK_RIGHT),
and Hoverboard (VK_SPACE) input synthesis without touching real hardware.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gestures.engine import HandLandmarks
from src.os_bridge.win32_kernel import VirtualKey
from src.games.profiles.subway_surfers import SubwaySurfersProfile


def make_hand_at(x: float, y: float, pinch: bool = False) -> HandLandmarks:
    """Creates a mock hand landmark centered at (x, y)."""
    pts = [(x, y, 0.0)] * 21
    # Knuckle / mid-palm
    pts[9] = (x, y, 0.0)

    if pinch:
        # Thumb tip (4) and Index tip (8) touching
        pts[4] = (x, y, 0.0)
        pts[8] = (x, y + 0.01, 0.0)
    else:
        # Normal open tips
        pts[4] = (x - 0.08, y, 0.0)
        pts[8] = (x + 0.08, y - 0.1, 0.0)

    return HandLandmarks(points=pts, handedness="Right")


class TestSubwaySurfersProfile(unittest.TestCase):
    def setUp(self):
        self.profile = SubwaySurfersProfile(
            velocity_threshold=0.35,
            min_displacement=0.03,
            swipe_cooldown=0.15,
            hoverboard_cooldown=0.60
        )
        self.mock_kernel = MagicMock()

    def test_metadata(self):
        self.assertEqual(self.profile.game_id, "subway_surfers")
        self.assertEqual(self.profile.game_name, "Subway Surfers")

    def test_jump_swipe(self):
        # Frame 1: baseline position (t=1.0)
        h1 = make_hand_at(0.5, 0.6)
        res1 = self.profile.process_frame(h1, None, self.mock_kernel, timestamp=1.0)
        self.assertEqual(res1["actions"], [])

        # Frame 2: fast upward flick (dy = -0.08 in 0.05s -> vy = -1.6)
        h2 = make_hand_at(0.5, 0.52)
        res2 = self.profile.process_frame(h2, None, self.mock_kernel, timestamp=1.05)

        self.assertTrue(any("JUMP" in a for a in res2["actions"]))
        self.mock_kernel.tap_key.assert_any_call(VirtualKey.VK_UP)
        self.mock_kernel.tap_key.assert_any_call(ord('W'))

    def test_roll_swipe(self):
        # Frame 1: baseline (t=2.0)
        h1 = make_hand_at(0.5, 0.4)
        self.profile.process_frame(h1, None, self.mock_kernel, timestamp=2.0)

        # Frame 2: fast downward flick (dy = +0.08 in 0.05s -> vy = +1.6)
        h2 = make_hand_at(0.5, 0.48)
        res = self.profile.process_frame(h2, None, self.mock_kernel, timestamp=2.05)

        self.assertTrue(any("ROLL" in a for a in res["actions"]))
        self.mock_kernel.tap_key.assert_any_call(VirtualKey.VK_DOWN)
        self.mock_kernel.tap_key.assert_any_call(ord('S'))

    def test_left_dodge_swipe(self):
        # Frame 1: baseline (t=3.0)
        h1 = make_hand_at(0.6, 0.5)
        self.profile.process_frame(h1, None, self.mock_kernel, timestamp=3.0)

        # Frame 2: fast leftward flick (dx = -0.09 in 0.05s -> vx = -1.8)
        h2 = make_hand_at(0.51, 0.5)
        res = self.profile.process_frame(h2, None, self.mock_kernel, timestamp=3.05)

        self.assertTrue(any("DODGE_LEFT" in a for a in res["actions"]))
        self.mock_kernel.tap_key.assert_any_call(VirtualKey.VK_LEFT)
        self.mock_kernel.tap_key.assert_any_call(ord('A'))

    def test_right_dodge_swipe(self):
        # Frame 1: baseline (t=4.0)
        h1 = make_hand_at(0.4, 0.5)
        self.profile.process_frame(h1, None, self.mock_kernel, timestamp=4.0)

        # Frame 2: fast rightward flick (dx = +0.09 in 0.05s -> vx = +1.8)
        h2 = make_hand_at(0.49, 0.5)
        res = self.profile.process_frame(h2, None, self.mock_kernel, timestamp=4.05)

        self.assertTrue(any("DODGE_RIGHT" in a for a in res["actions"]))
        self.mock_kernel.tap_key.assert_any_call(VirtualKey.VK_RIGHT)
        self.mock_kernel.tap_key.assert_any_call(ord('D'))

    def test_hoverboard_activation(self):
        # Hand with thumb and index pinched together
        h_pinch = make_hand_at(0.5, 0.5, pinch=True)
        res = self.profile.process_frame(h_pinch, None, self.mock_kernel, timestamp=5.0)

        self.assertIn("HOVERBOARD (VK_SPACE)", res["actions"])
        self.mock_kernel.tap_key.assert_called_with(VirtualKey.VK_SPACE)

    def test_slow_drift_does_not_trigger(self):
        h1 = make_hand_at(0.5, 0.5)
        self.profile.process_frame(h1, None, self.mock_kernel, timestamp=6.0)

        # Micro-drift: 0.005 in 0.1s -> velocity = 0.05 << threshold
        h2 = make_hand_at(0.5, 0.495)
        res = self.profile.process_frame(h2, None, self.mock_kernel, timestamp=6.10)
        self.assertEqual(res["actions"], [])

    def test_swipe_cooldown(self):
        h1 = make_hand_at(0.5, 0.6)
        self.profile.process_frame(h1, None, self.mock_kernel, timestamp=7.0)

        # Swipe 1 at t=7.05 -> fires
        h2 = make_hand_at(0.5, 0.52)
        res1 = self.profile.process_frame(h2, None, self.mock_kernel, timestamp=7.05)
        self.assertTrue(any("JUMP" in a for a in res1["actions"]))

        # Immediate follow-up frame at t=7.10 (< 0.15s cooldown) -> suppressed
        h3 = make_hand_at(0.5, 0.44)
        res2 = self.profile.process_frame(h3, None, self.mock_kernel, timestamp=7.10)
        self.assertEqual(res2["actions"], [])


if __name__ == "__main__":
    unittest.main()
