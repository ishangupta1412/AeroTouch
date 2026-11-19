import unittest
from src.service.scroll_controller import KineticScrollController
from src.gestures.engine import GestureMath, HandLandmarks


class TestKineticScroll(unittest.TestCase):
    def setUp(self):
        self.scroll_ctrl = KineticScrollController()

    def test_scroll_initial_anchor(self):
        """First frame of scroll gesture captures anchor point, yields 0 delta."""
        steps = self.scroll_ctrl.update(is_gesture_active=True, current_y=0.5, timestamp=1.0)
        self.assertEqual(steps, 0)
        self.assertTrue(self.scroll_ctrl.is_active)

    def test_scroll_up_positive_steps(self):
        """Moving fingers UP (decreasing y in image coords) yields positive scroll steps."""
        self.scroll_ctrl.update(is_gesture_active=True, current_y=0.50, timestamp=1.0)
        steps = self.scroll_ctrl.update(is_gesture_active=True, current_y=0.45, timestamp=1.016)
        self.assertGreater(steps, 0, "Moving fingers up must produce positive scroll steps (scroll up)")

    def test_scroll_down_negative_steps(self):
        """Moving fingers DOWN (increasing y in image coords) yields negative scroll steps."""
        self.scroll_ctrl.update(is_gesture_active=True, current_y=0.50, timestamp=1.0)
        steps = self.scroll_ctrl.update(is_gesture_active=True, current_y=0.55, timestamp=1.016)
        self.assertLess(steps, 0, "Moving fingers down must produce negative scroll steps (scroll down)")

    def test_kinetic_momentum_friction_decay(self):
        """Releasing gesture continues decelerating momentum across frames."""
        self.scroll_ctrl.update(is_gesture_active=True, current_y=0.50, timestamp=1.0)
        self.scroll_ctrl.update(is_gesture_active=True, current_y=0.40, timestamp=1.016)

        # Release gesture
        decay_1 = self.scroll_ctrl.update(is_gesture_active=False, current_y=0.40, timestamp=1.032)
        decay_2 = self.scroll_ctrl.update(is_gesture_active=False, current_y=0.40, timestamp=1.048)
        self.assertGreater(decay_1, 0)
        self.assertLessEqual(decay_2, decay_1, "Kinetic decay must reduce momentum over time")

    def test_two_finger_gesture_detection_math(self):
        """Validates that parallel index + middle fingers with ring + pinky curled triggers scroll."""
        pts = [(0.5, 0.8, 0.0)] * 21
        pts[0] = (0.5, 0.8, 0.0)
        pts[9] = (0.5, 0.5, 0.0)
        # Index extended
        pts[6] = (0.48, 0.45, 0.0)
        pts[8] = (0.48, 0.25, 0.0)
        # Middle extended
        pts[10] = (0.52, 0.45, 0.0)
        pts[12] = (0.52, 0.24, 0.0)
        # Ring curled
        pts[14] = (0.55, 0.55, 0.0)
        pts[16] = (0.55, 0.65, 0.0)
        # Pinky curled
        pts[18] = (0.60, 0.58, 0.0)
        pts[20] = (0.60, 0.68, 0.0)
        # Thumb open
        pts[4] = (0.35, 0.50, 0.0)

        hand = HandLandmarks(pts)
        self.assertTrue(GestureMath.is_two_finger_scroll(hand))


if __name__ == '__main__':
    unittest.main()
