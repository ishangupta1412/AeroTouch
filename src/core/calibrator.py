"""
AeroTouch Perspective & Coordinate Normalization Engine
Solves the HandWave corner-reachability defect by providing adaptive ergonomic bounding
with dual-axis sensitivity curvature.
"""

from typing import Tuple


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
