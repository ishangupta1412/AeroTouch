"""
AeroTouch CLI & Execution Entrypoint with Live Optical HUD Feedback
Displays real-time gesture telemetry, pinch distance indicators, and click notifications directly on the camera frame.
"""

import sys
import time
import cv2
import numpy as np

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
    print("  • Left Hand Fist + Right Pinch: Snap Window Left")
    print("  • Left Hand 3-Fingers + Right Pinch: Next Virtual Desktop\n")

    frame_count = 0
    start_time = time.time()
    last_click_display_time = 0.0
    last_click_label = ""
    last_click_color = (0, 255, 0)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Mirror frame horizontally for intuitive selfie view
            frame = cv2.flip(frame, 1)
            frame_h, frame_w = frame.shape[:2]

            now = time.perf_counter()
            right_hand, left_hand = tracker.process_frame(frame)

            # Process full spatial frame
            result = orchestrator.process_spatial_frame(right_hand, left_hand, timestamp=now)

            # Check if an action was executed to flash HUD notification
            action = result.get("action_executed")
            if action:
                last_click_display_time = now
                if "LEFT_CLICK" in action:
                    last_click_label = ">> LEFT CLICK <<"
                    last_click_color = (0, 255, 120)  # Neon Emerald
                elif "RIGHT_CLICK" in action:
                    last_click_label = ">> RIGHT CLICK <<"
                    last_click_color = (0, 180, 255)  # Amber Orange
                elif "SNAP" in action:
                    last_click_label = ">> WINDOW SNAP <<"
                    last_click_color = (255, 100, 200) # Purple
                elif "DESKTOP" in action:
                    last_click_label = ">> NEXT DESKTOP <<"
                    last_click_color = (255, 200, 0)   # Cyan

            # --- RENDER FUTURISTIC HUD OVERLAY ---
            # 1. Top HUD Bar
            cv2.rectangle(frame, (0, 0), (frame_w, 48), (15, 15, 20), -1)
            cv2.line(frame, (0, 48), (frame_w, 48), (50, 50, 65), 1)

            mode_text = f"MODE: {result['mode']}"
            cv2.putText(frame, "AEROTOUCH v1.0", (20, 32), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 240, 255), 2)
            cv2.putText(frame, mode_text, (240, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)

            # 2. Hand Landmarks & Pinch Visualizer
            act_state = result.get("action_state")
            if act_state and right_hand:
                # Right Hand Landmarks (in mirrored display coordinates)
                # In mirrored frame, x becomes (1.0 - raw_x)
                tx = int((1.0 - right_hand.thumb_tip[0]) * frame_w)
                ty = int(right_hand.thumb_tip[1] * frame_h)
                ix = int((1.0 - right_hand.index_tip[0]) * frame_w)
                iy = int(right_hand.index_tip[1] * frame_h)
                mx = int((1.0 - right_hand.middle_tip[0]) * frame_w)
                my = int(right_hand.middle_tip[1] * frame_h)

                pinch_dist = act_state.get("pinch_distance", 1.0)
                is_pinched = act_state.get("is_pinching", False)

                # Draw Thumb-to-Index line
                line_color = (0, 255, 120) if is_pinched else (180, 180, 180)
                thickness = 3 if is_pinched else 1
                cv2.line(frame, (tx, ty), (ix, iy), line_color, thickness)
                cv2.line(frame, (tx, ty), (mx, my), (100, 100, 200), 1)

                # Circles on fingertips
                cv2.circle(frame, (tx, ty), 6, (0, 255, 255), -1)  # Thumb Yellow
                cv2.circle(frame, (mx, my), 6, (0, 165, 255), -1)  # Middle Orange

                # Index Pointer Target Reticle
                reticle_color = (0, 255, 0) if is_pinched else (0, 240, 255)
                cv2.circle(frame, (ix, iy), 14, reticle_color, 2)
                cv2.circle(frame, (ix, iy), 4, reticle_color, -1)

                # Live Pinch Distance Metric
                cv2.putText(
                    frame,
                    f"Pinch: {pinch_dist:.2f} (Limit: 0.38)",
                    (ix + 20, iy - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 0) if pinch_dist < 0.38 else (200, 200, 200),
                    1
                )

            # 3. Flash Click Banner if recently fired (within 0.4s)
            if now - last_click_display_time < 0.4:
                cv2.rectangle(frame, (frame_w // 2 - 200, 60), (frame_w // 2 + 200, 115), (20, 20, 25), -1)
                cv2.rectangle(frame, (frame_w // 2 - 200, 60), (frame_w // 2 + 200, 115), last_click_color, 2)
                cv2.putText(
                    frame,
                    last_click_label,
                    (frame_w // 2 - 160, 98),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.8,
                    last_click_color,
                    2
                )

            # 4. Bottom Instructions Bar
            cv2.rectangle(frame, (0, frame_h - 32), (frame_w, frame_h), (15, 15, 20), -1)
            cv2.putText(
                frame,
                "PINCH Thumb+Index: Left Click | PINCH Thumb+Middle: Right Click | Left Fist: Snap Window | Q: Exit",
                (15, frame_h - 11),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (160, 160, 160),
                1
            )

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
