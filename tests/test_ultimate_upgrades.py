import os
import sys
import time
import unittest
from unittest.mock import MagicMock

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.async_capture import AsyncCameraCapture
from src.core.calibrator import ScreenSpaceMapper
from src.core.engagement import TrackingParadigm
from src.core.gaze_tracker import GazeHybridTracker
from src.core.kalman_filter import ConstantAccelerationKalman2D
from src.core.orchestrator import SpatialOrchestrator
from src.gestures.engine import HandLandmarks
from src.service.voice_intent import VoiceIntentService
from src.ui.cursor_halo import CursorHaloOverlay


class _DummyCap:
    def __init__(self):
        self.i = 0

    def read(self):
        self.i += 1
        time.sleep(0.002)
        return True, np.full((64, 64, 3), self.i % 255, dtype=np.uint8)


class TestUltimateUpgrades(unittest.TestCase):
    def test_async_camera_capture(self):
        cap = AsyncCameraCapture(_DummyCap())
        cap.start()
        ok, frame, ts = cap.read_latest(timeout=0.3)
        cap.stop()
        self.assertTrue(ok)
        self.assertIsNotNone(frame)
        self.assertGreater(ts, 0.0)

    def test_kalman_constant_acceleration_2d(self):
        kf = ConstantAccelerationKalman2D()
        t = 1.0
        px, py = 0.0, 0.0
        for step in range(10):
            t += 0.016
            px, py = kf.update(0.1 + step * 0.05, 0.2 + step * 0.03, timestamp=t)
        self.assertGreater(px, 0.50)
        self.assertGreater(py, 0.40)
        kf.reset()
        self.assertIsNone(kf._last_ts)

    def test_multi_monitor_virtual_mapper(self):
        mapper = ScreenSpaceMapper(3840, 1080, margin_x=0.0, margin_y=0.0, origin_x=-1920, origin_y=0)
        sx, sy = mapper.map_to_screen(0.0, 0.5)
        self.assertEqual(sx, -1920)
        sx2, _ = mapper.map_to_screen(1.0, 0.5)
        self.assertEqual(sx2, 1919)

    def test_orchestrator_paradigm_toggle_and_ml_telemetry(self):
        orch = SpatialOrchestrator()
        orch.kernel.move_cursor = MagicMock()
        self.assertEqual(orch.engagement_engine.current_paradigm, TrackingParadigm.ABSOLUTE_LASER)
        new_p = orch.toggle_tracking_paradigm()
        self.assertEqual(new_p, TrackingParadigm.RELATIVE_CLUTCHED)
        self.assertTrue(orch.use_engagement_gating)

        # Toggle back to Absolute
        orch.toggle_tracking_paradigm()
        pts = [(0.5, 0.7, 0.0)] * 21
        pts[0] = (0.5, 0.8, 0.0)
        pts[9] = (0.5, 0.5, 0.0)
        pts[8] = (0.5, 0.2, 0.0)
        rh = HandLandmarks(pts, "Right")
        res = orch.process_spatial_frame(rh, None, timestamp=1.0)
        self.assertIn("ml_gesture", res)
        self.assertIn("ml_confidence", res)

    def test_gaze_hybrid_coarse_blend(self):
        gaze = GazeHybridTracker(enabled=False)
        gaze.last_gaze_norm = (0.90, 0.85)
        # Close hand -> no coarse jump
        hx, hy = gaze.blend_with_hand(0.88, 0.84, jump_threshold=0.30)
        self.assertAlmostEqual(hx, 0.88)
        # Far hand -> coarse warp toward gaze
        bx, by = gaze.blend_with_hand(0.10, 0.15, gaze_weight=0.25, jump_threshold=0.30)
        self.assertGreater(bx, 0.25)
        self.assertGreater(by, 0.30)

    def test_cursor_halo_overlay_lifecycle(self):
        halo = CursorHaloOverlay()
        halo.start()
        time.sleep(0.15)
        halo.update_pointer(400, 300, locked=True, pinching=False)
        halo.update_pointer(410, 310, locked=False, pinching=True)
        time.sleep(0.1)
        halo.stop()
        self.assertFalse(halo.running)

    def test_voice_intent_whisper_transcription_hook(self):
        vi = VoiceIntentService()
        vi._whisper_checked = True
        seg = MagicMock()
        seg.text = "copy"
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([seg], None)
        vi._whisper_model = mock_model

        audio = MagicMock()
        audio.get_raw_data.return_value = b"\x00\x00" * 1600
        self.assertEqual(vi._transcribe_audio(audio), "copy")


if __name__ == "__main__":
    unittest.main()
