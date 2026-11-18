"""
AeroTouch Kinematic Telemetry Dataset Generator
Generates benchmark gesture sessions for verifying Qwen self-tuning optimization logic.
"""

import json
import os
import random
from typing import Dict, Any, List


def generate_synthetic_session(
    filename: str,
    num_frames: int = 180,
    hand_jitter: float = 0.003,
    pinch_bias: float = 0.26
) -> str:
    """Generates synthetic telemetry session data for testing the optimizer."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        base_x, base_y = 0.5, 0.5
        for i in range(num_frames):
            jitter_x = random.gauss(0, hand_jitter)
            jitter_y = random.gauss(0, hand_jitter)
            pinch_dist = max(0.02, random.gauss(pinch_bias, 0.04))
            mid_pinch = random.gauss(0.45, 0.05)

            is_pinching = pinch_dist < 0.28
            action = "MOUSE_LEFT_CLICK" if is_pinching and (i % 30 == 0) else None

            entry = {
                "frame": i + 1,
                "t": round(i * 0.0166, 4),
                "mode": "POINTER_NAV",
                "pinch_dist": round(pinch_dist, 4),
                "mid_pinch_dist": round(mid_pinch, 4),
                "is_pinching": is_pinching,
                "cursor_x": round(base_x + jitter_x, 5),
                "cursor_y": round(base_y + jitter_y, 5),
                "screen_x": int((base_x + jitter_x) * 1920),
                "screen_y": int((base_y + jitter_y) * 1080),
            }
            if action:
                entry["action"] = action

            f.write(json.dumps(entry) + "\n")

        # Summary entry
        summary = {
            "type": "SESSION_SUMMARY",
            "session_file": os.path.basename(filename),
            "duration_seconds": round(num_frames * 0.0166, 2),
            "total_frames": num_frames,
            "avg_fps": 60.0,
            "left_clicks": num_frames // 30,
            "right_clicks": 0
        }
        f.write(json.dumps(summary) + "\n")

    return filename
