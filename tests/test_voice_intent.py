"""
Unit tests for VoiceIntentService — parse_command, dispatch_intent,
and SpatialOrchestrator.handle_voice_intent.

All tests are fully offline (no microphone, no network, no Win32 calls).
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ---------------------------------------------------------------------------
# Stub speech_recognition BEFORE importing VoiceIntentService.
# This prevents the Google SR engine from touching the microphone or network.
# We do NOT stub PIL/mediapipe — those are not imported by voice_intent.
# ---------------------------------------------------------------------------
_sr_stub = MagicMock()
_sr_stub.Recognizer.return_value = MagicMock()
_sr_stub.Microphone.return_value = MagicMock()
sys.modules["speech_recognition"] = _sr_stub

from src.service.voice_intent import VoiceIntentService, VOICE_INTENTS  # noqa: E402


# ===========================================================================
# parse_command — canonical intent mapping
# ===========================================================================
class TestParseCommand(unittest.TestCase):

    def setUp(self):
        self.svc = VoiceIntentService()   # no callback needed

    # --- direct single-word matches ---
    def test_copy(self):
        self.assertEqual(self.svc.parse_command("copy"), "VOICE_COPY")

    def test_paste(self):
        self.assertEqual(self.svc.parse_command("paste"), "VOICE_PASTE")

    def test_undo(self):
        self.assertEqual(self.svc.parse_command("undo"), "VOICE_UNDO")

    def test_close(self):
        self.assertEqual(self.svc.parse_command("close"), "VOICE_CLOSE_WINDOW")

    def test_close_window_phrase(self):
        self.assertEqual(self.svc.parse_command("close window"), "VOICE_CLOSE_WINDOW")

    def test_maximize(self):
        self.assertEqual(self.svc.parse_command("maximize"), "VOICE_MAXIMIZE")

    def test_minimize(self):
        self.assertEqual(self.svc.parse_command("minimize"), "VOICE_MINIMIZE")

    def test_task_view(self):
        self.assertEqual(self.svc.parse_command("task view"), "VOICE_TASK_VIEW")

    def test_screenshot(self):
        self.assertEqual(self.svc.parse_command("screenshot"), "VOICE_SCREENSHOT")

    def test_snip_alias(self):
        self.assertEqual(self.svc.parse_command("snip"), "VOICE_SCREENSHOT")

    def test_laser(self):
        self.assertEqual(self.svc.parse_command("laser"), "VOICE_TOGGLE_LASER")

    def test_pointer_alias(self):
        self.assertEqual(self.svc.parse_command("pointer"), "VOICE_TOGGLE_LASER")

    def test_draw(self):
        self.assertEqual(self.svc.parse_command("draw"), "VOICE_TOGGLE_DRAW")

    def test_canvas_alias(self):
        self.assertEqual(self.svc.parse_command("canvas"), "VOICE_TOGGLE_DRAW")

    def test_clear(self):
        self.assertEqual(self.svc.parse_command("clear"), "VOICE_CLEAR_CANVAS")

    def test_pause(self):
        self.assertEqual(self.svc.parse_command("pause"), "VOICE_PAUSE")

    def test_resume(self):
        self.assertEqual(self.svc.parse_command("resume"), "VOICE_RESUME")

    def test_game_mode(self):
        self.assertEqual(self.svc.parse_command("game mode"), "VOICE_TOGGLE_GAME_MODE")

    def test_gaming_alias(self):
        self.assertEqual(self.svc.parse_command("gaming"), "VOICE_TOGGLE_GAME_MODE")

    # --- embedded / natural-language phrases ---
    def test_embedded_copy(self):
        self.assertEqual(self.svc.parse_command("please copy this"), "VOICE_COPY")

    def test_embedded_paste(self):
        self.assertEqual(self.svc.parse_command("can you paste it here"), "VOICE_PASTE")

    def test_embedded_screenshot(self):
        self.assertEqual(self.svc.parse_command("take a screenshot now"), "VOICE_SCREENSHOT")

    def test_embedded_maximize(self):
        self.assertEqual(self.svc.parse_command("maximize the window"), "VOICE_MAXIMIZE")

    def test_embedded_minimize(self):
        self.assertEqual(self.svc.parse_command("please minimize this"), "VOICE_MINIMIZE")

    def test_embedded_close_window(self):
        self.assertEqual(self.svc.parse_command("close window please"), "VOICE_CLOSE_WINDOW")

    def test_embedded_pause(self):
        self.assertEqual(self.svc.parse_command("okay pause tracking"), "VOICE_PAUSE")

    def test_embedded_resume(self):
        self.assertEqual(self.svc.parse_command("resume spatial control"), "VOICE_RESUME")

    # --- case-insensitivity ---
    def test_uppercase_copy(self):
        self.assertEqual(self.svc.parse_command("COPY"), "VOICE_COPY")

    def test_mixed_case_paste(self):
        self.assertEqual(self.svc.parse_command("PaSte ThAt"), "VOICE_PASTE")

    def test_all_caps_laser(self):
        self.assertEqual(self.svc.parse_command("LASER MODE"), "VOICE_TOGGLE_LASER")

    # --- no-match / noise ---
    def test_empty_string(self):
        self.assertIsNone(self.svc.parse_command(""))

    def test_gibberish(self):
        self.assertIsNone(self.svc.parse_command("asjdhaksjdh"))

    def test_unrelated_word(self):
        self.assertIsNone(self.svc.parse_command("weather today"))

    def test_whitespace_only(self):
        self.assertIsNone(self.svc.parse_command("   "))

    def test_partial_no_match(self):
        # "cop" is not a prefix match; full substring "copy" must be present
        self.assertIsNone(self.svc.parse_command("cop"))

    # --- VOICE_INTENTS dict completeness ---
    def test_all_intents_cover_expected_canonical_set(self):
        expected_canonical = {
            "VOICE_COPY", "VOICE_PASTE", "VOICE_UNDO",
            "VOICE_CLOSE_WINDOW", "VOICE_MAXIMIZE", "VOICE_MINIMIZE",
            "VOICE_TASK_VIEW", "VOICE_SCREENSHOT",
            "VOICE_TOGGLE_LASER", "VOICE_TOGGLE_DRAW",
            "VOICE_CLEAR_CANVAS", "VOICE_PAUSE", "VOICE_RESUME",
            "VOICE_TOGGLE_GAME_MODE",
        }
        self.assertEqual(set(VOICE_INTENTS.values()), expected_canonical)


# ===========================================================================
# dispatch_intent — callback wiring
# ===========================================================================
class TestDispatchIntent(unittest.TestCase):

    def test_dispatch_calls_callback(self):
        cb = MagicMock()
        svc = VoiceIntentService(on_intent=cb)
        svc.dispatch_intent("VOICE_COPY")
        cb.assert_called_once_with("VOICE_COPY")

    def test_dispatch_sets_last_intent(self):
        svc = VoiceIntentService()
        svc.dispatch_intent("VOICE_PASTE")
        self.assertEqual(svc.last_intent, "VOICE_PASTE")

    def test_dispatch_no_callback_does_not_raise(self):
        svc = VoiceIntentService(on_intent=None)
        svc.dispatch_intent("VOICE_UNDO")
        self.assertEqual(svc.last_intent, "VOICE_UNDO")

    def test_dispatch_callback_exception_is_swallowed(self):
        def bad_cb(_intent):
            raise RuntimeError("simulated downstream crash")
        svc = VoiceIntentService(on_intent=bad_cb)
        try:
            svc.dispatch_intent("VOICE_COPY")
        except Exception:
            self.fail("dispatch_intent propagated an unexpected exception")

    def test_dispatch_all_intents_sequentially(self):
        received = []
        svc = VoiceIntentService(on_intent=received.append)
        for intent in sorted(set(VOICE_INTENTS.values())):
            svc.dispatch_intent(intent)
        self.assertEqual(sorted(received), sorted(set(VOICE_INTENTS.values())))


# ===========================================================================
# start / stop lifecycle
# ===========================================================================
class TestLifecycle(unittest.TestCase):

    def test_start_sets_running(self):
        svc = VoiceIntentService()
        svc._has_sr = False   # prevent real microphone usage
        svc.start()
        self.assertTrue(svc.running)
        svc.stop()

    def test_stop_clears_running(self):
        svc = VoiceIntentService()
        svc._has_sr = False
        svc.start()
        svc.stop()
        self.assertFalse(svc.running)

    def test_double_start_is_idempotent(self):
        svc = VoiceIntentService()
        svc._has_sr = False
        svc.start()
        thread_id_1 = id(svc._thread)
        svc.start()   # second call must be a no-op
        thread_id_2 = id(svc._thread)
        self.assertEqual(thread_id_1, thread_id_2)
        svc.stop()


# ===========================================================================
# SpatialOrchestrator.handle_voice_intent — Win32 hotkey dispatch
# ===========================================================================
class TestOrchestratorVoiceDispatch(unittest.TestCase):
    """
    Tests that orchestrator.handle_voice_intent maps every VOICE_* intent
    to the correct Win32 action without touching real hardware.
    """

    def _make_orchestrator(self):
        """Return a SpatialOrchestrator with fully-mocked Win32Kernel + chime."""
        from src.core.orchestrator import SpatialOrchestrator
        orch = SpatialOrchestrator.__new__(SpatialOrchestrator)
        orch.kernel = MagicMock()
        orch.is_locked = False
        orch.air_canvas = None
        return orch

    def _handle(self, intent):
        orch = self._make_orchestrator()
        with patch("src.core.orchestrator.play_chime_async"):
            result = orch.handle_voice_intent(intent)
        return result, orch.kernel

    # --- hotkey-dispatching intents ---
    def test_copy(self):
        result, k = self._handle("VOICE_COPY")
        self.assertEqual(result, "VOICE_COPY")
        k.hotkey.assert_called_once()

    def test_paste(self):
        result, k = self._handle("VOICE_PASTE")
        self.assertEqual(result, "VOICE_PASTE")
        k.hotkey.assert_called_once()

    def test_undo(self):
        result, k = self._handle("VOICE_UNDO")
        self.assertEqual(result, "VOICE_UNDO")
        k.hotkey.assert_called_once()

    def test_close_window(self):
        result, k = self._handle("VOICE_CLOSE_WINDOW")
        self.assertEqual(result, "VOICE_CLOSE_WINDOW")
        k.hotkey.assert_called_once()

    def test_maximize(self):
        result, k = self._handle("VOICE_MAXIMIZE")
        self.assertEqual(result, "VOICE_MAXIMIZE")
        k.hotkey.assert_called_once()

    def test_minimize(self):
        result, k = self._handle("VOICE_MINIMIZE")
        self.assertEqual(result, "VOICE_MINIMIZE")
        k.hotkey.assert_called_once()

    def test_screenshot(self):
        result, k = self._handle("VOICE_SCREENSHOT")
        self.assertEqual(result, "VOICE_SCREENSHOT")
        k.hotkey.assert_called_once()

    def test_task_view(self):
        result, k = self._handle("VOICE_TASK_VIEW")
        self.assertEqual(result, "VOICE_TASK_VIEW")
        k.hotkey.assert_called_once()

    # --- state-mutating intents (pause / resume) ---
    def test_pause_sets_locked_and_returns_paused(self):
        orch = self._make_orchestrator()
        orch.is_locked = False
        with patch("src.core.orchestrator.play_chime_async"):
            result = orch.handle_voice_intent("VOICE_PAUSE")
        self.assertEqual(result, "VOICE_SYSTEM_PAUSED")
        self.assertTrue(orch.is_locked)

    def test_resume_clears_locked_and_returns_resumed(self):
        orch = self._make_orchestrator()
        orch.is_locked = True
        with patch("src.core.orchestrator.play_chime_async"):
            result = orch.handle_voice_intent("VOICE_RESUME")
        self.assertEqual(result, "VOICE_SYSTEM_RESUMED")
        self.assertFalse(orch.is_locked)

    # --- unknown intent ---
    def test_unknown_intent_returns_none(self):
        orch = self._make_orchestrator()
        with patch("src.core.orchestrator.play_chime_async"):
            result = orch.handle_voice_intent("VOICE_NONEXISTENT")
        self.assertIsNone(result)

    # --- canvas intents with no canvas attached ---
    def test_toggle_laser_no_canvas_returns_none(self):
        orch = self._make_orchestrator()
        with patch("src.core.orchestrator.play_chime_async"):
            result = orch.handle_voice_intent("VOICE_TOGGLE_LASER")
        self.assertIsNone(result)

    def test_toggle_draw_no_canvas_returns_none(self):
        orch = self._make_orchestrator()
        with patch("src.core.orchestrator.play_chime_async"):
            result = orch.handle_voice_intent("VOICE_TOGGLE_DRAW")
        self.assertIsNone(result)

    def test_clear_canvas_no_canvas_returns_none(self):
        orch = self._make_orchestrator()
        with patch("src.core.orchestrator.play_chime_async"):
            result = orch.handle_voice_intent("VOICE_CLEAR_CANVAS")
        self.assertIsNone(result)

    # --- canvas intents WITH canvas attached ---
    def test_toggle_laser_with_canvas(self):
        orch = self._make_orchestrator()
        mock_canvas = MagicMock()
        mock_canvas.laser_enabled = False
        orch.air_canvas = mock_canvas
        with patch("src.core.orchestrator.play_chime_async"):
            result = orch.handle_voice_intent("VOICE_TOGGLE_LASER")
        self.assertEqual(result, "VOICE_LASER_TOGGLED")
        mock_canvas.set_laser.assert_called_once_with(True)

    def test_toggle_draw_with_canvas(self):
        orch = self._make_orchestrator()
        mock_canvas = MagicMock()
        mock_canvas.drawing_enabled = True
        orch.air_canvas = mock_canvas
        with patch("src.core.orchestrator.play_chime_async"):
            result = orch.handle_voice_intent("VOICE_TOGGLE_DRAW")
        self.assertEqual(result, "VOICE_DRAW_TOGGLED")
        mock_canvas.set_drawing.assert_called_once_with(False)

    def test_clear_canvas_with_canvas(self):
        orch = self._make_orchestrator()
        mock_canvas = MagicMock()
        orch.air_canvas = mock_canvas
        with patch("src.core.orchestrator.play_chime_async"):
            result = orch.handle_voice_intent("VOICE_CLEAR_CANVAS")
        self.assertEqual(result, "VOICE_CANVAS_CLEARED")
        mock_canvas.clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
