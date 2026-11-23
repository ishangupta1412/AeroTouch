"""
Unit tests for AeroTouch Biomechanical Inverse Kinematics Engine.
Tests bone length calibration, rigid skeletal constraints, and jitter elimination.
"""

import math
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gestures.engine import HandLandmarks
from src.core.biomechanical_ik import BiomechanicalIKSolver, KINEMATIC_CHAINS


def make_clean_hand() -> HandLandmarks:
    # 21 points with standard spacing
    points = [(0.5, 0.7, 0.0)] * 21
    points[0] = (0.5, 0.7, 0.0)  # Wrist

    # Digits pointing upward
    for chain in KINEMATIC_CHAINS.values():
        for i, (parent, child) in enumerate(chain):
            py = points[parent][1] - 0.06
            px = points[parent][0]
            points[child] = (px, py, 0.0)

    return HandLandmarks(points=points, handedness="Right")


class TestBiomechanicalIK(unittest.TestCase):
    def setUp(self):
        self.solver = BiomechanicalIKSolver(calibration_frames=5)

    def test_calibration_phase(self):
        hand = make_clean_hand()
        self.assertFalse(self.solver.is_calibrated)

        for _ in range(4):
            self.solver.constrain_landmarks(hand)
            self.assertFalse(self.solver.is_calibrated)

        # 5th frame triggers calibration completion
        self.solver.constrain_landmarks(hand)
        self.assertTrue(self.solver.is_calibrated)
        self.assertIsNotNone(self.solver._calibrated_bone_lengths)

    def test_rigid_bone_length_invariance(self):
        hand = make_clean_hand()
        # Calibrate
        for _ in range(5):
            self.solver.constrain_landmarks(hand)

        calibrated_len = self.solver._calibrated_bone_lengths[(7, 8)]

        # Noisy frame where index tip (8) is stretched artificially by +0.04
        noisy_points = list(hand.points)
        noisy_points[8] = (noisy_points[7][0], noisy_points[7][1] - 0.10, 0.0)
        noisy_hand = HandLandmarks(points=noisy_points, handedness="Right")

        # Before constraint, bone length is 0.10
        raw_len = math.dist(noisy_points[7], noisy_points[8])
        self.assertAlmostEqual(raw_len, 0.10, places=3)

        # Apply constraint
        constrained_hand = self.solver.constrain_landmarks(noisy_hand)
        p7 = constrained_hand.points[7]
        p8 = constrained_hand.points[8]
        constrained_len = math.dist(p7, p8)

        # Must be restored exactly to calibrated rigid bone length
        self.assertAlmostEqual(constrained_len, calibrated_len, places=4)

    def test_reset(self):
        hand = make_clean_hand()
        for _ in range(5):
            self.solver.constrain_landmarks(hand)
        self.assertTrue(self.solver.is_calibrated)

        self.solver.reset()
        self.assertFalse(self.solver.is_calibrated)
        self.assertIsNone(self.solver._calibrated_bone_lengths)


if __name__ == "__main__":
    unittest.main()
