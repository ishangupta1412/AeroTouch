import unittest
from unittest.mock import MagicMock
from src.core.orchestrator import SpatialOrchestrator
from src.gestures.engine import HandLandmarks, HandMode
from src.os_bridge.win32_kernel import VirtualKey


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

    def test_left_hand_window_snap_trigger(self):
        # Biomechanically accurate closed fist:
        # Wrist at (0.5, 0.8)
        # PIPs extended up to y=0.5 (dist 0.3 from wrist)
        # Finger tips curled back down to y=0.65 (dist 0.15 from wrist, so wrist_to_tip < wrist_to_pip)
        left_points = [(0.5, 0.8, 0.0)] * 21
        left_points[0] = (0.5, 0.8, 0.0)  # Wrist
        left_points[9] = (0.5, 0.6, 0.0)  # Middle MCP
        left_points[2] = (0.45, 0.75, 0.0) # Thumb MCP
        left_points[17] = (0.55, 0.65, 0.0) # Pinky MCP

        # PIP joints (6, 10, 14, 18) are pushed forward
        for pip in [6, 10, 14, 18]:
            left_points[pip] = (0.5, 0.5, 0.0)

        # Tips (4, 8, 12, 16, 20) are curled inwards toward palm/wrist
        for tip in [4, 8, 12, 16, 20]:
            left_points[tip] = (0.5, 0.65, 0.0)

        left_hand = HandLandmarks(points=left_points, handedness="Left")

        # Right hand pinched to the LEFT of Middle MCP
        right_points = [(0.5, 0.8, 0.0)] * 21
        right_points[0] = (0.5, 0.8, 0.0)
        right_points[9] = (0.5, 0.5, 0.0)
        right_points[4] = (0.35, 0.5, 0.0)
        right_points[8] = (0.35, 0.5, 0.0) # Pinch directed left
        right_points[12] = (0.7, 0.2, 0.0)
        right_hand = HandLandmarks(points=right_points, handedness="Right")

        # Frame 1: Streak = 1
        self.orchestrator.process_spatial_frame(right_hand, left_hand, timestamp=10.0)
        # Frame 2: Streak = 2 -> WINDOW_SNAP_LEFT
        res2 = self.orchestrator.process_spatial_frame(right_hand, left_hand, timestamp=10.016)

        self.assertEqual(res2["action_executed"], "WINDOW_SNAP_LEFT")
        self.orchestrator.kernel.hotkey.assert_called_with(VirtualKey.VK_LWIN, VirtualKey.VK_LEFT)

    def test_recalibrate_resets_state(self):
        self.orchestrator.custom_gesture_streak = 5
        self.orchestrator.recalibrate()
        self.assertEqual(self.orchestrator.custom_gesture_streak, 0)
        self.assertIsNone(self.orchestrator.filter.last_output_x)

    def test_custom_few_shot_gesture_dispatch(self):
        self.orchestrator.kernel.execute_named_action = MagicMock()

        # Mock custom gesture in custom_engine
        self.orchestrator.custom_engine.classify = MagicMock(
            return_value=("CUSTOM_PLAY", 0.95, {"action": "MEDIA_PLAY_PAUSE", "action_param": None})
        )

        dummy_points = [(0.5, 0.5, 0.0)] * 21
        dummy_points[4] = (0.3, 0.3, 0.0)
        dummy_points[8] = (0.5, 0.2, 0.0)
        dummy_points[9] = (0.5, 0.6, 0.0)
        right_hand = HandLandmarks(points=dummy_points, handedness="Right")

        # Frame 1
        self.orchestrator.process_spatial_frame(right_hand, None, timestamp=1.0)
        # Frame 2
        self.orchestrator.process_spatial_frame(right_hand, None, timestamp=1.016)
        # Frame 3: confirmed!
        res3 = self.orchestrator.process_spatial_frame(right_hand, None, timestamp=1.032)

        self.assertEqual(res3["action_executed"], "CUSTOM_GESTURE_CUSTOM_PLAY")
        self.orchestrator.kernel.execute_named_action.assert_called_with("MEDIA_PLAY_PAUSE", None)


if __name__ == '__main__':
    unittest.main()
