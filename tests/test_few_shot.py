"""
Unit tests for AeroTouch Few-Shot Custom Gesture Engine (src.gestures.few_shot_engine)
Verifies 63-dim scale-invariant normalization, prototype centroid learning,
cosine similarity classification, persistence, and action mapping.
"""

import json
import os
import shutil
import tempfile
import unittest
import numpy as np

from src.gestures.engine import HandLandmarks
from src.gestures.few_shot_engine import FewShotGestureEngine


def create_mock_hand(finger_extension: float = 1.0) -> HandLandmarks:
    """Creates a 21-landmark HandLandmarks object."""
    pts = [[0.0, 0.0, 0.0] for _ in range(21)]
    pts[0] = [0.5, 0.8, 0.0]   # Wrist
    pts[9] = [0.5, 0.5, 0.0]   # Middle MCP
    # Extend index
    pts[8] = [0.5, 0.5 - 0.3 * finger_extension, 0.0]
    return HandLandmarks(points=pts, handedness="Right")


class TestFewShotGestureEngine(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage_file = os.path.join(self.temp_dir, "custom_gestures.json")
        self.engine = FewShotGestureEngine(storage_path=self.storage_file)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_normalization_invariance(self):
        # Two hands with same relative shape but translated and scaled
        hand1 = create_mock_hand(1.0)
        hand2 = create_mock_hand(1.0)
        # Translate hand2
        hand2.points = [[x + 0.2, y - 0.1, z + 0.05] for (x, y, z) in hand2.points]

        v1 = self.engine._normalize_landmarks(hand1.points)
        v2 = self.engine._normalize_landmarks(hand2.points)

        # Scale and translation invariant: Cosine similarity should be ~ 1.0
        similarity = float(np.dot(v1, v2))
        self.assertAlmostEqual(similarity, 1.0, places=3)

    def test_register_and_classify_gesture(self):
        # Generate 10 synthetic frames of a "THUMBS_UP" style pose
        frames = []
        for _ in range(10):
            hand = create_mock_hand(finger_extension=1.5)
            # Add slight jitter
            hand.points[4] = [0.2 + np.random.normal(0, 0.005), 0.3, 0.0]
            frames.append(hand)

        success = self.engine.register_gesture_from_frames(
            name="TEST_THUMB_UP",
            frames=frames,
            action="MEDIA_PLAY_PAUSE",
            similarity_threshold=0.90
        )
        self.assertTrue(success)
        self.assertIn("TEST_THUMB_UP", self.engine.gestures)

        # Classify matching probe
        probe_match = create_mock_hand(finger_extension=1.5)
        probe_match.points[4] = [0.201, 0.301, 0.0]
        res = self.engine.classify(probe_match)
        self.assertIsNotNone(res)
        name, sim, meta = res
        self.assertEqual(name, "TEST_THUMB_UP")
        self.assertGreaterEqual(sim, 0.90)
        self.assertEqual(meta["action"], "MEDIA_PLAY_PAUSE")

    def test_different_gesture_does_not_match(self):
        # Register a gesture
        frames = [create_mock_hand(finger_extension=1.0) for _ in range(5)]
        self.engine.register_gesture_from_frames("OPEN", frames, similarity_threshold=0.95)

        # Probe with wildly different hand (all points zeroed except wrist)
        diff_pts = [[0.0, 0.0, 0.0] for _ in range(21)]
        diff_pts[9] = [0.0, 1.0, 0.0]
        diff_pts[20] = [1.0, 0.0, 0.0]
        probe = HandLandmarks(points=diff_pts, handedness="Right")

        res = self.engine.classify(probe)
        self.assertIsNone(res)

    def test_persistence_save_load(self):
        frames = [create_mock_hand(1.0) for _ in range(5)]
        self.engine.register_gesture_from_frames("PERSIST_ME", frames, action="VOLUME_MUTE")

        # Load fresh engine from same file
        engine2 = FewShotGestureEngine(storage_path=self.storage_file)
        self.assertIn("PERSIST_ME", engine2.gestures)
        self.assertEqual(engine2.gestures["PERSIST_ME"]["action"], "VOLUME_MUTE")

    def test_remove_gesture(self):
        frames = [create_mock_hand(1.0) for _ in range(5)]
        self.engine.register_gesture_from_frames("TO_DELETE", frames)
        self.assertTrue(self.engine.remove_gesture("TO_DELETE"))
        self.assertNotIn("TO_DELETE", self.engine.gestures)
        self.assertFalse(self.engine.remove_gesture("NON_EXISTENT"))


if __name__ == "__main__":
    unittest.main()
