"""
Unit tests for AeroTouch Predictive Kinematic Filter.
Tests forward latency compensation, dual-stage deadband, and jitter elimination.
"""

import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core.predictive_filter import PredictiveKinematicFilter


class TestPredictiveKinematicFilter(unittest.TestCase):
    def setUp(self):
        self.filter = PredictiveKinematicFilter(
            lead_time_seconds=0.040,
            slow_deadband=0.003,
            speed_threshold=0.10,
            max_extrapolation_distance=0.05
        )

    def test_first_frame_anchor(self):
        x, y = self.filter.filter_and_predict(0.5, 0.5, timestamp=1.0)
        self.assertEqual(x, 0.5)
        self.assertEqual(y, 0.5)

    def test_slow_deadband_cancels_micro_jitter(self):
        self.filter.filter_and_predict(0.5, 0.5, timestamp=1.0)

        # Micro-jitter (+0.001 within deadband 0.003 at low speed)
        x_jitter, y_jitter = self.filter.filter_and_predict(0.501, 0.5005, timestamp=1.033)
        self.assertEqual(x_jitter, 0.5)
        self.assertEqual(y_jitter, 0.5)

    def test_fast_motion_forward_prediction(self):
        # Anchor
        self.filter.filter_and_predict(0.40, 0.50, timestamp=1.0)

        # Fast stroke to 0.45 in 0.033s (speed = 1.51 > 0.10)
        pred_x, pred_y = self.filter.filter_and_predict(0.45, 0.50, timestamp=1.033)

        # Predicted x must be ahead of raw x (0.45)
        self.assertGreater(pred_x, 0.45)
        self.assertAlmostEqual(pred_y, 0.50, places=2)

    def test_extrapolation_clamped_to_max_distance(self):
        self.filter.filter_and_predict(0.10, 0.50, timestamp=1.0)

        # Extreme fast flick: from 0.10 to 0.80 in 0.010s
        pred_x, pred_y = self.filter.filter_and_predict(0.80, 0.50, timestamp=1.010)

        # Forward prediction distance cannot exceed max_extrapolation_distance (0.05)
        self.assertLessEqual(pred_x, 0.80 + 0.05 + 1e-5)
        self.assertLessEqual(pred_x, 1.0)

    def test_reset(self):
        self.filter.filter_and_predict(0.5, 0.5, timestamp=1.0)
        self.filter.reset()
        self.assertEqual(len(self.filter._history), 0)
        self.assertIsNone(self.filter._filtered_pos)


if __name__ == "__main__":
    unittest.main()
