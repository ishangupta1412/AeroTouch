"""
Unit tests for AeroTouch System Tray Daemon (src.ui.tray)
Verifies tray lifecycle, callbacks, pause toggling, recalibration, and graceful teardown.
"""

import unittest
from unittest.mock import MagicMock
from src.ui.tray import AeroTouchTrayDaemon


class TestAeroTouchTrayDaemon(unittest.TestCase):

    def setUp(self):
        self.pause_mock = MagicMock(return_value=True)
        self.recal_mock = MagicMock()
        self.tune_mock = MagicMock()
        self.exit_mock = MagicMock()

        self.daemon = AeroTouchTrayDaemon(
            on_toggle_pause=self.pause_mock,
            on_recalibrate=self.recal_mock,
            on_cortex_tune=self.tune_mock,
            on_exit=self.exit_mock
        )

    def test_initial_state(self):
        self.assertFalse(self.daemon.is_running)
        self.assertFalse(self.daemon.is_paused)
        self.assertTrue(self.daemon.is_preview_visible)

    def test_wnd_proc_pause_toggle(self):
        # Simulate ID_PAUSE_RESUME command (0x0111 = WM_COMMAND)
        self.daemon._wnd_proc(None, 0x0111, self.daemon.ID_PAUSE_RESUME, 0)
        self.pause_mock.assert_called_once()
        self.assertTrue(self.daemon.is_paused)

    def test_wnd_proc_recalibrate(self):
        self.daemon._wnd_proc(None, 0x0111, self.daemon.ID_RECALIBRATE, 0)
        self.recal_mock.assert_called_once()

    def test_wnd_proc_exit(self):
        self.daemon.is_running = True
        self.daemon._wnd_proc(None, 0x0111, self.daemon.ID_EXIT, 0)
        self.assertFalse(self.daemon.is_running)
        self.exit_mock.assert_called_once()

    def test_notify_fallback_does_not_crash(self):
        # Even without win32 window handle, notify shouldn't raise exception
        try:
            self.daemon.notify("Test", "AeroTouch Test Message")
        except Exception as e:
            self.fail(f"notify raised an unexpected exception: {e}")


if __name__ == "__main__":
    unittest.main()
