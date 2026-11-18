"""
AeroTouch Core Signal Processing: One Euro (1€) Adaptive Dynamic Low-Pass Filter
Reference: Casiez, G., Roussel, N. and Vogel, D. (CHI 2012)
Designed to eliminate high-frequency hand tremors while maintaining sub-millisecond responsiveness during fast sweeps.
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
    Adaptive 1€ dynamic filter for 1D spatial tracking signals.
    Adapts cutoff frequency based on input signal derivative (velocity).
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,  # Hz (Minimum cutoff frequency: lower = smoother at rest)
        beta: float = 0.007,      # Velocity coefficient (higher = less lag during fast movement)
        d_cutoff: float = 1.0     # Hz (Cutoff for derivative calculation)
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
        """
        Filters incoming noisy coordinate 'x' based on its calculated velocity.
        """
        if timestamp is None:
            timestamp = time.perf_counter()

        if self.last_time is None:
            self.last_time = timestamp
            return self.x_filter.filter(x)

        dt = timestamp - self.last_time
        if dt <= 0.0:
            dt = 1e-5  # Prevent division by zero

        self.last_time = timestamp

        # 1. Estimate velocity (derivative)
        prev_x = self.x_filter.hat_x_prev if self.x_filter.hat_x_prev is not None else x
        dx = (x - prev_x) / dt

        # 2. Filter the derivative
        alpha_d = self._alpha(self.d_cutoff, dt)
        edx = self.dx_filter.filter(dx, alpha_d)

        # 3. Dynamically modulate cutoff frequency based on filtered velocity
        cutoff = self.min_cutoff + self.beta * abs(edx)

        # 4. Filter original signal using dynamic cutoff
        alpha_x = self._alpha(cutoff, dt)
        return self.x_filter.filter(x, alpha_x)


class SpatialPointFilter2D:
    """
    Twin 1€ filters managing (x, y) coordinates for sub-pixel cursor accuracy.
    """

    def __init__(self, min_cutoff: float = 0.8, beta: float = 0.02):
        self.filter_x = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self.filter_y = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)

    def reset(self) -> None:
        self.filter_x.reset()
        self.filter_y.reset()

    def filter(self, x: float, y: float, timestamp: Optional[float] = None) -> Tuple[float, float]:
        if timestamp is None:
            timestamp = time.perf_counter()
        filtered_x = self.filter_x.filter(x, timestamp)
        filtered_y = self.filter_y.filter(y, timestamp)
        return filtered_x, filtered_y
