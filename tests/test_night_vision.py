"""
Unit tests for AeroTouch Adaptive Night Vision CLAHE Pre-Processor.
Tests low-light detection, LAB contrast equalization, and daylight bypass.
"""

import os
import sys
import unittest
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core.night_vision import AdaptiveNightVisionEnhancer


class TestNightVision(unittest.TestCase):
    def setUp(self):
        self.enhancer = AdaptiveNightVisionEnhancer(low_light_threshold=80.0)

    def test_daylight_frame_bypassed(self):
        # Bright frame (mean ~150)
        bright_frame = np.full((240, 320, 3), 150, dtype=np.uint8)
        out_frame, is_active = self.enhancer.enhance(bright_frame)
        self.assertFalse(is_active)
        self.assertEqual(out_frame.shape, bright_frame.shape)

    def test_dark_frame_clahe_activated(self):
        # Dark frame (mean ~35) with gradient
        dark_frame = np.random.randint(20, 50, size=(240, 320, 3), dtype=np.uint8)
        out_frame, is_active = self.enhancer.enhance(dark_frame)
        self.assertTrue(is_active)
        self.assertEqual(out_frame.shape, dark_frame.shape)
        self.assertEqual(out_frame.dtype, np.uint8)

    def test_none_frame_safe_fallback(self):
        out, is_active = self.enhancer.enhance(None)
        self.assertIsNone(out)
        self.assertFalse(is_active)


if __name__ == "__main__":
    unittest.main()
