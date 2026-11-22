"""
Unit tests for AeroTouch Racing Wheel Profile.
Tests virtual steering wheel tilt, gas/brake pedal synthesis, and nitro boost.
"""

import math
import os
import sys
import unittest
from unittest.mock import MagicMock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gestures.engine import HandLandmarks
from src.games.profiles.racing_wheel import RacingWheelProfile
from src.os_bridge.win32_kernel import VirtualKey


def make_hand(
    palm_y: float = 0.5,
    is_fist: bool = False,
    is_pinch: bool = False,
    handedness: str = "Right"
) -> HandLandmarks:
    # Wrist at y = 0.8
    points = [(0.5, palm_y, 0.0)] * 21
    points[0] = (0.5, 0.8, 0.0)
    points[9] = (0.5, palm_y, 0.0)

    if is_fist:
        # Curled fingers
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            points[pip] = (0.5, 0.4, 0.0)
            points[tip] = (0.5, 0.5, 0.0)
        points[4] = (0.5, 0.5, 0.0)
    elif is_pinch:
        # Extended fingers except thumb and index meet
        for tip, pip in [(12, 10), (16, 14), (20, 18)]:
            points[pip] = (0.5, 0.4, 0.0)
            points[tip] = (0.5, 0.2, 0.0)
        points[4] = (0.5, palm_y, 0.0)
        points[8] = (0.5, palm_y + 0.02, 0.0)
    else:
        # Open hand
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            points[pip] = (0.5, 0.4, 0.0)
            points[tip] = (0.5, 0.2, 0.0)
        points[4] = (0.2, palm_y, 0.0)
        points[8] = (0.5, 0.2, 0.0)

    return HandLandmarks(points=points, handedness=handedness)


class TestRacingWheelProfile(unittest.TestCase):
    def setUp(self):
        self.profile = RacingWheelProfile()
        self.kernel = MagicMock()

    def test_center_steering(self):
        # Both hands at same height
        r_hand = make_hand(palm_y=0.50, handedness="Right")
        l_hand = make_hand(palm_y=0.50, handedness="Left")

        res = self.profile.process_frame(r_hand, l_hand, self.kernel, timestamp=1.0)
        self.assertEqual(res["steer"], "CENTER")
        self.kernel.tap_key.assert_not_called()

    def test_steer_right(self):
        # Right hand lower than Left hand (tilt > 0.06)
        r_hand = make_hand(palm_y=0.60, handedness="Right")
        l_hand = make_hand(palm_y=0.40, handedness="Left")

        res = self.profile.process_frame(r_hand, l_hand, self.kernel, timestamp=1.0)
        self.assertEqual(res["steer"], "RIGHT")
        self.assertIn("STEER_RIGHT", res["actions"])
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_RIGHT)
        self.kernel.tap_key.assert_any_call(ord('D'))

    def test_steer_left(self):
        # Right hand higher than Left hand (tilt < -0.06)
        r_hand = make_hand(palm_y=0.40, handedness="Right")
        l_hand = make_hand(palm_y=0.60, handedness="Left")

        res = self.profile.process_frame(r_hand, l_hand, self.kernel, timestamp=1.0)
        self.assertEqual(res["steer"], "LEFT")
        self.assertIn("STEER_LEFT", res["actions"])
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_LEFT)
        self.kernel.tap_key.assert_any_call(ord('A'))

    def test_gas_pedal_via_right_fist(self):
        r_fist = make_hand(palm_y=0.50, is_fist=True, handedness="Right")
        res = self.profile.process_frame(r_fist, None, self.kernel, timestamp=1.0)
        self.assertTrue(any("GAS" in a for a in res["actions"]))
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_UP)
        self.kernel.tap_key.assert_any_call(ord('W'))

    def test_brake_pedal_via_left_fist(self):
        l_fist = make_hand(palm_y=0.50, is_fist=True, handedness="Left")
        res = self.profile.process_frame(None, l_fist, self.kernel, timestamp=1.0)
        self.assertTrue(any("BRAKE" in a for a in res["actions"]))
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_DOWN)
        self.kernel.tap_key.assert_any_call(ord('S'))

    def test_nitro_dual_pinch(self):
        r_pinch = make_hand(palm_y=0.50, is_pinch=True, handedness="Right")
        l_pinch = make_hand(palm_y=0.50, is_pinch=True, handedness="Left")
        res = self.profile.process_frame(r_pinch, l_pinch, self.kernel, timestamp=1.0)
        self.assertTrue(any("NITRO" in a for a in res["actions"]))
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_SPACE)


if __name__ == "__main__":
    unittest.main()
