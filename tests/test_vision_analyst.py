"""
Unit tests for AeroTouch Rolling Vision Intelligence Pipeline.
Tests run entirely via mocks — no actual screenshot, Moondream inference,
or Ollama network call is required. 100% offline / CI-safe.
"""
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.cortex.vision_analyst import (
    RollingVisionAnalyst,
    MoondreamWrapper,
    VisionMemory,
    MEMORY_MAX_EXAMPLES,
    _get_foreground_window_title,
)


# ─────────────────────────────────────────────────────────────────────────────
# MoondreamWrapper Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMoondreamWrapperFallback(unittest.TestCase):
    """Tests the Win32-title fallback path that runs when Moondream is unavailable."""

    def test_fallback_context_structure(self):
        """Fallback context must contain all required keys."""
        wrapper = MoondreamWrapper()
        ctx = wrapper._fallback_context("/nonexistent/frame.png")
        self.assertIn("app_type", ctx)
        self.assertIn("ui_density", ctx)
        self.assertIn("precision_demand", ctx)
        self.assertIn("timestamp", ctx)

    def test_fallback_context_values_are_strings(self):
        """All tag values must be non-empty strings."""
        wrapper = MoondreamWrapper()
        ctx = wrapper._fallback_context("/nonexistent/frame.png")
        self.assertIsInstance(ctx["app_type"], str)
        self.assertIsInstance(ctx["ui_density"], str)
        self.assertIsInstance(ctx["precision_demand"], str)

    def test_parse_answers_code_editor(self):
        """Code-editor keywords → app_type='code_editor', precision='high'."""
        wrapper = MoondreamWrapper()
        answers = {
            "What type of app": "Visual Studio Code editor",
            "UI controls large": "small and dense interface",
            "User doing": "writing code",
            "Precision needed": "fine precise cursor control",
        }
        ctx = wrapper._parse_answers(answers)
        self.assertEqual(ctx["app_type"], "code_editor")
        self.assertEqual(ctx["precision_demand"], "high")

    def test_parse_answers_video(self):
        """Video keywords → app_type='video', precision='low'."""
        wrapper = MoondreamWrapper()
        answers = {
            "What type of app": "YouTube video player",
            "UI controls large": "large spacious controls",
            "User doing": "watching video",
            "Precision needed": "coarse navigation",
        }
        ctx = wrapper._parse_answers(answers)
        self.assertEqual(ctx["app_type"], "video")
        self.assertEqual(ctx["precision_demand"], "low")

    def test_parse_answers_browser(self):
        """Browser keywords → app_type='web_browser'."""
        wrapper = MoondreamWrapper()
        answers = {
            "What type of app": "Google Chrome browser",
            "UI controls large": "medium sized buttons",
            "User doing": "browsing the web",
            "Precision needed": "normal clicking",
        }
        ctx = wrapper._parse_answers(answers)
        self.assertEqual(ctx["app_type"], "web_browser")

    def test_parse_answers_image_editor(self):
        """Photoshop keywords → app_type='image_editor', precision='high'."""
        wrapper = MoondreamWrapper()
        answers = {
            "What type of app": "Adobe Photoshop",
            "UI controls large": "tiny dense toolbox",
            "User doing": "image editing",
            "Precision needed": "very precise",
        }
        ctx = wrapper._parse_answers(answers)
        self.assertEqual(ctx["app_type"], "image_editor")
        self.assertEqual(ctx["precision_demand"], "high")

    def test_ui_density_high_bumps_low_precision(self):
        """Dense UI should bump video's 'low' precision to 'medium'."""
        wrapper = MoondreamWrapper()
        answers = {
            "What type of app": "video player",
            "UI controls large": "small crowded controls",
            "User doing": "watching",
            "Precision needed": "some control",
        }
        ctx = wrapper._parse_answers(answers)
        # Dense UI on a video player → precision should not be 'low'
        self.assertNotEqual(ctx["precision_demand"], "low")


# ─────────────────────────────────────────────────────────────────────────────
# VisionMemory Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestVisionMemory(unittest.TestCase):
    """Tests the few-shot memory JSONL store."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.memory_file = os.path.join(self.temp_dir, "vision_memory.jsonl")
        self.memory = VisionMemory(path=self.memory_file)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_append_and_retrieve_single(self):
        """Appending one entry must be retrievable."""
        summary = {"dominant_app": "code_editor", "dominant_precision": "high"}
        recs = {"deadband": 0.004, "reasoning": "High precision mode"}
        self.memory.append(summary, recs)
        examples = self.memory.get_examples(n=5)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]["recommendations"]["deadband"], 0.004)

    def test_append_multiple_preserves_order(self):
        """Most recent entry must be last in get_examples."""
        for i in range(5):
            self.memory.append({"i": i}, {"deadband": 0.001 * (i + 1)})
        examples = self.memory.get_examples(n=10)
        self.assertEqual(len(examples), 5)
        self.assertAlmostEqual(examples[-1]["recommendations"]["deadband"], 0.005)

    def test_trim_to_max(self):
        """Memory must never exceed MEMORY_MAX_EXAMPLES entries."""
        for i in range(MEMORY_MAX_EXAMPLES + 5):
            self.memory.append({"i": i}, {"deadband": 0.003})
        examples = self.memory.get_examples(n=10000)
        self.assertLessEqual(len(examples), MEMORY_MAX_EXAMPLES)

    def test_get_examples_empty_file(self):
        """get_examples on a non-existent file returns an empty list."""
        fresh_memory = VisionMemory(path=os.path.join(self.temp_dir, "nonexistent.jsonl"))
        examples = fresh_memory.get_examples(n=5)
        self.assertEqual(examples, [])

    def test_get_examples_respects_n_limit(self):
        """get_examples(n=2) returns at most 2 entries even if more are stored."""
        for i in range(10):
            self.memory.append({"i": i}, {"deadband": 0.003})
        examples = self.memory.get_examples(n=2)
        self.assertLessEqual(len(examples), 2)


# ─────────────────────────────────────────────────────────────────────────────
# RollingVisionAnalyst._summarize_batch Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRollingVisionAnalystBatchSummary(unittest.TestCase):
    """Tests the batch aggregation logic without any real vision model or network."""

    def _make_analyst(self):
        """Create a RollingVisionAnalyst bypassing __init__ for pure unit tests."""
        analyst = RollingVisionAnalyst.__new__(RollingVisionAnalyst)
        analyst._buffer_lock = threading.Lock()
        return analyst

    def test_summarize_batch_dominant_app(self):
        """Dominant app is the most frequently observed app type."""
        analyst = self._make_analyst()
        batch = [
            {"app_type": "code_editor", "ui_density": "high", "precision_demand": "high", "timestamp": 1000.0},
            {"app_type": "code_editor", "ui_density": "high", "precision_demand": "high", "timestamp": 1004.0},
            {"app_type": "web_browser", "ui_density": "medium", "precision_demand": "medium", "timestamp": 1008.0},
        ]
        summary = analyst._summarize_batch(batch)
        self.assertEqual(summary["dominant_app"], "code_editor")
        self.assertEqual(summary["dominant_precision"], "high")
        self.assertEqual(summary["batch_size"], 3)

    def test_summarize_batch_duration(self):
        """Duration should be max_ts - min_ts of the batch."""
        analyst = self._make_analyst()
        batch = [
            {"app_type": "general", "ui_density": "medium", "precision_demand": "medium", "timestamp": 1000.0},
            {"app_type": "general", "ui_density": "medium", "precision_demand": "medium", "timestamp": 1040.0},
        ]
        summary = analyst._summarize_batch(batch)
        self.assertAlmostEqual(summary["duration_seconds"], 40.0, places=0)

    def test_summarize_batch_app_distribution(self):
        """app_distribution must include counts for each observed app type."""
        analyst = self._make_analyst()
        batch = [
            {"app_type": "code_editor", "ui_density": "high", "precision_demand": "high", "timestamp": 1.0},
            {"app_type": "web_browser", "ui_density": "medium", "precision_demand": "medium", "timestamp": 2.0},
            {"app_type": "web_browser", "ui_density": "medium", "precision_demand": "medium", "timestamp": 3.0},
        ]
        summary = analyst._summarize_batch(batch)
        self.assertEqual(summary["app_distribution"]["web_browser"], 2)
        self.assertEqual(summary["app_distribution"]["code_editor"], 1)


# ─────────────────────────────────────────────────────────────────────────────
# RollingVisionAnalyst._flush_batch Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRollingVisionAnalystFlush(unittest.TestCase):
    """Tests buffer flush with mocked Qwen and VisionMemory."""

    def _make_analyst_with_callback(self, callback, batch_size=3):
        analyst = RollingVisionAnalyst(
            on_params_updated=callback,
            batch_size=batch_size,
        )
        # Replace real dependencies with mocks
        analyst.memory = MagicMock()
        analyst.memory.get_examples.return_value = []
        analyst._call_qwen = MagicMock(return_value={
            "deadband": 0.004,
            "ballistics_precision_gain": 0.42,
            "reasoning": "Code editor detected — high precision mode.",
        })
        return analyst

    def test_buffer_flushes_and_clears(self):
        """After flush, buffer must be empty regardless of outcome."""
        callback = MagicMock()
        analyst = self._make_analyst_with_callback(callback, batch_size=3)

        with analyst._buffer_lock:
            analyst._buffer = [
                {"app_type": "code_editor", "ui_density": "high",
                 "precision_demand": "high", "timestamp": float(i)}
                for i in range(3)
            ]

        analyst._flush_batch()

        with analyst._buffer_lock:
            self.assertEqual(len(analyst._buffer), 0)

    def test_flush_calls_on_params_updated(self):
        """Flush must invoke the on_params_updated callback exactly once."""
        callback = MagicMock()
        analyst = self._make_analyst_with_callback(callback, batch_size=3)

        with analyst._buffer_lock:
            analyst._buffer = [
                {"app_type": "code_editor", "ui_density": "high",
                 "precision_demand": "high", "timestamp": float(i)}
                for i in range(3)
            ]

        analyst._flush_batch()
        callback.assert_called_once()

    def test_flush_increments_batches_processed(self):
        """batches_processed counter must increment after a successful flush."""
        callback = MagicMock()
        analyst = self._make_analyst_with_callback(callback, batch_size=2)

        with analyst._buffer_lock:
            analyst._buffer = [
                {"app_type": "general", "ui_density": "medium",
                 "precision_demand": "medium", "timestamp": float(i)}
                for i in range(2)
            ]

        analyst._flush_batch()
        self.assertEqual(analyst._batches_processed, 1)

    def test_flush_empty_buffer_is_noop(self):
        """Flushing an empty buffer must not raise or call callback."""
        callback = MagicMock()
        analyst = self._make_analyst_with_callback(callback)
        analyst._flush_batch()
        callback.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# RollingVisionAnalyst._parse_qwen_json Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestParseQwenJson(unittest.TestCase):
    """Tests robust JSON extraction from Qwen raw text responses."""

    def setUp(self):
        self.analyst = RollingVisionAnalyst.__new__(RollingVisionAnalyst)

    def test_parse_clean_json(self):
        text = '{"deadband": 0.004, "reasoning": "High precision mode"}'
        result = self.analyst._parse_qwen_json(text)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["deadband"], 0.004)

    def test_parse_markdown_json_block(self):
        text = '```json\n{"deadband": 0.003, "ballistics_precision_gain": 0.4}\n```'
        result = self.analyst._parse_qwen_json(text)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["deadband"], 0.003)

    def test_parse_json_embedded_in_prose(self):
        text = 'Based on the analysis: {"deadband": 0.005} — this should work.'
        result = self.analyst._parse_qwen_json(text)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["deadband"], 0.005)

    def test_parse_returns_none_for_garbage(self):
        text = "I cannot determine the parameters from this context."
        result = self.analyst._parse_qwen_json(text)
        self.assertIsNone(result)


# ─────────────────────────────────────────────────────────────────────────────
# Win32 Helper Test
# ─────────────────────────────────────────────────────────────────────────────

class TestGetForegroundWindowTitle(unittest.TestCase):
    def test_returns_string(self):
        """Must always return a string, never raises."""
        title = _get_foreground_window_title()
        self.assertIsInstance(title, str)


if __name__ == "__main__":
    unittest.main()
