import unittest
from unittest.mock import MagicMock
from src.os_bridge.volume_control import MediaScalarController, _clamp
from src.gestures.engine import HandLandmarks, HandMode
from src.core.orchestrator import SpatialOrchestrator


class TestMediaScalarController(unittest.TestCase):
    def setUp(self):
        self.ctrl = MediaScalarController()
        # Mock internal low-level drivers for deterministic testing
        self.ctrl.volume.set_volume = MagicMock()
        self.ctrl.brightness.set_brightness = MagicMock()

    def test_clamp_utility(self):
        self.assertEqual(_clamp(0.5, 0.0, 1.0), 0.5)
        self.assertEqual(_clamp(-0.5, 0.0, 1.0), 0.0)
        self.assertEqual(_clamp(1.5, 0.0, 1.0), 1.0)

    def test_pinch_to_scalar_mapping(self):
        # 0.0 pinch (touching) -> scalar 1.0
        self.assertAlmostEqual(self.ctrl.pinch_to_scalar(0.0), 1.0)
        # 0.6+ pinch (open) -> scalar 0.0
        self.assertAlmostEqual(self.ctrl.pinch_to_scalar(0.6), 0.0)
        self.assertAlmostEqual(self.ctrl.pinch_to_scalar(0.9), 0.0)
        # 0.3 pinch (half) -> scalar 0.5
        self.assertAlmostEqual(self.ctrl.pinch_to_scalar(0.3), 0.5)

    def test_deadband_suppresses_micro_flutter(self):
        # Initial call sets volume
        scalar1 = self.ctrl.apply_volume(0.3)  # scalar = 0.5
        self.assertIsNotNone(scalar1)
        self.ctrl.volume.set_volume.assert_called_with(0.5)

        # Tiny flutter delta (< 0.02) must be suppressed (returns None)
        scalar2 = self.ctrl.apply_volume(0.305)  # change < 0.01
        self.assertIsNone(scalar2)

        # Significant deliberate change (> 0.02) triggers update
        scalar3 = self.ctrl.apply_volume(0.2)  # scalar ~ 0.666
        self.assertIsNotNone(scalar3)

    def test_brightness_scalar_application(self):
        scalar = self.ctrl.apply_brightness(0.0)
        self.assertEqual(scalar, 1.0)
        self.ctrl.brightness.set_brightness.assert_called_with(1.0)

    def test_orchestrator_media_control_mode_integration(self):
        orchestrator = SpatialOrchestrator()
        orchestrator.media_ctrl.apply_volume = MagicMock(return_value=0.75)

        # Left hand: 2 fingers extended -> MEDIA_CONTROL mode
        points_peace = [(0.5, 0.8, 0.0)] * 21
        points_peace[0] = (0.5, 0.8, 0.0)
        points_peace[9] = (0.5, 0.5, 0.0)
        # Extend Index (8) and Middle (12)
        points_peace[8] = (0.5, 0.2, 0.0)
        points_peace[6] = (0.5, 0.5, 0.0)
        points_peace[12] = (0.6, 0.2, 0.0)
        points_peace[10] = (0.6, 0.5, 0.0)
        # Keep ring and pinky curled
        points_peace[16] = (0.7, 0.75, 0.0)
        points_peace[14] = (0.7, 0.7, 0.0)
        points_peace[20] = (0.8, 0.75, 0.0)
        points_peace[18] = (0.8, 0.7, 0.0)
        left_hand = HandLandmarks(points=points_peace, handedness="Left")

        # Right hand: open navigation
        points_right = [(0.5, 0.8, 0.0)] * 21
        right_hand = HandLandmarks(points=points_right, handedness="Right")

        res = orchestrator.process_spatial_frame(right_hand, left_hand, timestamp=1.0)
        self.assertEqual(res["mode"], "MEDIA_CONTROL")
        self.assertEqual(res["action_executed"], "VOLUME_SCALAR_75")


if __name__ == "__main__":
    unittest.main()
