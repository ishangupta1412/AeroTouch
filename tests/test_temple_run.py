"""
Unit tests for AeroTouch Temple Run Profile.
Tests rapid swipe turns, jumps, slides, and stumble recovery powerups.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gestures.engine import HandLandmarks
from src.games.profiles.temple_run import TempleRunProfile
from src.os_bridge.win32_kernel import VirtualKey


def make_hand(x: float = 0.5, y: float = 0.5, is_pinch: bool = False) -> HandLandmarks:
    points = [(x, y, 0.0)] * 21
    points[9] = (x, y, 0.0)

    if is_pinch:
        points[4] = (x, y, 0.0)
        points[8] = (x, y + 0.02, 0.0)
    else:
        points[4] = (x - 0.1, y, 0.0)
        points[8] = (x + 0.1, y, 0.0)

    return HandLandmarks(points=points, handedness="Right")


class TestTempleRunProfile(unittest.TestCase):
    def setUp(self):
        self.profile = TempleRunProfile(
            velocity_threshold=0.20,
            min_displacement=0.02,
            swipe_cooldown=0.10
        )
        self.kernel = MagicMock()

    def test_swipe_jump(self):
        # Move up rapidly (y decreases)
        h1 = make_hand(x=0.5, y=0.60)
        h2 = make_hand(x=0.5, y=0.45)

        self.profile.process_frame(h1, None, self.kernel, timestamp=1.0)
        res = self.profile.process_frame(h2, None, self.kernel, timestamp=1.05)

        self.assertIn("JUMP (Up / W)", res["actions"])
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_UP)
        self.kernel.tap_key.assert_any_call(ord('W'))

    def test_swipe_slide(self):
        # Move down rapidly (y increases)
        h1 = make_hand(x=0.5, y=0.45)
        h2 = make_hand(x=0.5, y=0.60)

        self.profile.process_frame(h1, None, self.kernel, timestamp=2.0)
        res = self.profile.process_frame(h2, None, self.kernel, timestamp=2.05)

        self.assertIn("SLIDE (Down / S)", res["actions"])
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_DOWN)
        self.kernel.tap_key.assert_any_call(ord('S'))

    def test_swipe_turn_left(self):
        # Move left rapidly (x decreases)
        h1 = make_hand(x=0.60, y=0.5)
        h2 = make_hand(x=0.45, y=0.5)

        self.profile.process_frame(h1, None, self.kernel, timestamp=3.0)
        res = self.profile.process_frame(h2, None, self.kernel, timestamp=3.05)

        self.assertIn("TURN_LEFT (Left / A)", res["actions"])
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_LEFT)
        self.kernel.tap_key.assert_any_call(ord('A'))

    def test_swipe_turn_right(self):
        # Move right rapidly (x increases)
        h1 = make_hand(x=0.45, y=0.5)
        h2 = make_hand(x=0.60, y=0.5)

        self.profile.process_frame(h1, None, self.kernel, timestamp=4.0)
        res = self.profile.process_frame(h2, None, self.kernel, timestamp=4.05)

        self.assertIn("TURN_RIGHT (Right / D)", res["actions"])
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_RIGHT)
        self.kernel.tap_key.assert_any_call(ord('D'))


if __name__ == "__main__":
    unittest.main()
