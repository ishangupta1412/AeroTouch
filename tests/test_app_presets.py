"""
Unit tests for AeroTouch Dynamic Foreground Application Presets Engine.
Tests process classification, window title heuristics, and preset parameter dispatch.
"""

import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core.app_presets import AppPresetEngine, AppCategory


class TestAppPresetEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AppPresetEngine()

    def test_classify_known_executables(self):
        self.assertEqual(self.engine.classify_process("C:\\Program Files\\Google\\Chrome\\chrome.exe"), AppCategory.BROWSER)
        self.assertEqual(self.engine.classify_process("C:\\Users\\User\\AppData\\Local\\Figma\\figma.exe"), AppCategory.CREATIVE)
        self.assertEqual(self.engine.classify_process("code.exe"), AppCategory.CODING)
        self.assertEqual(self.engine.classify_process("spotify.exe"), AppCategory.MEDIA)

    def test_classify_window_titles(self):
        self.assertEqual(self.engine.classify_process("YouTube - Google Chrome"), AppCategory.MEDIA)
        self.assertEqual(self.engine.classify_process("AeroTouch - Visual Studio Code"), AppCategory.CODING)
        self.assertEqual(self.engine.classify_process("Modern Dashboard - Figma"), AppCategory.CREATIVE)
        self.assertEqual(self.engine.classify_process("GitHub: Let's build from here - Brave"), AppCategory.BROWSER)

    def test_unknown_process_defaults_to_general(self):
        self.assertEqual(self.engine.classify_process("notepad.exe"), AppCategory.GENERAL)
        self.assertEqual(self.engine.classify_process("calculator.exe"), AppCategory.GENERAL)

    def test_update_and_get_preset(self):
        preset = self.engine.update_from_process("figma.exe")
        self.assertEqual(preset.category, AppCategory.CREATIVE)
        self.assertTrue(preset.enable_canvas_pan)
        self.assertEqual(self.engine.get_active_preset().name, "Creative Canvas")

        # Switch to Chrome
        browser_preset = self.engine.update_from_process("msedge.exe")
        self.assertEqual(browser_preset.category, AppCategory.BROWSER)
        self.assertTrue(browser_preset.enable_tab_flipping)


if __name__ == "__main__":
    unittest.main()
