"""
AeroTouch Session Telemetry Logger
Records per-frame gesture pipeline metrics for Qwen background self-tuning.
Writes to data/sessions/session_YYYYMMDD_HHMMSS.jsonl
"""

import json
import os
import time
from typing import Dict, Any, Optional


class SessionTelemetryLogger:
    """Lightweight per-frame telemetry recorder for precision pipeline analysis."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        self.session_dir = os.path.join(base_dir, "data", "sessions")
        os.makedirs(self.session_dir, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        self.session_file = os.path.join(self.session_dir, f"session_{ts}.jsonl")
        self._file_handle = None

        self.frame_count: int = 0
        self.click_count: int = 0
        self.right_click_count: int = 0
        self.false_positive_candidates: int = 0
        self.session_start: float = time.perf_counter()

    def open(self):
        """Opens the session log file for writing."""
        self._file_handle = open(self.session_file, "a", encoding="utf-8")

    def log_frame(self, action_state: Optional[Dict[str, Any]], cursor_pos: Optional[tuple],
                  mode: str, action_executed: Optional[str]):
        """Records a single spatial frame's telemetry data."""
        if self._file_handle is None:
            return

        self.frame_count += 1

        entry = {
            "frame": self.frame_count,
            "t": round(time.perf_counter() - self.session_start, 4),
            "mode": mode,
        }

        if action_state:
            entry["pinch_dist"] = round(action_state.get("pinch_distance", -1), 4)
            entry["mid_pinch_dist"] = round(action_state.get("middle_pinch_distance", -1), 4)
            entry["is_pinching"] = action_state.get("is_pinching", False)
            entry["cursor_x"] = round(action_state.get("cursor_x", 0), 5)
            entry["cursor_y"] = round(action_state.get("cursor_y", 0), 5)

        if cursor_pos:
            entry["screen_x"] = cursor_pos[0]
            entry["screen_y"] = cursor_pos[1]

        if action_executed:
            entry["action"] = action_executed
            if "LEFT_CLICK" in action_executed:
                self.click_count += 1
            elif "RIGHT_CLICK" in action_executed:
                self.right_click_count += 1

        # Only write frames with meaningful data (skip empty/no-hand frames to save disk)
        if action_state or action_executed:
            self._file_handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_session_summary(self) -> Dict[str, Any]:
        """Returns aggregated session statistics for Qwen analysis."""
        elapsed = time.perf_counter() - self.session_start
        return {
            "session_file": self.session_file,
            "duration_seconds": round(elapsed, 2),
            "total_frames": self.frame_count,
            "avg_fps": round(self.frame_count / max(elapsed, 0.001), 1),
            "left_clicks": self.click_count,
            "right_clicks": self.right_click_count,
        }

    def close(self):
        """Flushes and closes the session log file."""
        if self._file_handle:
            # Write session summary as final line
            summary = self.get_session_summary()
            summary["type"] = "SESSION_SUMMARY"
            self._file_handle.write(json.dumps(summary, ensure_ascii=False) + "\n")
            self._file_handle.flush()
            self._file_handle.close()
            self._file_handle = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
