"""
AeroTouch Perspective & Coordinate Normalization Engine
Solves the HandWave corner-reachability defect by providing adaptive ergonomic bounding
with dual-axis sensitivity curvature and non-linear pointer ballistics.
"""

import math
from typing import Optional, Tuple


class PointerBallistics:
    """
    Non-linear mouse acceleration curve matching Apple macOS & Windows 'Enhance Pointer Precision'.
    - Sniper Precision (< 0.003 normalized velocity): 0.5x speed for sub-pixel accuracy on small buttons.
    - Nominal 1:1 Range (0.003 - 0.015 velocity): Linear 1.0x response.
    - High-Speed Flick (> 0.015 velocity): Exponential power scaling up to 2.2x to effortlessly cross 4K screens.
    """

    def __init__(
        self,
        precision_threshold: float = 0.003,
        precision_gain: float = 0.5,
        flick_threshold: float = 0.015,
        max_multiplier: float = 2.2,
        power: float = 1.3
    ):
        self.precision_threshold = precision_threshold
        self.precision_gain = precision_gain
        self.flick_threshold = flick_threshold
        self.max_multiplier = max_multiplier
        self.power = power

        self.last_x: Optional[float] = None
        self.last_y: Optional[float] = None
        self.last_time: Optional[float] = None

    def apply(
        self,
        current_x: float,
        current_y: float,
        timestamp: Optional[float] = None
    ) -> Tuple[float, float]:
        """Applies non-linear velocity ballistics to normalized coordinates [0.0, 1.0]."""
        if self.last_x is None or self.last_y is None or timestamp is None or self.last_time is None:
            self.last_x = current_x
            self.last_y = current_y
            self.last_time = timestamp
            return current_x, current_y

        dt = max(timestamp - self.last_time, 0.001)
        dx = current_x - self.last_x
        dy = current_y - self.last_y
        dist = math.hypot(dx, dy)
        vel = dist / dt  # normalized units per second

        # Compute dynamic multiplier
        v_low = self.precision_threshold * 60.0
        v_high = self.flick_threshold * 60.0

        if vel < v_low:
            # Low-speed sniper precision mode (down to 0.5x)
            factor = vel / max(v_low, 1e-4)
            mult = self.precision_gain + (1.0 - self.precision_gain) * factor
        elif vel > v_high:
            # High-speed flick acceleration (up to 2.2x)
            excess = (vel - v_high) / 1.0
            mult = min(self.max_multiplier, 1.0 + (excess ** self.power))
        else:
            mult = 1.0

        accelerated_x = self.last_x + dx * mult
        accelerated_y = self.last_y + dy * mult

        # Clamp strictly within [0.0, 1.0]
        accelerated_x = max(0.0, min(1.0, accelerated_x))
        accelerated_y = max(0.0, min(1.0, accelerated_y))

        self.last_x = accelerated_x
        self.last_y = accelerated_y
        self.last_time = timestamp
        return accelerated_x, accelerated_y

    def reset(self):
        """Resets tracking state on tracking loss or mode change."""
        self.last_x = None
        self.last_y = None
        self.last_time = None


class ScreenSpaceMapper:
    """
    Transforms camera-space normalized coordinates [0.0, 1.0] to physical screen coordinates [0, Width] x [0, Height].
    Provides an ergonomic deadzone margin to reach screen borders without arm strain.
    """

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        margin_x: float = 0.15,  # 15% boundary margin for effortless reach
        margin_y: float = 0.18,
        flip_x: bool = False     # False: webcam frame is mirrored at capture, so norm_x is natural
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.flip_x = flip_x

    def map_to_screen(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """
        Maps normalized camera point (0 to 1) into screen pixels.
        """
        # Mirror horizontal axis if enabled (natural selfie webcam interaction)
        px = (1.0 - norm_x) if self.flip_x else norm_x
        py = norm_y

        # Normalize within ergonomic active tracking envelope
        min_x = self.margin_x
        max_x = 1.0 - self.margin_x
        min_y = self.margin_y
        max_y = 1.0 - self.margin_y

        # Clamp and scale
        clamped_x = max(0.0, min(1.0, (px - min_x) / (max_x - min_x)))
        clamped_y = max(0.0, min(1.0, (py - min_y) / (max_y - min_y)))

        # Convert to screen integer coordinates
        screen_x = int(clamped_x * (self.screen_width - 1))
        screen_y = int(clamped_y * (self.screen_height - 1))

        return screen_x, screen_y
