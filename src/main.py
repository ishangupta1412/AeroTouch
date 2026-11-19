"""
AeroTouch CLI & Execution Entrypoint
Starts the 60 FPS real-time touchless spatial OS control loop.
Zero-lag direct Win32 synthesis with Deadband Jitter Gate and Multi-Frame Confirmation.
Supports Ambient Floating Orb overlay (Gemini Live style).
Autonomous Qwen session telemetry self-tuner on session shutdown.
"""

import os
import sys

# Guarantee project root is in sys.path regardless of execution path
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

# Suppress native C++ MediaPipe/TensorFlow stderr spew in PowerShell/CMD
os.environ["GLOG_minloglevel"] = "2"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

try:
    # Ensure immediate terminal output on Windows
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

import time
from typing import Optional
import cv2

from src.core.orchestrator import SpatialOrchestrator
from src.core.tracker import DualHandTracker
from src.telemetry.session_logger import SessionTelemetryLogger
from src.ui.floating_orb import FloatingOrbOverlay
from src.ui.hud import SpatialHUD
from src.ui.dynamic_island import DynamicIslandOverlay
from src.ui.tray import AeroTouchTrayDaemon
from src.cortex.vision_analyst import RollingVisionAnalyst


def run_aerotouch(
    camera_index: int = 0,
    use_orb: bool = False,
    use_island: bool = True,
    show_preview: bool = True,
    use_tray: bool = False,
    use_vision: bool = True
):
    print("=" * 65)
    print("      AEROTOUCH: AUTONOMOUS DUAL-HAND SPATIAL OPERATING LAYER     ")
    print("=" * 65)
    print("Status: Initializing Precision Spatial Hardware Bridge...")

    orchestrator = SpatialOrchestrator()
    w, h = orchestrator.kernel.get_screen_resolution()
    print(f"Hardware Monitor: {w}x{h} Native Win32 Subsystem Linked")

    tracker = DualHandTracker(num_hands=2)

    def _init_camera(idx: int) -> Optional[cv2.VideoCapture]:
        # On Windows, prefer DirectShow (CAP_DSHOW) for zero matrix-stride assertion bugs and instant start
        backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if os.name == "nt" else [cv2.CAP_ANY]
        for backend in backends:
            c = cv2.VideoCapture(idx, backend)
            if c.isOpened():
                ret_ok, _ = c.read()
                if ret_ok:
                    c.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    c.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    c.set(cv2.CAP_PROP_FPS, 60)
                    return c
                c.release()
        return None

    cap = _init_camera(camera_index)
    if cap is None:
        fallback_idx = 1 if camera_index == 0 else 0
        print(f"[AeroTouch Vision]: Camera index {camera_index} unavailable, trying fallback index {fallback_idx}...")
        cap = _init_camera(fallback_idx)
        if cap is None:
            print(f"[ERROR]: Could not open webcam at index {camera_index} or {fallback_idx}.")
            print("Please check Windows camera privacy settings or close other camera apps.")
            return

    # Initialize Telemetry Logger
    telemetry = SessionTelemetryLogger()
    telemetry.open()

    hud = SpatialHUD()

    island: Optional[DynamicIslandOverlay] = None
    if use_island:
        print("[UI]: Launching Native Apple-Grade Dynamic Island Overlay...")
        island = DynamicIslandOverlay()
        island.start()

    orb: Optional[FloatingOrbOverlay] = None
    if use_orb:
        print("[UI]: Launching Ambient Floating Orb (Gemini Live Style)...")
        orb = FloatingOrbOverlay(size=88)
        orb.start()

    tray: Optional[AeroTouchTrayDaemon] = None
    exit_requested = False

    if use_tray:
        def _tray_toggle_pause():
            orchestrator.is_locked = not orchestrator.is_locked
            return orchestrator.is_locked

        def _tray_recalibrate():
            orchestrator.recalibrate()

        def _tray_cortex():
            try:
                from src.cortex.session_analyst import SessionAnalyst
                SessionAnalyst().analyze_latest_session()
            except Exception as e:
                print(f"[Tray Cortex Error]: {e}")

        def _tray_toggle_preview():
            nonlocal show_preview
            show_preview = not show_preview
            if not show_preview:
                cv2.destroyAllWindows()
            return show_preview

        def _tray_exit():
            nonlocal exit_requested
            exit_requested = True

        tray = AeroTouchTrayDaemon(
            on_toggle_pause=_tray_toggle_pause,
            on_recalibrate=_tray_recalibrate,
            on_cortex_tune=_tray_cortex,
            on_toggle_preview=_tray_toggle_preview,
            on_exit=_tray_exit
        )
        tray.start()
        tray.notify("AeroTouch", "Spatial Operating Layer running in background tray mode.")

    # ── Rolling Vision Intelligence Daemon ──────────────────────────────
    vision_analyst: Optional[RollingVisionAnalyst] = None
    if use_vision:
        print("[AeroTouch Cortex]: Starting Rolling Vision Intelligence daemon...")
        print("  Adaptive screen context analysis active (Win32 title analysis / Vision).")
        vision_analyst = RollingVisionAnalyst(
            on_params_updated=orchestrator.apply_context_profile,
            screenshot_interval=4.0,
            batch_size=10,
        )
        vision_analyst.start()

    print("\n[ACTIVE]: AeroTouch Precision Spatial Engine Running. Press 'q' to stop.")
    print("Controls:")
    print("  * Move Right Index Finger: Move Mouse (Rock-Solid Deadband Filtering)")
    print("  * Right Thumb + Index Pinch: Intentional Left Click (Multi-Frame Confirmed)")
    print("  * Right Thumb + Middle Pinch: Right Click")
    print("  * Right Closed Fist: Grab & Drag Active Window in 3D")
    print("  * Left Hand Peace Sign ('V'): Continuous Volume Slider (Pinch tighter = Louder)")
    print("  * Left Hand Fist + Right Pinch: Snap Active Window Left")
    print("  * Left Hand 3-Fingers + Right Pinch: Switch Virtual Desktop")
    print("  * 🤙 Shaka (Thumb + Pinky): Hold 0.6s to Pause / Resume AeroTouch")
    print("  * Press 'r': Toggle Live Gesture Stream Recording (Dataset Generator)\n")

    frame_count = 0
    start_time = time.time()
    current_fps = 60.0

    preview_window_name = "AeroTouch Spatial Kernel [Press Q to Exit, R to Record]"

    try:
        while not exit_requested:
            try:
                ret, frame = cap.read()
            except (cv2.error, Exception):
                time.sleep(0.01)
                continue

            if not ret or frame is None or getattr(frame, "size", 0) == 0:
                time.sleep(0.005)
                continue

            # Natural mirrored selfie view (OpenCV standard for interactive spatial control)
            frame = cv2.flip(frame, 1)

            now = time.perf_counter()
            right_hand, left_hand = tracker.process_frame(frame)

            # Process full spatial frame
            result = orchestrator.process_spatial_frame(right_hand, left_hand, timestamp=now)

            # Record telemetry for background Qwen kinematic self-tuning
            telemetry.log_frame(
                action_state=result.get("action_state"),
                cursor_pos=result.get("cursor_pos"),
                mode=result.get("mode", "POINTER_NAV"),
                action_executed=result.get("action_executed")
            )

            # Real-time console click logging
            action = result.get("action_executed")
            if action:
                ts = time.strftime('%H:%M:%S')
                if "LEFT_CLICK" in action:
                    print(f"[{ts}] >>> MOUSE LEFT CLICK <<<")
                elif "RIGHT_CLICK" in action:
                    print(f"[{ts}] >>> MOUSE RIGHT CLICK <<<")
                elif "SNAP" in action:
                    print(f"[{ts}] >>> WINDOW SNAP LEFT <<<")
                elif "DESKTOP" in action:
                    print(f"[{ts}] >>> NEXT VIRTUAL DESKTOP <<<")

            # Update Dynamic Island & Ambient Floating Orb
            if island:
                island.update_telemetry(
                    system_state=result.get("system_state", "ACTIVE"),
                    lock_progress=result.get("lock_progress", 0.0),
                    action_executed=action,
                    mode=result.get("mode", "POINTER_NAV")
                )

            if orb:
                is_tracking = (right_hand is not None or left_hand is not None)
                orb.set_state(is_tracking=is_tracking, action=action)

            frame_count += 1
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                current_fps = frame_count / max(elapsed, 0.001)

            if frame_count % 120 == 0:
                print(f"[AeroTouch Telemetry]: FPS: {current_fps:.1f} | Mode: {result['mode']} | Cursor: {result['cursor_pos']}")

            if show_preview:
                frame = hud.render_hud(frame, right_hand, left_hand, result, fps=current_fps)
                cv2.imshow(preview_window_name, frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord('q'), 27):  # 'q' or ESC only
                    break
                elif key == ord('r'):
                    is_rec = hud.recorder.toggle_recording()
                    status = "STARTED" if is_rec else "STOPPED"
                    print(f"\n[AeroTouch Studio]: Gesture Recording {status} -> {hud.recorder._current_file}")
                elif cv2.getWindowProperty(preview_window_name, cv2.WND_PROP_VISIBLE) < 1:
                    break
            else:
                time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nStopping AeroTouch...")
    except Exception as e:
        print(f"\n[AeroTouch Runtime Warning]: Handled stream interrupt: {e}")
    finally:
        if tray:
            tray.stop()
        cap.release()
        tracker.close()
        cv2.destroyAllWindows()
        if island:
            island.stop()
        if hud.recorder.is_recording:
            hud.recorder.stop_recording()
        if orb:
            orb.stop()
        if vision_analyst:
            vision_analyst.stop()
        telemetry.close()
        print("[AeroTouch]: Hardware links safely released.")

        # Trigger Autonomous Background Qwen Kinematic Optimization
        print("\n[AeroTouch Cortex]: Analyzing session telemetry with local Qwen coach...")
        try:
            from src.cortex.session_analyst import SessionAnalyst
            analyst = SessionAnalyst()
            tune_result = analyst.analyze_latest_session()
            status = tune_result.get("status")
            if status == "tuned":
                print(f"[Cortex Self-Tuning]: Adapted parameters: {tune_result.get('recommendations')}")
            else:
                reason = tune_result.get('reason', 'Precision nominal')
                print(f"[Cortex Self-Tuning]: Status: {status} ({reason})")
        except Exception as e:
            print(f"[Cortex Self-Tuning]: Analysis deferred ({e})")


def main():
    args = sys.argv[1:]
    use_orb = "--orb" in args
    use_island = "--no-island" not in args
    use_tray = "--tray" in args or "--background" in args
    headless = "--headless" in args or ("--orb" in args and "--preview" not in args)
    if use_tray and "--preview" not in args:
        headless = True
    show_preview = not headless
    use_vision = "--no-vision" not in args

    cam_id = 0
    for a in args:
        if a.isdigit():
            cam_id = int(a)

    run_aerotouch(
        camera_index=cam_id,
        use_orb=use_orb,
        use_island=use_island,
        show_preview=show_preview,
        use_tray=use_tray,
        use_vision=use_vision,
    )


if __name__ == "__main__":
    main()
