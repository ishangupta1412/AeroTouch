"""
AeroTouch Engagement Gating & Ergonomic Lap-Zone Engine
Solves the Gorilla Arm fatigue problem and Midas Touch accidental input problem:
1. Palm Normal 3D Orientation Gating: Differentiates intentional operational postures
   from casual movements (face scratching, drinking, typing).
2. Dual-Mode Tracking:
   - ABSOLUTE_LASER: 1:1 mapping for in-air presentations and canvas inking.
   - RELATIVE_CLUTCHED: Lap/Desk trackpad mode with micro-wrist clutching for 8-hour fatigue-free use.
"""

import math
from enum import Enum, auto
from typing import Optional, Tuple
from src.gestures.engine import HandLandmarks, GestureMath


class TrackingParadigm(Enum):
    ABSOLUTE_LASER = auto()     # 1:1 Screen mapping for presentations & canvas
    RELATIVE_CLUTCHED = auto()  # Sub-centimeter desk/lap trackpad with clutching


class EngagementGatingEngine:
    """
    Precision spatial engagement filter.
    Ensures cursor and OS interactions only occur when the user intentionally
    enters the operational engagement cone with their palm facing the display.
    """

    def __init__(
        self,
        alignment_threshold: float = 0.35,
        clutch_deadband: float = 0.0015,
        relative_sensitivity: float = 1.60,
    ):
        self.alignment_threshold = alignment_threshold
        self.clutch_deadband = clutch_deadband
        self.relative_sensitivity = relative_sensitivity
        self.current_paradigm: TrackingParadigm = TrackingParadigm.ABSOLUTE_LASER

        # State tracking for Relative Clutched Mode
        self._last_engaged_pos: Optional[Tuple[float, float]] = None
        self._is_clutched: bool = False
        self.engagement_confidence: float = 0.0

    def compute_palm_normal(self, hand: HandLandmarks) -> Tuple[float, float, float]:
        """
        Computes 3D unit normal vector of the palm plane via cross product:
        v1 = Index MCP (5) - Pinky MCP (17)
        v2 = Middle MCP (9) - Wrist (0)
        Normal = v1 x v2
        """
        p0 = hand.points[0]
        p5 = hand.points[5]
        p9 = hand.points[9]
        p17 = hand.points[17]

        # Vector across palm
        v1 = (p5[0] - p17[0], p5[1] - p17[1], p5[2] - p17[2])
        # Vector along palm
        v2 = (p9[0] - p0[0], p9[1] - p0[1], p9[2] - p0[2])

        # Cross product (v1 x v2)
        nx = v1[1] * v2[2] - v1[2] * v2[1]
        ny = v1[2] * v2[0] - v1[0] * v2[2]
        nz = v1[0] * v2[1] - v1[1] * v2[0]

        # Invert for left hand if needed to ensure normal points outward from palm
        if hand.handedness == "Left":
            nx, ny, nz = -nx, -ny, -nz

        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length < 1e-6:
            return (0.0, 0.0, 1.0)

        return (nx / length, ny / length, nz / length)

    def evaluate_engagement(self, hand: Optional[HandLandmarks]) -> Tuple[bool, float]:
        """
        Evaluates whether hand is in an intentional operational posture.
        Returns:
            (is_engaged: bool, confidence: float [0.0 - 1.0])
        """
        if hand is None:
            self._last_engaged_pos = None
            self.engagement_confidence = 0.0
            return False, 0.0

        # 1. 3D Palm Normal Orientation Score
        # In MediaPipe standard camera coordinates, negative Z points towards the camera.
        normal = self.compute_palm_normal(hand)
        # Normal Z component indicates whether palm faces camera
        palm_forward_score = max(0.0, min(1.0, -normal[2]))

        # 2. Finger Readiness Check
        # User is engaged if at least index finger is extended or in active pinch
        index_extended = GestureMath.is_finger_extended(hand, tip_idx=8, pip_idx=6)
        thumb_index_dist = GestureMath.euclidean_dist(hand.thumb_tip, hand.index_tip)
        is_pinch_ready = thumb_index_dist < 0.08

        readiness_score = 1.0 if (index_extended or is_pinch_ready) else 0.3

        # 3. Combined Engagement Confidence
        # Palm orientation weighted with posture readiness
        confidence = palm_forward_score * 0.65 + readiness_score * 0.35
        self.engagement_confidence = confidence

        is_engaged = confidence >= self.alignment_threshold
        if not is_engaged:
            self._last_engaged_pos = None

        return is_engaged, confidence

    def process_relative_motion(
        self,
        raw_x: float,
        raw_y: float,
        is_engaged: bool
    ) -> Optional[Tuple[float, float]]:
        """
        In Relative Clutched Mode:
        Computes delta displacement (dx, dy) when engaged.
        When disengaged (clutched), returns None without moving cursor,
        allowing user to lift/reposition hand effortlessly on the desk.
        """
        if not is_engaged:
            self._last_engaged_pos = None
            self._is_clutched = True
            return None

        if self._last_engaged_pos is None:
            self._last_engaged_pos = (raw_x, raw_y)
            self._is_clutched = False
            return None

        prev_x, prev_y = self._last_engaged_pos
        dx = (raw_x - prev_x) * self.relative_sensitivity
        dy = (raw_y - prev_y) * self.relative_sensitivity

        # Apply clutch deadband to cancel resting micro-twitches
        if abs(dx) < self.clutch_deadband and abs(dy) < self.clutch_deadband:
            dx, dy = 0.0, 0.0

        self._last_engaged_pos = (raw_x, raw_y)
        self._is_clutched = False
        return (dx, dy)

    def set_paradigm(self, paradigm: TrackingParadigm) -> None:
        """Switches between Absolute Laser and Relative Clutched Mode."""
        self.current_paradigm = paradigm
        self._last_engaged_pos = None
