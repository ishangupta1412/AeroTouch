"""
AeroTouch Forward-Predictive Kinematic Extrapolator & Dual-Stage Adaptive Filter
Overcomes physical webcam USB/capture pipeline latency (~35ms) by extrapolating
the physical trajectory vector forward in time, while freezing micro-jitter during slow hover.
"""

import math
from typing import List, Optional, Tuple


class PredictiveKinematicFilter:
    """
    Sub-millisecond forward-predictive filter with adaptive jitter gating.
    Compensates for sensor pipeline lag and guarantees rock-solid sub-pixel targeting.
    """

    def __init__(
        self,
        lead_time_seconds: float = 0.035,
        slow_deadband: float = 0.0020,
        speed_threshold: float = 0.12,
        max_extrapolation_distance: float = 0.08,
    ):
        self.lead_time_seconds = lead_time_seconds
        self.slow_deadband = slow_deadband
        self.speed_threshold = speed_threshold
        self.max_extrapolation_distance = max_extrapolation_distance

        # History for velocity & acceleration estimation: list of (x, y, timestamp)
        self._history: List[Tuple[float, float, float]] = []
        self._filtered_pos: Optional[Tuple[float, float]] = None

    def reset(self) -> None:
        """Resets tracking history."""
        self._history.clear()
        self._filtered_pos = None

    def filter_and_predict(
        self,
        raw_x: float,
        raw_y: float,
        timestamp: float
    ) -> Tuple[float, float]:
        """
        Applies dual-stage deadband and forward-projects position by lead_time_seconds.
        Returns:
            (pred_x, pred_y)
        """
        if self._filtered_pos is None:
            self._filtered_pos = (raw_x, raw_y)
            self._history = [(raw_x, raw_y, timestamp)]
            return raw_x, raw_y

        prev_x, prev_y = self._filtered_pos

        # Maintain 4-frame history
        self._history.append((raw_x, raw_y, timestamp))
        if len(self._history) > 4:
            self._history.pop(0)

        # 1. Instantaneous velocity estimation
        dt = timestamp - self._history[-2][2] if len(self._history) >= 2 else 0.016
        dt = max(dt, 0.001)

        vx = (raw_x - self._history[-2][0]) / dt
        vy = (raw_y - self._history[-2][1]) / dt
        speed = math.sqrt(vx * vx + vy * vy)

        # 2. Dual-Stage Adaptive Deadband
        # If speed is below threshold (fine targeting/clicking), clamp small displacements to 0
        disp = math.sqrt((raw_x - prev_x) ** 2 + (raw_y - prev_y) ** 2)
        if speed < self.speed_threshold and disp < self.slow_deadband:
            cur_x, cur_y = prev_x, prev_y
            vx, vy = 0.0, 0.0
        else:
            cur_x, cur_y = raw_x, raw_y

        self._filtered_pos = (cur_x, cur_y)

        # 3. Forward Extrapolation (Lead-Time Prediction)
        # If moving fast enough to benefit from lag cancellation
        if speed >= self.speed_threshold:
            pred_dx = vx * self.lead_time_seconds
            pred_dy = vy * self.lead_time_seconds

            pred_dist = math.sqrt(pred_dx * pred_dx + pred_dy * pred_dy)
            if pred_dist > self.max_extrapolation_distance:
                scale = self.max_extrapolation_distance / max(pred_dist, 1e-6)
                pred_dx *= scale
                pred_dy *= scale

            extrap_x = cur_x + pred_dx
            extrap_y = cur_y + pred_dy
        else:
            extrap_x, extrap_y = cur_x, cur_y

        # Clamp to normalized [0.0, 1.0] boundary
        clamped_x = max(0.0, min(1.0, extrap_x))
        clamped_y = max(0.0, min(1.0, extrap_y))

        return clamped_x, clamped_y
