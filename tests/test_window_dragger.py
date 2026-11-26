import unittest
from unittest.mock import MagicMock
from src.service.window_dragger import WindowDragger
from src.gestures.engine import HandLandmarks, GestureMath
from src.core.orchestrator import SpatialOrchestrator


class TestWindowDragger(unittest.TestCase):
    def setUp(self):
        self.dragger = WindowDragger()

    def test_initial_state(self):
        self.assertFalse(self.dragger.is_dragging)

    def test_start_drag_captures_origin(self):
        hwnd = 12345
        rect = (100, 150, 900, 750)  # width=800, height=600
        cur_x, cur_y = 500, 400

        self.dragger.start_drag(hwnd, rect, cur_x, cur_y)
        self.assertTrue(self.dragger.is_dragging)
        self.assertEqual(self.dragger._win_width, 800)
        self.assertEqual(self.dragger._win_height, 600)

    def test_update_drag_applies_delta(self):
        hwnd = 12345
        rect = (100, 150, 900, 750)
        cur_x, cur_y = 500, 400

        self.dragger.start_drag(hwnd, rect, cur_x, cur_y)

        # Move cursor by +50 in X, -30 in Y
        target_hwnd, new_x, new_y, w, h = self.dragger.update_drag(550, 370)
        self.assertEqual(target_hwnd, hwnd)
        self.assertEqual(new_x, 150)  # 100 + 50
        self.assertEqual(new_y, 120)  # 150 - 30
        self.assertEqual(w, 800)
        self.assertEqual(h, 600)

    def test_end_drag_cleans_up(self):
        self.dragger.start_drag(12345, (100, 100, 500, 500), 200, 200)
        self.assertTrue(self.dragger.is_dragging)
        self.dragger.end_drag()
        self.assertFalse(self.dragger.is_dragging)
        self.assertEqual(self.dragger._drag_hwnd, 0)

    def _make_fist_hand(self, handedness="Right"):
        """Biomechanically accurate closed fist."""
        points = [(0.5, 0.8, 0.0)] * 21
        points[0] = (0.5, 0.8, 0.0)    # Wrist
        points[9] = (0.5, 0.6, 0.0)    # Middle MCP
        points[2] = (0.45, 0.75, 0.0)  # Thumb MCP
        points[17] = (0.55, 0.65, 0.0) # Pinky MCP

        # PIP joints (6, 10, 14, 18) are pushed forward
        for pip in [6, 10, 14, 18]:
            points[pip] = (0.5, 0.5, 0.0)

        # Tips (8, 12, 16, 20) are curled inwards toward palm/wrist
        for tip in [8, 12, 16, 20]:
            points[tip] = (0.5, 0.65, 0.0)
        # Thumb tip (4) tucked alongside palm, NOT pinched onto index tip (8)
        points[4] = (0.43, 0.72, 0.0)

        return HandLandmarks(points=points, handedness=handedness)

    def test_fist_math_detection(self):
        fist_hand = self._make_fist_hand()
        self.assertTrue(GestureMath.is_fist(fist_hand))

    def test_slight_curl_never_triggers_fist(self):
        """A relaxed or slightly curled hand MUST NOT trigger a fist."""
        fist_hand = self._make_fist_hand()
        pts = list(fist_hand.points)
        # Tips slightly further from wrist than PIP (relaxed/slight curl: d_tip ~ 1.10 * d_pip)
        # Wrist is (0.5, 0.8), PIP is (0.5, 0.5) -> d_pip = 0.30.
        # Set tips at (0.5, 0.47) -> d_tip = 0.33 = 1.10 * d_pip (> 1.02 * d_pip)
        for tip in [8, 12, 16, 20]:
            pts[tip] = (0.5, 0.47, 0.0)
        slightly_curled = HandLandmarks(points=pts, handedness="Right")
        self.assertFalse(GestureMath.is_fist(slightly_curled))

    def test_pointing_hand_never_classified_as_fist(self):
        """Pointing (index extended) must NEVER trigger a fist or window drag."""
        fist_hand = self._make_fist_hand()
        pts = list(fist_hand.points)
        # Extend index finger (tip 8 extended away from wrist 0)
        pts[8] = (0.5, 0.1, 0.0)
        pointing_hand = HandLandmarks(points=pts, handedness="Right")
        self.assertFalse(GestureMath.is_fist(pointing_hand))

    def test_orchestrator_fist_drag_lifecycle(self):
        orchestrator = SpatialOrchestrator()
        # Mock kernel window functions
        orchestrator.kernel.get_foreground_window = MagicMock(return_value=999)
        orchestrator.kernel.get_window_rect = MagicMock(return_value=(100, 100, 700, 500))
        orchestrator.kernel.move_window = MagicMock()

        fist_hand = self._make_fist_hand()

        # Frame 1: fist streak = 1 (not confirmed yet)
        res1 = orchestrator.process_spatial_frame(fist_hand, None, timestamp=1.0)
        self.assertNotEqual(res1["action_executed"], "WINDOW_DRAG_START")

        # Frame 2: fist confirmed (streak = 2) -> DRAG_START
        res2 = orchestrator.process_spatial_frame(fist_hand, None, timestamp=1.033)
        self.assertEqual(res2["action_executed"], "WINDOW_DRAG_START")
        self.assertTrue(orchestrator.dragger.is_dragging)

        # Frame 3: sustained fist -> DRAG_MOVE
        res3 = orchestrator.process_spatial_frame(fist_hand, None, timestamp=1.066)
        self.assertEqual(res3["action_executed"], "WINDOW_DRAG_MOVE")
        orchestrator.kernel.move_window.assert_called()

        # Frame 4 & 5: open hand -> DRAG_END
        points_open = [(0.5, 0.8, 0.0)] * 21
        points_open[0] = (0.5, 0.8, 0.0)
        points_open[9] = (0.5, 0.5, 0.0)
        for pip in [6, 10, 14, 18]:
            points_open[pip] = (0.5, 0.4, 0.0)
        for tip in [8, 12, 16, 20]:
            points_open[tip] = (0.5, 0.1, 0.0)  # Fully extended
        points_open[4] = (0.35, 0.45, 0.0)      # Thumb spread open away from index tip
        open_hand = HandLandmarks(points=points_open, handedness="Right")

        orchestrator.process_spatial_frame(open_hand, None, timestamp=1.1)
        res5 = orchestrator.process_spatial_frame(open_hand, None, timestamp=1.133)
        self.assertEqual(res5["action_executed"], "WINDOW_DRAG_END")
        self.assertFalse(orchestrator.dragger.is_dragging)


if __name__ == "__main__":
    unittest.main()
