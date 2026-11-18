"""
AeroTouch Gesture Recognition & Bimanual State Engine
Implements scale-invariant landmark geometry, dual-hand chording, and non-blocking hysteresis debouncing.
"""

import math
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


class HandMode(Enum):
    IDLE = auto()
    POINTER_NAV = auto()
    WINDOW_SNAP = auto()
    DESKTOP_SWITCH = auto()
    MEDIA_CONTROL = auto()
    EMERGENCY_DESKTOP = auto()


@dataclass
class HandLandmarks:
    """Canonical 21 3D landmarks for a single hand (normalized [0, 1])."""
    points: List[Tuple[float, float, float]]
    handedness: str  # 'Left' or 'Right' (from camera perspective)

    @property
    def wrist(self) -> Tuple[float, float, float]:
        return self.points[0]

    @property
    def thumb_tip(self) -> Tuple[float, float, float]:
        return self.points[4]

    @property
    def index_tip(self) -> Tuple[float, float, float]:
        return self.points[8]

    @property
    def middle_tip(self) -> Tuple[float, float, float]:
        return self.points[12]

    @property
    def ring_tip(self) -> Tuple[float, float, float]:
        return self.points[16]

    @property
    def pinky_tip(self) -> Tuple[float, float, float]:
        return self.points[20]


class GestureMath:
    """Scale-invariant 3D vector geometry for hand poses."""

    @staticmethod
    def euclidean_dist(p1: Tuple[float, float, ...], p2: Tuple[float, float, ...]) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1[:2], p2[:2])))

    @classmethod
    def hand_scale(cls, hand: HandLandmarks) -> float:
        """Computes scale of hand using distance from wrist (0) to middle MCP (9)."""
        scale = cls.euclidean_dist(hand.wrist, hand.points[9])
        return max(scale, 0.01)

    @classmethod
    def normalized_pinch_distance(cls, hand: HandLandmarks, finger_idx: int = 8) -> float:
        """Pinch distance normalized by overall hand scale."""
        raw_dist = cls.euclidean_dist(hand.thumb_tip, hand.points[finger_idx])
        return raw_dist / cls.hand_scale(hand)

    @classmethod
    def is_finger_extended(cls, hand: HandLandmarks, tip_idx: int, pip_idx: int) -> bool:
        """Tests if a finger is extended relative to the wrist."""
        wrist_to_tip = cls.euclidean_dist(hand.wrist, hand.points[tip_idx])
        wrist_to_pip = cls.euclidean_dist(hand.wrist, hand.points[pip_idx])
        return wrist_to_tip > wrist_to_pip * 1.15

    @classmethod
    def count_extended_fingers(cls, hand: HandLandmarks) -> int:
        """Returns count of extended fingers [0 to 5]."""
        count = 0
        # Check fingers: Index (8,6), Middle (12,10), Ring (16,14), Pinky (20,18)
        pairs = [(8, 6), (12, 10), (16, 14), (20, 18)]
        for tip, pip in pairs:
            if cls.is_finger_extended(hand, tip, pip):
                count += 1
        # Thumb check (4 vs 2)
        if cls.euclidean_dist(hand.thumb_tip, hand.points[17]) > cls.euclidean_dist(hand.points[2], hand.points[17]):
            count += 1
        return count


class BimanualEngine:
    """
    Coordinates Left-Hand Mode (Modifier) with Right-Hand Pointer & Actions.
    Solves the HandWave 3s freeze bug using asynchronous hysteresis debounce.
    """

    def __init__(self, pinch_threshold: float = 0.35, release_threshold: float = 0.40, debounce_seconds: float = 0.20):
        self.pinch_threshold = pinch_threshold
        self.release_threshold = release_threshold
        self.debounce_seconds = debounce_seconds

        self.is_pinching: bool = False
        self.last_click_time: float = 0.0
        self.current_left_mode: HandMode = HandMode.POINTER_NAV

    def evaluate_left_modifier(self, left_hand: Optional[HandLandmarks]) -> HandMode:
        """
        Interprets Left Hand gesture to set the current System Modifier Mode.
        """
        if left_hand is None:
            self.current_left_mode = HandMode.POINTER_NAV
            return self.current_left_mode

        extended = GestureMath.count_extended_fingers(left_hand)

        if extended == 0:
            # Closed Fist -> Grab Active Window Snap Mode
            self.current_left_mode = HandMode.WINDOW_SNAP
        elif extended == 2:
            # Peace sign -> Volume & Media Control Mode
            self.current_left_mode = HandMode.MEDIA_CONTROL
        elif extended == 3:
            # 3 Fingers -> Virtual Desktop Navigation Mode
            self.current_left_mode = HandMode.DESKTOP_SWITCH
        elif extended >= 5:
            # Open palm -> Standard Pointer Mode
            self.current_left_mode = HandMode.POINTER_NAV
        else:
            self.current_left_mode = HandMode.POINTER_NAV

        return self.current_left_mode

    def evaluate_right_action(self, right_hand: HandLandmarks, now: Optional[float] = None) -> Dict[str, any]:
        """
        Processes Right Hand coordinates for cursor tracking and atomic pinch events.
        """
        if now is None:
            now = time.perf_counter()

        # 1. Cursor Target Coordinate (Index Tip)
        raw_x, raw_y, raw_z = right_hand.index_tip

        # 2. Invariant Normalized Pinch Metrics
        norm_pinch = GestureMath.normalized_pinch_distance(right_hand, finger_idx=8)
        norm_middle_pinch = GestureMath.normalized_pinch_distance(right_hand, finger_idx=12)

        # 3. Non-blocking Hysteresis State Machine
        click_event = None
        right_click_event = None

        is_index_pinch = norm_pinch < self.pinch_threshold
        is_middle_pinch = norm_middle_pinch < self.pinch_threshold

        if not self.is_pinching:
            if (now - self.last_click_time) > self.debounce_seconds:
                # Left Click: Index + Thumb pinch
                if is_index_pinch and (norm_pinch <= norm_middle_pinch):
                    self.is_pinching = True
                    self.last_click_time = now
                    click_event = "LEFT_CLICK"
                # Right Click: Middle + Thumb pinch
                elif is_middle_pinch and (norm_middle_pinch < norm_pinch):
                    self.is_pinching = True
                    self.last_click_time = now
                    right_click_event = "RIGHT_CLICK"
        else:
            # Release pinch state smoothly when both fingers separate
            if norm_pinch > self.release_threshold and norm_middle_pinch > self.release_threshold:
                self.is_pinching = False

        return {
            "cursor_x": raw_x,
            "cursor_y": raw_y,
            "cursor_z": raw_z,
            "is_pinching": self.is_pinching,
            "click_event": click_event,
            "right_click_event": right_click_event,
            "left_mode": self.current_left_mode
        }
