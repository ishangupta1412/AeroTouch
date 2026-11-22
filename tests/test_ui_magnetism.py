"""
Unit tests for AeroTouch Windows UI Element Magnetism Engine.
Tests gravitational attraction basins, escape velocity gating, and sub-pixel snapping.
"""

import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.os_bridge.ui_magnetism import UIMagnetismEngine, UITargetRect


class TestUIMagnetismEngine(unittest.TestCase):
    def setUp(self):
        self.engine = UIMagnetismEngine(
            snap_radius=30.0,
            attraction_strength=0.70,
            escape_speed_threshold=0.30
        )
        # Register a mock Close Button at (100, 100) to (130, 130) -> Center is (115, 115)
        self.engine.register_target("window_close_btn", 100, 100, 130, 130)

    def test_target_rect_center_and_contains(self):
        target = UITargetRect("test_btn", 50, 50, 70, 70)
        self.assertEqual(target.center_x, 60)
        self.assertEqual(target.center_y, 60)
        self.assertTrue(target.contains(65, 65))
        self.assertFalse(target.contains(80, 80))

    def test_magnetic_attraction_during_slow_hover(self):
        # Cursor at (110, 110), near center (115, 115) at low speed (0.05 < 0.30)
        adj_x, adj_y, locked_id = self.engine.apply_magnetism(110, 110, cursor_speed=0.05)
        self.assertEqual(locked_id, "window_close_btn")
        # Deflected closer to center 115
        self.assertGreater(adj_x, 110)
        self.assertGreater(adj_y, 110)
        self.assertLessEqual(adj_x, 115)
        self.assertLessEqual(adj_y, 115)

    def test_escape_velocity_bypasses_magnetism(self):
        # Cursor at same position but moving fast (speed 0.50 >= 0.30)
        adj_x, adj_y, locked_id = self.engine.apply_magnetism(110, 110, cursor_speed=0.50)
        self.assertIsNone(locked_id)
        # No deflection
        self.assertEqual(adj_x, 110)
        self.assertEqual(adj_y, 110)

    def test_far_cursor_no_deflection(self):
        # Cursor at (300, 300), far outside snap_radius 30
        adj_x, adj_y, locked_id = self.engine.apply_magnetism(300, 300, cursor_speed=0.05)
        self.assertIsNone(locked_id)
        self.assertEqual(adj_x, 300)
        self.assertEqual(adj_y, 300)

    def test_clear_targets(self):
        self.engine.clear_targets()
        adj_x, adj_y, locked_id = self.engine.apply_magnetism(115, 115, cursor_speed=0.05)
        self.assertIsNone(locked_id)


if __name__ == "__main__":
    unittest.main()
