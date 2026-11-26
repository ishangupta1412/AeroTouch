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

        # RAW input tracking — always follows camera-space hand coordinates
        self.last_raw_x: Optional[float] = None
        self.last_raw_y: Optional[float] = None
        self.last_time: Optional[float] = None

        # VIRTUAL cursor position — accumulates accelerated deltas, clamped to [0, 1]
        # Kept separate from raw hand coords so delta math never feeds on its own output
        self.cursor_x: float = 0.5
        self.cursor_y: float = 0.5
        self.last_speed: float = 0.0

    def apply(
        self,
        current_x: float,
        current_y: float,
        timestamp: Optional[float] = None
    ) -> Tuple[float, float]:
        """Applies non-linear velocity ballistics to normalized coordinates [0.0, 1.0].

        Coordinate-space separation guarantee:
          - `self.last_raw_x/y` always tracks the RAW camera-space hand position.
          - `self.cursor_x/y` accumulates scaled deltas with dynamic anchor relaxation.
          - dx = current_raw - last_raw  →  never contaminates from accelerated output.
          - Dynamic Anchor: relaxed gently to hand coordinate when stationary, killing drift.
        """
        if self.last_raw_x is None or self.last_raw_y is None or timestamp is None or self.last_time is None:
            self.last_raw_x = current_x
            self.last_raw_y = current_y
            self.cursor_x = current_x
            self.cursor_y = current_y
            self.last_time = timestamp
            return current_x, current_y

        dt = max(timestamp - self.last_time, 0.001)
        if dt > 0.2:  # Tracking gap > 200ms -> resync cleanly without teleport
            self.last_raw_x = current_x
            self.last_raw_y = current_y
            self.cursor_x = current_x
            self.cursor_y = current_y
            self.last_time = timestamp
            return current_x, current_y

        # Delta measured in RAW camera space — no feedback from accelerated cursor
        dx = current_x - self.last_raw_x
        dy = current_y - self.last_raw_y
        dist = math.hypot(dx, dy)
        vel = dist / dt  # normalized units per second
        self.last_speed = vel

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

        # Accumulate scaled delta onto virtual cursor
        new_cursor_x = self.cursor_x + dx * mult
        new_cursor_y = self.cursor_y + dy * mult

        # Dynamic Anchor: When moving slowly or stationary, gently relax cursor towards hand
        # This completely eliminates pointer drift while preserving high-speed flick reaches
        relax_speed = max(0.0, 1.0 - (vel / max(v_high, 1e-4)))
        alpha = 0.15 * relax_speed
        new_cursor_x += (current_x - new_cursor_x) * alpha
        new_cursor_y += (current_y - new_cursor_y) * alpha

        self.cursor_x = max(0.0, min(1.0, new_cursor_x))
        self.cursor_y = max(0.0, min(1.0, new_cursor_y))

        # Advance RAW tracker — NEVER store accelerated value here
        self.last_raw_x = current_x
        self.last_raw_y = current_y
        self.last_time = timestamp
        return self.cursor_x, self.cursor_y

    def reset(self):
        """Resets tracking state on tracking loss or mode change."""
        self.last_raw_x = None
        self.last_raw_y = None
        self.last_time = None
        self.cursor_x = 0.5
        self.cursor_y = 0.5
        self.last_speed = 0.0

    @property
    def current_speed(self) -> float:
        """Returns the instantaneous velocity magnitude in normalized units/sec."""
        return self.last_speed

    # ── Legacy test-compatibility properties ──────────────────────────────────
    @property
    def last_x(self) -> Optional[float]:
        """Legacy alias: returns raw hand X (not accelerated cursor X)."""
        return self.last_raw_x

    @property
    def last_y(self) -> Optional[float]:
        """Legacy alias: returns raw hand Y (not accelerated cursor Y)."""
        return self.last_raw_y


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
        flip_x: bool = False,    # False: webcam frame is mirrored at capture, so norm_x is natural
        origin_x: int = 0,
        origin_y: int = 0,
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.base_margin_x = margin_x
        self.base_margin_y = margin_y
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.flip_x = flip_x

    def update_ergonomics(self, hand_scale: float, reference_scale: float = 0.14) -> None:
        """
        Dynamically adapts the ergonomic active tracking envelope based on user's
        distance from the webcam (measured via 3D wrist-to-middle-MCP hand_scale).
        """
        if hand_scale <= 0.01:
            return
        # Farther away -> smaller hand_scale -> slightly larger margin (smaller box = easier reach)
        ratio = max(0.65, min(1.45, reference_scale / hand_scale))
        target_mx = max(0.10, min(0.25, self.base_margin_x * ratio))
        target_my = max(0.12, min(0.26, self.base_margin_y * ratio))
        # Smooth EMA to prevent sudden jumps
        alpha = 0.05
        self.margin_x = self.margin_x + (target_mx - self.margin_x) * alpha
        self.margin_y = self.margin_y + (target_my - self.margin_y) * alpha

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

        # Convert to screen integer coordinates (supports multi-monitor virtual desktop origin)
        screen_x = self.origin_x + int(clamped_x * (self.screen_width - 1))
        screen_y = self.origin_y + int(clamped_y * (self.screen_height - 1))

        return screen_x, screen_y
