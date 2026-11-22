"""
Unit tests for AeroTouch Spatial Audio Haptics Engine.
Tests in-memory PCM waveform synthesis, buffer headers, and non-blocking triggering.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.service.audio_haptics import AudioHapticsEngine, HapticCue


class TestAudioHapticsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AudioHapticsEngine(enabled=True, volume=0.8)

    def test_all_cues_synthesized(self):
        for cue in HapticCue:
            self.assertIn(cue, self.engine._sound_buffers)
            buf = self.engine._sound_buffers[cue]
            self.assertIsInstance(buf, bytes)
            self.assertGreater(len(buf), 100)
            # Verify RIFF/WAVE header
            self.assertTrue(buf.startswith(b'RIFF'))
            self.assertIn(b'WAVE', buf[:16])

    @patch("winsound.PlaySound")
    def test_trigger_plays_asynchronously(self, mock_play):
        success = self.engine.trigger(HapticCue.MECHANICAL_CLICK)
        self.assertTrue(success)
        mock_play.assert_called_once()
        args, kwargs = mock_play.call_args
        # First arg is bytes buffer
        self.assertTrue(args[0].startswith(b'RIFF'))

    @patch("winsound.PlaySound")
    def test_disabled_engine_does_not_play(self, mock_play):
        self.engine.enabled = False
        success = self.engine.trigger(HapticCue.GLASS_RELEASE)
        self.assertFalse(success)
        mock_play.assert_not_called()


if __name__ == "__main__":
    unittest.main()
