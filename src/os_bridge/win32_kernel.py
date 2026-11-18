"""
AeroTouch Low-Level Windows OS Kernel Bridge
Direct ctypes binding to user32.dll for sub-millisecond mouse and keyboard injection.
Bypasses PyAutoGUI I/O locks and latency bottlenecks.
"""

import ctypes
from ctypes import wintypes
from enum import IntEnum
from typing import Tuple


# Win32 Constants
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

# Mouse Event Flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x000C
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

# Keyboard Event Flags
KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

WHEEL_DELTA = 120


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulong),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulong),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


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
            self.user32.SetProcessDPIAware()

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
        inp = INPUT(type=INPUT_MOUSE)
        inp.union.mi = MOUSEINPUT(0, 0, 0, flags, 0, 0)
        self.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def mouse_up(self, left: bool = True) -> None:
        flags = MOUSEEVENTF_LEFTUP if left else MOUSEEVENTF_RIGHTUP
        inp = INPUT(type=INPUT_MOUSE)
        inp.union.mi = MOUSEINPUT(0, 0, 0, flags, 0, 0)
        self.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def click(self, left: bool = True) -> None:
        """Atomic click event using Win32 SendInput batch."""
        down_flag = MOUSEEVENTF_LEFTDOWN if left else MOUSEEVENTF_RIGHTDOWN
        up_flag = MOUSEEVENTF_LEFTUP if left else MOUSEEVENTF_RIGHTUP
        inputs = (INPUT * 2)()
        inputs[0].type = INPUT_MOUSE
        inputs[0].union.mi = MOUSEINPUT(0, 0, 0, down_flag, 0, 0)
        inputs[1].type = INPUT_MOUSE
        inputs[1].union.mi = MOUSEINPUT(0, 0, 0, up_flag, 0, 0)
        self.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

    def scroll(self, steps: int) -> None:
        """Scroll wheel (positive = up, negative = down)."""
        inp = INPUT(type=INPUT_MOUSE)
        inp.union.mi = MOUSEINPUT(0, 0, steps * WHEEL_DELTA, MOUSEEVENTF_WHEEL, 0, 0)
        self.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def key_down(self, vk_code: int) -> None:
        inp = INPUT(type=INPUT_KEYBOARD)
        inp.union.ki = KEYBDINPUT(vk_code, 0, KEYEVENTF_KEYDOWN, 0, 0)
        self.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def key_up(self, vk_code: int) -> None:
        inp = INPUT(type=INPUT_KEYBOARD)
        inp.union.ki = KEYBDINPUT(vk_code, 0, KEYEVENTF_KEYUP, 0, 0)
        self.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def hotkey(self, *vk_codes: int) -> None:
        """Executes combined hotkey sequence (e.g. Win + D, Win + Left)."""
        for vk in vk_codes:
            self.key_down(vk)
        for vk in reversed(vk_codes):
            self.key_up(vk)
