"""
AeroTouch Shared Tkinter UI Host
Runs a single tk.Tk() interpreter on one dedicated daemon thread so multiple
overlays (Dynamic Island, Floating Orb, AirCanvas) can coexist as tk.Toplevel
windows without triggering Tcl_AsyncDelete cross-thread crashes.
"""

import queue
import threading
import tkinter as tk
from typing import Callable, Optional


class _SharedTkHost:
    """Singleton host owning the sole tk.Tk() root and Tcl event loop."""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._root: Optional[tk.Tk] = None
        self._ready = threading.Event()
        self._task_queue: queue.Queue = queue.Queue()
        self._active_windows: int = 0

    def ensure_started(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._ready.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="AeroTouchTkHost",
            )
            self._thread.start()
        self._ready.wait(timeout=3.0)

    def _run_loop(self) -> None:
        root = tk.Tk()
        root.withdraw()
        self._root = root
        self._ready.set()

        def _poll():
            try:
                while not self._task_queue.empty():
                    fn = self._task_queue.get_nowait()
                    try:
                        fn(root)
                    except Exception:
                        pass
            except Exception:
                pass
            if self._root is not None:
                root.after(10, _poll)

        root.after(10, _poll)
        try:
            root.mainloop()
        except Exception:
            pass
        finally:
            self._root = None

    def post(self, fn: Callable[[tk.Tk], None]) -> None:
        """Schedules `fn(root)` to execute on the Tk host thread."""
        self.ensure_started()
        self._task_queue.put(fn)

    def register_window(self) -> None:
        with self._lock:
            self._active_windows += 1

    def unregister_window(self) -> None:
        with self._lock:
            self._active_windows = max(0, self._active_windows - 1)


_HOST = _SharedTkHost()


def get_tk_host() -> _SharedTkHost:
    return _HOST
