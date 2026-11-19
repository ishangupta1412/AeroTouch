import unittest
from unittest.mock import MagicMock
from src.core.tracker import DualHandTracker
from src.gestures.engine import HandLandmarks
from src.core.orchestrator import SpatialOrchestrator


class TestDualHandTracker(unittest.TestCase):
    def setUp(self):
        # Initialize tracker with mocked detector to test pure logic without camera
        self.tracker = DualHandTracker.__new__(DualHandTracker)
        self.tracker.num_hands = 2
        self.tracker.detector = MagicMock()

    def _build_anatomical_hand(self, handedness="Right"):
        """
        Builds a biomechanically accurate hand skeleton:
        Wrist at (0.5, 0.8, 0.0)
        Middle MCP (9) at (0.5, 0.5, 0.0) -> Palm axis points up (-Y)
        Index MCP (5) at (0.45, 0.52, 0.0)
        Pinky MCP (17) at (0.55, 0.52, 0.0) -> Palm width points (+X)
        Normal vector = axis x width = (0, -0.3) x (0.1, 0) -> normal points in -Z (facing camera)
        """
        points = [(0.5, 0.8, 0.0)] * 21
        points[0] = (0.5, 0.8, 0.0)      # Wrist
        points[9] = (0.5, 0.5, 0.0)      # Middle MCP
        points[5] = (0.45, 0.52, 0.0)    # Index MCP
        points[17] = (0.55, 0.52, 0.0)   # Pinky MCP

        if handedness == "Right":
            # For right hand facing camera, thumb is to the left (-X)
            points[2] = (0.40, 0.65, -0.02)  # Thumb MCP
            points[4] = (0.35, 0.55, -0.03)  # Thumb Tip
        else:
            # For left hand facing camera, thumb is to the right (+X)
            points[2] = (0.60, 0.65, -0.02)  # Thumb MCP
            points[4] = (0.65, 0.55, -0.03)  # Thumb Tip

        return points

    def test_anatomical_handedness_verification_right(self):
        pts_right = self._build_anatomical_hand("Right")
        verified = self.tracker._verify_anatomical_handedness(pts_right, "Right")
        self.assertEqual(verified, "Right")

    def test_anatomical_handedness_verification_left(self):
        pts_left = self._build_anatomical_hand("Left")
        verified = self.tracker._verify_anatomical_handedness(pts_left, "Left")
        self.assertEqual(verified, "Left")

    def test_single_left_hand_does_not_become_right(self):
        """CRITICAL: When only a left hand is present, right_hand MUST be None."""
        pts_left = self._build_anatomical_hand("Left")

        # Mock MediaPipe detection result with only 1 Left hand
        mock_lm = [MagicMock(x=p[0], y=p[1], z=p[2]) for p in pts_left]
        mock_result = MagicMock()
        mock_result.hand_landmarks = [mock_lm]
        mock_result.handedness = [[MagicMock(category_name="Left")]]

        self.tracker.detector.detect.return_value = mock_result

        # Synthetic BGR image
        import numpy as np
        dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)

        right_hand, left_hand = self.tracker.process_frame(dummy_img)

        # Right hand MUST be None (no cursor control)
        self.assertIsNone(right_hand, "Left hand must NEVER be assigned to right_hand!")
        # Left hand MUST be present
        self.assertIsNotNone(left_hand)
        self.assertEqual(left_hand.handedness, "Left")

    def test_orchestrator_ignores_cursor_when_right_hand_is_none(self):
        """When right_hand is None, orchestrator must NOT move cursor or click."""
        orchestrator = SpatialOrchestrator()
        orchestrator.kernel.move_cursor = MagicMock()
        orchestrator.kernel.click = MagicMock()

        pts_left = self._build_anatomical_hand("Left")
        left_hand = HandLandmarks(points=pts_left, handedness="Left")

        # Process frame with only left hand
        res = orchestrator.process_spatial_frame(right_hand=None, left_hand=left_hand, timestamp=1.0)

        # Cursor pos must be None
        self.assertIsNone(res["cursor_pos"])
        # Hardware mouse move must NOT have been called
        orchestrator.kernel.move_cursor.assert_not_called()
        orchestrator.kernel.click.assert_not_called()


if __name__ == "__main__":
    unittest.main()
