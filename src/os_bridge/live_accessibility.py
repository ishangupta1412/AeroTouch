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


# Interactive UI Automation ControlType IDs (Microsoft UIA)
_INTERACTIVE_UIA_TYPES = {
    50000,  # Button
    50002,  # CheckBox
    50003,  # ComboBox
    50004,  # Edit
    50005,  # Hyperlink
    50007,  # ListItem
    50011,  # MenuItem
    50013,  # RadioButton
    50018,  # TabItem
    50019,  # Text (only if small/clickable)
    50023,  # TreeItem
}


class LiveUIAccessibilityInspector:
    """
    Sub-millisecond native Win32 + Windows UI Automation (IUIAutomation) element inspector.
    Supports both classic Win32 controls and modern windowless apps (Chrome, VS Code, Electron, WinUI).
    """

    def __init__(self, max_target_width: int = 350, max_target_height: int = 150):
        self.max_target_width = max_target_width
        self.max_target_height = max_target_height
        self._oleacc = None
        self._user32 = None
        self._uia = None
        self._uia_init_attempted = False

        self._init_win32()

    def _init_win32(self) -> None:
        try:
            self._user32 = ctypes.windll.user32
            self._oleacc = ctypes.windll.oleacc
        except Exception:
            self._user32 = None
            self._oleacc = None

    def _ensure_uia(self) -> None:
        if self._uia_init_attempted:
            return
        self._uia_init_attempted = True
        try:
            import comtypes
            import comtypes.client
            try:
                comtypes.CoInitialize()
            except Exception:
                pass
            uia_mod = comtypes.client.GetModule("UIAutomationCore.dll")
            self._uia = comtypes.client.CreateObject(
                "{ff48dba4-60ef-4201-aa87-54103eef594e}",
                interface=uia_mod.IUIAutomation,
            )
        except Exception:
            self._uia = None

    def _probe_uia_at_point(self, screen_x: int, screen_y: int) -> Optional[Tuple[str, int, int, int, int]]:
        self._ensure_uia()
        if self._uia is None:
            return None
        try:
            pt = wintypes.POINT(int(screen_x), int(screen_y))
            elem = self._uia.ElementFromPoint(pt)
            if not elem:
                return None
            ctrl_type = int(elem.CurrentControlType)
            if ctrl_type not in _INTERACTIVE_UIA_TYPES:
                return None
            rect = elem.CurrentBoundingRectangle
            left, top, right, bottom = int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)
            w = right - left
            h = bottom - top
            if 10 <= w <= self.max_target_width and 10 <= h <= self.max_target_height:
                target_id = f"uia_{ctrl_type}_{left}_{top}"
                return target_id, left, top, right, bottom
        except Exception:
            pass
        return None

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

        # 0. Probe modern Windows UI Automation (Chrome tabs, VS Code, Electron, WinUI 3)
        uia_hit = self._probe_uia_at_point(screen_x, screen_y)
        if uia_hit is not None:
            return uia_hit

        # 1. Fallback to Win32 WindowFromPoint
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

        # 3. Probe child Win32 control using client coordinates (ScreenToClient)
        try:
            client_pt = wintypes.POINT(int(screen_x), int(screen_y))
            self._user32.ScreenToClient(hwnd, ctypes.byref(client_pt))
            child_hwnd = self._user32.ChildWindowFromPoint(hwnd, client_pt)
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
