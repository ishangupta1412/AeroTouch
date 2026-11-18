"""
AeroTouch Cortex OS Action Suite
Safe and atomic execution tools for Windows 11 automation triggered by Local LLM.
"""

import os
import subprocess
from typing import Dict, Any
from src.os_bridge.win32_kernel import Win32KernelBridge, VirtualKey


class CortexOSTools:
    """Windows 11 automation tools callable by AeroTouch Cortex LLM."""

    def __init__(self):
        self.kernel = Win32KernelBridge()

    def open_application(self, app_name: str) -> Dict[str, Any]:
        """Launches a common desktop application or opens via Windows search."""
        app_clean = app_name.lower().strip()
        
        app_map = {
            "spotify": "spotify",
            "chrome": "chrome",
            "vscode": "code",
            "code": "code",
            "notepad": "notepad",
            "calc": "calc",
            "calculator": "calc",
            "terminal": "wt",
            "cmd": "cmd",
            "explorer": "explorer",
            "files": "explorer"
        }

        target = app_map.get(app_clean, app_clean)
        try:
            subprocess.Popen(f"start {target}", shell=True)
            return {"status": "success", "message": f"Launched application: {target}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def snap_window(self, direction: str) -> Dict[str, Any]:
        """Snaps or controls active window layout (left, right, max, min)."""
        d = direction.lower().strip()
        if d in ["left", "l"]:
            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_LEFT)
        elif d in ["right", "r"]:
            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_RIGHT)
        elif d in ["max", "maximize", "up"]:
            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_UP)
        elif d in ["min", "minimize", "down"]:
            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_DOWN)
        else:
            return {"status": "error", "message": f"Unknown direction: {direction}"}

        return {"status": "success", "message": f"Window layout changed: {direction}"}

    def media_control(self, action: str) -> Dict[str, Any]:
        """Controls media playback and system volume."""
        act = action.lower().strip()
        # Windows multimedia virtual keys
        VK_VOLUME_MUTE = 0xAD
        VK_VOLUME_DOWN = 0xAE
        VK_VOLUME_UP = 0xAF
        VK_MEDIA_NEXT_TRACK = 0xB0
        VK_MEDIA_PREV_TRACK = 0xB1
        VK_MEDIA_PLAY_PAUSE = 0xB3

        if "up" in act:
            for _ in range(5):
                self.kernel.tap_key(VK_VOLUME_UP)
            return {"status": "success", "message": "Volume increased (+10%)"}
        elif "down" in act:
            for _ in range(5):
                self.kernel.tap_key(VK_VOLUME_DOWN)
            return {"status": "success", "message": "Volume decreased (-10%)"}
        elif "mute" in act:
            self.kernel.tap_key(VK_VOLUME_MUTE)
            return {"status": "success", "message": "Volume muted/unmuted"}
        elif "play" in act or "pause" in act:
            self.kernel.tap_key(VK_MEDIA_PLAY_PAUSE)
            return {"status": "success", "message": "Media play/pause toggled"}
        elif "next" in act:
            self.kernel.tap_key(VK_MEDIA_NEXT_TRACK)
            return {"status": "success", "message": "Skipped to next track"}
        elif "prev" in act:
            self.kernel.tap_key(VK_MEDIA_PREV_TRACK)
            return {"status": "success", "message": "Returned to previous track"}

        return {"status": "error", "message": f"Unknown media command: {action}"}

    def virtual_desktop(self, action: str) -> Dict[str, Any]:
        """Navigates virtual desktops (next, prev, overview)."""
        act = action.lower().strip()
        if "next" in act or "right" in act:
            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_CONTROL, VirtualKey.VK_RIGHT)
            return {"status": "success", "message": "Switched to next virtual desktop"}
        elif "prev" in act or "left" in act:
            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_CONTROL, VirtualKey.VK_LEFT)
            return {"status": "success", "message": "Switched to previous virtual desktop"}
        elif "overview" in act or "task" in act:
            self.kernel.hotkey(VirtualKey.VK_LWIN, VirtualKey.VK_TAB)
            return {"status": "success", "message": "Opened Task View / Desktop Overview"}

        return {"status": "error", "message": f"Unknown virtual desktop action: {action}"}

    def execute_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches dynamic function calls from the LLM."""
        if name == "open_application":
            return self.open_application(arguments.get("app_name", ""))
        elif name == "snap_window":
            return self.snap_window(arguments.get("direction", "left"))
        elif name == "media_control":
            return self.media_control(arguments.get("action", "play_pause"))
        elif name == "virtual_desktop":
            return self.virtual_desktop(arguments.get("action", "next"))
        else:
            return {"status": "error", "message": f"Unknown tool: {name}"}
