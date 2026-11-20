"""
Unit tests for AeroTouch Bimanual Spatial Zoom Controller.
"""

import unittest
from src.gestures.engine import HandLandmarks
from src.service.spatial_zoom import BimanualZoomController


class TestBimanualZoomController(unittest.TestCase):
    def setUp(self):
        self.ctrl = BimanualZoomController(step_threshold=0.03, debounce_seconds=0.05)

    def _make_hand(self, index_tip_pos, handedness="Right"):
        points = [(0.5, 0.8, 0.0)] * 21
        points[0] = (0.5, 0.8, 0.0)
        points[9] = (0.5, 0.6, 0.0)
        points[8] = index_tip_pos  # Index Tip
        points[6] = (index_tip_pos[0], index_tip_pos[1] + 0.1, index_tip_pos[2])  # PIP
        points[4] = (index_tip_pos[0] + 0.02, index_tip_pos[1], index_tip_pos[2])  # Thumb Tip close (pinch)
        return HandLandmarks(points=points, handedness=handedness)

    def test_single_hand_returns_zero(self):
        hand_r = self._make_hand((0.6, 0.5, 0.0), handedness="Right")
        steps = self.ctrl.update(hand_r, None, timestamp=1.0)
        self.assertEqual(steps, 0)
        self.assertFalse(self.ctrl.is_active)

    def test_initial_two_hand_engagement_captures_anchor(self):
        hand_r = self._make_hand((0.6, 0.5, 0.0), handedness="Right")
        hand_l = self._make_hand((0.4, 0.5, 0.0), handedness="Left")
        steps = self.ctrl.update(hand_r, hand_l, timestamp=1.0)
        self.assertEqual(steps, 0)
        self.assertTrue(self.ctrl.is_active)
        self.assertAlmostEqual(self.ctrl.last_distance, 0.2, delta=0.01)

    def test_hands_moving_apart_triggers_zoom_in(self):
        hand_r1 = self._make_hand((0.60, 0.5, 0.0), handedness="Right")
        hand_l1 = self._make_hand((0.40, 0.5, 0.0), handedness="Left")
        self.ctrl.update(hand_r1, hand_l1, timestamp=1.0)

        # Hands separate from 0.20 to 0.28 (delta = +0.08 >= threshold 0.03)
        hand_r2 = self._make_hand((0.64, 0.5, 0.0), handedness="Right")
        hand_l2 = self._make_hand((0.36, 0.5, 0.0), handedness="Left")
        steps = self.ctrl.update(hand_r2, hand_l2, timestamp=1.08)
        self.assertGreater(steps, 0, "Moving hands apart must trigger positive zoom steps (Zoom In).")

    def test_hands_moving_together_triggers_zoom_out(self):
        hand_r1 = self._make_hand((0.65, 0.5, 0.0), handedness="Right")
        hand_l1 = self._make_hand((0.35, 0.5, 0.0), handedness="Left")
        self.ctrl.update(hand_r1, hand_l1, timestamp=1.0)

        # Hands contract from 0.30 to 0.22 (delta = -0.08 <= -0.03)
        hand_r2 = self._make_hand((0.61, 0.5, 0.0), handedness="Right")
        hand_l2 = self._make_hand((0.39, 0.5, 0.0), handedness="Left")
        steps = self.ctrl.update(hand_r2, hand_l2, timestamp=1.08)
        self.assertLess(steps, 0, "Moving hands closer must trigger negative zoom steps (Zoom Out).")


if __name__ == "__main__":
    unittest.main()
