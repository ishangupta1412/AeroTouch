import unittest
from unittest.mock import MagicMock
from src.core.orchestrator import SpatialOrchestrator
from src.gestures.engine import HandLandmarks, GestureMath
from src.os_bridge.win32_kernel import VirtualKey


class TestWindowSnapMatrix(unittest.TestCase):
    def setUp(self):
        self.orchestrator = SpatialOrchestrator()
        self.orchestrator.kernel.hotkey = MagicMock()
        self.orchestrator.kernel.move_cursor = MagicMock()
        self.orchestrator.kernel.click = MagicMock()

    def _build_fist_hand(self):
        """Builds a Left hand closed fist (0 extended fingers)."""
        pts = [(0.5, 0.8, 0.0)] * 21
        pts[0] = (0.5, 0.8, 0.0)
        pts[9] = (0.5, 0.6, 0.0)
        pts[2] = (0.45, 0.75, 0.0)
        pts[17] = (0.55, 0.65, 0.0)
        for pip in [6, 10, 14, 18]:
            pts[pip] = (0.5, 0.5, 0.0)
        for tip in [8, 12, 16, 20]:
            pts[tip] = (0.5, 0.65, 0.0)
        pts[4] = (0.48, 0.72, 0.0)  # Tucked thumb
        return HandLandmarks(pts, handedness="Left")

    def _build_directed_pinch_hand(self, direction="LEFT"):
        """Builds a Right hand pinch offset in the specified direction."""
        pts = [(0.5, 0.8, 0.0)] * 21
        pts[0] = (0.5, 0.8, 0.0)
        ref_x, ref_y = 0.5, 0.5
        pts[9] = (ref_x, ref_y, 0.0)

        offset_map = {
            "LEFT": (-0.15, 0.0),
            "RIGHT": (0.15, 0.0),
            "UP": (0.0, -0.15),
            "DOWN": (0.0, 0.15)
        }
        dx, dy = offset_map.get(direction, (0.0, 0.0))
        pinch_pos = (ref_x + dx, ref_y + dy, 0.0)
        pts[4] = pinch_pos  # Thumb tip
        pts[8] = pinch_pos  # Index tip (pinched)
        pts[12] = (ref_x + 0.2, ref_y, 0.0) # Middle extended away

        return HandLandmarks(pts, handedness="Right")

    def test_snap_direction_math(self):
        hand_up = self._build_directed_pinch_hand("UP")
        self.assertEqual(GestureMath.get_snap_direction(hand_up), "UP")

        hand_down = self._build_directed_pinch_hand("DOWN")
        self.assertEqual(GestureMath.get_snap_direction(hand_down), "DOWN")

        hand_right = self._build_directed_pinch_hand("RIGHT")
        self.assertEqual(GestureMath.get_snap_direction(hand_right), "RIGHT")

        hand_left = self._build_directed_pinch_hand("LEFT")
        self.assertEqual(GestureMath.get_snap_direction(hand_left), "LEFT")

    def test_orchestrator_snap_maximize_trigger(self):
        left_fist = self._build_fist_hand()
        right_pinch_up = self._build_directed_pinch_hand("UP")

        # Frame 1: Streak = 1
        self.orchestrator.process_spatial_frame(right_pinch_up, left_fist, timestamp=1.0)
        # Frame 2: Confirmed click -> Maximize
        res = self.orchestrator.process_spatial_frame(right_pinch_up, left_fist, timestamp=1.016)

        self.assertEqual(res["action_executed"], "WINDOW_MAXIMIZE")
        self.orchestrator.kernel.hotkey.assert_called_with(VirtualKey.VK_LWIN, VirtualKey.VK_UP)

    def test_orchestrator_snap_right_trigger(self):
        left_fist = self._build_fist_hand()
        right_pinch_right = self._build_directed_pinch_hand("RIGHT")

        self.orchestrator.process_spatial_frame(right_pinch_right, left_fist, timestamp=1.0)
        res = self.orchestrator.process_spatial_frame(right_pinch_right, left_fist, timestamp=1.016)

        self.assertEqual(res["action_executed"], "WINDOW_SNAP_RIGHT")
        self.orchestrator.kernel.hotkey.assert_called_with(VirtualKey.VK_LWIN, VirtualKey.VK_RIGHT)


if __name__ == '__main__':
    unittest.main()
