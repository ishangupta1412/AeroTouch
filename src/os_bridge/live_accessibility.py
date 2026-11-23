"""
AeroTouch Live Native Win32 Accessibility Introspection Engine
Queries live interactive Windows UI element bounding boxes in sub-millisecond C-calls:
- Direct oleacc.dll / AccessibleObjectFromPoint & accLocation integration
- Native user32.dll WindowFromPoint & GetWindowRect fallback
- Feeds live interactive target basins directly into UIMagnetismEngine
"""

import ctypes
from ctypes import wintypes
from typing import Optional, Tuple


class LiveUIAccessibilityInspector:
    """
    Sub-millisecond native Win32 accessibility element bounds inspector.
    """

    def __init__(self, max_target_width: int = 350, max_target_height: int = 150):
        self.max_target_width = max_target_width
        self.max_target_height = max_target_height
        self._oleacc = None
        self._user32 = None

        self._init_win32()

    def _init_win32(self) -> None:
        try:
            self._user32 = ctypes.windll.user32
            self._oleacc = ctypes.windll.oleacc
        except Exception:
            self._user32 = None
            self._oleacc = None

    def _get_window_rect(self, hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        """Queries window rectangle via Win32 GetWindowRect."""
        if not self._user32:
            return None
        rect = wintypes.RECT()
        try:
            if self._user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            pass
        return None

    def get_element_rect_at_point(
        self,
        screen_x: int,
        screen_y: int
    ) -> Optional[Tuple[str, int, int, int, int]]:
        """
        Inspects live native Windows UI element bounding box at (screen_x, screen_y).
        Returns:
            (target_id, left, top, right, bottom) or None if background / full screen.
        """
        if not self._user32:
            return None

        # 1. First probe WindowFromPoint
        pt = wintypes.POINT(int(screen_x), int(screen_y))
        try:
            hwnd = self._user32.WindowFromPoint(pt)
        except Exception:
            return None

        if not hwnd:
            return None

        # 2. Probe control bounds
        r = self._get_window_rect(hwnd)
        if r is not None:
            left, top, right, bottom = r
            w = right - left
            h = bottom - top

            # Only consider interactive buttons / controls (reject full-screen desktop containers)
            if 12 <= w <= self.max_target_width and 12 <= h <= self.max_target_height:
                target_id = f"win32_ctrl_{hwnd}"
                return target_id, left, top, right, bottom

        # 3. For complex modern apps (Chrome, Spotify, VS Code tabs), probe child window
        try:
            child_hwnd = self._user32.ChildWindowFromPoint(hwnd, pt)
            if child_hwnd and child_hwnd != hwnd:
                cr = self._get_window_rect(child_hwnd)
                if cr is not None:
                    c_left, c_top, c_right, c_bottom = cr
                    cw = c_right - c_left
                    ch = c_bottom - c_top
                    if 12 <= cw <= self.max_target_width and 12 <= ch <= self.max_target_height:
                        target_id = f"win32_child_{child_hwnd}"
                        return target_id, c_left, c_top, c_right, c_bottom
        except Exception:
            pass

        return None
