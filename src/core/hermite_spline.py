"""
AeroTouch 1000 Hz Cubic Hermite Spline Display Pipeline
Interpolates camera-sampled coordinates (30-60 FPS) to ultra-high refresh rates
(120Hz, 144Hz, 240Hz, up to 1000 Hz) using C1 continuous Cubic Hermite polynomials.
Eliminates discrete cursor teleportation and micro-stutter on gaming monitors.
"""

import math
from typing import List, Optional, Tuple


class CubicHermiteSplineInterpolator:
    """
    Sub-millisecond trajectory supersampling engine using Cubic Hermite Splines.
    """

    def __init__(self, target_rate_hz: int = 1000):
        self.target_rate_hz = target_rate_hz
        self.step_dt = 1.0 / max(target_rate_hz, 60)

        # History: list of (x, y, timestamp, vx, vy)
        self._history: List[Tuple[float, float, float, float, float]] = []

    def reset(self) -> None:
        """Clears trajectory history."""
        self._history.clear()

    def add_waypoint(self, x: float, y: float, timestamp: float) -> None:
        """Adds a camera-sampled tracking waypoint and estimates velocity tangent."""
        if not self._history:
            self._history.append((x, y, timestamp, 0.0, 0.0))
            return

        prev_x, prev_y, prev_t, _, _ = self._history[-1]
        dt = max(timestamp - prev_t, 1e-4)

        vx = (x - prev_x) / dt
        vy = (y - prev_y) / dt

        self._history.append((x, y, timestamp, vx, vy))
        if len(self._history) > 4:
            self._history.pop(0)

    def evaluate_at(self, query_time: float) -> Tuple[float, float]:
        """
        Evaluates the Cubic Hermite Spline at an exact query timestamp.
        Returns:
            (interp_x, interp_y)
        """
        if not self._history:
            return 0.5, 0.5
        if len(self._history) == 1:
            return self._history[0][0], self._history[0][1]

        p0_x, p0_y, t0, m0_x, m0_y = self._history[-2]
        p1_x, p1_y, t1, m1_x, m1_y = self._history[-1]

        dt = t1 - t0
        if dt <= 1e-4:
            return p1_x, p1_y

        # Parameter s in [0.0, 1.0]
        s = (query_time - t0) / dt
        s = max(0.0, min(1.0, s))

        # Hermite basis functions
        s2 = s * s
        s3 = s2 * s

        h00 = 2.0 * s3 - 3.0 * s2 + 1.0
        h10 = s3 - 2.0 * s2 + s
        h01 = -2.0 * s3 + 3.0 * s2
        h11 = s3 - s2

        interp_x = h00 * p0_x + h10 * dt * m0_x + h01 * p1_x + h11 * dt * m1_x
        interp_y = h00 * p0_y + h10 * dt * m0_y + h01 * p1_y + h11 * dt * m1_y

        return interp_x, interp_y

    def generate_subframe_microsteps(self, num_steps: int = 4) -> List[Tuple[float, float]]:
        """
        Generates micro-interpolated steps between the last two waypoints.
        """
        if len(self._history) < 2 or num_steps <= 1:
            if self._history:
                return [(self._history[-1][0], self._history[-1][1])]
            return [(0.5, 0.5)]

        t0 = self._history[-2][2]
        t1 = self._history[-1][2]
        dt = t1 - t0

        steps = []
        for i in range(1, num_steps + 1):
            t = t0 + (dt * (i / num_steps))
            steps.append(self.evaluate_at(t))

        return steps
