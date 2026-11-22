"""
Unit tests for AeroTouch Engagement Gating & Ergonomic Lap-Zone Engine.
Tests 3D palm normal calculation, Midas Touch gating, and Relative Clutched Mode.
"""

import math
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gestures.engine import HandLandmarks
from src.core.engagement import EngagementGatingEngine, TrackingParadigm


def make_test_hand(
    palm_normal_facing_camera: bool = True,
    index_extended: bool = True,
    handedness: str = "Right"
) -> HandLandmarks:
    # 21 landmarks
    points = [(0.5, 0.5, 0.0)] * 21
    points[0] = (0.5, 0.7, 0.0)    # Wrist

    if palm_normal_facing_camera:
        # Normal vector pointing towards -Z (camera)
        # v1 across palm: p5 (x=0.45, y=0.5, z=0) - p17 (x=0.55, y=0.5, z=0) -> dx = -0.1
        # v2 along palm: p9 (x=0.5, y=0.45, z=0) - p0 (x=0.5, y=0.7, z=0) -> dy = -0.25
        # v1 x v2 -> nz is negative (facing camera)
        points[5] = (0.45, 0.5, 0.0)
        points[9] = (0.50, 0.45, 0.0)
        points[17] = (0.55, 0.5, 0.0)
    else:
        # Palm facing down or away (+Z)
        points[5] = (0.55, 0.5, 0.0)
        points[9] = (0.50, 0.45, 0.0)
        points[17] = (0.45, 0.5, 0.0)

    if index_extended:
        points[6] = (0.48, 0.40, 0.0)
        points[8] = (0.48, 0.25, 0.0)
    else:
        points[6] = (0.48, 0.40, 0.0)
        points[8] = (0.48, 0.50, 0.0)

    return HandLandmarks(points=points, handedness=handedness)


class TestEngagementGatingEngine(unittest.TestCase):
    def setUp(self):
        self.engine = EngagementGatingEngine(alignment_threshold=0.30)

    def test_none_hand_disengaged(self):
        engaged, conf = self.engine.evaluate_engagement(None)
        self.assertFalse(engaged)
        self.assertEqual(conf, 0.0)

    def test_forward_palm_engaged(self):
        hand = make_test_hand(palm_normal_facing_camera=True, index_extended=True)
        engaged, conf = self.engine.evaluate_engagement(hand)
        self.assertTrue(engaged)
        self.assertGreaterEqual(conf, 0.30)

    def test_relative_motion_delta(self):
        self.engine.set_paradigm(TrackingParadigm.RELATIVE_CLUTCHED)
        # First frame anchors position
        delta1 = self.engine.process_relative_motion(0.5, 0.5, is_engaged=True)
        self.assertIsNone(delta1)

        # Second frame moves to 0.52, 0.51
        delta2 = self.engine.process_relative_motion(0.52, 0.51, is_engaged=True)
        self.assertIsNotNone(delta2)
        dx, dy = delta2
        self.assertGreater(dx, 0.0)
        self.assertGreater(dy, 0.0)

    def test_clutch_release_and_reengage(self):
        self.engine.set_paradigm(TrackingParadigm.RELATIVE_CLUTCHED)
        self.engine.process_relative_motion(0.5, 0.5, is_engaged=True)
        self.engine.process_relative_motion(0.52, 0.5, is_engaged=True)

        # Disengage (clutch)
        delta_clutched = self.engine.process_relative_motion(0.8, 0.8, is_engaged=False)
        self.assertIsNone(delta_clutched)
        self.assertTrue(self.engine._is_clutched)

        # Re-engage at new position on desk: must anchor without sudden jump!
        delta_reengaged = self.engine.process_relative_motion(0.3, 0.3, is_engaged=True)
        self.assertIsNone(delta_reengaged)
        self.assertFalse(self.engine._is_clutched)


if __name__ == "__main__":
    unittest.main()
