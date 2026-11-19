import json
import os
import shutil
import tempfile
import unittest
import numpy as np

from src.ui.hud import GestureRecorder, SpatialHUD
from src.gestures.engine import HandLandmarks


class TestSpatialHUDAndRecorder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.recorder = GestureRecorder(output_dir=self.temp_dir)
        self.hud = SpatialHUD()
        self.hud.recorder = self.recorder

    def tearDown(self):
        if self.recorder.is_recording:
            self.recorder.stop_recording()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_dummy_hand(self, handedness="Right"):
        points = [(0.5, 0.5, 0.0)] * 21
        return HandLandmarks(points=points, handedness=handedness)

    def test_recorder_lifecycle(self):
        self.assertFalse(self.recorder.is_recording)

        # Start recording
        filepath = self.recorder.start_recording("fist_grab")
        self.assertTrue(self.recorder.is_recording)
        self.assertTrue(os.path.exists(filepath))

        # Record 3 frames
        hand_r = self._make_dummy_hand("Right")
        hand_l = self._make_dummy_hand("Left")
        for i in range(3):
            self.recorder.record_frame(hand_r, hand_l, {"is_pinching": False})

        self.assertEqual(self.recorder.recorded_frames, 3)

        # Stop recording
        saved_file = self.recorder.stop_recording()
        self.assertFalse(self.recorder.is_recording)
        self.assertEqual(saved_file, filepath)

        # Verify content on disk
        with open(saved_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 3)
        entry = json.loads(lines[0])
        self.assertEqual(entry["frame"], 1)
        self.assertEqual(len(entry["right_hand"]), 21)
        self.assertEqual(len(entry["left_hand"]), 21)

    def test_hud_rendering_pipeline(self):
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        hand_r = self._make_dummy_hand("Right")
        hand_l = self._make_dummy_hand("Left")
        result = {
            "mode": "POINTER_NAV",
            "action_executed": None,
            "action_state": {"pinch_distance": 0.35, "is_pinching": False, "is_fist": False}
        }

        # Render with both hands
        out_frame = self.hud.render_hud(dummy_frame.copy(), hand_r, hand_l, result, fps=59.5)
        self.assertEqual(out_frame.shape, dummy_frame.shape)

        # Render with no hands
        out_none = self.hud.render_hud(dummy_frame.copy(), None, None, result, fps=60.0)
        self.assertEqual(out_none.shape, dummy_frame.shape)


if __name__ == "__main__":
    unittest.main()
