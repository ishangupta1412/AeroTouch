"""
Unit tests for AeroTouch Fluid 3-Finger Desktop & Mission Control Swipe Engine.
"""

import unittest
from src.gestures.engine import HandLandmarks
from src.service.swipe_detector import FluidSwipeDetector


class TestFluidSwipeDetector(unittest.TestCase):
    def setUp(self):
        self.detector = FluidSwipeDetector(
            velocity_threshold=0.50,
            min_displacement=0.05,
            cooldown=0.5
        )

    def _make_hand(self, extended_indices=(8, 12, 16), wrist_y=0.8, cx=0.5, cy=0.5):
        """Constructs a test hand with specified fingers extended."""
        points = [(cx, wrist_y, 0.0)] * 21
        points[0] = (cx, wrist_y, 0.0)
        points[9] = (cx, 0.6, 0.0)

        # Base curl positions
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            points[pip] = (cx, 0.5, 0.0)
            points[tip] = (cx, 0.65, 0.0)

        # Extend requested fingers
        for tip in extended_indices:
            pip = tip - 2
            points[pip] = (cx, cy + 0.1, 0.0)
            points[tip] = (cx, cy, 0.0)

        return HandLandmarks(points=points, handedness="Right")

    def test_three_finger_pose_discrimination(self):
        # 3 fingers (8, 12, 16) extended, 20 curled -> True
        three_f = self._make_hand(extended_indices=(8, 12, 16))
        self.assertTrue(FluidSwipeDetector.is_three_finger_pose(three_f))

        # 4 fingers (open hand, including pinky 20) -> False
        four_f = self._make_hand(extended_indices=(8, 12, 16, 20))
        self.assertFalse(FluidSwipeDetector.is_three_finger_pose(four_f))

        # 2 fingers (peace sign) -> False
        two_f = self._make_hand(extended_indices=(8, 12))
        self.assertFalse(FluidSwipeDetector.is_three_finger_pose(two_f))

        # Fist (0 fingers) -> False
        fist = self._make_hand(extended_indices=())
        self.assertFalse(FluidSwipeDetector.is_three_finger_pose(fist))

    def test_swipe_up_detection(self):
        # Rapid upward movement (decreasing cy)
        t = 1.0
        res = None
        for i in range(6):
            hand = self._make_hand(extended_indices=(8, 12, 16), cx=0.5, cy=0.6 - i * 0.025)
            r = self.detector.update(hand, timestamp=t + i * 0.016)
            if r:
                res = r
        self.assertEqual(res, "SWIPE_UP")

    def test_swipe_down_detection(self):
        t = 1.0
        res = None
        for i in range(6):
            hand = self._make_hand(extended_indices=(8, 12, 16), cx=0.5, cy=0.3 + i * 0.025)
            r = self.detector.update(hand, timestamp=t + i * 0.016)
            if r:
                res = r
        self.assertEqual(res, "SWIPE_DOWN")

    def test_swipe_right_detection(self):
        t = 1.0
        res = None
        for i in range(6):
            hand = self._make_hand(extended_indices=(8, 12, 16), cx=0.3 + i * 0.025, cy=0.5)
            r = self.detector.update(hand, timestamp=t + i * 0.016)
            if r:
                res = r
        self.assertEqual(res, "SWIPE_RIGHT")

    def test_swipe_left_detection(self):
        t = 1.0
        res = None
        for i in range(6):
            hand = self._make_hand(extended_indices=(8, 12, 16), cx=0.7 - i * 0.025, cy=0.5)
            r = self.detector.update(hand, timestamp=t + i * 0.016)
            if r:
                res = r
        self.assertEqual(res, "SWIPE_LEFT")

    def test_cooldown_prevents_immediate_refire(self):
        t = 1.0
        for i in range(6):
            hand = self._make_hand(extended_indices=(8, 12, 16), cx=0.5, cy=0.6 - i * 0.025)
            r = self.detector.update(hand, timestamp=t + i * 0.016)
            if r:
                break

        # Attempt another swipe immediately within cooldown
        hand_rapid = self._make_hand(extended_indices=(8, 12, 16), cx=0.5, cy=0.4)
        r2 = self.detector.update(hand_rapid, timestamp=t + 0.15)
        self.assertIsNone(r2, "Swipe must be suppressed during cooldown window.")


if __name__ == "__main__":
    unittest.main()
