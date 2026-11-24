"""
AeroTouch AirCanvas & Presentation Laser Pointer Overlay
Fullscreen transparent click-through HUD overlay that renders:
  1. Presentation Laser Pointer: Pulsing glowing reticle for presentations and screen sharing.
  2. Spatial Inking: Draw annotations and circles in mid-air over any Windows app.
  3. Auto-Fading Ink Trails: Smoothly fades strokes after 4 seconds (or persistent mode).
"""

import collections
import ctypes
import math
import queue
import threading
import time
import tkinter as tk
from typing import Deque, List, Optional, Tuple

BG_COLORKEY = "#010101"

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000


class StrokePoint:
    def __init__(self, x: int, y: int, color: str = "#00f0ff", width: int = 4, timestamp: Optional[float] = None):
        self.x = x
        self.y = y
        self.color = color
        self.width = width
        self.timestamp = timestamp if timestamp is not None else time.time()


class AirCanvasOverlay:
    """
    Transparent fullscreen desktop overlay for real-time spatial annotation and presentation laser pointing.
    Remains hidden (withdrawn) by default so it never interferes with desktop apps or turns the screen black.
    Only deiconifies when laser pointer or spatial inking is active.
    """

    def __init__(self, fade_duration: float = 3.5):
        self.fade_duration = fade_duration
        self.running: bool = False
        self.root: Optional[tk.Tk] = None
        self.canvas: Optional[tk.Canvas] = None
        self._thread: Optional[threading.Thread] = None
        self._update_queue: queue.Queue = queue.Queue(maxsize=128)
        self._is_visible: bool = False

        # State
        self.laser_enabled: bool = False
        self.drawing_enabled: bool = False
        self.laser_pos: Optional[Tuple[int, int]] = None
        self.current_color: str = "#00f0ff"  # High-visibility Neon Cyan
        self.brush_width: int = 4

        # Active stroke segments: list of lists of StrokePoints
        self._strokes: List[List[StrokePoint]] = []
        self._current_stroke: List[StrokePoint] = []
        self.anim_phase: float = 0.0

    def start(self):
        """Launches AirCanvas in a dedicated background UI thread."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_ui, daemon=True)
        self._thread.start()

    def stop(self):
        """Cleanly destroys the transparent overlay window."""
        self.running = False
        self._post_update({"type": "stop"})
        if self.root:
            try:
                self.root.after(0, self._cleanup_root)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=0.6)
            except Exception:
                pass

    def _cleanup_root(self):
        try:
            if self.root:
                self.root.quit()
                self.root.destroy()
        except Exception:
            pass
        self.root = None

    def set_laser(self, enabled: bool):
        """Toggles presentation laser pointer mode."""
        self.laser_enabled = enabled
        self._post_update({"type": "laser_toggle", "enabled": enabled})

    def set_drawing(self, enabled: bool):
        """Toggles in-air drawing mode."""
        self.drawing_enabled = enabled
        self._post_update({"type": "drawing_toggle", "enabled": enabled})

    def clear(self):
        """Clears all drawing strokes on screen."""
        self._post_update({"type": "clear"})

    def update_cursor(self, x: int, y: int, is_drawing_down: bool = False):
        """Feeds real-time screen cursor position."""
        self._post_update({
            "type": "cursor",
            "x": x,
            "y": y,
            "drawing_down": is_drawing_down
        })

    def _post_update(self, msg: dict):
        try:
            self._update_queue.put_nowait(msg)
        except queue.Full:
            pass

    def _get_toplevel_hwnd(self) -> int:
        if not self.root:
            return 0
        try:
            user32 = ctypes.windll.user32
            child = self.root.winfo_id()
            parent = user32.GetParent(child)
            return parent if parent else child
        except Exception:
            try:
                return self.root.winfo_id()
            except Exception:
                return 0

    def _enable_click_through(self, hwnd: int):
        try:
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
            )
        except Exception:
            pass

    def _run_ui(self):
        self.root = tk.Tk()
        self.root.title("AeroTouch AirCanvas")
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", BG_COLORKEY)
        self.root.configure(bg=BG_COLORKEY)

        # Start hidden/withdrawn so NO black screen or overlay interference on startup
        self.root.withdraw()
        self._is_visible = False

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{sw}x{sh}+0+0")

        self.canvas = tk.Canvas(
            self.root,
            width=sw,
            height=sh,
            bg=BG_COLORKEY,
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.root.update()
        top_hwnd = self._get_toplevel_hwnd()
        if top_hwnd:
            self._enable_click_through(top_hwnd)

        self._render_loop()
        try:
            self.root.mainloop()
        finally:
            try:
                if self.root:
                    self.root.destroy()
            except Exception:
                pass
            self.root = None

    def _drain_messages(self) -> bool:
        """Drains incoming thread messages. Returns True if a stop command was received."""
        while not self._update_queue.empty():
            try:
                msg = self._update_queue.get_nowait()
                mtype = msg.get("type")
                if mtype == "stop":
                    self.running = False
                    if self.root:
                        try:
                            self.root.quit()
                            self.root.destroy()
                            self.root = None
                        except Exception:
                            pass
                    return True
                elif mtype == "laser_toggle":
                    self.laser_enabled = msg["enabled"]
                elif mtype == "drawing_toggle":
                    self.drawing_enabled = msg["enabled"]
                    if not self.drawing_enabled and self._current_stroke:
                        self._strokes.append(self._current_stroke)
                        self._current_stroke = []
                elif mtype == "clear":
                    self._strokes.clear()
                    self._current_stroke.clear()
                elif mtype == "cursor":
                    cx, cy = msg["x"], msg["y"]
                    self.laser_pos = (cx, cy)
                    if self.drawing_enabled and msg.get("drawing_down", False):
                        pt = StrokePoint(cx, cy, color=self.current_color, width=self.brush_width)
                        self._current_stroke.append(pt)
                    else:
                        if self._current_stroke:
                            self._strokes.append(self._current_stroke)
                            self._current_stroke = []
            except queue.Empty:
                break
        return False

    def _render_loop(self):
        if not self.running or not self.root:
            return

        stopped = self._drain_messages()
        if stopped or not self.running or not self.root or not self.canvas:
            return

        should_be_visible = (
            self.laser_enabled
            or self.drawing_enabled
            or bool(self._strokes)
            or bool(self._current_stroke)
        )

        if should_be_visible:
            if not self._is_visible:
                try:
                    self.root.deiconify()
                    top_hwnd = self._get_toplevel_hwnd()
                    if top_hwnd:
                        self._enable_click_through(top_hwnd)
                    self._is_visible = True
                except Exception:
                    pass

            self.canvas.delete("all")
            now = time.time()
            self.anim_phase += 0.12

            # 1. Render Strokes with Fade-Out Decay
            surviving_strokes = []
            for stroke in self._strokes:
                if not stroke:
                    continue
                # Check age of newest point in stroke
                age = now - stroke[-1].timestamp
                if age < self.fade_duration:
                    surviving_strokes.append(stroke)
                    # Draw lines between consecutive points
                    pts = [(p.x, p.y) for p in stroke]
                    if len(pts) >= 2:
                        flat_coords = [coord for pt in pts for coord in pt]
                        self.canvas.create_line(
                            *flat_coords,
                            fill=stroke[0].color,
                            width=stroke[0].width,
                            capstyle=tk.ROUND,
                            joinstyle=tk.ROUND,
                            smooth=True
                        )
            self._strokes = surviving_strokes

            # Render current active stroke in progress
            if len(self._current_stroke) >= 2:
                pts = [(p.x, p.y) for p in self._current_stroke]
                flat_coords = [coord for pt in pts for coord in pt]
                self.canvas.create_line(
                    *flat_coords,
                    fill=self.current_color,
                    width=self.brush_width,
                    capstyle=tk.ROUND,
                    joinstyle=tk.ROUND,
                    smooth=True
                )

            # 2. Render Presentation Laser Pointer if enabled
            if self.laser_enabled and self.laser_pos:
                lx, ly = self.laser_pos
                pulse = math.sin(self.anim_phase) * 2.0
                r_outer = 10 + pulse
                r_inner = 4

                # Outer glowing halo
                self.canvas.create_oval(
                    lx - r_outer, ly - r_outer, lx + r_outer, ly + r_outer,
                    fill="#ff0055", outline="#ff88aa", width=1
                )
                # Center bright white core
                self.canvas.create_oval(
                    lx - r_inner, ly - r_inner, lx + r_inner, ly + r_inner,
                    fill="#ffffff", outline=""
                )

            if self.root:
                self.root.after(16, self._render_loop)
        else:
            if self._is_visible:
                try:
                    self.canvas.delete("all")
                    self.root.withdraw()
                    self._is_visible = False
                except Exception:
                    pass
            if self.root:
                self.root.after(33, self._render_loop)
