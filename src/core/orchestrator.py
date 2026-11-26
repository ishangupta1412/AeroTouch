"""
AeroTouch Spatial Orchestrator & Event Loop
Harmonizes Camera Vision, Deadband Jitter Filtering, Coordinate Projection, and Direct Win32 OS Dispatch.
Supports adaptive profile loading tuned by Qwen background coach.
"""

import os
import json
import threading
import time
from typing import Dict, Optional, Tuple

from src.core.calibrator import ScreenSpaceMapper, PointerBallistics
from src.core.one_euro_filter import PrecisionSpatialFilter2D
from src.gestures.engine import BimanualEngine, HandLandmarks, HandMode, GestureMath
from src.os_bridge.win32_kernel import VirtualKey, Win32KernelBridge
from src.service.window_dragger import WindowDragger
from src.service.scroll_controller import KineticScrollController
from src.service.swipe_detector import FluidSwipeDetector
from src.service.spatial_zoom import BimanualZoomController
from src.os_bridge.volume_control import MediaScalarController
from src.os_bridge.audio_feedback import play_chime_async
from src.gestures.few_shot_engine import FewShotGestureEngine
from src.games.engine import GameEngine
from src.core.engagement import EngagementGatingEngine, TrackingParadigm
from src.core.predictive_filter import PredictiveKinematicFilter
from src.core.kalman_filter import ConstantAccelerationKalman2D
from src.core.gaze_tracker import GazeHybridTracker
from src.gestures.micro_classifier import MicroGestureClassifier
from src.service.audio_haptics import AudioHapticsEngine, HapticCue
from src.os_bridge.ui_magnetism import UIMagnetismEngine
from src.core.app_presets import AppPresetEngine
from src.core.biomechanical_ik import BiomechanicalIKSolver
from src.core.hermite_spline import CubicHermiteSplineInterpolator
from src.os_bridge.live_accessibility import LiveUIAccessibilityInspector


class SpatialOrchestrator:
    """
    Central loop coordinator executing sub-millisecond gesture-to-OS commands.
    Features deadband noise gate and multi-frame click confirmation.
    Auto-loads adaptive user profile parameters tuned by local Qwen.
    """

    def __init__(self, profile_path: Optional[str] = None):
        self.kernel = Win32KernelBridge()
        screen_w, screen_h = self.kernel.get_screen_resolution()
        vx, vy, vw, vh = 0, 0, screen_w, screen_h
        try:
            bounds = self.kernel.get_virtual_screen_bounds()
            if isinstance(bounds, tuple) and len(bounds) == 4 and bounds[2] > 0 and bounds[3] > 0:
                vx, vy, vw, vh = bounds
        except Exception:
            pass

        # Load adaptive profile if present
        profile = self._load_profile(profile_path)

        self.mapper = ScreenSpaceMapper(screen_width=vw, screen_height=vh, origin_x=vx, origin_y=vy)
        self.filter = PrecisionSpatialFilter2D(
            min_cutoff=profile.get("min_cutoff", 0.05),    # Rock-solid stillness at rest
            beta=profile.get("beta", 0.015),                # Velocity response for sweeps
            deadband=profile.get("deadband", 0.0025)        # ~4.8px noise gate suppresses tremor
        )
        self.engine = BimanualEngine(
            pinch_threshold=profile.get("pinch_threshold", 0.36),     # Ergonomic & responsive pinch
            release_threshold=profile.get("release_threshold", 0.46), # Wide hysteresis gap
            debounce_seconds=profile.get("debounce_seconds", 0.15),   # 150ms debounce
            confirm_frames=int(profile.get("confirm_frames", 2))      # Multi-frame confirmation
        )

        self.dragger = WindowDragger()
        self.scroll_ctrl = KineticScrollController()
        self.swipe_detector = FluidSwipeDetector()
        self.zoom_ctrl = BimanualZoomController()
        self.ballistics = PointerBallistics()
        self.media_ctrl = MediaScalarController()
        self.air_canvas = None
        self.game_engine = GameEngine()
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

        # Peak Spatial Computing Engines
        self.engagement_engine = EngagementGatingEngine()
        self.use_engagement_gating: bool = False
        self.predictive_filter = PredictiveKinematicFilter()
        self.kalman_filter = ConstantAccelerationKalman2D()
        self.gaze_tracker = GazeHybridTracker(enabled=True)
        self.ml_classifier = MicroGestureClassifier()
        self.haptics = AudioHapticsEngine()
        self.magnetism = UIMagnetismEngine()
        self.app_presets = AppPresetEngine()
        self._last_preset_refresh_time: float = 0.0
        self._last_locked_ui_target: Optional[str] = None

        # World-Class Biomechanical IK & 1000 Hz Spline Engines
        self.ik_solver_right = BiomechanicalIKSolver(calibration_frames=8)
        self.ik_solver_left = BiomechanicalIKSolver(calibration_frames=8)
        self.hermite_spline = CubicHermiteSplineInterpolator(target_rate_hz=1000)
        self.live_inspector = LiveUIAccessibilityInspector()
        self._last_accessibility_probe_time: float = 0.0
        self._hermite_running: bool = False
        self._hermite_thread: Optional[threading.Thread] = None
        self._hermite_last_waypoint_time: float = 0.0
        self._hermite_last_sent: Optional[Tuple[int, int]] = None

    def start_hermite_driver(self, rate_hz: int = 120) -> None:
        """Starts high-frequency Hermite sub-frame cursor interpolation between camera frames."""
        if self._hermite_running:
            return
        self._hermite_running = True
        interval = 1.0 / max(60, rate_hz)

        def _loop():
            while self._hermite_running:
                now = time.perf_counter()
                if (
                    not self.is_locked
                    and not self.game_engine.is_active
                    and (now - self._hermite_last_waypoint_time) < 0.08
                    and len(self.hermite_spline._history) >= 2
                ):
                    ix, iy = self.hermite_spline.evaluate_at(now)
                    px, py = int(ix), int(iy)
                    if self._hermite_last_sent != (px, py):
                        self._hermite_last_sent = (px, py)
                        try:
                            self.kernel.move_cursor(px, py)
                        except Exception:
                            pass
                time.sleep(interval)

        self._hermite_thread = threading.Thread(target=_loop, daemon=True, name="AeroTouchHermiteDriver")
        self._hermite_thread.start()

    def stop_hermite_driver(self) -> None:
        """Stops the high-frequency Hermite cursor driver cleanly."""
        self._hermite_running = False
        if self._hermite_thread and self._hermite_thread.is_alive():
            try:
                self._hermite_thread.join(timeout=0.3)
            except Exception:
                pass
        self._hermite_thread = None

    def toggle_tracking_paradigm(self) -> TrackingParadigm:
        """Toggles between 1:1 Absolute Laser mode and Relative Desk/Lap Trackpad mode."""
        new_mode = (
            TrackingParadigm.RELATIVE_CLUTCHED
            if self.engagement_engine.current_paradigm == TrackingParadigm.ABSOLUTE_LASER
            else TrackingParadigm.ABSOLUTE_LASER
        )
        self.engagement_engine.set_paradigm(new_mode)
        self.use_engagement_gating = (new_mode == TrackingParadigm.RELATIVE_CLUTCHED)
        return new_mode

    def recalibrate(self) -> None:
        """Resets all spatial filters, pointer ballistics, and dragging states."""
        self.filter.reset()
        self.predictive_filter.reset()
        self.kalman_filter.reset()
        self.ik_solver_right.reset()
        self.ik_solver_left.reset()
        self.hermite_spline.reset()
        self.ballistics.reset()
        self.scroll_ctrl.reset()
        self.swipe_detector.reset()
        self.zoom_ctrl.reset()
        self.dragger.reset()
        self.magnetism.clear_targets()
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
            "beta": 1.8,
            "deadband": 0.0020,
            "pinch_threshold": 0.36,
            "release_threshold": 0.46,
            "debounce_seconds": 0.15,
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

    def attach_air_canvas(self, air_canvas) -> None:
        """Attaches live desktop AirCanvas overlay instance."""
        self.air_canvas = air_canvas

    def handle_voice_intent(self, intent: str) -> Optional[str]:
        """
        Executes multimodal voice intents directly through the OS kernel bridge.
        Returns the name of the executed action or None.
        """
        action = None
        if intent == "VOICE_COPY":
            self.kernel.hotkey(VirtualKey.VK_CONTROL, ord('C'))
            action = "VOICE_COPY"
        elif intent == "VOICE_PASTE":
            self.kernel.hotkey(VirtualKey.VK_CONTROL, ord('V'))
            action = "VOICE_PASTE"
        elif intent == "VOICE_UNDO":
            self.kernel.hotkey(VirtualKey.VK_CONTROL, ord('Z'))
            action = "VOICE_UNDO"
        elif intent == "VOICE_CLOSE_WINDOW":
            self.kernel.hotkey(VirtualKey.VK_MENU, VirtualKey.VK_F4)
            action = "VOICE_CLOSE_WINDOW"
        elif intent == "VOICE_MAXIMIZE":
            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_UP)
            action = "VOICE_MAXIMIZE"
        elif intent == "VOICE_MINIMIZE":
            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_DOWN)
            action = "VOICE_MINIMIZE"
        elif intent == "VOICE_TASK_VIEW":
            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_TAB)
            action = "VOICE_TASK_VIEW"
        elif intent == "VOICE_SCREENSHOT":
            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_SHIFT, ord('S'))
            action = "VOICE_SCREENSHOT"
        elif intent == "VOICE_TOGGLE_LASER":
            if self.air_canvas:
                self.air_canvas.set_laser(not self.air_canvas.laser_enabled)
                action = "VOICE_LASER_TOGGLED"
        elif intent == "VOICE_TOGGLE_DRAW":
            if self.air_canvas:
                self.air_canvas.set_drawing(not self.air_canvas.drawing_enabled)
                action = "VOICE_DRAW_TOGGLED"
        elif intent == "VOICE_CLEAR_CANVAS":
            if self.air_canvas:
                self.air_canvas.clear()
                action = "VOICE_CANVAS_CLEARED"
        elif intent == "VOICE_PAUSE":
            self.is_locked = True
            action = "VOICE_SYSTEM_PAUSED"
            play_chime_async(is_lock=True)
        elif intent == "VOICE_RESUME":
            self.is_locked = False
            action = "VOICE_SYSTEM_RESUMED"
            play_chime_async(is_lock=False)
        elif intent in ("VOICE_TOGGLE_GAME_MODE", "VOICE_GAME_MODE"):
            is_gaming = self.game_engine.toggle(self.kernel)
            action = "GAME_MODE_ENABLED" if is_gaming else "GAME_MODE_DISABLED"
            play_chime_async(is_lock=not is_gaming)
        elif intent == "VOICE_SELECT_SUBWAY_SURFERS":
            self.game_engine.set_active_profile("subway_surfers", self.kernel)
            if not self.game_engine.is_active:
                self.game_engine.toggle(self.kernel)
            action = "GAME_SUBWAY_SURFERS_ACTIVE"
            play_chime_async(is_lock=False)
        elif intent == "VOICE_SELECT_RACING":
            self.game_engine.set_active_profile("racing", self.kernel)
            if not self.game_engine.is_active:
                self.game_engine.toggle(self.kernel)
            action = "GAME_RACING_ACTIVE"
            play_chime_async(is_lock=False)
        elif intent == "VOICE_SELECT_TEMPLE_RUN":
            self.game_engine.set_active_profile("temple_run", self.kernel)
            if not self.game_engine.is_active:
                self.game_engine.toggle(self.kernel)
            action = "GAME_TEMPLE_RUN_ACTIVE"
            play_chime_async(is_lock=False)
        elif intent == "VOICE_SELECT_MINECRAFT":
            self.game_engine.set_active_profile("minecraft", self.kernel)
            if not self.game_engine.is_active:
                self.game_engine.toggle(self.kernel)
            action = "GAME_MINECRAFT_ACTIVE"
            play_chime_async(is_lock=False)
        elif intent == "VOICE_SELECT_FRUIT_NINJA":
            self.game_engine.set_active_profile("fruit_ninja", self.kernel)
            if not self.game_engine.is_active:
                self.game_engine.toggle(self.kernel)
            action = "GAME_FRUIT_NINJA_ACTIVE"
            play_chime_async(is_lock=False)
        elif intent == "VOICE_SELECT_FLAPPY_BIRD":
            self.game_engine.set_active_profile("flappy_bird", self.kernel)
            if not self.game_engine.is_active:
                self.game_engine.toggle(self.kernel)
            action = "GAME_FLAPPY_BIRD_ACTIVE"
            play_chime_async(is_lock=False)
        elif intent == "VOICE_NEXT_GAME":
            next_prof = self.game_engine.cycle_next_profile(self.kernel)
            if not self.game_engine.is_active:
                self.game_engine.toggle(self.kernel)
            action = f"GAME_{next_prof.upper()}_ACTIVE"
            play_chime_async(is_lock=False)

        return action

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

        # Step -0.1: Biomechanical Inverse Kinematics Bone-Length Invariance
        if right_hand is not None:
            right_hand = self.ik_solver_right.constrain_landmarks(right_hand)
        if left_hand is not None:
            left_hand = self.ik_solver_left.constrain_landmarks(left_hand)

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

        # Step 0.5: Dual-Hand Fist Bump (🤜🤛) Game Mode Trigger
        bump_triggered, bump_progress = self.game_engine.evaluate_trigger(right_hand, left_hand, timestamp)
        if bump_triggered:
            is_gaming = self.game_engine.toggle(self.kernel)
            toggle_action = "GAME_MODE_ENABLED" if is_gaming else "GAME_MODE_DISABLED"
            play_chime_async(is_lock=not is_gaming)

        # If Game Mode is active, delegate entire frame to GameEngine
        if self.game_engine.is_active:
            game_res = self.game_engine.process_frame(right_hand, left_hand, self.kernel, timestamp)
            return {
                "system_state": "GAME_MODE",
                "lock_progress": bump_progress,
                "mode": f"GAMING:{self.game_engine.active_profile_id}",
                "cursor_pos": None,
                "action_executed": toggle_action or ("GAME_ACTIVE" if game_res.get("is_gaming") else None),
                "action_state": game_res,
                "game_data": game_res
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
            # Optional Palm-Normal Midas-Touch Gating (active in Relative Trackpad Mode or when enabled)
            if self.use_engagement_gating:
                engaged, eng_conf = self.engagement_engine.evaluate_engagement(right_hand)
                if not engaged:
                    result_summary["mode"] = "DISENGAGED"
                    return result_summary

            # Refresh active application preset periodically (~0.5s)
            if (timestamp - self._last_preset_refresh_time) > 0.5:
                try:
                    self.app_presets.update_active_window()
                except Exception:
                    pass
                self._last_preset_refresh_time = timestamp
            active_preset = self.app_presets.get_active_preset()

            action_state = self.engine.evaluate_right_action(right_hand, now=timestamp)
            result_summary["action_state"] = action_state
            norm_x = action_state["cursor_x"]
            norm_y = action_state["cursor_y"]

            # Relative Desk/Lap Trackpad Mode (delta wrist/finger clutching)
            if self.engagement_engine.current_paradigm == TrackingParadigm.RELATIVE_CLUTCHED:
                dx_rel, dy_rel = self.engagement_engine.compute_relative_delta(right_hand)
                sens = active_preset.pointer_sensitivity
                norm_x = max(0.0, min(1.0, self.ballistics.cursor_x + dx_rel * sens))
                norm_y = max(0.0, min(1.0, self.ballistics.cursor_y + dy_rel * sens))

            # Optional Gaze + Hand Hybrid Coarse Assist ("Look + Pinch")
            if self.gaze_tracker.available:
                norm_x, norm_y = self.gaze_tracker.blend_with_hand(norm_x, norm_y)

            # 1. Stage 1: Adaptive 1-Euro Filter (eliminates high-frequency hand tremor first)
            smooth_x, smooth_y = self.filter.filter(norm_x, norm_y, timestamp=timestamp)

            # 2. Stage 2: Hybrid Predictive + Constant-Acceleration Kalman Filtering
            pred_x, pred_y = self.predictive_filter.filter_and_predict(smooth_x, smooth_y, timestamp=timestamp)
            kal_x, kal_y = self.kalman_filter.update(smooth_x, smooth_y, timestamp=timestamp)
            fused_x = 0.5 * pred_x + 0.5 * kal_x
            fused_y = 0.5 * pred_y + 0.5 * kal_y

            # 3. Stage 3: Dynamic Pointer Ballistics (Sniper Precision Mode & Flick Acceleration)
            accel_x, accel_y = self.ballistics.apply(fused_x, fused_y, timestamp=timestamp)

            # 4. Dynamic Ergonomic Reach & Screen Space Mapping
            self.mapper.update_ergonomics(GestureMath.hand_scale(right_hand))
            screen_x, screen_y = self.mapper.map_to_screen(accel_x, accel_y)

            # Probe live native Windows UI element under cursor to feed gravity basins
            if (timestamp - self._last_accessibility_probe_time) > 0.040:
                elem = self.live_inspector.get_element_rect_at_point(screen_x, screen_y)
                if elem:
                    target_id, el_l, el_t, el_r, el_b = elem
                    self.magnetism.register_target(target_id, el_l, el_t, el_r, el_b)
                self._last_accessibility_probe_time = timestamp

            # Sub-Pixel UI Magnetism (Apple visionOS gravitational attraction)
            screen_x, screen_y, locked_target = self.magnetism.apply_magnetism(
                screen_x, screen_y, cursor_speed=self.ballistics.current_speed
            )
            if locked_target and locked_target != self._last_locked_ui_target:
                self.haptics.trigger(HapticCue.SNAP_PING)
            self._last_locked_ui_target = locked_target

            # 1000 Hz Hermite Spline supersampling
            self.hermite_spline.add_waypoint(screen_x, screen_y, timestamp=timestamp)
            self._hermite_last_waypoint_time = timestamp

            # Sub-millisecond ML Gesture Classification telemetry
            try:
                ml_cls, ml_conf = self.ml_classifier.predict(right_hand.points)
                result_summary["ml_gesture"] = ml_cls
                result_summary["ml_confidence"] = round(float(ml_conf), 3)
            except Exception:
                pass

            result_summary["cursor_pos"] = (screen_x, screen_y)
            result_summary["magnetic_lock"] = locked_target
            result_summary["app_preset"] = active_preset.name

            # Two-Finger Kinetic Scroll with Momentum Decay + App Preset Multiplier
            is_scroll = action_state.get("is_scroll", False)
            scroll_y = action_state.get("scroll_y", norm_y)
            scroll_steps = self.scroll_ctrl.update(is_scroll, scroll_y, timestamp=timestamp)
            if scroll_steps != 0 and active_preset.scroll_multiplier != 1.0:
                scaled = int(round(scroll_steps * active_preset.scroll_multiplier))
                scroll_steps = scaled if scaled != 0 else scroll_steps

            if is_scroll:
                if scroll_steps != 0:
                    self.kernel.scroll(scroll_steps)
                    self.haptics.trigger(HapticCue.SCROLL_RATCHET)
                    result_summary["action_executed"] = f"TWO_FINGER_SCROLL_{scroll_steps}"
            else:
                if scroll_steps != 0:
                    self.kernel.scroll(scroll_steps)
                    self.haptics.trigger(HapticCue.SCROLL_RATCHET)
                    result_summary["action_executed"] = f"KINETIC_SCROLL_{scroll_steps}"

                # Only move cursor when not actively two-finger scrolling
                self.kernel.move_cursor(screen_x, screen_y)

            # AirCanvas Real-Time Inking & Laser Reticle
            if self.air_canvas:
                is_draw_down = action_state.get("is_pinching", False)
                self.air_canvas.update_cursor(screen_x, screen_y, is_drawing_down=is_draw_down)

            # Bimanual Spatial Zoom (Ctrl + Wheel)
            if left_hand is not None:
                zoom_steps = self.zoom_ctrl.update(right_hand, left_hand, timestamp=timestamp)
                if zoom_steps != 0:
                    self.kernel.zoom(zoom_steps)
                    result_summary["action_executed"] = f"BIMANUAL_ZOOM_{zoom_steps}"
            else:
                self.zoom_ctrl.reset()

            # 3-Finger Fluid Desktop & Mission Control Swipes
            swipe = self.swipe_detector.update(right_hand, timestamp=timestamp)
            if swipe:
                if swipe == "SWIPE_UP":
                    self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_TAB)
                    result_summary["action_executed"] = "TASK_VIEW"
                elif swipe == "SWIPE_DOWN":
                    self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_D)
                    result_summary["action_executed"] = "SHOW_DESKTOP"
                elif swipe == "SWIPE_LEFT":
                    self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_CONTROL, VirtualKey.VK_LEFT)
                    result_summary["action_executed"] = "DESKTOP_PREV"
                elif swipe == "SWIPE_RIGHT":
                    self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_CONTROL, VirtualKey.VK_RIGHT)
                    result_summary["action_executed"] = "DESKTOP_NEXT"

            # Continuous Media Scalar Control (Volume)
            if left_mode == HandMode.MEDIA_CONTROL:
                vol = self.media_ctrl.apply_volume(action_state["pinch_distance"])
                if vol is not None:
                    result_summary["action_executed"] = f"VOLUME_SCALAR_{int(vol * 100)}"

            # Fist-based Spatial Window Dragging
            fist_ev = action_state.get("fist_event")
            if fist_ev == "DRAG_START":
                hwnd = self.kernel.get_target_window_at_point_or_foreground(screen_x, screen_y)
                if hwnd:
                    if hasattr(self.kernel, "is_window_maximized") and self.kernel.is_window_maximized(hwnd) is True:
                        self.kernel.restore_window(hwnd)
                    rect = self.kernel.get_window_rect(hwnd)
                    self.dragger.start_drag(hwnd, rect, screen_x, screen_y)
                    result_summary["action_executed"] = "WINDOW_DRAG_START"
            elif action_state.get("is_fist") and self.dragger.is_dragging:
                hwnd, new_x, new_y, w, h = self.dragger.update_drag(screen_x, screen_y)
                if hwnd:
                    self.kernel.move_window(hwnd, new_x, new_y, w, h)
                    result_summary["action_executed"] = "WINDOW_DRAG_MOVE"
            elif fist_ev == "DRAG_END" and self.dragger.is_dragging:
                self.dragger.end_drag()
                result_summary["action_executed"] = "WINDOW_DRAG_END"

            # Handle Actions & Left-Hand Compound Modifiers
            if action_state["click_event"] == "LEFT_CLICK":
                self.haptics.trigger(HapticCue.MECHANICAL_CLICK)
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
                elif left_mode == HandMode.MEDIA_CONTROL:
                    # In continuous volume mode, pinch adjusts volume scalar without injecting synthetic mouse click
                    pass
                else:
                    self.kernel.click(left=True)
                    result_summary["action_executed"] = "MOUSE_LEFT_CLICK"

            elif action_state["right_click_event"] == "RIGHT_CLICK":
                self.haptics.trigger(HapticCue.MECHANICAL_CLICK)
                self.kernel.click(left=False)
                result_summary["action_executed"] = "MOUSE_RIGHT_CLICK"

            # Pinch-and-Hold Drag-and-Drop / Text Selection
            pinch_hold_ev = action_state.get("pinch_hold_event")
            if pinch_hold_ev == "PINCH_DOWN" and left_mode == HandMode.POINTER_NAV:
                self.kernel.mouse_down(left=True)
                result_summary["action_executed"] = "MOUSE_PINCH_HOLD_START"
            elif pinch_hold_ev == "PINCH_UP":
                self.kernel.mouse_up(left=True)
                result_summary["action_executed"] = "MOUSE_PINCH_HOLD_END"

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
            self.scroll_ctrl.reset()
            self.swipe_detector.reset()
            self.zoom_ctrl.reset()
            self.engine.pinch_streak = 0
            self.engine.middle_pinch_streak = 0
            self.engine.is_pinching = False
            if self.dragger.is_dragging:
                self.dragger.end_drag()

        return result_summary
