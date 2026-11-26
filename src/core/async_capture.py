"""
AeroTouch Lock-Free Latest-Frame Async Camera Capture
Decouples blocking USB DirectShow cap.read() from the inference and 120Hz cursor pipeline.
Always retains only the freshest frame (drops stale buffered frames) to minimize motion-to-photon latency.
"""

import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np


class AsyncCameraCapture:
    """
    Producer thread wrapper around cv2.VideoCapture.
    Exposes non-blocking read_latest() returning (frame, frame_id, timestamp).
    """

    def __init__(self, cap: cv2.VideoCapture):
        self.cap = cap
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_ts: float = 0.0
        self._frame_id: int = 0
        self._last_consumed_id: int = 0
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="AeroTouchAsyncCapture")
        self._thread.start()

    def _capture_loop(self) -> None:
        while self._running:
            try:
                ret, frame = self.cap.read()
            except Exception:
                time.sleep(0.005)
                continue

            if not ret or frame is None or getattr(frame, "size", 0) == 0:
                time.sleep(0.002)
                continue

            try:
                h, w = frame.shape[:2]
                if h < 2 or w < 2:
                    continue
            except Exception:
                continue

            now = time.perf_counter()
            with self._lock:
                self._latest_frame = frame
                self._latest_ts = now
                self._frame_id += 1

    def read_latest(self, timeout: float = 0.05) -> Tuple[bool, Optional[np.ndarray], float]:
        """
        Returns (True, frame, timestamp) if a new frame is available, else waits briefly up to timeout.
        """
        deadline = time.perf_counter() + timeout
        while self._running:
            with self._lock:
                if self._frame_id > self._last_consumed_id and self._latest_frame is not None:
                    self._last_consumed_id = self._frame_id
                    return True, self._latest_frame, self._latest_ts
            if time.perf_counter() >= deadline:
                break
            time.sleep(0.001)
        return False, None, 0.0

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=0.5)
            except Exception:
                pass
        self._thread = None
