"""
AeroTouch Volume & Brightness Scalar Controller
Maps continuous pinch distance [0.0 → 1.0] to system volume and screen brightness.
Uses pycaw for audio (Windows COM), screen-brightness-control for display.
Both are non-blocking — called per-frame only when MEDIA_CONTROL mode is active.
"""

from typing import Optional


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class VolumeController:
    """
    Wraps pycaw Windows Core Audio API.
    Lazily imports so the whole system doesn't break if pycaw is missing.
    """

    def __init__(self):
        self._volume = None
        self._available = False
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._volume = cast(interface, POINTER(IAudioEndpointVolume))
            self._available = True
        except Exception:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def get_volume(self) -> float:
        """Returns current volume as float in [0.0, 1.0]."""
        if not self._available:
            return 0.5
        try:
            return float(self._volume.GetMasterVolumeLevelScalar())
        except Exception:
            return 0.5

    def set_volume(self, level: float) -> None:
        """Sets volume scalar in [0.0, 1.0]."""
        if not self._available:
            return
        try:
            self._volume.SetMasterVolumeLevelScalar(_clamp(level, 0.0, 1.0), None)
        except Exception:
            pass


class BrightnessController:
    """
    Wraps screen-brightness-control.
    Lazily imports — degrades gracefully if library missing or no supported display.
    """

    def __init__(self):
        self._available = False
        try:
            import screen_brightness_control as sbc  # noqa: F401
            self._available = True
        except Exception:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def get_brightness(self) -> float:
        """Returns current brightness as float in [0.0, 1.0]."""
        if not self._available:
            return 0.5
        try:
            import screen_brightness_control as sbc
            val = sbc.get_brightness(display=0)
            return float(val[0] if isinstance(val, list) else val) / 100.0
        except Exception:
            return 0.5

    def set_brightness(self, level: float) -> None:
        """Sets brightness from float [0.0, 1.0] → integer percent [5, 100]."""
        if not self._available:
            return
        try:
            import screen_brightness_control as sbc
            percent = int(_clamp(level, 0.05, 1.0) * 100)
            sbc.set_brightness(percent, display=0)
        except Exception:
            pass


class MediaScalarController:
    """
    Unified entry point: pinch distance → volume or brightness scalar.
    Pinch distance is INVERTED: smaller gap = louder/brighter.
    
    Mapping:
        norm_pinch 0.0 (fully closed) → scalar 1.0 (max)
        norm_pinch 0.5 (half open)   → scalar 0.5
        norm_pinch 1.0 (open)        → scalar 0.0 (min)

    Deadband: only applies update when delta > 0.02 to avoid micro-flicker.
    """

    DEADBAND = 0.02

    def __init__(self):
        self.volume = VolumeController()
        self.brightness = BrightnessController()
        self._last_scalar: float = -1.0   # Force first update

    def pinch_to_scalar(self, norm_pinch: float) -> float:
        """Converts normalized pinch distance to a [0.0, 1.0] scalar."""
        # Map: 0.0 pinch → 1.0 scalar (inverted, clamped)
        scalar = _clamp(1.0 - (norm_pinch / 0.6), 0.0, 1.0)
        return scalar

    def apply_volume(self, norm_pinch: float) -> Optional[float]:
        """
        Applies volume from pinch if delta exceeds deadband.
        Returns the new volume level, or None if deadband suppressed it.
        """
        scalar = self.pinch_to_scalar(norm_pinch)
        if abs(scalar - self._last_scalar) < self.DEADBAND:
            return None
        self._last_scalar = scalar
        self.volume.set_volume(scalar)
        return scalar

    def apply_brightness(self, norm_pinch: float) -> Optional[float]:
        """
        Applies brightness from pinch if delta exceeds deadband.
        Returns the new brightness level, or None if deadband suppressed it.
        """
        scalar = self.pinch_to_scalar(norm_pinch)
        if abs(scalar - self._last_scalar) < self.DEADBAND:
            return None
        self._last_scalar = scalar
        self.brightness.set_brightness(scalar)
        return scalar
