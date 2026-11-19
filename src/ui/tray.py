"""
AeroTouch Windows System Tray Daemon
Allows AeroTouch to run quietly in the background without a persistent console window.
Provides quick-access notification tray menu:
 - Pause / Resume Tracking
 - Recalibrate Kinematics
 - Cortex Self-Tuning
 - Show / Hide Preview
 - Exit AeroTouch
Uses native Win32 Shell_NotifyIcon API with robust fallback.
"""

import sys
import os
import threading
import time
from typing import Callable, Optional

# Prepend project root
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


class AeroTouchTrayDaemon:
    """
    Native Win32 System Tray Daemon for AeroTouch.
    Manages the notification area icon, right-click context menu, and background lifecycle.
    """

    # Custom Windows Messages and Menu IDs
    WM_TRAYMESSAGE = 0x8000 + 100  # WM_USER + 100
    ID_PAUSE_RESUME = 1001
    ID_RECALIBRATE = 1002
    ID_CORTEX_TUNE = 1003
    ID_TOGGLE_PREVIEW = 1004
    ID_EXIT = 1005

    def __init__(
        self,
        on_toggle_pause: Optional[Callable[[], bool]] = None,
        on_recalibrate: Optional[Callable[[], None]] = None,
        on_cortex_tune: Optional[Callable[[], None]] = None,
        on_toggle_preview: Optional[Callable[[], bool]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        title: str = "AeroTouch — Spatial Operating Layer"
    ):
        self.on_toggle_pause = on_toggle_pause
        self.on_recalibrate = on_recalibrate
        self.on_cortex_tune = on_cortex_tune
        self.on_toggle_preview = on_toggle_preview
        self.on_exit = on_exit
        self.title = title

        self.is_running: bool = False
        self.is_paused: bool = False
        self.is_preview_visible: bool = True
        self._hwnd = None
        self._thread: Optional[threading.Thread] = None
        self._icon_added: bool = False

    def notify(self, title: str, message: str) -> None:
        """Emits a Windows toast notification or tray balloon tip."""
        try:
            import win32gui
            import win32con
            if self._hwnd and self._icon_added:
                flags = win32gui.NIF_INFO
                nid = (
                    self._hwnd,
                    0,
                    flags,
                    self.WM_TRAYMESSAGE,
                    0,
                    self.title,
                    message,
                    200,
                    title,
                    win32gui.NIIF_INFO
                )
                win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)
                return
        except Exception:
            pass

        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=3, threaded=True)
        except Exception:
            print(f"[Tray Notification]: {title} - {message}")

    def _create_window(self):
        """Creates the hidden Win32 message window to receive tray events."""
        import win32gui
        import win32con

        msg_wnd_class = "AeroTouchTrayWindowClass"
        wc = win32gui.WNDCLASS()
        hinst = win32gui.GetModuleHandle(None)
        wc.hInstance = hinst
        wc.lpszClassName = msg_wnd_class
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc.hbrBackground = win32con.COLOR_WINDOW
        wc.lpfnWndProc = self._wnd_proc

        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass  # Already registered

        hwnd = win32gui.CreateWindow(
            msg_wnd_class,
            "AeroTouchTrayWindow",
            0,
            0, 0, 0, 0,
            0, 0, hinst, None
        )
        self._hwnd = hwnd

        # Add Tray Icon
        icon_handle = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (hwnd, 0, flags, self.WM_TRAYMESSAGE, icon_handle, self.title)
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        self._icon_added = True

    def _show_context_menu(self):
        """Displays the popup context menu on right-click."""
        import win32gui
        import win32con

        menu = win32gui.CreatePopupMenu()
        pause_label = "Resume Tracking" if self.is_paused else "Pause Tracking"
        preview_label = "Hide Preview Window" if self.is_preview_visible else "Show Preview Window"

        win32gui.AppendMenu(menu, win32con.MF_STRING, self.ID_PAUSE_RESUME, pause_label)
        win32gui.AppendMenu(menu, win32con.MF_STRING, self.ID_TOGGLE_PREVIEW, preview_label)
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, self.ID_RECALIBRATE, "Recalibrate Kinematics")
        win32gui.AppendMenu(menu, win32con.MF_STRING, self.ID_CORTEX_TUNE, "Run Cortex Telemetry Optimization")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, self.ID_EXIT, "Exit AeroTouch")

        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self._hwnd)
        win32gui.TrackPopupMenu(menu, win32con.TPM_RIGHTALIGN, pos[0], pos[1], 0, self._hwnd, None)
        win32gui.PostMessage(self._hwnd, win32con.WM_NULL, 0, 0)

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        """Win32 window message processor."""
        import win32gui
        import win32con

        if msg == self.WM_TRAYMESSAGE:
            if lparam == win32con.WM_RBUTTONUP or lparam == win32con.WM_LBUTTONUP:
                self._show_context_menu()
            return 0

        elif msg == win32con.WM_COMMAND:
            cmd = wparam & 0xFFFF
            if cmd == self.ID_PAUSE_RESUME:
                self.is_paused = not self.is_paused
                if self.on_toggle_pause:
                    try:
                        self.is_paused = bool(self.on_toggle_pause())
                    except Exception as e:
                        print(f"[Tray]: Pause toggle error: {e}")
                status = "Paused" if self.is_paused else "Active"
                self.notify("AeroTouch", f"Hand Tracking is now {status}.")

            elif cmd == self.ID_TOGGLE_PREVIEW:
                self.is_preview_visible = not self.is_preview_visible
                if self.on_toggle_preview:
                    try:
                        self.is_preview_visible = bool(self.on_toggle_preview())
                    except Exception as e:
                        print(f"[Tray]: Toggle preview error: {e}")

            elif cmd == self.ID_RECALIBRATE:
                if self.on_recalibrate:
                    try:
                        self.on_recalibrate()
                    except Exception as e:
                        print(f"[Tray]: Recalibration error: {e}")
                self.notify("AeroTouch", "Spatial filters recalibrated.")

            elif cmd == self.ID_CORTEX_TUNE:
                self.notify("AeroTouch Cortex", "Running Qwen telemetry analysis in background...")
                if self.on_cortex_tune:
                    threading.Thread(target=self.on_cortex_tune, daemon=True).start()

            elif cmd == self.ID_EXIT:
                self.stop()
            return 0

        elif msg == win32con.WM_DESTROY:
            self._remove_tray_icon()
            win32gui.PostQuitMessage(0)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _remove_tray_icon(self):
        """Removes the tray icon from the notification bar."""
        if self._icon_added and self._hwnd:
            try:
                import win32gui
                nid = (self._hwnd, 0)
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
            except Exception:
                pass
            self._icon_added = False

    def _message_loop(self):
        """Dedicated message pump thread for Windows events."""
        try:
            import win32gui
            self._create_window()
            win32gui.PumpMessages()
        except Exception as e:
            print(f"[Tray Daemon]: Message loop exited: {e}")
        finally:
            self._remove_tray_icon()

    def start(self) -> None:
        """Starts the tray icon in a dedicated daemon thread."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True, name="AeroTouchTrayThread")
        self._thread.start()
        print("[AeroTouch Daemon]: System Tray presence initialized in Windows notification area.")

    def stop(self) -> None:
        """Gracefully shuts down the tray icon and invokes exit handler."""
        if not self.is_running:
            return
        self.is_running = False
        if self._hwnd:
            try:
                import win32gui
                import win32con
                win32gui.PostMessage(self._hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass
        self._remove_tray_icon()
        if self.on_exit:
            self.on_exit()


if __name__ == "__main__":
    daemon = AeroTouchTrayDaemon(
        on_toggle_pause=lambda: print("[Tray]: Toggle pause triggered"),
        on_exit=lambda: sys.exit(0)
    )
    daemon.start()
    daemon.notify("AeroTouch", "AeroTouch System Tray Daemon is active.")
    try:
        while daemon.is_running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        daemon.stop()
