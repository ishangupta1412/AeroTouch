import unittest
from src.gestures.engine import BimanualEngine, HandLandmarks, HandMode, GestureMath


class TestBimanualEngine(unittest.TestCase):
    def setUp(self):
        self.engine = BimanualEngine(
            pinch_threshold=0.28,
            release_threshold=0.38,
            debounce_seconds=0.20,
            confirm_frames=2
        )

    def _make_dummy_hand(self, handedness="Right", pinch=False):
        """Creates synthetic 21 3D landmarks."""
        points = [(0.5, 0.8, 0.0)] * 21
        points[0] = (0.5, 0.8, 0.0)      # Wrist
        points[9] = (0.5, 0.5, 0.0)      # Middle MCP (Scale = 0.3)
        points[4] = (0.5, 0.3, 0.0)      # Thumb tip
        points[12] = (0.7, 0.2, 0.0)     # Middle tip far away (no right-click)

        if pinch:
            points[8] = (0.5, 0.3, 0.0)  # Index tip touching thumb tip
        else:
            points[8] = (0.7, 0.2, 0.0)  # Index tip extended far away

        return HandLandmarks(points=points, handedness=handedness)

    def test_scale_invariant_pinch(self):
        hand_open = self._make_dummy_hand(pinch=False)
        self.assertGreater(GestureMath.normalized_pinch_distance(hand_open), 0.5)

        hand_pinched = self._make_dummy_hand(pinch=True)
        self.assertLess(GestureMath.normalized_pinch_distance(hand_pinched), 0.05)

    def test_single_frame_does_not_click(self):
        """A single frame with pinch must NOT fire click (ghost-click prevention)."""
        hand_pinched = self._make_dummy_hand(pinch=True)

        res1 = self.engine.evaluate_right_action(hand_pinched, now=10.0)
        self.assertIsNone(res1["click_event"], "Single frame pinch must NOT trigger LEFT_CLICK")
        self.assertFalse(res1["is_pinching"], "Single frame should not transition to pinching state")
        self.assertEqual(self.engine.pinch_streak, 1)

    def test_multi_frame_confirmation_fires_click(self):
        """Sustained pinch across confirm_frames (2) DOES fire click."""
        hand_pinched = self._make_dummy_hand(pinch=True)

        # Frame 1: streak builds to 1, no click
        res1 = self.engine.evaluate_right_action(hand_pinched, now=10.0)
        self.assertIsNone(res1["click_event"])

        # Frame 2: streak hits confirm_frames=2, fires LEFT_CLICK
        res2 = self.engine.evaluate_right_action(hand_pinched, now=10.016)
        self.assertEqual(res2["click_event"], "LEFT_CLICK")
        self.assertTrue(res2["is_pinching"])

    def test_non_blocking_debounce(self):
        """After a confirmed click, immediate next frames must NOT re-trigger."""
        hand_pinched = self._make_dummy_hand(pinch=True)

        # Build up to click (2 frames)
        self.engine.evaluate_right_action(hand_pinched, now=10.0)
        res_click = self.engine.evaluate_right_action(hand_pinched, now=10.016)
        self.assertEqual(res_click["click_event"], "LEFT_CLICK")

        # Immediate next frame (16ms later) must NOT re-trigger click
        res_post = self.engine.evaluate_right_action(hand_pinched, now=10.032)
        self.assertIsNone(res_post["click_event"])
        self.assertTrue(res_post["is_pinching"])

    def test_release_resets_pinch_state(self):
        """After release, pinch state and streaks must fully reset."""
        hand_pinched = self._make_dummy_hand(pinch=True)
        hand_open = self._make_dummy_hand(pinch=False)

        # Click sequence
        self.engine.evaluate_right_action(hand_pinched, now=10.0)
        self.engine.evaluate_right_action(hand_pinched, now=10.016)

        # Release
        res_release = self.engine.evaluate_right_action(hand_open, now=10.032)
        self.assertFalse(res_release["is_pinching"])
        self.assertEqual(self.engine.pinch_streak, 0)

    def test_left_hand_modes(self):
        """Left hand modifier mode detection."""
        # Fist (0 extended) => WINDOW_SNAP
        fist_hand = HandLandmarks(
            points=[(0.5, 0.8, 0.0)] * 21,
            handedness="Left"
        )
        fist_hand.points[0] = (0.5, 0.8, 0.0)
        fist_hand.points[9] = (0.5, 0.5, 0.0)
        mode = self.engine.evaluate_left_modifier(fist_hand)
        self.assertEqual(mode, HandMode.WINDOW_SNAP)

        # No left hand => POINTER_NAV
        mode_none = self.engine.evaluate_left_modifier(None)
        self.assertEqual(mode_none, HandMode.POINTER_NAV)


if __name__ == '__main__':
    unittest.main()
