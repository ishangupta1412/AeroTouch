"""
AeroTouch Low-Latency Audio Feedback (Earcons)
Plays a custom WAV chime for gesture lock/unlock events using native Windows audio.
Runs in daemon threads to ensure 0ms latency impact on the 60 FPS vision loop.
"""

import os
import threading

# Resolve chime path relative to this module so it works from any CWD
_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sounds")
_CHIME_PATH = os.path.normpath(os.path.join(_ASSETS_DIR, "aerotouch_chime.wav"))


def _play_wav() -> None:
    """Play the chime WAV file asynchronously via winsound."""
    try:
        import winsound  # Windows-only stdlib — always available on target platform
        winsound.PlaySound(_CHIME_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass


def play_chime_async(is_lock: bool = True) -> None:
    """Dispatch lock or unlock audio chime in a non-blocking daemon thread.

    Both lock and unlock use the same premium WAV chime.
    ``is_lock`` is kept as a parameter for API compatibility and future
    differentiation (e.g. pitch-shifted variant) without breaking callers.
    """
    t = threading.Thread(target=_play_wav, daemon=True)
    t.start()
