"""
AeroTouch Flagship Dynamic Island (Pillar & Apple Architecture)
Inspired by warpirate/pillar-dynamic-island-for-windows:
- 2nd-Order Spring Dynamics (Stiffness=340, Damping=28, Mass=0.8) for organic fluid morphing.
- Multi-layer glassmorphic capsule with ambient rim lighting and dual-tone borders.
- Three-Zone Modular Layout (Left Glyph Wing, Center Morphing Core, Right Telemetry Wing).
- Live animated equalizer waves for Volume Control and circular activity rings for 🤙 Shaka countdown.
- Win32 WS_EX_TRANSPARENT click-through layered window (zero input interference).
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

# Color Palette (Obsidian Glassmorphism)
BG_COLORKEY = "#010101"         # Colorkey for full transparency
PILL_OBSIDIAN = "#0b0b0e"       # Deep glass black
BORDER_OUTER = "#222228"        # Subtle matte edge
BORDER_HIGHLIGHT = "#32323c"    # Top subtle specular rim
ACCENT_EMERALD = "#10b981"      # Active emerald
ACCENT_CYAN = "#06b6d4"         # Audio / volume
ACCENT_CRIMSON = "#ef4444"      # Locked / pause
ACCENT_AMBER = "#f59e0b"        # Window drag
ACCENT_INDIGO = "#818cf8"       # Window snap
TEXT_PRIMARY = "#f9fafb"        # Crisp white
TEXT_SECONDARY = "#9ca3af"      # Neutral gray
TRACK_BG = "#1c1c22"            # Dark slider track


class SpringPhysics:
    """
    Second-order spring physics model (Hooke's Law with damping).
    Matches Framer Motion / Apple Spring curves: stiffness=340, damping=28, mass=0.8.
    """

    def __init__(self, stiffness: float = 340.0, damping: float = 28.0, mass: float = 0.8, initial_pos: float = 180.0):
        self.stiffness = stiffness
        self.damping = damping
        self.mass = mass
        self.pos: float = initial_pos
        self.vel: float = 0.0
        self.target: float = initial_pos

    def update(self, dt: float = 0.016) -> float:
        # F = -k*(x - x_target) - c*v
        displacement = self.pos - self.target
        force = -self.stiffness * displacement - self.damping * self.vel
        accel = force / self.mass
        self.vel += accel * dt
        self.pos += self.vel * dt
        return self.pos


class DynamicIslandOverlay:
    """
    Pillar-inspired flagship Dynamic Island overlay for Windows 11.
    Renders an always-on-top morphing glass capsule with spring physics.
    """

    def __init__(self):
        self.root: Optional[tk.Tk] = None
        self.canvas: Optional[tk.Canvas] = None
        self.running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._state_queue = queue.Queue(maxsize=32)

        # Spring physics for width and height morphing
        self.spring_w = SpringPhysics(stiffness=340.0, damping=28.0, mass=0.8, initial_pos=180.0)
        self.spring_h = SpringPhysics(stiffness=360.0, damping=30.0, mass=0.8, initial_pos=36.0)

        self.screen_w = 1920
        self.system_state: str = "ACTIVE"
        self.lock_progress: float = 0.0
        self.last_action: Optional[str] = None
        self.last_action_time: float = 0.0
        self.volume_level: float = 0.5
        self.anim_phase: float = 0.0

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
        """Enforces Win32 click-through transparency."""
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
        max_canvas_w = 420
        max_canvas_h = 74

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
        Calculates morphing layout dimensions and contents.
        Returns (target_w, target_h, mode_type, headline, subline).
        """
        now = time.time()
        time_since_action = now - self.last_action_time

        # 1. 🤙 Shaka Dwell Progress (Highest visual priority)
        if self.lock_progress > 0.05:
            label = "HOLD TO PAUSE" if self.system_state == "ACTIVE" else "HOLD TO RESUME"
            return 260.0, 42.0, "SHAKA_PROGRESS", label, f"{int(self.lock_progress * 100)}%"

        # 2. System Locked / Paused
        if self.system_state == "LOCKED":
            return 200.0, 36.0, "LOCKED", "PAUSED", "Show 🤙 to Resume"

        # 3. Transient Action Morphing (Pillar style active card for 1.3s)
        if self.last_action and time_since_action < 1.3:
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

    def _draw_pillar_capsule(self, x: float, y: float, w: float, h: float, accent_glow: Optional[str] = None):
        """Draws multi-layer frosted capsule with dual-tone borders and ambient specular rim."""
        r = h / 2.0

        # Ambient Glow Layer (if active action)
        if accent_glow:
            glow_pad = 2
            self.canvas.create_oval(x - glow_pad, y - glow_pad, x + 2 * r + glow_pad, y + h + glow_pad,
                                    fill="", outline=accent_glow, width=1)
            self.canvas.create_oval(x + w - 2 * r - glow_pad, y - glow_pad, x + w + glow_pad, y + h + glow_pad,
                                    fill="", outline=accent_glow, width=1)
            self.canvas.create_line(x + r, y - glow_pad, x + w - r, y - glow_pad, fill=accent_glow, width=1)

        # Base Obsidian Glass Body
        self.canvas.create_oval(x, y, x + 2 * r, y + h, fill=PILL_OBSIDIAN, outline=BORDER_OUTER, width=1)
        self.canvas.create_oval(x + w - 2 * r, y, x + w, y + h, fill=PILL_OBSIDIAN, outline=BORDER_OUTER, width=1)
        self.canvas.create_rectangle(x + r, y, x + w - r, y + h, fill=PILL_OBSIDIAN, outline=PILL_OBSIDIAN)

        # Specular Top Highlight Rim (Pillar / Apple glass reflection)
        self.canvas.create_line(x + r, y + 1, x + w - r, y + 1, fill=BORDER_HIGHLIGHT, width=1)
        self.canvas.create_line(x + r, y + h - 1, x + w - r, y + h - 1, fill=BORDER_OUTER, width=1)

    def _draw_animated_equalizer(self, cx: float, cy: float, level: float):
        """Renders 3 dancing vertical audio waveform bars (like Pillar SMTC)."""
        bar_w = 2.5
        spacing = 4.0
        offsets = [-spacing, 0, spacing]

        for i, dx in enumerate(offsets):
            h_mod = math.sin(self.anim_phase * 3.5 + i * 1.5) * 4.0 * max(level, 0.2)
            bar_h = max(4.0, 8.0 + h_mod)
            bx = cx + dx
            self.canvas.create_line(bx, cy - bar_h / 2, bx, cy + bar_h / 2, fill=ACCENT_CYAN, width=int(bar_w))

    def _draw_circular_progress_ring(self, cx: float, cy: float, r: float, progress: float, color: str):
        """Pillar-style circular countdown activity ring (for 🤙 Shaka hold)."""
        # Background Track Ring
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=TRACK_BG, width=2.5)

        # Animated Progress Arc
        extent_angle = -int(progress * 359)
        if extent_angle != 0:
            self.canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=extent_angle,
                                   outline=color, width=2.5, style=tk.ARC)

    def _tick_loop(self):
        if not self.running or not self.root:
            return

        self._drain_queue()
        self.anim_phase += 0.08

        # 1. Update Spring Physics
        tw, th, mode_type, headline, subline = self._determine_target_geometry()
        self.spring_w.target = tw
        self.spring_h.target = th

        current_w = self.spring_w.update(dt=0.016)
        current_h = self.spring_h.update(dt=0.016)

        # 2. Render Island
        self.canvas.delete("all")
        canvas_w = 420
        canvas_h = 74
        pill_x = (canvas_w - current_w) / 2.0
        pill_y = (canvas_h - current_h) / 2.0

        accent_glow = None
        if mode_type == "VOLUME":
            accent_glow = "#0e3a42"
        elif mode_type == "LOCKED":
            accent_glow = "#3a1215"
        elif mode_type == "SHAKA_PROGRESS":
            accent_glow = "#3a1215" if self.system_state == "ACTIVE" else "#0e3a24"

        self._draw_pillar_capsule(pill_x, pill_y, current_w, current_h, accent_glow)

        mid_y = pill_y + current_h / 2.0

        # 3. Modular Zone Rendering
        if mode_type == "LOCKED":
            # Zone 1: Crimson Padlock
            dot_x = pill_x + 18
            self.canvas.create_oval(dot_x - 4, mid_y - 4, dot_x + 4, mid_y + 4, fill=ACCENT_CRIMSON, outline="")
            # Zone 2: Title & Instruction
            self.canvas.create_text(pill_x + 30, mid_y - 1, text="PAUSED", anchor="w",
                                    fill=ACCENT_CRIMSON, font=("Segoe UI", 9, "bold"))
            self.canvas.create_text(pill_x + 85, mid_y, text="Show 🤙 to Resume", anchor="w",
                                    fill=TEXT_SECONDARY, font=("Segoe UI", 8))

        elif mode_type == "SHAKA_PROGRESS":
            # Zone 1: Shaka Glyph
            self.canvas.create_text(pill_x + 18, mid_y, text="🤙", anchor="center", font=("Segoe UI", 10))
            # Zone 2: Label
            accent_col = ACCENT_CRIMSON if self.system_state == "ACTIVE" else ACCENT_EMERALD
            self.canvas.create_text(pill_x + 36, mid_y, text=headline, anchor="w",
                                    fill=TEXT_PRIMARY, font=("Segoe UI", 8, "bold"))
            # Zone 3: Circular Activity Ring + Percent (Pillar Timer Style)
            ring_cx = pill_x + current_w - 24
            self._draw_circular_progress_ring(ring_cx, mid_y, r=9, progress=self.lock_progress, color=accent_col)
            self.canvas.create_text(ring_cx - 24, mid_y, text=subline, anchor="e",
                                    fill=accent_col, font=("Segoe UI", 8, "bold"))

        elif mode_type == "VOLUME":
            # Zone 1: Animated Equalizer Waveform Bars
            self._draw_animated_equalizer(pill_x + 18, mid_y, self.volume_level)
            # Zone 2: Volume Scrubber Slider Bar
            self.canvas.create_text(pill_x + 34, mid_y, text="VOL", anchor="w",
                                    fill=TEXT_PRIMARY, font=("Segoe UI", 8, "bold"))
            track_x = pill_x + 68
            track_w = 120
            track_h = 5
            self.canvas.create_rectangle(track_x, mid_y - track_h / 2, track_x + track_w, mid_y + track_h / 2,
                                         fill=TRACK_BG, outline="")
            fill_w = track_w * self.volume_level
            if fill_w > 1:
                self.canvas.create_rectangle(track_x, mid_y - track_h / 2, track_x + fill_w, mid_y + track_h / 2,
                                             fill=ACCENT_CYAN, outline="")
            # Zone 3: Percentage badge
            self.canvas.create_text(pill_x + current_w - 20, mid_y, text=subline, anchor="center",
                                    fill=ACCENT_CYAN, font=("Segoe UI", 8, "bold"))

        elif mode_type == "CLICK":
            # Left Click Pulse
            dot_x = pill_x + 18
            pulse_r = 4.0 + math.sin(self.anim_phase * 2) * 1.0
            self.canvas.create_oval(dot_x - pulse_r, mid_y - pulse_r, dot_x + pulse_r, mid_y + pulse_r,
                                    fill=ACCENT_EMERALD, outline="")
            self.canvas.create_text(pill_x + 32, mid_y, text=headline, anchor="w",
                                    fill=TEXT_PRIMARY, font=("Segoe UI", 8, "bold"))
            self.canvas.create_text(pill_x + 130, mid_y, text="Confirmed", anchor="w",
                                    fill=ACCENT_EMERALD, font=("Segoe UI", 8))

        elif mode_type == "DRAG":
            self.canvas.create_text(pill_x + 18, mid_y, text="⇱", anchor="center", font=("Segoe UI", 10), fill=ACCENT_AMBER)
            self.canvas.create_text(pill_x + 34, mid_y, text=headline, anchor="w",
                                    fill=ACCENT_AMBER, font=("Segoe UI", 8, "bold"))
            self.canvas.create_text(pill_x + 160, mid_y, text="Moving", anchor="w",
                                    fill=TEXT_SECONDARY, font=("Segoe UI", 8))

        elif mode_type == "SNAP":
            self.canvas.create_text(pill_x + 18, mid_y, text="⊞", anchor="center", font=("Segoe UI", 9), fill=ACCENT_INDIGO)
            self.canvas.create_text(pill_x + 34, mid_y, text=headline, anchor="w",
                                    fill=TEXT_PRIMARY, font=("Segoe UI", 8, "bold"))
            self.canvas.create_text(pill_x + 145, mid_y, text="Win+Left", anchor="w",
                                    fill=ACCENT_INDIGO, font=("Segoe UI", 8))

        else:
            # Compact Idle State: Glowing Breathing Core + Micro Pill Badge
            dot_x = pill_x + 18
            pulse_r = 3.5 + math.sin(self.anim_phase) * 0.8
            self.canvas.create_oval(dot_x - pulse_r, mid_y - pulse_r, dot_x + pulse_r, mid_y + pulse_r,
                                    fill=ACCENT_EMERALD, outline="")
            self.canvas.create_text(pill_x + 30, mid_y, text="AEROTOUCH", anchor="w",
                                    fill=TEXT_PRIMARY, font=("Segoe UI", 8, "bold"))
            self.canvas.create_text(pill_x + 115, mid_y, text="ACTIVE", anchor="w",
                                    fill=TEXT_SECONDARY, font=("Segoe UI", 7))

        self.root.after(16, self._tick_loop)
