"""
Unit tests for AeroTouch 1000 Hz Cubic Hermite Spline Engine.
Tests C1 continuity, boundary evaluation, and sub-frame microstepping.
"""

import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core.hermite_spline import CubicHermiteSplineInterpolator


class TestCubicHermiteSpline(unittest.TestCase):
    def setUp(self):
        self.interpolator = CubicHermiteSplineInterpolator(target_rate_hz=1000)

    def test_single_waypoint_evaluation(self):
        self.interpolator.add_waypoint(0.25, 0.40, timestamp=1.0)
        x, y = self.interpolator.evaluate_at(1.0)
        self.assertEqual(x, 0.25)
        self.assertEqual(y, 0.40)

    def test_endpoint_exact_interpolation(self):
        # Two points separated by 33ms (approx 30 FPS frame)
        self.interpolator.add_waypoint(0.20, 0.30, timestamp=1.000)
        self.interpolator.add_waypoint(0.60, 0.70, timestamp=1.033)

        # At t = 1.000 (s = 0.0), evaluates to P0
        x0, y0 = self.interpolator.evaluate_at(1.000)
        self.assertAlmostEqual(x0, 0.20, places=3)
        self.assertAlmostEqual(y0, 0.30, places=3)

        # At t = 1.033 (s = 1.0), evaluates to P1
        x1, y1 = self.interpolator.evaluate_at(1.033)
        self.assertAlmostEqual(x1, 0.60, places=3)
        self.assertAlmostEqual(y1, 0.70, places=3)

    def test_intermediate_curvature_smoothness(self):
        self.interpolator.add_waypoint(0.10, 0.10, timestamp=1.000)
        self.interpolator.add_waypoint(0.30, 0.30, timestamp=1.033)
        self.interpolator.add_waypoint(0.70, 0.70, timestamp=1.066)

        # Midpoint at 1.050
        mid_x, mid_y = self.interpolator.evaluate_at(1.050)
        self.assertGreater(mid_x, 0.30)
        self.assertLess(mid_x, 0.70)
        self.assertGreater(mid_y, 0.30)
        self.assertLess(mid_y, 0.70)

    def test_generate_subframe_microsteps(self):
        self.interpolator.add_waypoint(0.20, 0.20, timestamp=1.000)
        self.interpolator.add_waypoint(0.40, 0.40, timestamp=1.033)

        steps = self.interpolator.generate_subframe_microsteps(num_steps=4)
        self.assertEqual(len(steps), 4)

        # Steps must monotonically increase towards P1
        self.assertGreater(steps[0][0], 0.20)
        self.assertGreater(steps[1][0], steps[0][0])
        self.assertGreater(steps[2][0], steps[1][0])
        self.assertAlmostEqual(steps[3][0], 0.40, places=3)

    def test_reset(self):
        self.interpolator.add_waypoint(0.20, 0.20, timestamp=1.000)
        self.interpolator.reset()
        self.assertEqual(len(self.interpolator._history), 0)


if __name__ == "__main__":
    unittest.main()
