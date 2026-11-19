import unittest
from src.core.calibrator import ScreenSpaceMapper


class TestScreenSpaceMapper(unittest.TestCase):
    def setUp(self):
        self.mapper = ScreenSpaceMapper(screen_width=1920, screen_height=1080)

    def test_center_mapping(self):
        sx, sy = self.mapper.map_to_screen(0.5, 0.5)
        # Center should map roughly to 960, 540
        self.assertAlmostEqual(sx, 959, delta=5)
        self.assertAlmostEqual(sy, 539, delta=5)

    def test_corner_reachability(self):
        # In natural mirrored mode (flip_x=False):
        # Hand at 0.9 reaches right border 1919 without strain
        sx_right, _ = self.mapper.map_to_screen(0.9, 0.5)
        self.assertEqual(sx_right, 1919)

        # Hand at 0.1 reaches left border 0 without strain
        sx_left, _ = self.mapper.map_to_screen(0.1, 0.5)
        self.assertEqual(sx_left, 0)


if __name__ == '__main__':
    unittest.main()
