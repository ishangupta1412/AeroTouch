import unittest
from src.core.calibrator import PointerBallistics


class TestPointerBallistics(unittest.TestCase):
    def setUp(self):
        self.ballistics = PointerBallistics()

    def test_first_point_initialization(self):
        x, y = self.ballistics.apply(0.5, 0.5, timestamp=1.0)
        self.assertEqual(x, 0.5)
        self.assertEqual(y, 0.5)

    def test_slow_movement_precision_mode(self):
        """Micro-movement below threshold must be geared down (< 1.0x) for sub-pixel accuracy."""
        self.ballistics.apply(0.5, 0.5, timestamp=1.0)
        # Slow delta of 0.0005 over 16ms
        x, y = self.ballistics.apply(0.5005, 0.5005, timestamp=1.016)
        # Delta from origin must be less than 0.0005 because of gearing down
        dx = x - 0.5
        self.assertLess(dx, 0.0005)
        self.assertGreater(dx, 0.0002)

    def test_fast_sweep_ballistic_acceleration(self):
        """Fast flick above threshold must scale up (> 1.0x) to cross screens effortlessly."""
        self.ballistics.apply(0.5, 0.5, timestamp=1.0)
        # Fast flick of 0.05 over 16ms
        x, y = self.ballistics.apply(0.55, 0.55, timestamp=1.016)
        dx = x - 0.5
        # Multiplier must scale past 0.05
        self.assertGreater(dx, 0.05)

    def test_boundary_clamping(self):
        """Accelerated coordinates must never exceed [0.0, 1.0] envelope."""
        self.ballistics.apply(0.9, 0.9, timestamp=1.0)
        x, y = self.ballistics.apply(1.5, 1.5, timestamp=1.016)
        self.assertLessEqual(x, 1.0)
        self.assertLessEqual(y, 1.0)

    def test_reset_clears_state(self):
        self.ballistics.apply(0.5, 0.5, timestamp=1.0)
        self.ballistics.reset()
        self.assertIsNone(self.ballistics.last_x)
        self.assertIsNone(self.ballistics.last_time)

    def test_tracking_gap_resync(self):
        """Tracking loss gap (> 0.2s) must resync instantly without velocity explosion."""
        self.ballistics.apply(0.8, 0.8, timestamp=1.0)
        # Gap of 1.5 seconds, hand reappears at (0.2, 0.2)
        x, y = self.ballistics.apply(0.2, 0.2, timestamp=2.5)
        self.assertEqual(x, 0.2)
        self.assertEqual(y, 0.2)

    def test_drift_elimination(self):
        """Dynamic anchor must eliminate pointer drift and return to hand position."""
        self.ballistics.apply(0.5, 0.5, timestamp=1.0)
        # High speed sweep
        self.ballistics.apply(0.7, 0.7, timestamp=1.016)
        # Return hand to center
        self.ballistics.apply(0.5, 0.5, timestamp=1.032)
        # Stationary for a few frames
        for t in range(25):
            x, y = self.ballistics.apply(0.5, 0.5, timestamp=1.048 + t * 0.016)
        self.assertAlmostEqual(x, 0.5, delta=0.01)
        self.assertAlmostEqual(y, 0.5, delta=0.01)


if __name__ == '__main__':
    unittest.main()
