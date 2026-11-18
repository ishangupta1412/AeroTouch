import math
import time
import unittest
from src.core.one_euro_filter import OneEuroFilter, SpatialPointFilter2D


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


if __name__ == '__main__':
    unittest.main()
