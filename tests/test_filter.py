import math
import time
import unittest
from src.core.one_euro_filter import OneEuroFilter, PrecisionSpatialFilter2D, SpatialPointFilter2D


class TestOneEuroFilter(unittest.TestCase):
    def test_one_euro_filter_initialization(self):
        f = OneEuroFilter(min_cutoff=1.0, beta=0.01)
        self.assertEqual(f.min_cutoff, 1.0)
        self.assertEqual(f.beta, 0.01)

    def test_one_euro_filter_tremor_damping(self):
        """Verify low-amplitude high-frequency tremor is heavily damped."""
        filter_1e = OneEuroFilter(min_cutoff=0.5, beta=0.001)
        base_val = 100.0

        filtered_outputs = []
        t0 = time.time()
        for i in range(40):
            noise = 2.5 * math.sin(i * 1.8)
            raw_val = base_val + noise
            out = filter_1e.filter(raw_val, timestamp=t0 + i * (1.0 / 60.0))
            filtered_outputs.append(out)

        # Variance of filtered outputs should be well damped
        recent_variance = max(filtered_outputs[20:]) - min(filtered_outputs[20:])
        self.assertLess(recent_variance, 2.0)

    def test_spatial_point_filter_2d(self):
        filter_2d = SpatialPointFilter2D()
        x, y = filter_2d.filter(500.0, 300.0)
        self.assertIsInstance(x, float)
        self.assertIsInstance(y, float)

    def test_precision_filter_deadband_suppression(self):
        """Verify that micro-movements below deadband threshold are 100% frozen."""
        p_filter = PrecisionSpatialFilter2D(deadband=0.005)

        # Initial point
        x0, y0 = p_filter.filter(0.5000, 0.5000, timestamp=1.0)

        # Micro-tremor < deadband
        x1, y1 = p_filter.filter(0.5020, 0.5015, timestamp=1.016)
        self.assertEqual(x1, x0, "Micro-tremor below deadband MUST not move cursor")
        self.assertEqual(y1, y0, "Micro-tremor below deadband MUST not move cursor")

        # Intentional sweep > deadband
        x2, y2 = p_filter.filter(0.5500, 0.5500, timestamp=1.032)
        self.assertNotEqual(x2, x0, "Deliberate movement MUST break through deadband")


if __name__ == '__main__':
    unittest.main()
