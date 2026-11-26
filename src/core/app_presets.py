"""
AeroTouch Dynamic Foreground Application Presets Engine
Detects the active focused Windows application and automatically tailors
spatial ballistics, gestures, and hotkeys for peak domain productivity:
- BROWSER: Chrome, Edge, Firefox, Brave (Tab flipping, history back/forward)
- CREATIVE: Figma, Photoshop, Illustrator, Blender (Canvas panning, zoom)
- CODING: VS Code, Cursor, PyCharm, Terminal (Terminal toggle, code folding)
- MEDIA: Spotify, YouTube, VLC, Netflix (In-air volume dial, play/pause, skip)
- GENERAL: Default universal OS desktop navigation
"""

import os
from enum import Enum, auto
from typing import Dict, Optional, Tuple


class AppCategory(Enum):
    GENERAL = auto()
    BROWSER = auto()
    CREATIVE = auto()
    CODING = auto()
    MEDIA = auto()


class AppPreset:
    """Configurable kinematic & gesture parameters for a specific application domain."""

    def __init__(
        self,
        category: AppCategory,
        name: str,
        scroll_multiplier: float = 1.0,
        pointer_sensitivity: float = 1.0,
        enable_tab_flipping: bool = False,
        enable_canvas_pan: bool = False,
        enable_media_rotary: bool = False,
    ):
        self.category = category
        self.name = name
        self.scroll_multiplier = scroll_multiplier
        self.pointer_sensitivity = pointer_sensitivity
        self.enable_tab_flipping = enable_tab_flipping
        self.enable_canvas_pan = enable_canvas_pan
        self.enable_media_rotary = enable_media_rotary


class AppPresetEngine:
    """
    Monitors active foreground window and hot-swaps spatial interaction profiles.
    """

    KNOWN_PROCESSES: Dict[str, AppCategory] = {
        # Browsers
        "chrome.exe": AppCategory.BROWSER,
        "msedge.exe": AppCategory.BROWSER,
        "firefox.exe": AppCategory.BROWSER,
        "brave.exe": AppCategory.BROWSER,
        # Creative / Design
        "figma.exe": AppCategory.CREATIVE,
        "photoshop.exe": AppCategory.CREATIVE,
        "illustrator.exe": AppCategory.CREATIVE,
        "blender.exe": AppCategory.CREATIVE,
        "canva.exe": AppCategory.CREATIVE,
        # Coding / IDEs
        "code.exe": AppCategory.CODING,
        "cursor.exe": AppCategory.CODING,
        "pycharm64.exe": AppCategory.CODING,
        "windowsterminal.exe": AppCategory.CODING,
        "powershell.exe": AppCategory.CODING,
        "cmd.exe": AppCategory.CODING,
        # Media Players
        "spotify.exe": AppCategory.MEDIA,
        "vlc.exe": AppCategory.MEDIA,
        "wmplayer.exe": AppCategory.MEDIA,
    }

    def __init__(self):
        self._presets: Dict[AppCategory, AppPreset] = {
            AppCategory.GENERAL: AppPreset(
                category=AppCategory.GENERAL,
                name="Desktop OS",
                scroll_multiplier=1.0,
                pointer_sensitivity=1.0,
            ),
            AppCategory.BROWSER: AppPreset(
                category=AppCategory.BROWSER,
                name="Web Browser",
                scroll_multiplier=1.25,
                pointer_sensitivity=1.05,
                enable_tab_flipping=True,
            ),
            AppCategory.CREATIVE: AppPreset(
                category=AppCategory.CREATIVE,
                name="Creative Canvas",
                scroll_multiplier=0.85,
                pointer_sensitivity=0.90,
                enable_canvas_pan=True,
            ),
            AppCategory.CODING: AppPreset(
                category=AppCategory.CODING,
                name="Code IDE",
                scroll_multiplier=1.15,
                pointer_sensitivity=1.0,
            ),
            AppCategory.MEDIA: AppPreset(
                category=AppCategory.MEDIA,
                name="Media Player",
                scroll_multiplier=1.0,
                pointer_sensitivity=1.0,
                enable_media_rotary=True,
            ),
        }
        self.current_category: AppCategory = AppCategory.GENERAL
        self.current_process_name: str = "explorer.exe"

    def classify_process(self, process_or_title: str) -> AppCategory:
        """Classifies process executable name or window title to an AppCategory."""
        cleaned = process_or_title.strip().lower()

        # Direct executable match
        for exe_name, cat in self.KNOWN_PROCESSES.items():
            if exe_name in cleaned:
                return cat

        # Fallback keyword match in window title
        if any(w in cleaned for w in ["youtube", "spotify", "music", "netflix", "vlc"]):
            return AppCategory.MEDIA
        if any(w in cleaned for w in ["chrome", "edge", "firefox", "brave", "safari"]):
            return AppCategory.BROWSER
        if any(w in cleaned for w in ["figma", "photoshop", "blender", "illustrator", "canvas"]):
            return AppCategory.CREATIVE
        if any(w in cleaned for w in ["visual studio", "vs code", "cursor", "terminal", "powershell"]):
            return AppCategory.CODING

        return AppCategory.GENERAL

    def get_active_preset(self) -> AppPreset:
        """Returns the currently active domain preset."""
        return self._presets.get(self.current_category, self._presets[AppCategory.GENERAL])

    def update_from_process(self, process_or_title: str) -> AppPreset:
        """Updates internal state and returns active preset."""
        self.current_process_name = os.path.basename(process_or_title).lower()
        self.current_category = self.classify_process(process_or_title)
        return self.get_active_preset()

    def update_active_window(self) -> AppPreset:
        """Queries the active Win32 foreground window title and updates the preset."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                buf = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, buf, 512)
                if buf.value:
                    return self.update_from_process(buf.value)
        except Exception:
            pass
        return self.get_active_preset()
