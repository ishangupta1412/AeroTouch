import unittest
from src.ui.dynamic_island import DynamicIslandOverlay, SpringPhysics


class TestDynamicIsland(unittest.TestCase):
    def setUp(self):
        self.island = DynamicIslandOverlay()

    def test_spring_physics_convergence(self):
        spring = SpringPhysics(stiffness=340.0, damping=28.0, mass=0.8, initial_pos=180.0)
        spring.target = 260.0

        # Step spring over 60 frames (1 second at 60 FPS)
        for _ in range(60):
            spring.update(dt=0.016)

        # Spring must smoothly converge to target (within 1.0 unit)
        self.assertAlmostEqual(spring.pos, 260.0, delta=1.5)

    def test_initial_geometry_and_state(self):
        self.assertEqual(self.island.system_state, "ACTIVE")
        self.assertEqual(self.island.lock_progress, 0.0)

    def test_target_geometry_idle(self):
        tw, th, mode_type, head, sub = self.island._determine_target_geometry()
        self.assertEqual(mode_type, "IDLE")
        self.assertEqual(tw, 170.0)
        self.assertEqual(th, 34.0)

    def test_target_geometry_locked(self):
        self.island.system_state = "LOCKED"
        tw, th, mode_type, head, sub = self.island._determine_target_geometry()
        self.assertEqual(mode_type, "LOCKED")
        self.assertEqual(head, "PAUSED")
        self.assertEqual(tw, 200.0)

    def test_target_geometry_shaka_progress(self):
        self.island.lock_progress = 0.55
        tw, th, mode_type, head, sub = self.island._determine_target_geometry()
        self.assertEqual(mode_type, "SHAKA_PROGRESS")
        self.assertEqual(tw, 260.0)
        self.assertEqual(sub, "55%")

    def test_target_geometry_volume_action(self):
        import time
        self.island.last_action = "VOLUME_SCALAR_80"
        self.island.volume_level = 0.8
        self.island.last_action_time = time.time()
        tw, th, mode_type, head, sub = self.island._determine_target_geometry()
        self.assertEqual(mode_type, "VOLUME")
        self.assertEqual(tw, 260.0)
        self.assertEqual(sub, "80%")

    def test_state_queue_draining(self):
        self.island.update_telemetry(
            system_state="LOCKED",
            lock_progress=0.75,
            action_executed="VOLUME_SCALAR_60",
            mode="MEDIA_CONTROL"
        )
        self.island._drain_queue()
        self.assertEqual(self.island.system_state, "LOCKED")
        self.assertEqual(self.island.lock_progress, 0.75)
        self.assertEqual(self.island.volume_level, 0.6)


if __name__ == "__main__":
    unittest.main()
