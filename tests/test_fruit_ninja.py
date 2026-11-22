"""
Unit tests for AeroTouch Fruit Ninja Profile.
Tests high-speed katana blade slicing, auto mouse drag & release, and dual combos.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gestures.engine import HandLandmarks
from src.games.profiles.fruit_ninja import FruitNinjaProfile


def make_ninja_hand(x: float = 0.5, y: float = 0.5, handedness: str = "Right") -> HandLandmarks:
    points = [(x, y, 0.0)] * 21
    points[8] = (x, y, 0.0)  # Index fingertip
    return HandLandmarks(points=points, handedness=handedness)


class TestFruitNinjaProfile(unittest.TestCase):
    def setUp(self):
        self.profile = FruitNinjaProfile(
            slice_velocity_threshold=0.20,
            min_slice_displacement=0.01
        )
        self.kernel = MagicMock()
        self.kernel.get_screen_resolution.return_value = (1920, 1080)

    def test_fast_slash_triggers_katana_slice(self):
        # Initial position
        h1 = make_ninja_hand(x=0.20, y=0.50)
        self.profile.process_frame(h1, None, self.kernel, timestamp=1.0)

        # Fast slash to x=0.50 in 0.05s (vx = 6.0 > 0.20)
        h2 = make_ninja_hand(x=0.50, y=0.50)
        res = self.profile.process_frame(h2, None, self.kernel, timestamp=1.05)

        self.assertTrue(res["is_slicing"])
        self.assertEqual(res["slice_count"], 1)
        self.kernel.mouse_down.assert_called_with(left=True)
        self.kernel.move_cursor.assert_called()

    def test_deceleration_releases_mouse(self):
        # Fast slash
        h1 = make_ninja_hand(x=0.20, y=0.50)
        self.profile.process_frame(h1, None, self.kernel, timestamp=1.0)
        h2 = make_ninja_hand(x=0.50, y=0.50)
        self.profile.process_frame(h2, None, self.kernel, timestamp=1.05)
        self.assertTrue(self.profile._is_slicing)

        # Hand stops / barely moves in 0.20s
        h3 = make_ninja_hand(x=0.501, y=0.50)
        res = self.profile.process_frame(h3, None, self.kernel, timestamp=1.25)
        self.assertFalse(res["is_slicing"])
        self.kernel.mouse_up.assert_called_with(left=True)

    def test_dual_blade_combo(self):
        h_r1 = make_ninja_hand(x=0.20, y=0.50, handedness="Right")
        h_l1 = make_ninja_hand(x=0.80, y=0.50, handedness="Left")
        self.profile.process_frame(h_r1, h_l1, self.kernel, timestamp=1.0)

        h_r2 = make_ninja_hand(x=0.50, y=0.50, handedness="Right")
        h_l2 = make_ninja_hand(x=0.50, y=0.50, handedness="Left")
        res = self.profile.process_frame(h_r2, h_l2, self.kernel, timestamp=1.05)

        self.assertIn("DUAL_BLADE_COMBO", res["actions"])

    def test_clean_exit_releases_slicing(self):
        h1 = make_ninja_hand(x=0.20, y=0.50)
        self.profile.process_frame(h1, None, self.kernel, timestamp=1.0)
        h2 = make_ninja_hand(x=0.50, y=0.50)
        self.profile.process_frame(h2, None, self.kernel, timestamp=1.05)
        self.assertTrue(self.profile._is_slicing)

        self.profile.on_exit(self.kernel)
        self.assertFalse(self.profile._is_slicing)
        self.kernel.mouse_up.assert_called_with(left=True)


if __name__ == "__main__":
    unittest.main()
