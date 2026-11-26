import os
import sys
import time
import unittest
from unittest.mock import MagicMock

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.calibrator import ScreenSpaceMapper
from src.core.orchestrator import SpatialOrchestrator
from src.core.tracker import DualHandTracker
from src.gestures.engine import BimanualEngine, HandLandmarks
from src.os_bridge.ui_magnetism import UIMagnetismEngine


def _make_hand(index_tip=(0.5, 0.4, 0.0), thumb_tip=(0.35, 0.5, 0.0), middle_tip=(0.6, 0.4, 0.0)):
    pts = [(0.5, 0.7, 0.0)] * 21
    pts[0] = (0.5, 0.8, 0.0)
    pts[9] = (0.5, 0.5, 0.0)
    pts[4] = thumb_tip
    pts[8] = index_tip
    pts[12] = middle_tip
    pts[16] = (0.65, 0.45, 0.0)
    pts[20] = (0.70, 0.50, 0.0)
    return HandLandmarks(pts, "Right")


class TestPrecisionUpgrades(unittest.TestCase):
    def test_pinch_drift_stabilization_damps_approach(self):
        engine = BimanualEngine(pinch_threshold=0.32, release_threshold=0.42, confirm_frames=2, pre_pinch_threshold=0.46)
        # Scale = 0.30. Entry into pre-pinch zone (< 0.46 * 0.30 = 0.138)
        h1 = _make_hand(index_tip=(0.50, 0.40, 0.0), thumb_tip=(0.50, 0.52, 0.0))  # dist=0.12 -> norm=0.40
        s1 = engine.evaluate_right_action(h1, now=1.0)
        self.assertAlmostEqual(s1["cursor_y"], 0.40, places=4)

        # Index tip pulls down by +0.08 during pinch approach -> damped to 15% (0.40 + 0.012 = 0.412)
        h2 = _make_hand(index_tip=(0.50, 0.48, 0.0), thumb_tip=(0.50, 0.52, 0.0))  # dist=0.04 -> norm=0.133
        s2 = engine.evaluate_right_action(h2, now=1.02)
        self.assertLess(s2["cursor_y"], 0.42)

    def test_pinch_hold_drag_lifecycle(self):
        engine = BimanualEngine(pinch_threshold=0.32, release_threshold=0.42, confirm_frames=2, hold_threshold_seconds=0.20)
        pinch = _make_hand(index_tip=(0.50, 0.50, 0.0), thumb_tip=(0.50, 0.51, 0.0))
        open_h = _make_hand(index_tip=(0.50, 0.30, 0.0), thumb_tip=(0.30, 0.60, 0.0))

        # Confirm click on frame 2
        engine.evaluate_right_action(pinch, now=1.0)
        s2 = engine.evaluate_right_action(pinch, now=1.02)
        self.assertEqual(s2["click_event"], "LEFT_CLICK")
        self.assertIsNone(s2["pinch_hold_event"])

        # Hold past 0.20s -> PINCH_DOWN
        s3 = engine.evaluate_right_action(pinch, now=1.25)
        self.assertEqual(s3["pinch_hold_event"], "PINCH_DOWN")
        self.assertTrue(s3["is_pinch_holding"])

        # Release -> PINCH_UP
        s4 = engine.evaluate_right_action(open_h, now=1.30)
        self.assertEqual(s4["pinch_hold_event"], "PINCH_UP")
        self.assertFalse(s4["is_pinch_holding"])

    def test_orchestrator_dispatches_pinch_hold(self):
        orch = SpatialOrchestrator()
        orch.kernel.click = MagicMock()
        orch.kernel.mouse_down = MagicMock()
        orch.kernel.mouse_up = MagicMock()
        orch.kernel.move_cursor = MagicMock()

        pinch = _make_hand(index_tip=(0.50, 0.50, 0.0), thumb_tip=(0.50, 0.51, 0.0))
        open_h = _make_hand(index_tip=(0.50, 0.30, 0.0), thumb_tip=(0.30, 0.60, 0.0))

        orch.process_spatial_frame(pinch, None, timestamp=1.0)
        orch.process_spatial_frame(pinch, None, timestamp=1.02)
        res_hold = orch.process_spatial_frame(pinch, None, timestamp=1.30)
        self.assertEqual(res_hold["action_executed"], "MOUSE_PINCH_HOLD_START")
        orch.kernel.mouse_down.assert_called_with(left=True)

        res_rel = orch.process_spatial_frame(open_h, None, timestamp=1.35)
        self.assertEqual(res_rel["action_executed"], "MOUSE_PINCH_HOLD_END")
        orch.kernel.mouse_up.assert_called_with(left=True)

    def test_ui_magnetism_ttl_eviction(self):
        mag = UIMagnetismEngine(snap_radius=50.0, ttl_seconds=0.05, max_targets=4)
        mag.register_target("btn1", 90, 90, 110, 110)
        _, _, locked = mag.apply_magnetism(102, 102, cursor_speed=0.0)
        self.assertEqual(locked, "btn1")

        time.sleep(0.08)
        _, _, locked_after = mag.apply_magnetism(102, 102, cursor_speed=0.0)
        self.assertIsNone(locked_after)

    def test_dynamic_ergonomics_reach_adaptation(self):
        mapper = ScreenSpaceMapper(1920, 1080, margin_x=0.15, margin_y=0.18)
        initial_mx = mapper.margin_x
        for _ in range(10):
            mapper.update_ergonomics(hand_scale=0.09)  # Far from camera -> tighter box (higher margin)
        self.assertGreater(mapper.margin_x, initial_mx)

    def test_tracker_video_mode_and_hermite_driver(self):
        tracker = DualHandTracker(num_hands=2, mirrored=True)
        self.assertTrue(tracker._video_mode)
        rh, lh = tracker.process_frame(np.zeros((240, 320, 3), dtype=np.uint8))
        self.assertIsNone(rh)
        self.assertIsNone(lh)
        tracker.close()

        orch = SpatialOrchestrator()
        orch.start_hermite_driver(rate_hz=120)
        self.assertTrue(orch._hermite_running)
        orch.stop_hermite_driver()
        self.assertFalse(orch._hermite_running)


if __name__ == "__main__":
    unittest.main()
