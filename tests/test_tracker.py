import unittest
from unittest.mock import MagicMock
import numpy as np

from src.core.tracker import DualHandTracker
from src.gestures.engine import HandLandmarks
from src.core.orchestrator import SpatialOrchestrator


class TestDualHandTracker(unittest.TestCase):
    def setUp(self):
        # Initialize tracker with mocked detector to test pure logic without camera
        self.tracker = DualHandTracker.__new__(DualHandTracker)
        self.tracker.num_hands = 2
        self.tracker.mirrored = False  # Base mock tests use unmirrored convention
        self.tracker.detector = MagicMock()

    def _build_anatomical_hand(self, handedness="Right", face_back=False, wrist_x=0.5):
        """
        Builds a 3D biomechanically accurate hand skeleton.
        Wrist at (wrist_x, 0.8, 0.0)
        Middle MCP (9) at (wrist_x, 0.5, -0.02)
        Index MCP (5) and Pinky MCP (17) define transverse palm width.
        """
        points = [(wrist_x, 0.8, 0.0)] * 21
        points[0] = (wrist_x, 0.8, 0.0)      # Wrist
        points[9] = (wrist_x, 0.5, -0.02)    # Middle MCP

        if handedness == "Right":
            points[5] = (wrist_x - 0.06, 0.52, -0.01)   # Index MCP (radial side)
            points[17] = (wrist_x + 0.06, 0.52, -0.01)  # Pinky MCP (ulnar side)
            points[2] = (wrist_x - 0.08, 0.65, -0.04)   # Thumb MCP
            points[4] = (wrist_x - 0.12, 0.55, -0.05)   # Thumb Tip
        else:
            points[5] = (wrist_x + 0.06, 0.52, -0.01)   # Index MCP
            points[17] = (wrist_x - 0.06, 0.52, -0.01)  # Pinky MCP
            points[2] = (wrist_x + 0.08, 0.65, -0.04)   # Thumb MCP
            points[4] = (wrist_x + 0.12, 0.55, -0.05)   # Thumb Tip

        if face_back:
            # 180 degree rotation around Y (showing back of hand)
            center = np.array([wrist_x, 0.5, 0.0])
            R180 = np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]])
            rotated = []
            for p in points:
                rel = np.array(p) - center
                rot = R180 @ rel + center
                rotated.append((float(rot[0]), float(rot[1]), float(rot[2])))
            return rotated

        return points

    def test_anatomical_handedness_verification_right(self):
        pts_right = self._build_anatomical_hand("Right")
        verified = self.tracker._verify_anatomical_handedness(pts_right, "Right", score=0.90)
        self.assertEqual(verified, "Right")

    def test_anatomical_handedness_verification_left(self):
        pts_left = self._build_anatomical_hand("Left")
        verified = self.tracker._verify_anatomical_handedness(pts_left, "Left", score=0.90)
        self.assertEqual(verified, "Left")

    def test_right_hand_back_of_hand_stays_right(self):
        """CRITICAL: Showing the back of the Right hand must NEVER flip to Left."""
        pts_back = self._build_anatomical_hand("Right", face_back=True, wrist_x=0.7)
        # Even with low ML confidence, 3D chirality and spatial prior keep it as Right
        verified = self.tracker._verify_anatomical_handedness(pts_back, "Right", score=0.50)
        self.assertEqual(verified, "Right", "Back of right hand must remain classified as Right!")

    def test_single_left_hand_does_not_become_right(self):
        """CRITICAL: When only a left hand is present, right_hand MUST be None."""
        pts_left = self._build_anatomical_hand("Left", wrist_x=0.3)

        mock_lm = [MagicMock(x=p[0], y=p[1], z=p[2]) for p in pts_left]
        mock_result = MagicMock()
        mock_result.hand_landmarks = [mock_lm]
        mock_cat = MagicMock(category_name="Left", score=0.92)
        mock_result.handedness = [[mock_cat]]

        self.tracker.detector.detect.return_value = mock_result

        dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
        right_hand, left_hand = self.tracker.process_frame(dummy_img)

        self.assertIsNone(right_hand, "Left hand must NEVER be assigned to right_hand!")
        self.assertIsNotNone(left_hand)
        self.assertEqual(left_hand.handedness, "Left")

    def test_both_hands_simultaneous_detection(self):
        """Both hands visible: right_hand and left_hand are both returned simultaneously."""
        pts_left = self._build_anatomical_hand("Left", wrist_x=0.25)
        pts_right = self._build_anatomical_hand("Right", wrist_x=0.75)

        mock_lm_l = [MagicMock(x=p[0], y=p[1], z=p[2]) for p in pts_left]
        mock_lm_r = [MagicMock(x=p[0], y=p[1], z=p[2]) for p in pts_right]

        mock_result = MagicMock()
        mock_result.hand_landmarks = [mock_lm_l, mock_lm_r]
        mock_result.handedness = [
            [MagicMock(category_name="Left", score=0.88)],
            [MagicMock(category_name="Right", score=0.91)]
        ]

        self.tracker.detector.detect.return_value = mock_result

        dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
        right_hand, left_hand = self.tracker.process_frame(dummy_img)

        self.assertIsNotNone(right_hand, "Right hand must be detected in dual-hand view!")
        self.assertIsNotNone(left_hand, "Left hand must be detected in dual-hand view!")
        self.assertEqual(right_hand.handedness, "Right")
        self.assertEqual(left_hand.handedness, "Left")

    def test_both_hands_duplicate_label_resolution(self):
        """MediaPipe duplicate-label bug ([Right, Right]): spatial sorting resolves cleanly."""
        # Two hands: one on screen left (wrist_x=0.3), one on screen right (wrist_x=0.7)
        pts_screen_left = self._build_anatomical_hand("Left", wrist_x=0.30)
        pts_screen_right = self._build_anatomical_hand("Right", wrist_x=0.70)

        mock_lm_0 = [MagicMock(x=p[0], y=p[1], z=p[2]) for p in pts_screen_left]
        mock_lm_1 = [MagicMock(x=p[0], y=p[1], z=p[2]) for p in pts_screen_right]

        mock_result = MagicMock()
        mock_result.hand_landmarks = [mock_lm_0, mock_lm_1]
        # Both glitched to "Right"
        mock_result.handedness = [
            [MagicMock(category_name="Right", score=0.60)],
            [MagicMock(category_name="Right", score=0.65)]
        ]

        self.tracker.detector.detect.return_value = mock_result

        dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
        right_hand, left_hand = self.tracker.process_frame(dummy_img)

        self.assertIsNotNone(right_hand, "Spatial resolution must recover Right hand!")
        self.assertIsNotNone(left_hand, "Spatial resolution must recover Left hand!")
        self.assertEqual(right_hand.points[0][0], 0.70)
        self.assertEqual(left_hand.points[0][0], 0.30)

    def test_orchestrator_ignores_cursor_when_right_hand_is_none(self):
        """When right_hand is None, orchestrator must NOT move cursor or click."""
        orchestrator = SpatialOrchestrator()
        orchestrator.kernel.move_cursor = MagicMock()
        orchestrator.kernel.click = MagicMock()

        pts_left = self._build_anatomical_hand("Left", wrist_x=0.3)
        left_hand = HandLandmarks(points=pts_left, handedness="Left")

        res = orchestrator.process_spatial_frame(right_hand=None, left_hand=left_hand, timestamp=1.0)

        self.assertIsNone(res["cursor_pos"])
        orchestrator.kernel.move_cursor.assert_not_called()
        orchestrator.kernel.click.assert_not_called()

    def test_mirrored_webcam_right_hand_controls_pointer(self):
        """In mirrored selfie mode, user's physical right hand (MediaPipe label 'Left') must become right_hand."""
        self.tracker.mirrored = True
        pts_right_in_mirror = self._build_anatomical_hand("Right", wrist_x=0.7)

        mock_lm = [MagicMock(x=p[0], y=p[1], z=p[2]) for p in pts_right_in_mirror]
        mock_result = MagicMock()
        mock_result.hand_landmarks = [mock_lm]
        # MediaPipe sees mirrored right hand as "Left"
        mock_cat = MagicMock(category_name="Left", score=0.95)
        mock_result.handedness = [[mock_cat]]
        self.tracker.detector.detect.return_value = mock_result

        dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
        right_hand, left_hand = self.tracker.process_frame(dummy_img)

        self.assertIsNotNone(right_hand, "Mirrored user's right hand must be assigned to right_hand!")
        self.assertIsNone(left_hand)
        self.assertEqual(right_hand.handedness, "Right")

    def test_mirrored_webcam_left_hand_controls_modifier(self):
        """In mirrored selfie mode, user's physical left hand (MediaPipe label 'Right') must become left_hand."""
        self.tracker.mirrored = True
        pts_left_in_mirror = self._build_anatomical_hand("Left", wrist_x=0.3)

        mock_lm = [MagicMock(x=p[0], y=p[1], z=p[2]) for p in pts_left_in_mirror]
        mock_result = MagicMock()
        mock_result.hand_landmarks = [mock_lm]
        # MediaPipe sees mirrored left hand as "Right"
        mock_cat = MagicMock(category_name="Right", score=0.95)
        mock_result.handedness = [[mock_cat]]
        self.tracker.detector.detect.return_value = mock_result

        dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
        right_hand, left_hand = self.tracker.process_frame(dummy_img)

        self.assertIsNone(right_hand, "Mirrored user's left hand must NOT be assigned to right_hand!")
        self.assertIsNotNone(left_hand)
        self.assertEqual(left_hand.handedness, "Left")


if __name__ == "__main__":
    unittest.main()
