"""
AeroTouch Spatial Orchestrator & Event Loop
Harmonizes Camera Vision, Jitter Filtering, Coordinate Projection, and Direct Win32 OS Dispatch.
"""

import time
from typing import Dict, Optional, Tuple

from src.core.calibrator import ScreenSpaceMapper
from src.core.one_euro_filter import SpatialPointFilter2D
from src.gestures.engine import BimanualEngine, HandLandmarks, HandMode
from src.os_bridge.win32_kernel import VirtualKey, Win32KernelBridge


class SpatialOrchestrator:
    """
    Central loop coordinator executing sub-millisecond gesture-to-OS commands.
    """

    def __init__(self):
        self.kernel = Win32KernelBridge()
        screen_w, screen_h = self.kernel.get_screen_resolution()

        self.mapper = ScreenSpaceMapper(screen_width=screen_w, screen_height=screen_h)
        self.filter = SpatialPointFilter2D(min_cutoff=0.8, beta=0.015)
        self.engine = BimanualEngine(pinch_threshold=0.28, debounce_seconds=0.15)

        self.last_snap_time: float = 0.0

    def process_spatial_frame(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        timestamp: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Executes a single end-to-end spatial frame:
        1. Evaluates Left Hand Mode (Modifier).
        2. Filters & Smooths Right Hand Pointer.
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

            # Filter raw coordinates with adaptive 1€ filter to kill hand tremors
            smooth_x, smooth_y = self.filter.filter(norm_x, norm_y, timestamp=timestamp)

            # Map to physical screen resolution
            screen_x, screen_y = self.mapper.map_to_screen(smooth_x, smooth_y)
            result_summary["cursor_pos"] = (screen_x, screen_y)

            # Move hardware cursor via direct Win32 API
            self.kernel.move_cursor(screen_x, screen_y)

            # Handle Actions & Left-Hand Compound Modifiers
            if action_state["click_event"] == "LEFT_CLICK":
                if left_mode == HandMode.WINDOW_SNAP:
                    # Chording: Left Fist + Right Pinch = Snap Window to Left
                    if timestamp - self.last_snap_time > 0.5:
                        self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_LEFT)
                        self.last_snap_time = timestamp
                        result_summary["action_executed"] = "WINDOW_SNAP_LEFT"
                elif left_mode == HandMode.DESKTOP_SWITCH:
                    # Chording: Left 3-Fingers + Right Pinch = Next Virtual Desktop
                    self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_CONTROL, VirtualKey.VK_RIGHT)
                    result_summary["action_executed"] = "DESKTOP_NEXT"
                else:
                    # Standard Native Mouse Click
                    self.kernel.click(left=True)
                    result_summary["action_executed"] = "MOUSE_LEFT_CLICK"

            elif action_state["right_click_event"] == "RIGHT_CLICK":
                self.kernel.click(left=False)
                result_summary["action_executed"] = "MOUSE_RIGHT_CLICK"

        return result_summary
