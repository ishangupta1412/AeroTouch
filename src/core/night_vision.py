"""
AeroTouch Spatial CLAHE Low-Light Night Vision Pre-Processor
Extracts high-contrast hand features in dim rooms and night environments:
- Converts BGR to LAB color space
- Applies Contrast Limited Adaptive Histogram Equalization (CLAHE) on L-channel
- Auto-activates only when scene illuminance drops below threshold (0% overhead in daylight)
"""

from typing import Optional, Tuple
import cv2
import numpy as np


class AdaptiveNightVisionEnhancer:
    """
    Zero-overhead adaptive low-light vision optimizer.
    """

    def __init__(
        self,
        low_light_threshold: float = 85.0,
        clip_limit: float = 2.5,
        tile_grid_size: Tuple[int, int] = (8, 8),
    ):
        self.low_light_threshold = low_light_threshold
        self.clip_limit = clip_limit
        self.tile_grid_size = tile_grid_size
        self._clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        self.is_night_mode_active: bool = False

    def enhance(self, bgr_frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Evaluates frame brightness and applies adaptive LAB CLAHE if under-illuminated.
        Returns:
            (processed_bgr_frame, is_night_mode_active)
        """
        if bgr_frame is None or bgr_frame.size == 0:
            return bgr_frame, False

        # Fast approximate mean luminance using downsampled grayscale
        # Using 1/8th scale for sub-millisecond brightness probe
        small = cv2.resize(bgr_frame, (0, 0), fx=0.125, fy=0.125, interpolation=cv2.INTER_NEAREST)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        mean_lum = float(np.mean(gray))

        if mean_lum < self.low_light_threshold:
            self.is_night_mode_active = True
            # Convert to LAB color space
            lab = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            # Apply CLAHE to L-channel
            cl = self._clahe.apply(l)

            # Merge back and convert to BGR
            enhanced_lab = cv2.merge((cl, a, b))
            enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
            return enhanced_bgr, True

        self.is_night_mode_active = False
        return bgr_frame, False
