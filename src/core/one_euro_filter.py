"""
AeroTouch Core Signal Processing: Precision Adaptive 1-Euro Filter with Dynamic Spatial Deadband
Reference: Casiez, G., Roussel, N. and Vogel, D. (CHI 2012)
Engineered for zero-vibration stationary cursor stability and instantaneous dynamic velocity response.
"""

import math
import time
from typing import Optional, Tuple


class LowPassFilter:
    """Standard first-order low-pass filter with exponential smoothing."""

    def __init__(self, alpha: float):
        self.alpha: float = alpha
        self.hat_x_prev: Optional[float] = None

    def reset(self) -> None:
        self.hat_x_prev = None

    def filter(self, x: float, alpha: Optional[float] = None) -> float:
        if alpha is not None:
            self.alpha = alpha

        if self.hat_x_prev is None:
            hat_x = x
        else:
            hat_x = self.alpha * x + (1.0 - self.alpha) * self.hat_x_prev

        self.hat_x_prev = hat_x
        return hat_x


class OneEuroFilter:
    """
    Adaptive 1€ dynamic filter for 1D spatial tracking signals in normalized space [0.0, 1.0].
    Minimizes jitter at low speeds (min_cutoff=0.05Hz) and eliminates lag at high speeds.
    """

    def __init__(
        self,
        min_cutoff: float = 0.05,  # Lower cutoff kills stationary muscle tremor completely
        beta: float = 4.0,         # Velocity scaling factor for normalized coordinates [0, 1]
        d_cutoff: float = 1.0      # Derivative cutoff frequency
    ):
        self.min_cutoff: float = float(min_cutoff)
        self.beta: float = float(beta)
        self.d_cutoff: float = float(d_cutoff)

        self.x_filter = LowPassFilter(alpha=self._alpha(min_cutoff, 1.0 / 60.0))
        self.dx_filter = LowPassFilter(alpha=self._alpha(d_cutoff, 1.0 / 60.0))
        self.last_time: Optional[float] = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        """Calculates smoothing factor alpha from cutoff frequency and delta-time."""
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def reset(self) -> None:
        self.x_filter.reset()
        self.dx_filter.reset()
        self.last_time = None

    def filter(self, x: float, timestamp: Optional[float] = None) -> float:
        """Filters coordinate based on instantaneous movement velocity."""
        if timestamp is None:
            timestamp = time.perf_counter()

        if self.last_time is None:
            self.last_time = timestamp
            return self.x_filter.filter(x)

        dt = timestamp - self.last_time
        if dt <= 0.0:
            dt = 1e-5

        self.last_time = timestamp

        # 1. Estimate velocity (derivative)
        prev_x = self.x_filter.hat_x_prev if self.x_filter.hat_x_prev is not None else x
        dx = (x - prev_x) / dt

        # 2. Filter the derivative
        alpha_d = self._alpha(self.d_cutoff, dt)
        edx = self.dx_filter.filter(dx, alpha_d)

        # 3. Dynamically modulate cutoff frequency based on velocity
        cutoff = self.min_cutoff + self.beta * abs(edx)

        # 4. Filter original signal using dynamic cutoff
        alpha_x = self._alpha(cutoff, dt)
        return self.x_filter.filter(x, alpha_x)


class PrecisionSpatialFilter2D:
    """
    Dual-stage 2D spatial filter with Velocity Noise Gate (Deadband).
    Suppresses micro-jitter < deadband threshold, guaranteeing stationary cursor stillness.
    """

    def __init__(
        self,
        min_cutoff: float = 0.05,
        beta: float = 4.0,
        deadband: float = 0.0025  # Normalized deadband threshold (~4.8 screen pixels)
    ):
        self.filter_x = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self.filter_y = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self.deadband = deadband

        self.last_output_x: Optional[float] = None
        self.last_output_y: Optional[float] = None

    def reset(self) -> None:
        self.filter_x.reset()
        self.filter_y.reset()
        self.last_output_x = None
        self.last_output_y = None

    def filter(self, x: float, y: float, timestamp: Optional[float] = None) -> Tuple[float, float]:
        if timestamp is None:
            timestamp = time.perf_counter()

        # Initial frame bootstrap
        if self.last_output_x is None:
            filtered_x = self.filter_x.filter(x, timestamp)
            filtered_y = self.filter_y.filter(y, timestamp)
            self.last_output_x = filtered_x
            self.last_output_y = filtered_y
            return filtered_x, filtered_y

        # Step 1: Spatial Noise Gate (Deadband suppression against last stable cursor position)
        dist_sq = (x - self.last_output_x) ** 2 + (y - self.last_output_y) ** 2
        deadband_sq = self.deadband ** 2

        if dist_sq < deadband_sq:
            # Human tremor below noise gate threshold -> Lock position completely still
            # Keep 1-Euro internal filters synced to prevent jump on release
            self.filter_x.filter(self.last_output_x, timestamp)
            self.filter_y.filter(self.last_output_y, timestamp)
            return self.last_output_x, self.last_output_y

        # Step 2: Intentional human movement -> apply 1-Euro adaptive frequency filtering
        filtered_x = self.filter_x.filter(x, timestamp)
        filtered_y = self.filter_y.filter(y, timestamp)
        self.last_output_x = filtered_x
        self.last_output_y = filtered_y
        return filtered_x, filtered_y


# Backward compatibility alias
SpatialPointFilter2D = PrecisionSpatialFilter2D
