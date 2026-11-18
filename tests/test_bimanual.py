import unittest
from src.gestures.engine import BimanualEngine, HandLandmarks, HandMode, GestureMath


class TestBimanualEngine(unittest.TestCase):
    def setUp(self):
        self.engine = BimanualEngine()

    def _make_dummy_hand(self, handedness="Right", pinch=False):
        """Creates synthetic 21 3D landmarks."""
        points = [(0.5, 0.8, 0.0)] * 21  # Default wrist at bottom
        points[0] = (0.5, 0.8, 0.0)      # Wrist
        points[9] = (0.5, 0.5, 0.0)      # Middle MCP (Scale = 0.3)
        points[4] = (0.5, 0.3, 0.0)      # Thumb tip

        if pinch:
            # Index tip touching thumb tip
            points[8] = (0.5, 0.3, 0.0)
        else:
            # Index tip extended far away
            points[8] = (0.7, 0.2, 0.0)

        return HandLandmarks(points=points, handedness=handedness)

    def test_scale_invariant_pinch(self):
        hand_open = self._make_dummy_hand(pinch=False)
        self.assertGreater(GestureMath.normalized_pinch_distance(hand_open), 0.5)

        hand_pinched = self._make_dummy_hand(pinch=True)
        self.assertLess(GestureMath.normalized_pinch_distance(hand_pinched), 0.05)

    def test_non_blocking_debounce(self):
        hand_pinched = self._make_dummy_hand(pinch=True)

        # First evaluation should register LEFT_CLICK
        res1 = self.engine.evaluate_right_action(hand_pinched, now=10.0)
        self.assertEqual(res1["click_event"], "LEFT_CLICK")
        self.assertTrue(res1["is_pinching"])

        # Immediate next frame (16ms later) must NOT re-trigger click (zero double-click flutter)
        res2 = self.engine.evaluate_right_action(hand_pinched, now=10.016)
        self.assertIsNone(res2["click_event"])
        self.assertTrue(res2["is_pinching"])


if __name__ == '__main__':
    unittest.main()
