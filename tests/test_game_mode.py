"""
Unit tests for AeroTouch Game Mode & Fist Bump (🤜🤛) Trigger Engine.
Tests dwell collision physics, refractory cooldowns, game profile registration,
and spatial orchestrator dispatch without touching real hardware.
"""

import math
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gestures.engine import HandLandmarks
from src.games.trigger import FistBumpTrigger
from src.games.engine import GameEngine, DefaultArcadeProfile
from src.games.base_profile import BaseGameProfile


def make_test_hand(cx: float = 0.5, cy: float = 0.5, is_fist: bool = True, handedness: str = "Right") -> HandLandmarks:
    """Helper creating a test hand landmarks object."""
    points = [(cx, cy, 0.0)] * 21
    # Wrist
    points[0] = (cx, cy + 0.2, 0.0)

    if is_fist:
        # All 4 fingertips curled below PIP joints
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            points[pip] = (cx, cy, 0.0)
            points[tip] = (cx, cy + 0.08, 0.0)
    else:
        # Open hand: fingertips extended above PIP joints
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            points[pip] = (cx, cy + 0.05, 0.0)
            points[tip] = (cx, cy - 0.05, 0.0)

    # Landmark 5 (Index MCP) and 9 (Middle MCP)
    points[5] = (cx - 0.02, cy, 0.0)
    points[9] = (cx, cy, 0.0)

    return HandLandmarks(points=points, handedness=handedness)


class TestFistBumpTrigger(unittest.TestCase):
    def setUp(self):
        self.trigger = FistBumpTrigger(
            bump_distance_threshold=0.16,
            dwell_duration=0.35,
            cooldown=1.2
        )

    def test_single_hand_does_not_trigger(self):
        r_fist = make_test_hand(cx=0.5, is_fist=True, handedness="Right")
        triggered, progress = self.trigger.update(r_fist, None, timestamp=1.0)
        self.assertFalse(triggered)
        self.assertEqual(progress, 0.0)

    def test_open_hands_do_not_trigger(self):
        # Both hands close together, but NOT fists
        r_open = make_test_hand(cx=0.50, is_fist=False, handedness="Right")
        l_open = make_test_hand(cx=0.52, is_fist=False, handedness="Left")
        triggered, progress = self.trigger.update(r_open, l_open, timestamp=1.0)
        self.assertFalse(triggered)
        self.assertEqual(progress, 0.0)

    def test_fists_far_apart_do_not_trigger(self):
        # Fists on opposite sides of screen
        r_fist = make_test_hand(cx=0.85, is_fist=True, handedness="Right")
        l_fist = make_test_hand(cx=0.15, is_fist=True, handedness="Left")
        triggered, progress = self.trigger.update(r_fist, l_fist, timestamp=1.0)
        self.assertFalse(triggered)
        self.assertEqual(progress, 0.0)

    def test_dwell_confirmation_triggers_fist_bump(self):
        # Fists colliding close together (dx = 0.04 < 0.16)
        r_fist = make_test_hand(cx=0.52, is_fist=True, handedness="Right")
        l_fist = make_test_hand(cx=0.48, is_fist=True, handedness="Left")

        # Initial collision (t = 0.0)
        trig0, prog0 = self.trigger.update(r_fist, l_fist, timestamp=10.0)
        self.assertFalse(trig0)
        self.assertEqual(prog0, 0.0)

        # Mid-dwell (t = 0.20s < 0.35s)
        trig1, prog1 = self.trigger.update(r_fist, l_fist, timestamp=10.20)
        self.assertFalse(trig1)
        self.assertGreater(prog1, 0.5)
        self.assertLess(prog1, 1.0)

        # Dwell complete (t = 0.36s > 0.35s)
        trig2, prog2 = self.trigger.update(r_fist, l_fist, timestamp=10.36)
        self.assertTrue(trig2)
        self.assertEqual(prog2, 1.0)

    def test_cooldown_prevents_immediate_retrigger(self):
        r_fist = make_test_hand(cx=0.52, is_fist=True, handedness="Right")
        l_fist = make_test_hand(cx=0.48, is_fist=True, handedness="Left")

        # Trigger first bump
        self.trigger.update(r_fist, l_fist, timestamp=1.0)
        trig, _ = self.trigger.update(r_fist, l_fist, timestamp=1.40)
        self.assertTrue(trig)

        # Immediate next frame at 1.50s (cooldown is 1.2s -> valid until 2.6s)
        trig_cd, prog_cd = self.trigger.update(r_fist, l_fist, timestamp=1.50)
        self.assertFalse(trig_cd)
        self.assertEqual(prog_cd, 0.0)

        # After cooldown passes (t = 2.70s)
        self.trigger.update(r_fist, l_fist, timestamp=2.70)
        trig_after, _ = self.trigger.update(r_fist, l_fist, timestamp=3.10)
        self.assertTrue(trig_after)

    def test_separating_hands_aborts_dwell(self):
        r_fist = make_test_hand(cx=0.52, is_fist=True, handedness="Right")
        l_fist = make_test_hand(cx=0.48, is_fist=True, handedness="Left")

        # Start dwell
        self.trigger.update(r_fist, l_fist, timestamp=5.0)
        _, prog_mid = self.trigger.update(r_fist, l_fist, timestamp=5.20)
        self.assertGreater(prog_mid, 0.0)

        # Separate fists
        r_far = make_test_hand(cx=0.80, is_fist=True, handedness="Right")
        trig_sep, prog_sep = self.trigger.update(r_far, l_fist, timestamp=5.25)
        self.assertFalse(trig_sep)
        self.assertEqual(prog_sep, 0.0)


class MockCustomGame(BaseGameProfile):
    def __init__(self):
        super().__init__(game_id="mock_speed_racer", game_name="Speed Racer 3D")
        self.entered = False
        self.exited = False

    def on_enter(self, kernel):
        super().on_enter(kernel)
        self.entered = True

    def on_exit(self, kernel):
        super().on_exit(kernel)
        self.exited = True

    def process_frame(self, right_hand, left_hand, kernel, timestamp):
        return {"action": "ACCELERATE", "is_gaming": True}


class TestGameEngine(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()

    def test_default_initialization(self):
        self.assertFalse(self.engine.is_active)
        self.assertEqual(self.engine.active_profile_id, "subway_surfers")
        profiles = self.engine.list_profiles()
        self.assertEqual(len(profiles), 7)

    def test_register_and_switch_profile(self):
        custom = MockCustomGame()
        self.engine.register_profile(custom)
        self.assertEqual(len(self.engine.list_profiles()), 8)

        switched = self.engine.set_active_profile("mock_speed_racer")
        self.assertTrue(switched)
        self.assertEqual(self.engine.active_profile_id, "mock_speed_racer")

    def test_cycle_next_profile(self):
        initial = self.engine.active_profile_id
        next_id = self.engine.cycle_next_profile()
        self.assertNotEqual(initial, next_id)
        self.assertEqual(self.engine.active_profile_id, next_id)

    def test_toggle_lifecycle(self):
        custom = MockCustomGame()
        self.engine.register_profile(custom)
        self.engine.set_active_profile("mock_speed_racer")

        # Toggle ON
        state = self.engine.toggle(kernel=None)
        self.assertTrue(state)
        self.assertTrue(self.engine.is_active)
        self.assertTrue(custom.entered)

        # Process frame while active
        frame_res = self.engine.process_frame(None, None, None, 1.0)
        self.assertTrue(frame_res["is_gaming"])
        self.assertEqual(frame_res["action"], "ACCELERATE")

        # Toggle OFF
        state_off = self.engine.toggle(kernel=None)
        self.assertFalse(state_off)
        self.assertFalse(self.engine.is_active)
        self.assertTrue(custom.exited)


class TestSpatialOrchestratorGameIntegration(unittest.TestCase):
    def test_orchestrator_game_mode_activation(self):
        from src.core.orchestrator import SpatialOrchestrator
        orch = SpatialOrchestrator()

        r_fist = make_test_hand(cx=0.52, is_fist=True, handedness="Right")
        l_fist = make_test_hand(cx=0.48, is_fist=True, handedness="Left")

        # Bump fists to trigger game mode
        with patch("src.core.orchestrator.play_chime_async"):
            orch.process_spatial_frame(r_fist, l_fist, timestamp=1.0)
            res = orch.process_spatial_frame(r_fist, l_fist, timestamp=1.90)

        self.assertEqual(res["system_state"], "GAME_MODE")
        self.assertTrue(orch.game_engine.is_active)

    def test_voice_intent_toggles_game_mode(self):
        from src.core.orchestrator import SpatialOrchestrator
        orch = SpatialOrchestrator()
        self.assertFalse(orch.game_engine.is_active)

        with patch("src.core.orchestrator.play_chime_async"):
            action = orch.handle_voice_intent("VOICE_TOGGLE_GAME_MODE")
            self.assertEqual(action, "GAME_MODE_ENABLED")
            self.assertTrue(orch.game_engine.is_active)

            action_off = orch.handle_voice_intent("VOICE_TOGGLE_GAME_MODE")
            self.assertEqual(action_off, "GAME_MODE_DISABLED")
            self.assertFalse(orch.game_engine.is_active)


if __name__ == "__main__":
    unittest.main()
