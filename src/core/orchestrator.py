"""
AeroTouch Spatial Orchestrator & Event Loop
Harmonizes Camera Vision, Deadband Jitter Filtering, Coordinate Projection, and Direct Win32 OS Dispatch.
Supports adaptive profile loading tuned by Qwen background coach.
"""

import os
import json
import time
from typing import Dict, Optional, Tuple

from src.core.calibrator import ScreenSpaceMapper, PointerBallistics
from src.core.one_euro_filter import PrecisionSpatialFilter2D
from src.gestures.engine import BimanualEngine, HandLandmarks, HandMode, GestureMath
from src.os_bridge.win32_kernel import VirtualKey, Win32KernelBridge
from src.service.window_dragger import WindowDragger
from src.service.scroll_controller import KineticScrollController
from src.os_bridge.volume_control import MediaScalarController
from src.os_bridge.audio_feedback import play_chime_async
from src.gestures.few_shot_engine import FewShotGestureEngine


class SpatialOrchestrator:
    """
    Central loop coordinator executing sub-millisecond gesture-to-OS commands.
    Features deadband noise gate and multi-frame click confirmation.
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

        self.dragger = WindowDragger()
        self.scroll_ctrl = KineticScrollController()
        self.ballistics = PointerBallistics()
        self.media_ctrl = MediaScalarController()
        self.last_snap_time: float = 0.0

        # Few-Shot Custom Gesture Engine
        self.custom_engine = FewShotGestureEngine()
        self.custom_gesture_streak: int = 0
        self.last_custom_gesture_time: float = 0.0
        self.last_custom_gesture_name: Optional[str] = None

        # Shaka Gesture (🤙) Lock / Sleep State Machine
        self.is_locked: bool = False
        self.shaka_streak: int = 0
        self.last_lock_toggle_time: float = 0.0
        self.shaka_required_frames: int = int(profile.get("shaka_frames", 35))
        self.lock_cooldown: float = 1.2

    def recalibrate(self) -> None:
        """Resets all spatial filters, pointer ballistics, and dragging states."""
        self.filter.reset()
        self.ballistics.reset()
        self.scroll_ctrl.reset()
        self.dragger.reset()
        self.custom_gesture_streak = 0

    def apply_context_profile(self, recommendations: Dict[str, any]) -> None:
        """
        Applies live parameter updates from the Rolling Vision Intelligence pipeline.
        Called in background thread from RollingVisionAnalyst.on_params_updated.
        Thread-safe: each attribute assignment is atomic in CPython (GIL guarantee).

        Parameter bounds enforced here are the same ranges Qwen is told about,
        preventing any out-of-range recommendation from destabilising the system.
        """
        if "deadband" in recommendations:
            val = max(0.001, min(0.008, float(recommendations["deadband"])))
            self.filter.deadband = val

        if "ballistics_precision_gain" in recommendations:
            val = max(0.3, min(0.8, float(recommendations["ballistics_precision_gain"])))
            self.ballistics.precision_gain = val

        if "ballistics_max_multiplier" in recommendations:
            val = max(1.5, min(2.5, float(recommendations["ballistics_max_multiplier"])))
            self.ballistics.max_multiplier = val

        if "scroll_sensitivity" in recommendations:
            val = max(8.0, min(25.0, float(recommendations["scroll_sensitivity"])))
            self.scroll_ctrl.sensitivity = val

        reasoning = recommendations.get("reasoning", "")
        if reasoning:
            print(f"[AeroTouch Vision]: Context adaptation applied — {reasoning}")

    def _load_profile(self, profile_path: Optional[str] = None) -> Dict[str, any]:
        """Loads configuration from config.toml and adaptive user_profile.json."""
        defaults = {
            "min_cutoff": 0.05,
            "beta": 0.015,
            "deadband": 0.0025,
            "pinch_threshold": 0.28,
            "release_threshold": 0.38,
            "debounce_seconds": 0.20,
            "confirm_frames": 2,
            "shaka_frames": 35
        }

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        toml_path = os.path.join(base_dir, "config.toml")

        # 1. Load config.toml if present
        if os.path.exists(toml_path):
            try:
                import tomllib
                with open(toml_path, "rb") as f:
                    cfg = tomllib.load(f)
                    if "filter" in cfg:
                        for k in ["min_cutoff", "beta", "deadband"]:
                            if k in cfg["filter"]:
                                defaults[k] = float(cfg["filter"][k])
                    if "gestures" in cfg:
                        for k in ["pinch_threshold", "release_threshold", "debounce_seconds"]:
                            if k in cfg["gestures"]:
                                defaults[k] = float(cfg["gestures"][k])
                        if "confirm_frames" in cfg["gestures"]:
                            defaults["confirm_frames"] = int(cfg["gestures"]["confirm_frames"])
                        if "shaka_frames" in cfg["gestures"]:
                            defaults["shaka_frames"] = int(cfg["gestures"]["shaka_frames"])
            except Exception:
                pass

        # 2. Overlay adaptive profile if present
        if profile_path is None:
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

        # Step 0: Shaka (🤙) Gesture Lock / Unlock State Machine
        shaka_detected = False
        if right_hand is not None and GestureMath.is_shaka(right_hand):
            shaka_detected = True
        elif left_hand is not None and GestureMath.is_shaka(left_hand):
            shaka_detected = True

        toggle_action = None
        if shaka_detected:
            if (timestamp - self.last_lock_toggle_time) > self.lock_cooldown:
                self.shaka_streak += 1
                if self.shaka_streak >= self.shaka_required_frames:
                    self.is_locked = not self.is_locked
                    self.last_lock_toggle_time = timestamp
                    self.shaka_streak = 0
                    toggle_action = "AEROTOUCH_LOCKED" if self.is_locked else "AEROTOUCH_UNLOCKED"
                    play_chime_async(is_lock=self.is_locked)
        else:
            self.shaka_streak = max(0, self.shaka_streak - 2)

        lock_progress = min(1.0, self.shaka_streak / max(1, self.shaka_required_frames))

        # If system is LOCKED, freeze all spatial inputs completely
        if self.is_locked:
            return {
                "system_state": "LOCKED",
                "lock_progress": lock_progress,
                "mode": "PAUSED",
                "cursor_pos": None,
                "action_executed": toggle_action or ("HOLDING_SHAKA" if lock_progress > 0 else None),
                "action_state": None
            }

        # Step 1: Left-hand modifier mode
        left_mode = self.engine.evaluate_left_modifier(left_hand)

        result_summary = {
            "system_state": "ACTIVE",
            "lock_progress": lock_progress,
            "mode": left_mode.name,
            "cursor_pos": None,
            "action_executed": toggle_action,
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

            # Apply Dynamic Pointer Ballistics (Sniper Precision Mode & Flick Acceleration)
            accel_x, accel_y = self.ballistics.apply(smooth_x, smooth_y, timestamp=timestamp)

            # Map to physical screen resolution
            screen_x, screen_y = self.mapper.map_to_screen(accel_x, accel_y)
            result_summary["cursor_pos"] = (screen_x, screen_y)

            # Two-Finger Kinetic Scroll with Momentum Decay
            is_scroll = action_state.get("is_scroll", False)
            scroll_y = action_state.get("scroll_y", norm_y)
            scroll_steps = self.scroll_ctrl.update(is_scroll, scroll_y, timestamp=timestamp)

            if is_scroll:
                if scroll_steps != 0:
                    self.kernel.scroll(scroll_steps)
                    result_summary["action_executed"] = f"TWO_FINGER_SCROLL_{scroll_steps}"
            else:
                if scroll_steps != 0:
                    self.kernel.scroll(scroll_steps)
                    result_summary["action_executed"] = f"KINETIC_SCROLL_{scroll_steps}"

                # Only move cursor when not actively two-finger scrolling
                self.kernel.move_cursor(screen_x, screen_y)

            # Continuous Media Scalar Control (Volume)
            if left_mode == HandMode.MEDIA_CONTROL:
                vol = self.media_ctrl.apply_volume(action_state["pinch_distance"])
                if vol is not None:
                    result_summary["action_executed"] = f"VOLUME_SCALAR_{int(vol * 100)}"

            # Fist-based Spatial Window Dragging
            fist_ev = action_state.get("fist_event")
            if fist_ev == "DRAG_START":
                hwnd = self.kernel.get_foreground_window()
                rect = self.kernel.get_window_rect(hwnd)
                self.dragger.start_drag(hwnd, rect, screen_x, screen_y)
                result_summary["action_executed"] = "WINDOW_DRAG_START"
            elif action_state.get("is_fist") and self.dragger.is_dragging:
                hwnd, new_x, new_y, w, h = self.dragger.update_drag(screen_x, screen_y)
                self.kernel.move_window(hwnd, new_x, new_y, w, h)
                result_summary["action_executed"] = "WINDOW_DRAG_MOVE"
            elif fist_ev == "DRAG_END" and self.dragger.is_dragging:
                self.dragger.end_drag()
                result_summary["action_executed"] = "WINDOW_DRAG_END"

            # Handle Actions & Left-Hand Compound Modifiers
            if action_state["click_event"] == "LEFT_CLICK":
                if left_mode == HandMode.WINDOW_SNAP:
                    if timestamp - self.last_snap_time > 0.5:
                        direction = GestureMath.get_snap_direction(right_hand)
                        if direction == "UP":
                            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_UP)
                            result_summary["action_executed"] = "WINDOW_MAXIMIZE"
                        elif direction == "DOWN":
                            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_DOWN)
                            result_summary["action_executed"] = "WINDOW_MINIMIZE"
                        elif direction == "RIGHT":
                            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_RIGHT)
                            result_summary["action_executed"] = "WINDOW_SNAP_RIGHT"
                        else:
                            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_LEFT)
                            result_summary["action_executed"] = "WINDOW_SNAP_LEFT"
                        self.last_snap_time = timestamp
                elif left_mode == HandMode.DESKTOP_SWITCH:
                    self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_CONTROL, VirtualKey.VK_RIGHT)
                    result_summary["action_executed"] = "DESKTOP_NEXT"
                else:
                    self.kernel.click(left=True)
                    result_summary["action_executed"] = "MOUSE_LEFT_CLICK"

            elif action_state["right_click_event"] == "RIGHT_CLICK":
                self.kernel.click(left=False)
                result_summary["action_executed"] = "MOUSE_RIGHT_CLICK"

            # Check Custom Few-Shot Gestures (e.g. Media, Hotkey, Screenshot)
            if not is_scroll and not action_state.get("is_fist") and not action_state.get("click_event"):
                custom_match = self.custom_engine.classify(right_hand)
                if custom_match is not None:
                    c_name, c_sim, c_meta = custom_match
                    if c_name == self.last_custom_gesture_name:
                        self.custom_gesture_streak += 1
                    else:
                        self.custom_gesture_streak = 1
                        self.last_custom_gesture_name = c_name

                    # 3 confirmed consecutive frames and debounce cooldown
                    if self.custom_gesture_streak >= 3 and (timestamp - self.last_custom_gesture_time) > 0.8:
                        action_type = c_meta.get("action", "HOTKEY")
                        action_param = c_meta.get("action_param")
                        self.kernel.execute_named_action(action_type, action_param)
                        result_summary["action_executed"] = f"CUSTOM_GESTURE_{c_name}"
                        self.last_custom_gesture_time = timestamp
                else:
                    self.custom_gesture_streak = 0
                    self.last_custom_gesture_name = None
        else:
            # Tracking lost / Hand absent: reset spatial state cleanly
            self.filter.reset()
            self.ballistics.reset()
            self.engine.pinch_streak = 0
            self.engine.middle_pinch_streak = 0
            self.engine.is_pinching = False
            if self.dragger.is_dragging:
                self.dragger.end_drag()

        return result_summary
