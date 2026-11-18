"""
AeroTouch Low-Level Windows OS Kernel Bridge
Direct ctypes binding to user32.dll for sub-millisecond mouse and keyboard injection.
Uses native user32.mouse_event and user32.keybd_event to guarantee 100% compatibility
across 64-bit Windows without struct alignment discrepancies.
"""

import ctypes
from enum import IntEnum
from typing import Tuple


# Win32 Mouse Event Flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

# Win32 Keyboard Event Flags
KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

WHEEL_DELTA = 120


# Virtual Key Codes (Standard Windows VK)
class VirtualKey(IntEnum):
    VK_LBUTTON = 0x01
    VK_RBUTTON = 0x02
    VK_TAB = 0x09
    VK_RETURN = 0x0D
    VK_SHIFT = 0x10
    VK_CONTROL = 0x11
    VK_MENU = 0x12  # Alt
    VK_ESCAPE = 0x1B
    VK_SPACE = 0x20
    VK_LEFT = 0x25
    VK_UP = 0x26
    VK_RIGHT = 0x27
    VK_DOWN = 0x28
    VK_LWIN = 0x5B  # Windows key
    VK_D = 0x44


class Win32KernelBridge:
    """High-performance direct Win32 API bridge for input synthesis."""

    def __init__(self):
        self.user32 = ctypes.windll.user32
        # Enable DPI awareness to get exact hardware pixel metrics
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                self.user32.SetProcessDPIAware()
            except Exception:
                pass

        self.screen_width = self.user32.GetSystemMetrics(0)
        self.screen_height = self.user32.GetSystemMetrics(1)

    def get_screen_resolution(self) -> Tuple[int, int]:
        return self.screen_width, self.screen_height

    def move_cursor(self, screen_x: int, screen_y: int) -> None:
        """
        Directly sets cursor position via SetCursorPos (0 latency).
        """
        self.user32.SetCursorPos(int(screen_x), int(screen_y))

    def mouse_down(self, left: bool = True) -> None:
        flags = MOUSEEVENTF_LEFTDOWN if left else MOUSEEVENTF_RIGHTDOWN
        self.user32.mouse_event(flags, 0, 0, 0, 0)

    def mouse_up(self, left: bool = True) -> None:
        flags = MOUSEEVENTF_LEFTUP if left else MOUSEEVENTF_RIGHTUP
        self.user32.mouse_event(flags, 0, 0, 0, 0)

    def click(self, left: bool = True) -> None:
        """Atomic click event (down then up)."""
        self.mouse_down(left)
        self.mouse_up(left)

    def scroll(self, steps: int) -> None:
        """Scroll wheel (positive = up, negative = down)."""
        self.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(steps * WHEEL_DELTA), 0)

    def key_down(self, vk_code: int) -> None:
        self.user32.keybd_event(int(vk_code), 0, KEYEVENTF_KEYDOWN, 0)

    def key_up(self, vk_code: int) -> None:
        self.user32.keybd_event(int(vk_code), 0, KEYEVENTF_KEYUP, 0)

    def tap_key(self, vk_code: int) -> None:
        self.key_down(vk_code)
        self.key_up(vk_code)

    def hotkey(self, *vk_codes: int) -> None:
        """Chords multiple keys sequentially and releases in reverse order."""
        for vk in vk_codes:
            self.key_down(vk)
        for vk in reversed(vk_codes):
            self.key_up(vk)
