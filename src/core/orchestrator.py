"""
AeroTouch Spatial Orchestrator & Event Loop (Precision v2.0)
Harmonizes Camera Vision, Deadband Jitter Filtering, Coordinate Projection, and Direct Win32 OS Dispatch.
Supports adaptive profile loading tuned by Qwen background coach.
"""

import os
import json
import time
from typing import Dict, Optional, Tuple

from src.core.calibrator import ScreenSpaceMapper
from src.core.one_euro_filter import PrecisionSpatialFilter2D
from src.gestures.engine import BimanualEngine, HandLandmarks, HandMode
from src.os_bridge.win32_kernel import VirtualKey, Win32KernelBridge


class SpatialOrchestrator:
    """
    Central loop coordinator executing sub-millisecond gesture-to-OS commands.
    Precision v2.0: Deadband noise gate + multi-frame click confirmation.
    Auto-loads adaptive user profile parameters tuned by local Qwen.
    """

    def __init__(self, profile_path: Optional[str] = None):
        self.kernel = Win32KernelBridge()
        screen_w, screen_h = self.kernel.get_screen_resolution()

        # Load adaptive profile if present
        profile = self._load_profile(profile_path)

        self.mapper = ScreenSpaceMapper(screen_width=screen_w, screen_height=screen_h)
        self.filter = PrecisionSpatialFilter2D(
            min_cutoff=profile.get("min_cutoff", 0.05),    # Rock-solid stillness at rest
            beta=profile.get("beta", 0.015),                # Velocity response for sweeps
            deadband=profile.get("deadband", 0.0025)        # ~4.8px noise gate suppresses tremor
        )
        self.engine = BimanualEngine(
            pinch_threshold=profile.get("pinch_threshold", 0.28),     # Deliberate pinch only
            release_threshold=profile.get("release_threshold", 0.38), # Wide hysteresis gap
            debounce_seconds=profile.get("debounce_seconds", 0.20),   # 200ms debounce
            confirm_frames=int(profile.get("confirm_frames", 2))      # Multi-frame confirmation
        )

        self.last_snap_time: float = 0.0

    def _load_profile(self, profile_path: Optional[str] = None) -> Dict[str, any]:
        """Loads learned parameters from disk or defaults."""
        defaults = {
            "min_cutoff": 0.05,
            "beta": 0.015,
            "deadband": 0.0025,
            "pinch_threshold": 0.28,
            "release_threshold": 0.38,
            "debounce_seconds": 0.20,
            "confirm_frames": 2
        }

        if profile_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            profile_path = os.path.join(base_dir, "data", "user_profile.json")

        if os.path.exists(profile_path):
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    defaults.update(saved)
            except Exception:
                pass

        return defaults

    def process_spatial_frame(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        timestamp: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Executes a single end-to-end spatial frame:
        1. Evaluates Left Hand Mode (Modifier).
        2. Filters & Smooths Right Hand Pointer with Deadband Noise Gate.
        3. Projects to Native Screen Pixels.
        4. Synthesizes Direct Win32 Mouse & Keyboard inputs.
        """
        if timestamp is None:
            timestamp = time.perf_counter()

        # Step 1: Left-hand modifier mode
        left_mode = self.engine.evaluate_left_modifier(left_hand)

        result_summary = {
            "mode": left_mode.name,
            "cursor_pos": None,
            "action_executed": None,
            "action_state": None
        }

        # Step 2: Right-hand execution
        if right_hand is not None:
            action_state = self.engine.evaluate_right_action(right_hand, now=timestamp)
            result_summary["action_state"] = action_state
            norm_x = action_state["cursor_x"]
            norm_y = action_state["cursor_y"]

            # Filter with Deadband Noise Gate — eliminates micro-vibrations completely
            smooth_x, smooth_y = self.filter.filter(norm_x, norm_y, timestamp=timestamp)

            # Map to physical screen resolution
            screen_x, screen_y = self.mapper.map_to_screen(smooth_x, smooth_y)
            result_summary["cursor_pos"] = (screen_x, screen_y)

            # Move hardware cursor via direct Win32 API
            self.kernel.move_cursor(screen_x, screen_y)

            # Handle Actions & Left-Hand Compound Modifiers
            if action_state["click_event"] == "LEFT_CLICK":
                if left_mode == HandMode.WINDOW_SNAP:
                    if timestamp - self.last_snap_time > 0.5:
                        self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_LEFT)
                        self.last_snap_time = timestamp
                        result_summary["action_executed"] = "WINDOW_SNAP_LEFT"
                elif left_mode == HandMode.DESKTOP_SWITCH:
                    self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_CONTROL, VirtualKey.VK_RIGHT)
                    result_summary["action_executed"] = "DESKTOP_NEXT"
                else:
                    self.kernel.click(left=True)
                    result_summary["action_executed"] = "MOUSE_LEFT_CLICK"

            elif action_state["right_click_event"] == "RIGHT_CLICK":
                self.kernel.click(left=False)
                result_summary["action_executed"] = "MOUSE_RIGHT_CLICK"

        return result_summary
