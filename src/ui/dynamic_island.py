"""
AeroTouch Dynamic Island (Apple & Flagship Android Style)
A minimalist, frameless, hardware-accelerated top-screen pill widget.
Features fluid morphing geometry, anti-slop typography, click-through transparency,
and real-time reactive animations for spatial actions and gesture lock states.
"""

import ctypes
from ctypes import wintypes
import math
import queue
import threading
import time
import tkinter as tk
from typing import Optional, Dict, Any, Tuple


# Win32 Window Styles
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000

# Color Palette (OLED Obsidian Matte)
BG_COLORKEY = "#010101"        # Colorkey for 100% transparent cutouts
PILL_BG = "#0c0c0e"            # Deep obsidian black
PILL_BORDER = "#24242a"        # Subtle 1px matte border
ACCENT_GREEN = "#10b981"       # Emerald active glow
ACCENT_RED = "#ef4444"         # Crimson lock glow
ACCENT_CYAN = "#06b6d4"        # Cyan pointer / volume glow
ACCENT_AMBER = "#f59e0b"       # Amber drag glow
ACCENT_INDIGO = "#818cf8"      # Indigo snap glow
TEXT_MAIN = "#f3f4f6"          # Clean off-white
TEXT_MUTED = "#9ca3af"         # Muted secondary text
BAR_TRACK = "#1e1e24"          # Dark progress track


class DynamicIslandOverlay:
    """
    Top-center morphing Dynamic Island overlay.
    Clicks pass straight through it without interfering with OS applications.
    """

    def __init__(self):
        self.root: Optional[tk.Tk] = None
        self.canvas: Optional[tk.Canvas] = None
        self.running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._state_queue = queue.Queue(maxsize=16)

        # Dynamic morphing geometry
        self.screen_w = 1920
        self.current_w: float = 180.0
        self.current_h: float = 36.0
        self.target_w: float = 180.0
        self.target_h: float = 36.0

        # Island reactive state
        self.system_state: str = "ACTIVE"  # "ACTIVE" or "LOCKED"
        self.lock_progress: float = 0.0
        self.last_action: Optional[str] = None
        self.last_action_time: float = 0.0
        self.volume_level: float = 0.5
        self.pulse_phase: float = 0.0

    def start(self):
        """Launches Dynamic Island in a dedicated background UI thread."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_ui, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self.root:
            try:
                self.root.after(0, self.root.destroy)
            except Exception:
                pass

    def update_telemetry(
        self,
        system_state: str = "ACTIVE",
        lock_progress: float = 0.0,
        action_executed: Optional[str] = None,
        mode: str = "POINTER_NAV"
    ):
        """Thread-safe state update called from the 60 FPS spatial engine."""
        try:
            self._state_queue.put_nowait({
                "system_state": system_state,
                "lock_progress": lock_progress,
                "action_executed": action_executed,
                "mode": mode
            })
        except queue.Full:
            pass

    def _enable_click_through(self, hwnd: int):
        """Applies Win32 WS_EX_TRANSPARENT so mouse clicks pass straight through."""
        try:
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
            )
        except Exception:
            pass

    def _run_ui(self):
        self.root = tk.Tk()
        self.root.title("AeroTouch Dynamic Island")
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", BG_COLORKEY)
        self.root.configure(bg=BG_COLORKEY)

        self.screen_w = self.root.winfo_screenwidth()
        max_canvas_w = 400
        max_canvas_h = 70

        # Position at top-center of primary screen
        pos_x = (self.screen_w - max_canvas_w) // 2
        pos_y = 12
        self.root.geometry(f"{max_canvas_w}x{max_canvas_h}+{pos_x}+{pos_y}")

        self.canvas = tk.Canvas(
            self.root,
            width=max_canvas_w,
            height=max_canvas_h,
            bg=BG_COLORKEY,
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.root.update()
        hwnd = self.root.winfo_id()
        self._enable_click_through(hwnd)

        self._tick_loop()
        self.root.mainloop()

    def _drain_queue(self):
        while not self._state_queue.empty():
            try:
                state = self._state_queue.get_nowait()
                self.system_state = state["system_state"]
                self.lock_progress = state["lock_progress"]

                action = state["action_executed"]
                if action and action != "HOLDING_SHAKA":
                    self.last_action = action
                    self.last_action_time = time.time()
                    if "VOLUME_SCALAR_" in action:
                        try:
                            self.volume_level = int(action.split("_")[-1]) / 100.0
                        except Exception:
                            pass
            except queue.Empty:
                break

    def _determine_target_geometry(self) -> Tuple[float, float, str, str, str]:
        """
        Determines the target morphing dimensions and visual layout.
        Returns (target_w, target_h, status_type, headline, subline).
        """
        now = time.time()
        time_since_action = now - self.last_action_time

        # 1. Shaka Gesture Countdown (Highest priority active indicator)
        if self.lock_progress > 0.05:
            target_w = 260.0
            target_h = 42.0
            label = "HOLD TO PAUSE" if self.system_state == "ACTIVE" else "HOLD TO RESUME"
            return target_w, target_h, "SHAKA_PROGRESS", label, f"{int(self.lock_progress * 100)}%"

        # 2. System Locked / Paused
        if self.system_state == "LOCKED":
            target_w = 200.0
            target_h = 36.0
            return target_w, target_h, "LOCKED", "PAUSED", "Show 🤙 to Resume"

        # 3. Recent Actions (Transient expansion for 1.2s)
        if self.last_action and time_since_action < 1.2:
            if "LEFT_CLICK" in self.last_action:
                return 210.0, 38.0, "CLICK", "LEFT CLICK", "Confirmed"
            elif "RIGHT_CLICK" in self.last_action:
                return 210.0, 38.0, "RIGHT_CLICK", "RIGHT CLICK", "Context"
            elif "VOLUME_SCALAR" in self.last_action:
                return 260.0, 42.0, "VOLUME", "VOLUME", f"{int(self.volume_level * 100)}%"
            elif "WINDOW_DRAG" in self.last_action:
                return 230.0, 38.0, "DRAG", "WINDOW DRAG", "Active"
            elif "WINDOW_SNAP" in self.last_action:
                return 220.0, 38.0, "SNAP", "WINDOW SNAP", "Win + Left"
            elif "DESKTOP" in self.last_action:
                return 230.0, 38.0, "DESKTOP", "DESKTOP", "Flipped"

        # 4. Default Idle Active Capsule
        return 170.0, 34.0, "IDLE", "AEROTOUCH", "ACTIVE"

    def _draw_rounded_capsule(self, x: float, y: float, w: float, h: float, color: str, border_color: str):
        r = h / 2.0
        # Draw base pill with circles and rectangle
        self.canvas.create_oval(x, y, x + 2 * r, y + h, fill=color, outline=border_color, width=1)
        self.canvas.create_oval(x + w - 2 * r, y, x + w, y + h, fill=color, outline=border_color, width=1)
        self.canvas.create_rectangle(x + r, y, x + w - r, y + h, fill=color, outline=color)
        # Top and bottom borders for rectangular body
        self.canvas.create_line(x + r, y, x + w - r, y, fill=border_color, width=1)
        self.canvas.create_line(x + r, y + h, x + w - r, y + h, fill=border_color, width=1)

    def _tick_loop(self):
        if not self.running or not self.root:
            return

        self._drain_queue()
        self.pulse_phase += 0.08

        # 1. Calculate target geometry and morph smoothly (Spring lerp)
        tw, th, mode_type, headline, subline = self._determine_target_geometry()
        self.target_w = tw
        self.target_h = th

        lerp_speed = 0.28
        self.current_w += (self.target_w - self.current_w) * lerp_speed
        self.current_h += (self.target_h - self.current_h) * lerp_speed

        # 2. Render Island Canvas
        self.canvas.delete("all")
        canvas_w = 400
        canvas_h = 70
        pill_w = self.current_w
        pill_h = self.current_h
        pill_x = (canvas_w - pill_w) / 2.0
        pill_y = (canvas_h - pill_h) / 2.0

        # Draw obsidian body
        self._draw_rounded_capsule(pill_x, pill_y, pill_w, pill_h, PILL_BG, PILL_BORDER)

        # 3. Draw Interior Elements
        mid_y = pill_y + pill_h / 2.0

        if mode_type == "LOCKED":
            # Amber/Red lock dot
            dot_x = pill_x + 18
            self.canvas.create_oval(dot_x - 4, mid_y - 4, dot_x + 4, mid_y + 4, fill=ACCENT_RED, outline="")
            self.canvas.create_text(pill_x + 30, mid_y - 1, text="PAUSED", anchor="w",
                                    fill=ACCENT_RED, font=("Segoe UI", 9, "bold"))
            self.canvas.create_text(pill_x + 85, mid_y, text="Show 🤙", anchor="w",
                                    fill=TEXT_MUTED, font=("Segoe UI", 8))

        elif mode_type == "SHAKA_PROGRESS":
            # Countdown progress bar
            self.canvas.create_text(pill_x + 18, mid_y, text="🤙", anchor="center", font=("Segoe UI", 10))
            self.canvas.create_text(pill_x + 36, mid_y, text=headline, anchor="w",
                                    fill=TEXT_MAIN, font=("Segoe UI", 8, "bold"))
            # Track
            track_x = pill_x + 145
            track_w = 65
            track_h = 6
            self.canvas.create_rectangle(track_x, mid_y - track_h / 2, track_x + track_w, mid_y + track_h / 2,
                                         fill=BAR_TRACK, outline="")
            fill_w = track_w * self.lock_progress
            accent_col = ACCENT_RED if self.system_state == "ACTIVE" else ACCENT_GREEN
            if fill_w > 1:
                self.canvas.create_rectangle(track_x, mid_y - track_h / 2, track_x + fill_w, mid_y + track_h / 2,
                                             fill=accent_col, outline="")
            self.canvas.create_text(track_x + track_w + 14, mid_y, text=subline, anchor="center",
                                    fill=accent_col, font=("Segoe UI", 8, "bold"))

        elif mode_type == "VOLUME":
            # Volume slider inside Island
            self.canvas.create_text(pill_x + 20, mid_y, text="🔊", anchor="center", font=("Segoe UI", 9))
            self.canvas.create_text(pill_x + 36, mid_y, text=headline, anchor="w",
                                    fill=TEXT_MAIN, font=("Segoe UI", 8, "bold"))
            track_x = pill_x + 95
            track_w = 95
            track_h = 6
            self.canvas.create_rectangle(track_x, mid_y - track_h / 2, track_x + track_w, mid_y + track_h / 2,
                                         fill=BAR_TRACK, outline="")
            fill_w = track_w * self.volume_level
            if fill_w > 1:
                self.canvas.create_rectangle(track_x, mid_y - track_h / 2, track_x + fill_w, mid_y + track_h / 2,
                                             fill=ACCENT_CYAN, outline="")
            self.canvas.create_text(track_x + track_w + 18, mid_y, text=subline, anchor="center",
                                    fill=ACCENT_CYAN, font=("Segoe UI", 8, "bold"))

        elif mode_type == "CLICK":
            # Left Click micro-pulse
            dot_x = pill_x + 18
            pulse_r = 4.0 + math.sin(self.pulse_phase * 2) * 1.0
            self.canvas.create_oval(dot_x - pulse_r, mid_y - pulse_r, dot_x + pulse_r, mid_y + pulse_r,
                                    fill=ACCENT_GREEN, outline="")
            self.canvas.create_text(pill_x + 32, mid_y, text=headline, anchor="w",
                                    fill=TEXT_MAIN, font=("Segoe UI", 8, "bold"))
            self.canvas.create_text(pill_x + 130, mid_y, text="Confirmed", anchor="w",
                                    fill=ACCENT_GREEN, font=("Segoe UI", 8))

        elif mode_type == "DRAG":
            self.canvas.create_text(pill_x + 20, mid_y, text="⇱", anchor="center", font=("Segoe UI", 10), fill=ACCENT_AMBER)
            self.canvas.create_text(pill_x + 36, mid_y, text=headline, anchor="w",
                                    fill=ACCENT_AMBER, font=("Segoe UI", 8, "bold"))
            self.canvas.create_text(pill_x + 165, mid_y, text="Moving", anchor="w",
                                    fill=TEXT_MUTED, font=("Segoe UI", 8))

        elif mode_type == "SNAP":
            self.canvas.create_text(pill_x + 20, mid_y, text="⊞", anchor="center", font=("Segoe UI", 9), fill=ACCENT_INDIGO)
            self.canvas.create_text(pill_x + 36, mid_y, text=headline, anchor="w",
                                    fill=TEXT_MAIN, font=("Segoe UI", 8, "bold"))
            self.canvas.create_text(pill_x + 145, mid_y, text="Win+Left", anchor="w",
                                    fill=ACCENT_INDIGO, font=("Segoe UI", 8))

        else:
            # Compact Idle State: Glowing pulse dot + AEROTOUCH ACTIVE
            dot_x = pill_x + 18
            pulse_r = 3.5 + math.sin(self.pulse_phase) * 0.8
            self.canvas.create_oval(dot_x - pulse_r, mid_y - pulse_r, dot_x + pulse_r, mid_y + pulse_r,
                                    fill=ACCENT_GREEN, outline="")
            self.canvas.create_text(pill_x + 30, mid_y, text="AEROTOUCH", anchor="w",
                                    fill=TEXT_MAIN, font=("Segoe UI", 8, "bold"))
            self.canvas.create_text(pill_x + 115, mid_y, text="ACTIVE", anchor="w",
                                    fill=TEXT_MUTED, font=("Segoe UI", 7))

        self.root.after(16, self._tick_loop)
