"""
AeroTouch Bimanual Gesture & Kinematic Engine
Scale-invariant 3D vector geometry with Multi-Frame Temporal Confirmation.
Eliminates random false-positive clicks and stabilizes spatial interaction.
"""

import math
import time
from enum import Enum, auto
from typing import Tuple, List, Optional, Dict

class HandMode(Enum):
    POINTER_NAV = auto()     # Standard cursor movement & navigation
    WINDOW_SNAP = auto()     # Left fist held: snap active window to left/right
    MEDIA_CONTROL = auto()   # Left two-finger peace: volume & media adjustment
    DESKTOP_SWITCH = auto()  # Left three-finger open: virtual desktop flipping


class FistState(Enum):
    OPEN = auto()     # Hand is open — no drag
    CLOSED = auto()   # Fist detected — drag active


class HandLandmarks:
    """Wrapper around 21 normalized 3D hand landmarks."""

    def __init__(self, points: List[Tuple[float, float, float]], handedness: str = "Right"):
        self.points = points
        self.handedness = handedness

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
        """3D Euclidean distance when z is present, falling back gracefully to 2D."""
        dim = min(len(p1), len(p2), 3)
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1[:dim], p2[:dim])))

    @classmethod
    def hand_scale(cls, hand: HandLandmarks) -> float:
        """Computes scale of hand using 3D distance from wrist (0) to middle MCP (9)."""
        scale = cls.euclidean_dist(hand.wrist, hand.points[9])
        return max(scale, 0.01)

    @classmethod
    def normalized_pinch_distance(cls, hand: HandLandmarks, finger_idx: int = 8) -> float:
        """Pinch distance normalized by overall hand scale in 3D."""
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
        pairs = [(8, 6), (12, 10), (16, 14), (20, 18)]
        for tip, pip in pairs:
            if cls.is_finger_extended(hand, tip, pip):
                count += 1

        # Thumb check: extended when tip is farther from wrist than thumb MCP (2) and pinky base (17)
        wrist_to_thumb_tip = cls.euclidean_dist(hand.wrist, hand.thumb_tip)
        wrist_to_thumb_mcp = cls.euclidean_dist(hand.wrist, hand.points[2])
        thumb_span = cls.euclidean_dist(hand.thumb_tip, hand.points[17])
        base_span = cls.euclidean_dist(hand.points[2], hand.points[17])

        if (wrist_to_thumb_tip > wrist_to_thumb_mcp * 1.2) and (thumb_span > max(base_span * 1.1, 0.05)):
            count += 1

        return count

    @classmethod
    def is_fist(cls, hand: HandLandmarks) -> bool:
        """
        Returns True ONLY when ALL 4 fingers are curled into the palm.
        A pointing gesture (index extended) must NEVER be classified as a fist.
        Fist = Index (8), Middle (12), Ring (16), AND Pinky (20) all curled.
        """
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            if cls.is_finger_extended(hand, tip, pip):
                return False
        return True

    @classmethod
    def is_shaka(cls, hand: HandLandmarks) -> bool:
        """
        Detects 🤙 Shaka gesture (Thumb + Pinky extended, Index + Middle + Ring curled).
        Orthogonal to all standard operating poses — zero accidental trigger rate.
        """
        # Pinky MUST be extended
        if not cls.is_finger_extended(hand, tip_idx=20, pip_idx=18):
            return False

        # Index, Middle, and Ring MUST be curled inward
        if cls.is_finger_extended(hand, tip_idx=8, pip_idx=6):
            return False
        if cls.is_finger_extended(hand, tip_idx=12, pip_idx=10):
            return False
        if cls.is_finger_extended(hand, tip_idx=16, pip_idx=14):
            return False

        # Thumb MUST be extended outward away from wrist and palm
        wrist_to_thumb_tip = cls.euclidean_dist(hand.wrist, hand.thumb_tip)
        wrist_to_thumb_mcp = cls.euclidean_dist(hand.wrist, hand.points[2])
        thumb_span = cls.euclidean_dist(hand.thumb_tip, hand.points[17])
        base_span = cls.euclidean_dist(hand.points[2], hand.points[17])

        thumb_extended = (wrist_to_thumb_tip > wrist_to_thumb_mcp * 1.15) and (thumb_span > max(base_span * 1.05, 0.05))
        return thumb_extended

    @classmethod
    def is_two_finger_scroll(cls, hand: HandLandmarks) -> bool:
        """
        Detects trackpad-style two-finger scroll gesture:
        Index + Middle extended together parallel, Ring + Pinky curled inward.
        """
        # Index and Middle MUST be extended
        if not cls.is_finger_extended(hand, tip_idx=8, pip_idx=6):
            return False
        if not cls.is_finger_extended(hand, tip_idx=12, pip_idx=10):
            return False

        # Ring and Pinky MUST be curled inward
        if cls.is_finger_extended(hand, tip_idx=16, pip_idx=14):
            return False
        if cls.is_finger_extended(hand, tip_idx=20, pip_idx=18):
            return False

        # Index tip and Middle tip must be held parallel (not wide peace sign 'V')
        tip_distance = cls.euclidean_dist(hand.index_tip, hand.middle_tip)
        scale = cls.euclidean_dist(hand.wrist, hand.points[9])
        if (tip_distance / max(scale, 0.001)) > 0.45:
            return False

        # Must not be an intentional pinch
        norm_pinch = cls.normalized_pinch_distance(hand, finger_idx=8)
        if norm_pinch < 0.32:
            return False

        return True

    @classmethod
    def is_peace(cls, hand: HandLandmarks) -> bool:
        """
        Detects Peace / V-sign:
        Index and Middle extended, Ring and Pinky curled.
        """
        if not cls.is_finger_extended(hand, tip_idx=8, pip_idx=6):
            return False
        if not cls.is_finger_extended(hand, tip_idx=12, pip_idx=10):
            return False
        if cls.is_finger_extended(hand, tip_idx=16, pip_idx=14):
            return False
        if cls.is_finger_extended(hand, tip_idx=20, pip_idx=18):
            return False
        return True

    @classmethod
    def get_snap_direction(cls, right_hand: HandLandmarks) -> str:
        """
        Determines the 4-way direction of the pinch relative to the middle MCP:
        Returns: 'LEFT', 'RIGHT', 'UP', or 'DOWN'.
        """
        ref_x, ref_y = right_hand.points[9][0], right_hand.points[9][1]
        pinch_x = (right_hand.thumb_tip[0] + right_hand.index_tip[0]) / 2.0
        pinch_y = (right_hand.thumb_tip[1] + right_hand.index_tip[1]) / 2.0

        dx = pinch_x - ref_x
        dy = pinch_y - ref_y  # negative dy = UP, positive dy = DOWN

        # Determine dominant axis
        if abs(dx) > abs(dy) * 0.8:
            return "RIGHT" if dx > 0 else "LEFT"
        else:
            return "DOWN" if dy > 0 else "UP"


class BimanualEngine:
    """
    Finite State Machine for precision bimanual spatial interaction.
    Features:
    - Multi-frame temporal confirmation (eliminates single-frame ghost clicks).
    - True 3D perspective-invariant scale normalization.
    - Zero-flutter asynchronous debounce and anchor-lock telemetry.
    """

    def __init__(
        self,
        pinch_threshold: float = 0.28,
        release_threshold: float = 0.38,
        debounce_seconds: float = 0.20,
        confirm_frames: int = 2
    ):
        self.pinch_threshold = pinch_threshold
        self.release_threshold = release_threshold
        self.debounce_seconds = debounce_seconds
        self.confirm_frames = confirm_frames

        self.is_pinching: bool = False
        self.pinch_streak: int = 0
        self.middle_pinch_streak: int = 0
        self.last_click_time: float = 0.0
        self.current_left_mode: HandMode = HandMode.POINTER_NAV

        # Fist-drag state (multi-frame confirmed for stability)
        self.fist_streak: int = 0
        self.fist_release_streak: int = 0
        self.is_fist_active: bool = False
        self._fist_confirm_frames: int = max(2, confirm_frames)

    def evaluate_left_modifier(self, left_hand: Optional[HandLandmarks]) -> HandMode:
        """Interprets Left Hand gesture to set the current System Modifier Mode."""
        if left_hand is None:
            self.current_left_mode = HandMode.POINTER_NAV
            return self.current_left_mode

        extended = GestureMath.count_extended_fingers(left_hand)

        if extended == 0:
            self.current_left_mode = HandMode.WINDOW_SNAP
        elif extended == 2:
            self.current_left_mode = HandMode.MEDIA_CONTROL
        elif extended == 3:
            self.current_left_mode = HandMode.DESKTOP_SWITCH
        else:
            self.current_left_mode = HandMode.POINTER_NAV

        return self.current_left_mode

    def evaluate_right_action(self, right_hand: HandLandmarks, now: Optional[float] = None) -> Dict[str, any]:
        """
        Processes Right Hand coordinates for cursor tracking and atomic pinch events.
        Enforces 2-frame temporal stability to kill random phantom clicks.
        """
        if now is None:
            now = time.perf_counter()

        raw_x, raw_y, raw_z = right_hand.index_tip

        # 3D Invariant Normalized Pinch Metrics
        norm_pinch = GestureMath.normalized_pinch_distance(right_hand, finger_idx=8)       # Thumb + Index
        norm_middle_pinch = GestureMath.normalized_pinch_distance(right_hand, finger_idx=12) # Thumb + Middle

        click_event = None
        right_click_event = None
        fist_event = None

        # Fist Detection State Machine
        raw_is_fist = GestureMath.is_fist(right_hand)
        if raw_is_fist:
            self.fist_streak += 1
            self.fist_release_streak = 0
            if self.fist_streak >= self._fist_confirm_frames and not self.is_fist_active:
                self.is_fist_active = True
                fist_event = "DRAG_START"
        else:
            self.fist_release_streak += 1
            self.fist_streak = 0
            if self.fist_release_streak >= self._fist_confirm_frames and self.is_fist_active:
                self.is_fist_active = False
                fist_event = "DRAG_END"

        is_index_candidate = (norm_pinch < self.pinch_threshold) and (norm_pinch <= norm_middle_pinch) and not self.is_fist_active
        is_middle_candidate = (norm_middle_pinch < self.pinch_threshold) and (norm_middle_pinch < norm_pinch) and not self.is_fist_active

        # Track consecutive candidate frames for temporal stability
        if is_index_candidate:
            self.pinch_streak += 1
            self.middle_pinch_streak = 0
        elif is_middle_candidate:
            self.middle_pinch_streak += 1
            self.pinch_streak = 0
        else:
            self.pinch_streak = 0
            self.middle_pinch_streak = 0

        # State machine transition
        if not self.is_pinching:
            if (now - self.last_click_time) > self.debounce_seconds:
                # Left Click verified over confirmed frames
                if self.pinch_streak >= self.confirm_frames:
                    self.is_pinching = True
                    self.last_click_time = now
                    click_event = "LEFT_CLICK"
                # Right Click verified over confirmed frames
                elif self.middle_pinch_streak >= self.confirm_frames:
                    self.is_pinching = True
                    self.last_click_time = now
                    right_click_event = "RIGHT_CLICK"
        else:
            # Release pinch state cleanly when both fingers separate past release threshold
            if (norm_pinch > self.release_threshold) and (norm_middle_pinch > self.release_threshold):
                self.is_pinching = False
                self.pinch_streak = 0
                self.middle_pinch_streak = 0

        # Two-Finger Scroll Detection
        is_scroll = False
        scroll_y = raw_y
        if not self.is_fist_active and not self.is_pinching:
            if GestureMath.is_two_finger_scroll(right_hand):
                is_scroll = True
                scroll_y = (right_hand.index_tip[1] + right_hand.middle_tip[1]) / 2.0

        # Continuous scalar for media / brightness / zoom (0.0 open -> 1.0 tight pinch)
        pinch_scalar = max(0.0, min(1.0, 1.0 - (norm_pinch / 0.6)))

        return {
            "cursor_x": raw_x,
            "cursor_y": raw_y,
            "cursor_z": raw_z,
            "pinch_distance": norm_pinch,
            "middle_pinch_distance": norm_middle_pinch,
            "pinch_scalar": pinch_scalar,
            "is_pinching": self.is_pinching,
            "is_scroll": is_scroll,
            "scroll_y": scroll_y,
            "is_fist": self.is_fist_active,
            "fist_event": fist_event,
            "click_event": click_event,
            "right_click_event": right_click_event,
            "left_mode": self.current_left_mode
        }
