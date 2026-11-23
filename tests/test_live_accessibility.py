"""
Unit tests for AeroTouch Live Native Win32 Accessibility Inspector.
Tests element hit-testing, bounding box extraction, and container filtering.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.os_bridge.live_accessibility import LiveUIAccessibilityInspector


class TestLiveAccessibility(unittest.TestCase):
    def setUp(self):
        self.inspector = LiveUIAccessibilityInspector(
            max_target_width=300,
            max_target_height=100
        )

    def test_interactive_button_extracted(self):
        mock_user32 = MagicMock()
        mock_user32.WindowFromPoint.return_value = 12345
        self.inspector._user32 = mock_user32

        # Mock _get_window_rect returning a button-sized rectangle (80x36)
        self.inspector._get_window_rect = MagicMock(return_value=(200, 200, 280, 236))

        res = self.inspector.get_element_rect_at_point(220, 210)
        self.assertIsNotNone(res)
        target_id, left, top, right, bottom = res
        self.assertEqual(target_id, "win32_ctrl_12345")
        self.assertEqual(left, 200)
        self.assertEqual(top, 200)
        self.assertEqual(right, 280)
        self.assertEqual(bottom, 236)

    def test_giant_fullscreen_window_rejected(self):
        mock_user32 = MagicMock()
        mock_user32.WindowFromPoint.return_value = 99999
        self.inspector._user32 = mock_user32

        # Mock full desktop 1920x1080
        self.inspector._get_window_rect = MagicMock(return_value=(0, 0, 1920, 1080))

        # Giant window exceeds max_target_width 300
        res = self.inspector.get_element_rect_at_point(500, 500)
        self.assertIsNone(res)

    def test_no_hwnd_returns_none(self):
        mock_user32 = MagicMock()
        mock_user32.WindowFromPoint.return_value = 0
        self.inspector._user32 = mock_user32

        res = self.inspector.get_element_rect_at_point(10, 10)
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
