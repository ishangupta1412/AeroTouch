"""
AeroTouch Visual HUD & Gesture Recording Studio
Provides 60 FPS real-time color-coded skeleton overlays, gesture state badges,
pinch distance gauges, deadband stability indicators, and one-key gesture dataset recording.
"""

import json
import math
import os
import time
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from src.gestures.engine import HandLandmarks, HandMode


# MediaPipe 21 Landmark Connections
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),           # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),           # Index
    (5, 9), (9, 10), (10, 11), (11, 12),      # Middle
    (9, 13), (13, 14), (14, 15), (15, 16),    # Ring
    (13, 17), (17, 18), (18, 19), (19, 20),   # Pinky
    (0, 17)                                   # Palm base
]

# Color Palette (BGR)
COLOR_RIGHT_CYAN = (255, 215, 0)      # High-visibility Neon Cyan for Right Hand
COLOR_LEFT_AMBER = (0, 165, 255)      # Warm Neon Amber for Left Hand
COLOR_PINCH_LOCK = (0, 255, 128)      # Emerald Green on Click Confirmation
COLOR_PINCH_WARN = (0, 215, 255)      # Yellow on Approaching Pinch
COLOR_REC_RED = (50, 50, 240)         # Red recording beacon
COLOR_PANEL_BG = (20, 20, 20)         # Dark panel background


class GestureRecorder:
    """
    Records raw normalized 3D landmark streams for training and fine-tuning.
    Toggled on/off via 'R' key in the studio window.
    """

    def __init__(self, output_dir: Optional[str] = None):
        if output_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, "data", "recorded_gestures")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.is_recording: bool = False
        self._current_file: Optional[str] = None
        self._file_handle = None
        self.recorded_frames: int = 0

    def toggle_recording(self, label: str = "unlabeled") -> bool:
        """Toggles recording state. Returns True if now recording, False if stopped."""
        if self.is_recording:
            self.stop_recording()
            return False
        else:
            self.start_recording(label=label)
            return True

    def start_recording(self, label: str = "unlabeled") -> str:
        self.is_recording = True
        self.recorded_frames = 0
        ts = time.strftime("%Y%m%d_%H%M%S")
        self._current_file = os.path.join(self.output_dir, f"gesture_{label}_{ts}.jsonl")
        self._file_handle = open(self._current_file, "w", encoding="utf-8")
        return self._current_file

    def record_frame(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        action_state: Optional[Dict[str, any]] = None
    ) -> None:
        if not self.is_recording or self._file_handle is None:
            return

        frame_data = {
            "frame": self.recorded_frames + 1,
            "timestamp": time.time(),
            "right_hand": [p[:3] for p in right_hand.points] if right_hand else None,
            "left_hand": [p[:3] for p in left_hand.points] if left_hand else None,
            "action_state": action_state
        }
        self._file_handle.write(json.dumps(frame_data) + "\n")
        self._file_handle.flush()
        self.recorded_frames += 1

    def stop_recording(self) -> Optional[str]:
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        self.is_recording = False
        saved_path = self._current_file
        self._current_file = None
        return saved_path


class SpatialHUD:
    """
    High-performance, minimal HUD rendering hand tracking skeletons,
    spatial telemetry, pinch meters, and recording indicators.
    """

    def __init__(self):
        self.recorder = GestureRecorder()

    def draw_skeleton(
        self,
        frame: np.ndarray,
        hand: HandLandmarks,
        color: Tuple[int, int, int],
        is_right: bool = True
    ) -> None:
        """Renders 21 landmarks and skeletal connection lines."""
        h, w, _ = frame.shape
        pixel_points = []

        for p in hand.points:
            px = int(np.clip(p[0], 0.0, 1.0) * w)
            py = int(np.clip(p[1], 0.0, 1.0) * h)
            pixel_points.append((px, py))

        # Draw bones
        for start_idx, end_idx in HAND_CONNECTIONS:
            pt1 = pixel_points[start_idx]
            pt2 = pixel_points[end_idx]
            cv2.line(frame, pt1, pt2, color, 2, cv2.LINE_AA)

        # Draw joints
        for i, pt in enumerate(pixel_points):
            radius = 5 if i in (4, 8, 12, 16, 20) else 3
            cv2.circle(frame, pt, radius, color, -1, cv2.LINE_AA)
            cv2.circle(frame, pt, radius + 1, (20, 20, 20), 1, cv2.LINE_AA)

        # Handedness label at wrist
        wrist_pt = pixel_points[0]
        hand_name = "RIGHT (POINTER)" if is_right else "LEFT (MODIFIER)"
        cv2.putText(
            frame, hand_name, (wrist_pt[0] - 40, wrist_pt[1] + 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA
        )

    def render_hud(
        self,
        frame: np.ndarray,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        result: Dict[str, any],
        fps: float = 60.0
    ) -> np.ndarray:
        """Overlays studio HUD telemetry and hand skeletons onto camera frame."""
        h, w, _ = frame.shape

        # 1. Draw Hand Skeletons
        if right_hand is not None:
            self.draw_skeleton(frame, right_hand, COLOR_RIGHT_CYAN, is_right=True)

            # Draw Pinch Tether between Thumb (4) and Index (8)
            action_state = result.get("action_state") or {}
            norm_pinch = action_state.get("pinch_distance", 1.0)
            is_pinching = action_state.get("is_pinching", False)
            is_fist = action_state.get("is_fist", False)

            p_thumb = (int(right_hand.points[4][0] * w), int(right_hand.points[4][1] * h))
            p_index = (int(right_hand.points[8][0] * w), int(right_hand.points[8][1] * h))

            tether_color = COLOR_PINCH_LOCK if is_pinching else (
                COLOR_PINCH_WARN if norm_pinch < 0.35 else (180, 180, 180)
            )
            cv2.line(frame, p_thumb, p_index, tether_color, 2, cv2.LINE_AA)

            # Pinch distance text readout
            mid_x = (p_thumb[0] + p_index[0]) // 2
            mid_y = (p_thumb[1] + p_index[1]) // 2
            pinch_label = f"{norm_pinch:.2f}"
            if is_pinching:
                pinch_label += " [CLICK]"
            cv2.putText(frame, pinch_label, (mid_x + 8, mid_y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, tether_color, 1, cv2.LINE_AA)

            # Fist drag indicator
            if is_fist:
                wrist_pt = (int(right_hand.points[0][0] * w), int(right_hand.points[0][1] * h))
                cv2.circle(frame, wrist_pt, 40, (0, 200, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, "[WINDOW DRAG]", (wrist_pt[0] - 50, wrist_pt[1] - 45),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 2, cv2.LINE_AA)

        if left_hand is not None:
            self.draw_skeleton(frame, left_hand, COLOR_LEFT_AMBER, is_right=False)

            # Left Hand Mode Badge
            mode_name = result.get("mode", "POINTER_NAV")
            wrist_pt = (int(left_hand.points[0][0] * w), int(left_hand.points[0][1] * h))
            cv2.putText(frame, f"MODE: {mode_name}", (wrist_pt[0] - 50, wrist_pt[1] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_LEFT_AMBER, 2, cv2.LINE_AA)

        # 2. Studio Header Telemetry Bar
        panel_h = 36
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, panel_h), COLOR_PANEL_BG, -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Header Text
        status_text = f"AeroTouch Studio | {fps:.1f} FPS"
        if right_hand:
            status_text += " | Right: ACTIVE"
        else:
            status_text += " | Right: NONE"

        if left_hand:
            status_text += f" | Left: {result.get('mode', 'IDLE')}"

        action_exec = result.get("action_executed")
        if action_exec:
            status_text += f" | Event: {action_exec}"

        cv2.putText(frame, status_text, (12, 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)

        # 3. Recording Indicator
        if self.recorder.is_recording:
            pulse = int((time.time() * 3) % 2)
            rec_color = COLOR_REC_RED if pulse else (200, 200, 200)
            cv2.circle(frame, (w - 180, 18), 6, rec_color, -1)
            rec_text = f"REC [{self.recorder.recorded_frames} f] (Press R)"
            cv2.putText(frame, rec_text, (w - 165, 23),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, rec_color, 1, cv2.LINE_AA)
        else:
            cv2.putText(frame, "[R] Record Gesture", (w - 150, 23),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 140, 140), 1, cv2.LINE_AA)

        # Record frame if active
        if self.recorder.is_recording:
            self.recorder.record_frame(
                right_hand=right_hand,
                left_hand=left_hand,
                action_state=result.get("action_state")
            )

        return frame
