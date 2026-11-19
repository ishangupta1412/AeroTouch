"""
AeroTouch CLI & Execution Entrypoint
Starts the 60 FPS real-time touchless spatial OS control loop.
Zero-lag direct Win32 synthesis with Deadband Jitter Gate and Multi-Frame Confirmation.
Supports Ambient Floating Orb overlay (Gemini Live style).
Autonomous Qwen session telemetry self-tuner on session shutdown.
"""

import sys
import time
from typing import Optional
import cv2

from src.core.orchestrator import SpatialOrchestrator
from src.core.tracker import DualHandTracker
from src.telemetry.session_logger import SessionTelemetryLogger
from src.ui.floating_orb import FloatingOrbOverlay
from src.ui.hud import SpatialHUD


def run_aerotouch(camera_index: int = 0, use_orb: bool = False, show_preview: bool = True):
    print("=" * 65)
    print("      AEROTOUCH: AUTONOMOUS DUAL-HAND SPATIAL OPERATING LAYER     ")
    print("=" * 65)
    print("Status: Initializing Precision Spatial Hardware Bridge...")

    orchestrator = SpatialOrchestrator()
    w, h = orchestrator.kernel.get_screen_resolution()
    print(f"Hardware Monitor: {w}x{h} Native Win32 Subsystem Linked")

    tracker = DualHandTracker(num_hands=2)

    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 60)

    if not cap.isOpened():
        print(f"[ERROR]: Could not open webcam at index {camera_index}.")
        print("Please check webcam permissions or try index 1.")
        return

    # Initialize Telemetry Logger
    telemetry = SessionTelemetryLogger()
    telemetry.open()

    hud = SpatialHUD()

    orb: Optional[FloatingOrbOverlay] = None
    if use_orb:
        print("[UI]: Launching Ambient Floating Orb (Gemini Live Style)...")
        orb = FloatingOrbOverlay(size=88)
        orb.start()

    print("\n[ACTIVE]: AeroTouch Precision Spatial Engine Running. Press 'q' to stop.")
    print("Controls:")
    print("  * Move Right Index Finger: Move Mouse (Rock-Solid Deadband Filtering)")
    print("  * Right Thumb + Index Pinch: Intentional Left Click (Multi-Frame Confirmed)")
    print("  * Right Thumb + Middle Pinch: Right Click")
    print("  * Right Closed Fist: Grab & Drag Active Window in 3D")
    print("  * Left Hand Peace Sign ('V'): Continuous Volume Slider (Pinch tighter = Louder)")
    print("  * Left Hand Fist + Right Pinch: Snap Active Window Left")
    print("  * Left Hand 3-Fingers + Right Pinch: Switch Virtual Desktop")
    print("  * Press 'r': Toggle Live Gesture Stream Recording (Dataset Generator)\n")

    frame_count = 0
    start_time = time.time()
    current_fps = 60.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

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

            # Update Ambient Floating Orb
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
                cv2.imshow("AeroTouch Spatial Kernel [Press Q to Exit, R to Record]", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    is_rec = hud.recorder.toggle_recording()
                    status = "STARTED" if is_rec else "STOPPED"
                    print(f"\n[AeroTouch Studio]: Gesture Recording {status} -> {hud.recorder._current_file}")
            else:
                time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nStopping AeroTouch...")
    finally:
        cap.release()
        tracker.close()
        cv2.destroyAllWindows()
        if hud.recorder.is_recording:
            hud.recorder.stop_recording()
        if orb:
            orb.stop()
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


if __name__ == "__main__":
    args = sys.argv[1:]
    use_orb = "--orb" in args
    headless = "--headless" in args or ("--orb" in args and "--preview" not in args)
    show_preview = not headless

    cam_id = 0
    for a in args:
        if a.isdigit():
            cam_id = int(a)

    run_aerotouch(camera_index=cam_id, use_orb=use_orb, show_preview=show_preview)
