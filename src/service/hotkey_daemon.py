"""
AeroTouch Native Win32 Hotkey Daemon
Registers global shortcut Ctrl + Alt + A directly in Windows OS user32.dll.
Toggles AeroTouch on and off instantly without polling or CPU overhead.
"""

import os
import sys
import time
import ctypes
import winsound
import subprocess
from ctypes import wintypes
from typing import Optional


MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
VK_A = 0x41
HOTKEY_ID = 101
WM_HOTKEY = 0x0312


class NativeHotkeyDaemon:
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.active_process: Optional[subprocess.Popen] = None

    def start_listener(self):
        # Register global hotkey: Ctrl + Alt + A
        success = self.user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_ALT, VK_A)
        if not success:
            err = ctypes.GetLastError()
            print(f"[ERROR]: Failed to register Ctrl+Alt+A (Error Code: {err}). Maybe another app is using it?")
            return

        print("=" * 65)
        print("      AEROTOUCH: NATIVE GLOBAL HOTKEY DAEMON ONLINE     ")
        print("=" * 65)
        print("Listening for: [Ctrl + Alt + A]")
        print("Status: Ready to toggle AeroTouch from ANY window.")
        print("Press Ctrl + C in this terminal to stop daemon.\n")

        msg = wintypes.MSG()
        try:
            while self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    self._on_hotkey_triggered()

                self.user32.TranslateMessage(ctypes.byref(msg))
                self.user32.DispatchMessageW(ctypes.byref(msg))
        except KeyboardInterrupt:
            print("\nShutting down hotkey daemon...")
        finally:
            self.user32.UnregisterHotKey(None, HOTKEY_ID)
            if self.active_process and self.active_process.poll() is None:
                self.active_process.terminate()
            print("[AeroTouch]: Hotkey unregistered safely.")

    def _on_hotkey_triggered(self):
        # If already running, toggle OFF
        if self.active_process and self.active_process.poll() is None:
            print("[HOTKEY]: Ctrl+Alt+A detected -> Stopping AeroTouch...")
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            self.active_process.terminate()
            self.active_process = None
        else:
            # If stopped, toggle ON
            print("[HOTKEY]: Ctrl+Alt+A detected -> Starting AeroTouch with Floating Orb...")
            winsound.MessageBeep(winsound.MB_OK)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.active_process = subprocess.Popen(
                [sys.executable, "-m", "src.main", "--orb"],
                cwd=base_dir
            )


if __name__ == "__main__":
    daemon = NativeHotkeyDaemon()
    daemon.start_listener()
