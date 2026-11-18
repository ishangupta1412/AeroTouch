"""
AeroTouch CLI & Execution Entrypoint
Starts the 60 FPS real-time touchless spatial OS control loop.
Zero-lag direct Win32 synthesis with 1-Euro adaptive jitter filtering.
"""

import sys
import time
import cv2

from src.core.orchestrator import SpatialOrchestrator
from src.core.tracker import DualHandTracker


def run_aerotouch(camera_index: int = 0):
    print("=" * 65)
    print("      AEROTOUCH: AUTONOMOUS DUAL-HAND SPATIAL OPERATING LAYER     ")
    print("=" * 65)
    print("Status: Initializing Spatial Hardware Bridge...")

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

    print("\n[ACTIVE]: AeroTouch Spatial Engine Running. Press 'q' to stop.")
    print("Controls:")
    print("  • Move Index Finger: Move Mouse")
    print("  • Thumb + Index Pinch: Instant Left Click")
    print("  • Thumb + Middle Pinch: Right Click")
    print("  • Left Hand Fist + Right Pinch: Snap Active Window Left")
    print("  • Left Hand 3-Fingers + Right Pinch: Switch Virtual Desktop\n")

    frame_count = 0
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            now = time.perf_counter()
            right_hand, left_hand = tracker.process_frame(frame)

            # Process full spatial frame
            result = orchestrator.process_spatial_frame(right_hand, left_hand, timestamp=now)

            # Real-time console click logging (zero latency)
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

            frame_count += 1
            if frame_count % 120 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"[AeroTouch Telemetry]: FPS: {fps:.1f} | Mode: {result['mode']} | Cursor: {result['cursor_pos']}")

            cv2.imshow("AeroTouch Spatial Kernel [Press Q to Exit]", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\nStopping AeroTouch...")
    finally:
        cap.release()
        tracker.close()
        cv2.destroyAllWindows()
        print("[AeroTouch]: Hardware links safely released.")


if __name__ == "__main__":
    cam_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    run_aerotouch(cam_id)
