"""
Unit tests for AeroTouch CLI entrypoint and argument parsing.
"""

import io
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.main import main


class TestCLIEntrypoint(unittest.TestCase):
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_help_flag_displays_usage_and_exits(self, mock_stdout):
        with patch.object(sys, "argv", ["main.py", "--help"]):
            main()
        output = mock_stdout.getvalue()
        self.assertIn("AeroTouch: Autonomous Dual-Hand Spatial Operating Layer", output)
        self.assertIn("--orb", output)
        self.assertIn("--tray", output)
        self.assertIn("-h, --help", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_short_help_flag(self, mock_stdout):
        with patch.object(sys, "argv", ["main.py", "-h"]):
            main()
        output = mock_stdout.getvalue()
        self.assertIn("AeroTouch: Autonomous Dual-Hand Spatial Operating Layer", output)

    @patch("src.main.run_aerotouch")
    def test_flag_parsing_forwarding(self, mock_run):
        with patch.object(sys, "argv", ["main.py", "--orb", "--no-island", "--no-vision", "--no-voice", "1"]):
            main()
        mock_run.assert_called_once_with(
            camera_index=1,
            use_orb=True,
            use_island=False,
            show_preview=False,
            use_tray=False,
            use_vision=False,
            use_canvas=True,
            use_voice=False,
        )


if __name__ == "__main__":
    unittest.main()
