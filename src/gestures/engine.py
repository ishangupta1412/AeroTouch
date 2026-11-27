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
        """
        Pinch distance normalized by overall hand scale.
        Dampens monocular z-axis occlusion noise (0.25x weight) so thumb+index
        contact never fails to register due to webcam depth estimation spikes.
        """
        p1 = hand.thumb_tip
        p2 = hand.points[finger_idx]
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        dz = (p1[2] - p2[2]) * 0.25 if len(p1) > 2 and len(p2) > 2 else 0.0
        raw_dist = math.sqrt(dx * dx + dy * dy + dz * dz)
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
        Returns True ONLY when all 4 fingers (Index, Middle, Ring, Pinky) are deeply curled.
        A slight finger curl, pointing gesture, or pinch MUST NEVER trigger a fist.
        In a true fist, all fingertips curl inward so tip is strictly closer to wrist compared to PIP.
        """
        if cls.count_extended_fingers(hand) > 0:
            return False
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            d_tip = cls.euclidean_dist(hand.wrist, hand.points[tip])
            d_pip = cls.euclidean_dist(hand.wrist, hand.points[pip])
            if d_tip > d_pip * 0.82:
                return False
        return True

    @classmethod
    def is_peace_sign(cls, hand: HandLandmarks) -> bool:
        """
        Detects ✌️ Peace Sign ('V'):
        Index (8) and Middle (12) extended.
        Ring (16) and Pinky (20) curled.
        """
        index_ext = cls.is_finger_extended(hand, tip_idx=8, pip_idx=6)
        middle_ext = cls.is_finger_extended(hand, tip_idx=12, pip_idx=10)
        ring_ext = cls.is_finger_extended(hand, tip_idx=16, pip_idx=14)
        pinky_ext = cls.is_finger_extended(hand, tip_idx=20, pip_idx=18)
        return index_ext and middle_ext and not ring_ext and not pinky_ext

    @classmethod
    def is_three_fingers(cls, hand: HandLandmarks) -> bool:
        """
        Detects 3 fingers extended:
        Index (8), Middle (12), and Ring (16) extended.
        Pinky (20) curled.
        """
        index_ext = cls.is_finger_extended(hand, tip_idx=8, pip_idx=6)
        middle_ext = cls.is_finger_extended(hand, tip_idx=12, pip_idx=10)
        ring_ext = cls.is_finger_extended(hand, tip_idx=16, pip_idx=14)
        pinky_ext = cls.is_finger_extended(hand, tip_idx=20, pip_idx=18)
        return index_ext and middle_ext and ring_ext and not pinky_ext

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
        pinch_threshold: float = 0.36,
        release_threshold: float = 0.46,
        debounce_seconds: float = 0.15,
        confirm_frames: int = 2,
        pre_pinch_threshold: float = 0.50,
        hold_threshold_seconds: float = 0.24,
    ):
        self.pinch_threshold = pinch_threshold
        self.release_threshold = release_threshold
        self.debounce_seconds = debounce_seconds
        self.confirm_frames = confirm_frames
        self.pre_pinch_threshold = pre_pinch_threshold
        self.hold_threshold_seconds = hold_threshold_seconds

        self.is_pinching: bool = False
        self.pinch_streak: int = 0
        self.middle_pinch_streak: int = 0
        self.last_click_time: float = 0.0
        self.current_left_mode: HandMode = HandMode.POINTER_NAV

        # Pinch-drift stabilization & pinch-hold drag state
        self._pinch_anchor: Optional[Tuple[float, float]] = None
        self._last_stable_cursor: Optional[Tuple[float, float]] = None
        self._prev_norm_pinch: Optional[float] = None
        self._pinch_start_time: float = 0.0
        self._is_pinch_holding: bool = False
        self._last_click_was_left: bool = False

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

        if GestureMath.is_fist(left_hand):
            self.current_left_mode = HandMode.WINDOW_SNAP
        elif GestureMath.is_peace_sign(left_hand):
            self.current_left_mode = HandMode.MEDIA_CONTROL
        elif GestureMath.is_three_fingers(left_hand):
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
        pinch_hold_event = None

        # Fist Detection State Machine
        raw_is_fist = GestureMath.is_fist(right_hand)

        # Critical: If the user is actively pinching (Index + Thumb OR Middle + Thumb),
        # it is a click intent — override any false fist trigger so clicking is NEVER blocked!
        MIDDLE_PINCH_THRESHOLD = self.pinch_threshold * 1.15  # Middle finger normalises higher anatomically
        if norm_pinch < self.pinch_threshold or norm_middle_pinch < MIDDLE_PINCH_THRESHOLD:
            raw_is_fist = False
            self.is_fist_active = False
            self.fist_streak = 0

        if raw_is_fist:
            self.fist_streak += 1
            self.fist_release_streak = 0
            if self.fist_streak >= self._fist_confirm_frames and not self.is_fist_active:
                self.is_fist_active = True
                fist_event = "DRAG_START"
        else:
            self.fist_release_streak += 1
            self.fist_streak = 0
            if self.fist_release_streak >= 2 and self.is_fist_active:
                self.is_fist_active = False
                fist_event = "DRAG_END"

        # Clean mutual exclusivity based on anatomical proximity to thumb:
        # If middle finger is closer to thumb than index: Right Click candidate
        # If index finger is closer to thumb (or equal): Left Click candidate
        # MIDDLE_PINCH_THRESHOLD accounts for middle finger being anatomically longer.
        is_index_candidate = (
            (norm_pinch < self.pinch_threshold)
            and (norm_pinch <= norm_middle_pinch)
            and not self.is_fist_active
        )
        is_middle_candidate = (
            (norm_middle_pinch < MIDDLE_PINCH_THRESHOLD)
            and (norm_middle_pinch < norm_pinch)
            and not self.is_fist_active
        )

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
                    self._pinch_start_time = now
                    self._is_pinch_holding = False
                    self._last_click_was_left = True
                    click_event = "LEFT_CLICK"
                # Right Click verified over confirmed frames
                elif self.middle_pinch_streak >= self.confirm_frames:
                    self.is_pinching = True
                    self.last_click_time = now
                    self._pinch_start_time = now
                    self._is_pinch_holding = False
                    self._last_click_was_left = False
                    right_click_event = "RIGHT_CLICK"
        else:
            # Release pinch state cleanly as soon as the active pinching finger separates
            released = (
                (norm_pinch > self.release_threshold)
                if self._last_click_was_left
                else (norm_middle_pinch > self.release_threshold)
            )
            if released:
                if self._is_pinch_holding:
                    self._is_pinch_holding = False
                    pinch_hold_event = "PINCH_UP"
                self.is_pinching = False
                self.pinch_streak = 0
                self.middle_pinch_streak = 0
                self._pinch_anchor = None
            elif (
                self._last_click_was_left
                and not self._is_pinch_holding
                and (now - self._pinch_start_time) >= self.hold_threshold_seconds
                and norm_pinch <= self.release_threshold
            ):
                # Sustained left pinch transitions into drag-and-drop / text-selection hold
                self._is_pinch_holding = True
                pinch_hold_event = "PINCH_DOWN"

        # Pinch-Drift Stabilization: lock cursor to pre-pinch position as soon as fingers close
        closing_pinch = (
            self._prev_norm_pinch is not None
            and norm_pinch < (self._prev_norm_pinch - 0.025)
            and norm_pinch < 0.65
        )
        self._prev_norm_pinch = norm_pinch

        approaching_pinch = (
            (norm_pinch < self.pre_pinch_threshold or norm_middle_pinch < self.pre_pinch_threshold or closing_pinch)
            and not self.is_fist_active
        )
        if (approaching_pinch or self.is_pinching) and not self._is_pinch_holding:
            if self._pinch_anchor is None:
                self._pinch_anchor = self._last_stable_cursor if self._last_stable_cursor is not None else (raw_x, raw_y)
            raw_x, raw_y = self._pinch_anchor
        elif not approaching_pinch and not self.is_pinching:
            self._pinch_anchor = None
            self._last_stable_cursor = (raw_x, raw_y)

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
            "approaching_pinch": approaching_pinch,
            "is_pinch_holding": self._is_pinch_holding,
            "pinch_hold_event": pinch_hold_event,
            "is_scroll": is_scroll,
            "scroll_y": scroll_y,
            "is_fist": self.is_fist_active,
            "fist_event": fist_event,
            "click_event": click_event,
            "right_click_event": right_click_event,
            "left_mode": self.current_left_mode
        }
