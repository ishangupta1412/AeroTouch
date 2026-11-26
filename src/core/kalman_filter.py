"""
AeroTouch 2D Constant-Acceleration Kalman Filter
Models [pos, vel, accel] independently on X and Y axes for curved trajectory tracking,
micro-tremor rejection, and overshoot-free forward latency compensation.
"""

from typing import Optional, Tuple
import numpy as np


class _AxisKalmanCA:
    """3-state [pos, vel, accel] Constant-Acceleration Kalman filter for one axis."""

    def __init__(self, process_noise: float = 0.08, measurement_noise: float = 1e-4):
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.x: Optional[np.ndarray] = None  # shape (3,)
        self.P: Optional[np.ndarray] = None  # shape (3, 3)

    def reset(self) -> None:
        self.x = None
        self.P = None

    def update(self, z: float, dt: float, lead_time: float = 0.028) -> float:
        if self.x is None or self.P is None:
            self.x = np.array([z, 0.0, 0.0], dtype=np.float64)
            self.P = np.eye(3, dtype=np.float64) * 1e-2
            return z

        dt = max(1e-3, min(0.1, dt))
        dt2 = 0.5 * dt * dt
        F = np.array([
            [1.0, dt, dt2],
            [0.0, 1.0, dt],
            [0.0, 0.0, 0.92],  # Mild acceleration decay prevents runaway on stops
        ], dtype=np.float64)

        Q = np.array([
            [0.25 * dt**4, 0.5 * dt**3, 0.5 * dt**2],
            [0.5 * dt**3, dt**2, dt],
            [0.5 * dt**2, dt, 1.0],
        ], dtype=np.float64) * self.process_noise

        # Predict
        x_pred = F @ self.x
        P_pred = F @ self.P @ F.T + Q

        # Measurement update (H = [1, 0, 0])
        y = z - x_pred[0]
        S = P_pred[0, 0] + self.measurement_noise
        K = P_pred[:, 0] / max(S, 1e-9)

        self.x = x_pred + K * y
        I_KH = np.eye(3, dtype=np.float64)
        I_KH[:, 0] -= K
        self.P = I_KH @ P_pred

        # Forward lead-time projection using velocity + damped acceleration
        lt = max(0.0, min(0.05, lead_time))
        proj = self.x[0] + self.x[1] * lt + 0.5 * self.x[2] * (lt * lt)
        return float(max(0.0, min(1.0, proj)))


class ConstantAccelerationKalman2D:
    """2D Constant-Acceleration Kalman Filter for smooth, lag-free cursor tracking."""

    def __init__(self, process_noise: float = 0.08, measurement_noise: float = 1e-4, lead_time: float = 0.025):
        self.lead_time = lead_time
        self._kx = _AxisKalmanCA(process_noise=process_noise, measurement_noise=measurement_noise)
        self._ky = _AxisKalmanCA(process_noise=process_noise, measurement_noise=measurement_noise)
        self._last_ts: Optional[float] = None

    def reset(self) -> None:
        self._kx.reset()
        self._ky.reset()
        self._last_ts = None

    def update(self, raw_x: float, raw_y: float, timestamp: float) -> Tuple[float, float]:
        if self._last_ts is None:
            dt = 0.016
        else:
            dt = max(1e-4, timestamp - self._last_ts)
            if dt > 0.25:
                self.reset()
                dt = 0.016
        self._last_ts = timestamp

        px = self._kx.update(raw_x, dt, lead_time=self.lead_time)
        py = self._ky.update(raw_y, dt, lead_time=self.lead_time)
        return px, py
