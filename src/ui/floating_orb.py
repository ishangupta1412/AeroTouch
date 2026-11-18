"""
AeroTouch Floating Ambient Orb (Gemini Live / Dynamic Island Style)
A transparent, borderless, always-on-top circular widget with fluid breathing animations.
Visualizes spatial tracking state and click events without obstructing the screen.
"""

import math
import time
import tkinter as tk
import threading
from typing import Optional


class FloatingOrbOverlay:
    """
    Floating circular glass orb widget.
    Smooth animated breathing core with reactive color changes on gesture events.
    """

    def __init__(self, size: int = 90):
        self.size = size
        self.root: Optional[tk.Tk] = None
        self.canvas: Optional[tk.Canvas] = None
        self.running = False
        self._thread: Optional[threading.Thread] = None

        # State tracking
        self.is_tracking = False
        self.last_action: Optional[str] = None
        self.last_action_time: float = 0.0

        # Animation parameters
        self.phase = 0.0
        self.drag_x = 0
        self.drag_y = 0

    def start(self):
        """Starts the floating orb in a dedicated UI thread."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_ui, daemon=True)
        self._thread.start()

    def _run_ui(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)

        # Transparent background colorkey for Windows
        TRANS_BG = "#010101"
        self.root.wm_attributes("-transparentcolor", TRANS_BG)
        self.root.configure(bg=TRANS_BG)

        # Default position: bottom-right corner
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x = screen_w - self.size - 40
        pos_y = screen_h - self.size - 80
        self.root.geometry(f"{self.size}x{self.size}+{pos_x}+{pos_y}")

        self.canvas = tk.Canvas(
            self.root,
            width=self.size,
            height=self.size,
            bg=TRANS_BG,
            highlightthickness=0
        )
        self.canvas.pack()

        # Dragging support
        def start_drag(event):
            self.drag_x = event.x
            self.drag_y = event.y

        def on_drag(event):
            dx = event.x - self.drag_x
            dy = event.y - self.drag_y
            new_x = self.root.winfo_x() + dx
            new_y = self.root.winfo_y() + dy
            self.root.geometry(f"+{new_x}+{new_y}")

        self.canvas.bind("<Button-1>", start_drag)
        self.canvas.bind("<B1-Motion>", on_drag)

        self._animate_loop()
        self.root.mainloop()

    def set_state(self, is_tracking: bool, action: Optional[str] = None):
        """Thread-safe update of current tracking and gesture state."""
        self.is_tracking = is_tracking
        if action:
            self.last_action = action
            self.last_action_time = time.time()

    def _animate_loop(self):
        if not self.running or not self.root:
            return

        self.phase += 0.08
        self._draw_orb()
        self.root.after(30, self._animate_loop)

    def _draw_orb(self):
        self.canvas.delete("all")
        cx = self.size / 2.0
        cy = self.size / 2.0

        now = time.time()
        is_action_active = (now - self.last_action_time) < 0.45

        # Colors based on action / tracking state
        if is_action_active and self.last_action:
            if "LEFT_CLICK" in self.last_action:
                # Neon Emerald (Gemini Click)
                outer_color = "#052e16"
                mid_color = "#15803d"
                core_color = "#22c55e"
                ring_color = "#4ade80"
            elif "RIGHT_CLICK" in self.last_action:
                # Amber Gold (Right Click)
                outer_color = "#451a03"
                mid_color = "#b45309"
                core_color = "#f59e0b"
                ring_color = "#fbbf24"
            else:
                # Purple / Violet (Window Snap / Desktop Switch)
                outer_color = "#3b0764"
                mid_color = "#7e22ce"
                core_color = "#a855f7"
                ring_color = "#c084fc"
        elif self.is_tracking:
            # Active Spatial Tracking (Electric Cyan & Deep Gemini Blue)
            outer_color = "#082f49"
            mid_color = "#0284c7"
            core_color = "#38bdf8"
            ring_color = "#7dd3fc"
        else:
            # Idle Ambient Breathing (Deep Obsidian Slate)
            outer_color = "#0f172a"
            mid_color = "#1e293b"
            core_color = "#334155"
            ring_color = "#475569"

        # Breathing radius oscillation
        breath = math.sin(self.phase) * (4.0 if is_action_active else 2.5)

        r_outer = (self.size / 2.0) - 4 + (breath * 0.5)
        r_mid = r_outer * 0.75 + breath
        r_core = r_outer * 0.45 + (breath * 0.8)

        # 1. Outer Dark Glass Shield
        self.canvas.create_oval(
            cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer,
            fill=outer_color, outline=ring_color, width=1.5
        )

        # 2. Mid Fluid Halo
        self.canvas.create_oval(
            cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid,
            fill=mid_color, outline=""
        )

        # 3. Bright Glowing Core
        self.canvas.create_oval(
            cx - r_core, cy - r_core, cx + r_core, cy + r_core,
            fill=core_color, outline=""
        )

        # 4. Center Micro Reticle Dot
        dot_r = 3 if not is_action_active else 5
        self.canvas.create_oval(
            cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r,
            fill="#ffffff", outline=""
        )

    def stop(self):
        """Closes and destroys the orb overlay."""
        self.running = False
        if self.root:
            try:
                self.root.after(0, self._cleanup_root)
            except Exception:
                pass

    def _cleanup_root(self):
        try:
            if self.root:
                self.root.quit()
                self.root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    # Demo preview
    orb = FloatingOrbOverlay(size=90)
    orb.start()
    print("Floating Orb active! Simulating gesture events...")
    time.sleep(2)
    orb.set_state(is_tracking=True)
    time.sleep(2)
    orb.set_state(is_tracking=True, action="LEFT_CLICK")
    time.sleep(1)
    orb.set_state(is_tracking=True, action="RIGHT_CLICK")
    time.sleep(1.5)
    orb.stop()
    print("Demo finished.")
