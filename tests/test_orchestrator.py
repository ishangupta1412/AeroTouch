import unittest
from unittest.mock import MagicMock
from src.core.orchestrator import SpatialOrchestrator
from src.gestures.engine import HandLandmarks, HandMode


class TestSpatialOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orchestrator = SpatialOrchestrator()
        # Mock low-level kernel so test doesn't move user's actual mouse during CI
        self.orchestrator.kernel.move_cursor = MagicMock()
        self.orchestrator.kernel.click = MagicMock()
        self.orchestrator.kernel.hotkey = MagicMock()

    def test_end_to_end_cursor_pipeline(self):
        dummy_points = [(0.5, 0.5, 0.0)] * 21
        dummy_points[4] = (0.2, 0.2, 0.0) # open thumb
        dummy_points[8] = (0.5, 0.5, 0.0) # index tip
        dummy_points[9] = (0.5, 0.7, 0.0) # MCP scale anchor
        dummy_hand = HandLandmarks(points=dummy_points, handedness="Right")

        res = self.orchestrator.process_spatial_frame(
            right_hand=dummy_hand,
            left_hand=None,
            timestamp=100.0
        )

        self.assertEqual(res["mode"], "POINTER_NAV")
        self.assertIsNotNone(res["cursor_pos"])
        self.orchestrator.kernel.move_cursor.assert_called_once()


if __name__ == '__main__':
    unittest.main()
