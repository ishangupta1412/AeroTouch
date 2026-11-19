"""
AeroTouch Low-Latency Audio Feedback (Earcons)
Synthesizes subtle sci-fi lock and unlock audio cues using native Windows audio kernel.
Runs in daemon threads to ensure 0ms latency impact on the 60 FPS vision loop.
"""

import threading
import time


def _beep_lock():
    try:
        import winsound
        # Sleek descending minor third: G5 (784Hz) -> E5 (659Hz) -> C5 (523Hz)
        winsound.Beep(784, 70)
        time.sleep(0.02)
        winsound.Beep(523, 110)
    except Exception:
        pass


def _beep_unlock():
    try:
        import winsound
        # Bright ascending fifth: C5 (523Hz) -> G5 (784Hz)
        winsound.Beep(523, 70)
        time.sleep(0.02)
        winsound.Beep(784, 120)
    except Exception:
        pass


def play_chime_async(is_lock: bool = True) -> None:
    """Dispatches lock or unlock audio chime in a non-blocking thread."""
    target = _beep_lock if is_lock else _beep_unlock
    t = threading.Thread(target=target, daemon=True)
    t.start()
