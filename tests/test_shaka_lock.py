import unittest
from unittest.mock import MagicMock
from src.gestures.engine import HandLandmarks, GestureMath
from src.core.orchestrator import SpatialOrchestrator


class TestShakaGestureLock(unittest.TestCase):
    def _make_shaka_hand(self, handedness="Right"):
        """
        Constructs an accurate 🤙 Shaka hand:
        Wrist at (0.5, 0.8, 0.0)
        Thumb MCP at (0.45, 0.75, 0.0), Thumb Tip extended to (0.30, 0.60, 0.0)
        Pinky PIP at (0.60, 0.65, 0.0), Pinky Tip extended to (0.75, 0.50, 0.0)
        Index, Middle, Ring curled down (tip closer to wrist than PIP)
        """
        points = [(0.5, 0.8, 0.0)] * 21
        points[0] = (0.5, 0.8, 0.0)      # Wrist
        points[9] = (0.5, 0.5, 0.0)      # Middle MCP (Palm scale)
        points[2] = (0.45, 0.75, 0.0)    # Thumb MCP
        points[17] = (0.55, 0.65, 0.0)   # Pinky base

        # Thumb extended outward
        points[4] = (0.30, 0.55, 0.0)

        # Pinky extended outward
        points[18] = (0.58, 0.65, 0.0)
        points[20] = (0.70, 0.50, 0.0)

        # Index (8, 6), Middle (12, 10), Ring (16, 14) Curled
        for pip, tip in [(6, 8), (10, 12), (14, 16)]:
            points[pip] = (0.50, 0.55, 0.0)   # PIP forward
            points[tip] = (0.50, 0.70, 0.0)   # Tip curled inward toward wrist

        return HandLandmarks(points=points, handedness=handedness)

    def _make_open_hand(self, handedness="Right"):
        points = [(0.5, 0.8, 0.0)] * 21
        points[0] = (0.5, 0.8, 0.0)
        points[9] = (0.5, 0.5, 0.0)
        for pip in [6, 10, 14, 18]:
            points[pip] = (0.5, 0.45, 0.0)
        for tip in [4, 8, 12, 16, 20]:
            points[tip] = (0.5, 0.15, 0.0)
        return HandLandmarks(points=points, handedness=handedness)

    def test_shaka_math_geometry(self):
        shaka_hand = self._make_shaka_hand()
        self.assertTrue(GestureMath.is_shaka(shaka_hand), "Accurate Shaka hand must return True")

        open_hand = self._make_open_hand()
        self.assertFalse(GestureMath.is_shaka(open_hand), "Open hand must NOT be recognized as Shaka")

    def test_orchestrator_lock_toggle_lifecycle(self):
        orchestrator = SpatialOrchestrator()
        orchestrator.shaka_required_frames = 5   # Short streak for fast test execution
        orchestrator.lock_cooldown = 0.2
        orchestrator.kernel.move_cursor = MagicMock()
        orchestrator.kernel.click = MagicMock()

        shaka_hand = self._make_shaka_hand()
        open_hand = self._make_open_hand()

        self.assertFalse(orchestrator.is_locked)

        # Frames 1 to 4: Streak builds
        for i in range(1, 5):
            res = orchestrator.process_spatial_frame(shaka_hand, None, timestamp=1.0 + i * 0.016)
            self.assertFalse(orchestrator.is_locked)
            self.assertGreater(res["lock_progress"], 0.0)

        # Frame 5: Hits required frames -> System Locks!
        res_locked = orchestrator.process_spatial_frame(shaka_hand, None, timestamp=1.1)
        self.assertTrue(orchestrator.is_locked)
        self.assertEqual(res_locked["system_state"], "LOCKED")
        self.assertEqual(res_locked["action_executed"], "AEROTOUCH_LOCKED")

        # Now system is locked: Reset mocks to verify no further OS calls occur
        orchestrator.kernel.move_cursor.reset_mock()
        orchestrator.kernel.click.reset_mock()

        # Move hand to trigger click while locked
        pinch_hand = HandLandmarks(points=[(0.5, 0.8, 0.0)] * 21, handedness="Right")
        pinch_hand.points[4] = (0.5, 0.3, 0.0)
        pinch_hand.points[8] = (0.5, 0.3, 0.0)

        res_blocked = orchestrator.process_spatial_frame(pinch_hand, None, timestamp=1.15)
        self.assertEqual(res_blocked["system_state"], "LOCKED")
        self.assertIsNone(res_blocked["cursor_pos"])
        # Hardware mouse must be frozen completely
        orchestrator.kernel.move_cursor.assert_not_called()
        orchestrator.kernel.click.assert_not_called()

        # Hold Shaka again after cooldown (0.2s) to UNLOCK
        t_base = 2.0
        for i in range(1, 5):
            orchestrator.process_spatial_frame(shaka_hand, None, timestamp=t_base + i * 0.016)
            self.assertTrue(orchestrator.is_locked)

        # 5th frame: Unlocks!
        res_unlocked = orchestrator.process_spatial_frame(shaka_hand, None, timestamp=t_base + 0.1)
        self.assertFalse(orchestrator.is_locked)
        self.assertEqual(res_unlocked["system_state"], "ACTIVE")
        self.assertEqual(res_unlocked["action_executed"], "AEROTOUCH_UNLOCKED")


if __name__ == "__main__":
    unittest.main()
