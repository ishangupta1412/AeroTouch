"""
Unit tests for AeroTouch Minecraft & FPS Sandbox Profile.
Tests camera aiming, mining/placing clicks, WASD movement, jumping, and sneaking.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gestures.engine import HandLandmarks
from src.games.profiles.minecraft import MinecraftProfile
from src.os_bridge.win32_kernel import VirtualKey


def make_minecraft_hand(
    x: float = 0.5,
    y: float = 0.5,
    is_index_pinch: bool = False,
    is_middle_pinch: bool = False,
    is_pinky_pinch: bool = False,
    is_fist: bool = False,
    is_peace: bool = False,
    handedness: str = "Right"
) -> HandLandmarks:
    points = [(x, y, 0.0)] * 21
    points[0] = (x, y + 0.15, 0.0)
    points[8] = (x, y - 0.05, 0.0)   # Index tip
    points[9] = (x, y, 0.0)          # Palm center
    points[12] = (x, y - 0.05, 0.0)  # Middle tip
    points[16] = (x, y - 0.05, 0.0)  # Ring tip
    points[20] = (x, y - 0.05, 0.0)  # Pinky tip

    if is_index_pinch:
        points[4] = (x, y, 0.0)
        points[8] = (x, y + 0.02, 0.0)
    elif is_middle_pinch:
        points[4] = (x, y, 0.0)
        points[12] = (x, y + 0.02, 0.0)
    elif is_pinky_pinch:
        points[4] = (x, y, 0.0)
        points[20] = (x, y + 0.02, 0.0)
    elif is_fist:
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            points[pip] = (x, y, 0.0)
            points[tip] = (x, y + 0.08, 0.0)
    elif is_peace:
        # Index and middle extended, ring and pinky curled
        points[8] = (x - 0.02, y - 0.1, 0.0)
        points[12] = (x + 0.02, y - 0.1, 0.0)
        points[6] = (x - 0.02, y - 0.02, 0.0)
        points[10] = (x + 0.02, y - 0.02, 0.0)
        points[16] = (x, y + 0.05, 0.0)
        points[20] = (x, y + 0.05, 0.0)
        points[14] = (x, y, 0.0)
        points[18] = (x, y, 0.0)
    else:
        points[4] = (x - 0.1, y, 0.0)

    return HandLandmarks(points=points, handedness=handedness)


class TestMinecraftProfile(unittest.TestCase):
    def setUp(self):
        self.profile = MinecraftProfile(action_cooldown=0.05)
        self.kernel = MagicMock()
        self.kernel.get_screen_resolution.return_value = (1920, 1080)

    def test_camera_aiming_and_look(self):
        r_hand = make_minecraft_hand(x=0.5, y=0.5, handedness="Right")
        self.profile.process_frame(r_hand, None, self.kernel, timestamp=1.0)
        self.kernel.move_cursor.assert_called()

    def test_mine_attack_left_click(self):
        # Index pinch -> mouse_down left
        r_pinch = make_minecraft_hand(x=0.5, y=0.5, is_index_pinch=True, handedness="Right")
        res = self.profile.process_frame(r_pinch, None, self.kernel, timestamp=1.0)
        self.assertTrue(any("MINE/ATTACK" in a for a in res["actions"]))
        self.kernel.mouse_down.assert_called_with(left=True)

        # Release pinch -> mouse_up left
        r_open = make_minecraft_hand(x=0.5, y=0.5, is_index_pinch=False, handedness="Right")
        self.profile.process_frame(r_open, None, self.kernel, timestamp=1.1)
        self.kernel.mouse_up.assert_called_with(left=True)

    def test_place_block_right_click(self):
        r_mid = make_minecraft_hand(x=0.5, y=0.5, is_middle_pinch=True, handedness="Right")
        res = self.profile.process_frame(r_mid, None, self.kernel, timestamp=1.0)
        self.assertTrue(any("PLACE/USE" in a for a in res["actions"]))
        self.kernel.click.assert_called_with(left=False)

    def test_left_hand_walk_forward(self):
        # dy < -0.12 (palm_y = 0.30 vs neutral 0.50)
        l_hand = make_minecraft_hand(x=0.5, y=0.30, handedness="Left")
        res = self.profile.process_frame(None, l_hand, self.kernel, timestamp=1.0)
        self.assertTrue(any("FORWARD" in a for a in res["actions"]))
        self.kernel.tap_key.assert_any_call(ord('W'), hold_seconds=0.06)

    def test_left_hand_jump_via_fist(self):
        l_fist = make_minecraft_hand(x=0.5, y=0.5, is_fist=True, handedness="Left")
        res = self.profile.process_frame(None, l_fist, self.kernel, timestamp=1.0)
        self.assertTrue(any("JUMP" in a for a in res["actions"]))
        self.kernel.tap_key.assert_any_call(VirtualKey.VK_SPACE, hold_seconds=0.06)

    def test_clean_exit_releases_held_mouse(self):
        r_pinch = make_minecraft_hand(x=0.5, y=0.5, is_index_pinch=True, handedness="Right")
        self.profile.process_frame(r_pinch, None, self.kernel, timestamp=1.0)
        self.assertTrue(self.profile._is_left_down)

        self.profile.on_exit(self.kernel)
        self.assertFalse(self.profile._is_left_down)
        self.kernel.mouse_up.assert_called_with(left=True)


if __name__ == "__main__":
    unittest.main()
