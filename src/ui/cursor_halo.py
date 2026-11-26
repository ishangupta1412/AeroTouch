"""
AeroTouch Morphing Glass Cursor Halo (visionOS / iPadOS Pointer Feedback)
Lightweight 38x38 click-through translucent ring that follows the spatial cursor:
  - Hover: subtle electric cyan reticle
  - Magnetic Lock: warm amber target-lock ring
  - Pinch / Hold: glowing emerald pulse ring
Runs safely as a tk.Toplevel on the shared AeroTouchTkHost thread.
"""

import ctypes
import queue
import tkinter as tk
from typing import Optional, Tuple

BG_COLORKEY = "#010101"
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000


class CursorHaloOverlay:
    """Click-through cursor feedback halo rendered around the live pointer."""

    def __init__(self, size: int = 38):
        self.size = size
        self.root: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        self.running: bool = False
        self._queue: queue.Queue = queue.Queue(maxsize=16)
        self._pos: Optional[Tuple[int, int]] = None
        self._state: str = "HOVER"  # HOVER | LOCKED | PINCH
        self._is_visible: bool = False

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        from src.ui.tk_host import get_tk_host
        get_tk_host().post(self._init_window)

    def stop(self) -> None:
        self.running = False
        try:
            self._queue.put_nowait(("STOP", None))
        except Exception:
            pass
        try:
            from src.ui.tk_host import get_tk_host
            get_tk_host().post(lambda _m: self._cleanup_root())
        except Exception:
            pass

    def _cleanup_root(self) -> None:
        try:
            if self.root:
                self.root.destroy()
        except Exception:
            pass
        self.root = None
        self.canvas = None

    def update_pointer(self, x: Optional[int], y: Optional[int], locked: bool = False, pinching: bool = False) -> None:
        if not self.running:
            return
        state = "PINCH" if pinching else ("LOCKED" if locked else "HOVER")
        try:
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
            self._queue.put_nowait(("POS", (x, y, state)))
        except Exception:
            pass

    def _enable_click_through(self, hwnd: int) -> None:
        try:
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_LAYERED
            )
            user32.SetLayeredWindowAttributes(hwnd, 0x00010101, 0, 1)  # LWA_COLORKEY = 1
        except Exception:
            pass

    def _init_window(self, master: tk.Tk) -> None:
        if not self.running:
            return
        self.root = tk.Toplevel(master)
        self.root.title("AeroTouch Cursor Halo")
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", BG_COLORKEY)
        self.root.configure(bg=BG_COLORKEY)
        self.root.withdraw()
        self._is_visible = False

        self.canvas = tk.Canvas(
            self.root,
            width=self.size,
            height=self.size,
            bg=BG_COLORKEY,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self.root.update_idletasks()
        try:
            child = self.root.winfo_id()
            top = ctypes.windll.user32.GetParent(child) or child
            self._enable_click_through(top)
        except Exception:
            pass

        self._tick()

    def _tick(self) -> None:
        if not self.running or not self.root or not self.canvas:
            return

        while not self._queue.empty():
            try:
                cmd, payload = self._queue.get_nowait()
                if cmd == "STOP":
                    self.running = False
                    self._cleanup_root()
                    return
                elif cmd == "POS":
                    x, y, st = payload
                    self._pos = (x, y) if (x is not None and y is not None) else None
                    self._state = st
            except queue.Empty:
                break

        if self._pos is None:
            if self._is_visible:
                self.root.withdraw()
                self._is_visible = False
            self.root.after(24, self._tick)
            return

        half = self.size // 2
        wx = self._pos[0] - half
        wy = self._pos[1] - half
        self.root.geometry(f"{self.size}x{self.size}+{wx}+{wy}")
        if not self._is_visible:
            self.root.deiconify()
            self._is_visible = True

        self.canvas.delete("all")
        if self._state == "PINCH":
            color, r = "#10b981", half - 4
        elif self._state == "LOCKED":
            color, r = "#f59e0b", half - 3
        else:
            color, r = "#06b6d4", half - 6

        self.canvas.create_oval(
            half - r, half - r, half + r, half + r,
            outline=color, width=2
        )
        self.root.after(16, self._tick)
