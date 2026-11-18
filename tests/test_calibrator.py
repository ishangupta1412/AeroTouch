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
        # Even with hand at 0.1 margin, it should reach full 1920 border without strain
        sx_right, _ = self.mapper.map_to_screen(0.1, 0.5)
        self.assertEqual(sx_right, 1919)

        sx_left, _ = self.mapper.map_to_screen(0.9, 0.5)
        self.assertEqual(sx_left, 0)


if __name__ == '__main__':
    unittest.main()
