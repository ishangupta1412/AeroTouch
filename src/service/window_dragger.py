"""
AeroTouch Window Dragger Service
Fist-gesture based spatial window drag using Win32 SetWindowPos.
State machine: fist-down captures window + cursor anchor → 
               fist-held moves window to follow cursor delta →
               fist-release drops window at final position.
"""

from typing import Optional, Tuple


class WindowDragger:
    """
    Tracks fist-drag state and translates cursor delta into window movement.
    Completely stateful — call update() on every frame.
    """

    def __init__(self):
        self._dragging: bool = False
        self._drag_hwnd: int = 0
        self._win_origin_x: int = 0      # Window left at drag start
        self._win_origin_y: int = 0      # Window top at drag start
        self._win_width: int = 0
        self._win_height: int = 0
        self._cursor_anchor_x: int = 0   # Cursor screen-x at drag start
        self._cursor_anchor_y: int = 0   # Cursor screen-y at drag start

    @property
    def is_dragging(self) -> bool:
        return self._dragging

    def start_drag(self, hwnd: int, win_rect: Tuple[int, int, int, int],
                   cursor_x: int, cursor_y: int) -> None:
        """
        Called when fist first closes over a window.
        Captures the window geometry and the cursor's screen anchor.
        """
        self._dragging = True
        self._drag_hwnd = hwnd
        left, top, right, bottom = win_rect
        self._win_origin_x = left
        self._win_origin_y = top
        self._win_width = right - left
        self._win_height = bottom - top
        self._cursor_anchor_x = cursor_x
        self._cursor_anchor_y = cursor_y

    def update_drag(self, cursor_x: int, cursor_y: int
                    ) -> Tuple[int, int, int, int, int]:
        """
        Returns (hwnd, new_x, new_y, width, height) based on cursor delta.
        Call on every frame while fist is held.
        """
        dx = cursor_x - self._cursor_anchor_x
        dy = cursor_y - self._cursor_anchor_y
        new_x = self._win_origin_x + dx
        new_y = self._win_origin_y + dy
        return (self._drag_hwnd, new_x, new_y,
                self._win_width, self._win_height)

    def end_drag(self) -> None:
        """Called when fist opens — releases window at current position."""
        self._dragging = False
        self._drag_hwnd = 0

    def reset(self) -> None:
        """Resets dragging state immediately."""
        self.end_drag()
