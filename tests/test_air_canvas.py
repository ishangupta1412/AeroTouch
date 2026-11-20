"""
Unit tests for AeroTouch AirCanvas & Presentation Laser Pointer Overlay.
"""

import unittest
from src.ui.air_canvas import AirCanvasOverlay, StrokePoint


class TestAirCanvasOverlay(unittest.TestCase):
    def setUp(self):
        self.canvas = AirCanvasOverlay(fade_duration=2.0)

    def test_stroke_point_initialization(self):
        pt = StrokePoint(100, 200, color="#ff0055", width=6)
        self.assertEqual(pt.x, 100)
        self.assertEqual(pt.y, 200)
        self.assertEqual(pt.color, "#ff0055")
        self.assertEqual(pt.width, 6)

    def test_laser_mode_queue_dispatch(self):
        self.assertFalse(self.canvas.laser_enabled)
        self.canvas.set_laser(True)
        self.canvas._drain_messages()
        self.assertTrue(self.canvas.laser_enabled)

    def test_drawing_and_clear_cycle(self):
        self.canvas.set_drawing(True)
        self.canvas.update_cursor(150, 250, is_drawing_down=True)
        self.canvas.update_cursor(160, 260, is_drawing_down=True)
        self.canvas._drain_messages()
        self.assertEqual(len(self.canvas._current_stroke), 2)

        # Clear canvas
        self.canvas.clear()
        self.canvas._drain_messages()
        self.assertEqual(len(self.canvas._current_stroke), 0)
        self.assertEqual(len(self.canvas._strokes), 0)


if __name__ == "__main__":
    unittest.main()
