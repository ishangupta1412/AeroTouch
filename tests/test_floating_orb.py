import unittest
import time
from src.ui.floating_orb import FloatingOrbOverlay


class TestFloatingOrb(unittest.TestCase):
    def test_orb_state_machine(self):
        orb = FloatingOrbOverlay(size=80)
        self.assertFalse(orb.running)
        self.assertFalse(orb.is_tracking)

        orb.set_state(is_tracking=True)
        self.assertTrue(orb.is_tracking)

        orb.set_state(is_tracking=True, action="LEFT_CLICK")
        self.assertEqual(orb.last_action, "LEFT_CLICK")


if __name__ == '__main__':
    unittest.main()
