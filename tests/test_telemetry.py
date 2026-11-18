import os
import shutil
import tempfile
import unittest

from src.telemetry.session_logger import SessionTelemetryLogger
from src.cortex.session_analyst import SessionAnalyst


class TestTelemetryAndAnalyst(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.logger = SessionTelemetryLogger(base_dir=self.test_dir)
        self.analyst = SessionAnalyst(base_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_session_logger_lifecycle(self):
        self.logger.open()

        # Log some frames
        for i in range(10):
            action_state = {
                "pinch_distance": 0.35 - (i * 0.02),
                "middle_pinch_distance": 0.50,
                "is_pinching": (i > 5),
                "cursor_x": 0.5,
                "cursor_y": 0.5
            }
            action = "MOUSE_LEFT_CLICK" if i == 6 else None
            self.logger.log_frame(
                action_state=action_state,
                cursor_pos=(960, 540),
                mode="POINTER_NAV",
                action_executed=action
            )

        self.logger.close()

        # Verify session file was written
        self.assertTrue(os.path.exists(self.logger.session_file))
        summary = self.logger.get_session_summary()
        self.assertEqual(summary["total_frames"], 10)
        self.assertEqual(summary["left_clicks"], 1)

    def test_analyst_profile_load_save(self):
        profile = self.analyst.load_user_profile()
        self.assertEqual(profile["pinch_threshold"], 0.28)
        self.assertEqual(profile["confirm_frames"], 2)

        # Modify and save
        profile["pinch_threshold"] = 0.25
        self.analyst.save_user_profile(profile)

        reloaded = self.analyst.load_user_profile()
        self.assertEqual(reloaded["pinch_threshold"], 0.25)

    def test_analyst_extract_json(self):
        # Raw JSON string
        raw = '{"pinch_threshold": 0.25, "reasoning": "Tuned"}'
        res = self.analyst._extract_json(raw)
        self.assertIsNotNone(res)
        self.assertEqual(res["pinch_threshold"], 0.25)

        # Markdown wrapped
        wrapped = 'Here is the result:\n```json\n{"min_cutoff": 0.04}\n```\nDone.'
        res2 = self.analyst._extract_json(wrapped)
        self.assertIsNotNone(res2)
        self.assertEqual(res2["min_cutoff"], 0.04)

    def test_analyst_apply_recommendations_clamping(self):
        profile = self.analyst.load_user_profile()
        # Out-of-bounds recommendation
        recs = {
            "pinch_threshold": 0.99,  # Should clamp to 0.40
            "deadband": 0.0001,       # Should clamp to 0.001
            "confirm_frames": 5       # Should clamp to 4
        }
        updated = self.analyst._apply_recommendations(profile, recs)
        self.assertEqual(updated["pinch_threshold"], 0.40)
        self.assertEqual(updated["deadband"], 0.001)
        self.assertEqual(updated["confirm_frames"], 4)
        self.assertEqual(updated["sessions_analyzed"], 1)


if __name__ == '__main__':
    unittest.main()
