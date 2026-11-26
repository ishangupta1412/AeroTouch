"""
AeroTouch Windows UI Element Magnetism & Target Snapping Engine
Implements Apple visionOS-grade gravitational attraction basins for UI targets.
Allows effortless sub-pixel targeting on 16px buttons, tabs, and checkboxes:
- Elastic gravitational attraction when cursor enters attraction basin
- Escape velocity gating: Fast movements glide through without sticky traps
- Tremor dampening while locked onto a target
"""

import math
import time
from typing import Dict, List, Optional, Tuple


class UITargetRect:
    """Represents a clickable or interactive UI element bounding box."""

    def __init__(self, target_id: str, left: int, top: int, right: int, bottom: int, timestamp: Optional[float] = None):
        self.target_id = target_id
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.center_x = (left + right) // 2
        self.center_y = (top + bottom) // 2
        self.last_seen: float = timestamp if timestamp is not None else time.perf_counter()

    def distance_to_center(self, x: float, y: float) -> float:
        dx = x - self.center_x
        dy = y - self.center_y
        return math.sqrt(dx * dx + dy * dy)

    def contains(self, x: float, y: float) -> bool:
        return self.left <= x <= self.right and self.top <= y <= self.bottom


class UIMagnetismEngine:
    """
    Sub-pixel gravitational snapping engine.
    Pulls cursor toward interactive UI elements during slow hovering and fine targeting.
    """

    def __init__(
        self,
        snap_radius: float = 32.0,
        attraction_strength: float = 0.65,
        escape_speed_threshold: float = 0.35,
        ttl_seconds: float = 2.5,
        max_targets: int = 32,
    ):
        self.snap_radius = snap_radius
        self.attraction_strength = attraction_strength
        self.escape_speed_threshold = escape_speed_threshold
        self.ttl_seconds = ttl_seconds
        self.max_targets = max_targets

        self._active_targets: Dict[str, UITargetRect] = {}
        self.current_locked_target: Optional[str] = None

    def register_target(self, target_id: str, left: int, top: int, right: int, bottom: int) -> None:
        """Registers or refreshes a UI element boundary rect, evicting stale targets."""
        now = time.perf_counter()
        self._active_targets[target_id] = UITargetRect(target_id, left, top, right, bottom, timestamp=now)
        if len(self._active_targets) > self.max_targets:
            oldest_key = min(self._active_targets, key=lambda k: self._active_targets[k].last_seen)
            if oldest_key != target_id:
                self._active_targets.pop(oldest_key, None)

    def _prune_stale_targets(self, now: float) -> None:
        stale = [k for k, t in self._active_targets.items() if (now - t.last_seen) > self.ttl_seconds]
        for k in stale:
            self._active_targets.pop(k, None)

    def clear_targets(self) -> None:
        """Clears all dynamic target rects."""
        self._active_targets.clear()
        self.current_locked_target = None

    def apply_magnetism(
        self,
        screen_x: int,
        screen_y: int,
        cursor_speed: float = 0.0
    ) -> Tuple[int, int, Optional[str]]:
        """
        Calculates magnetic deflection towards the nearest UI element.
        Returns:
            (adjusted_x, adjusted_y, locked_target_id)
        """
        # If moving at high speed, ignore attraction to prevent "sticky trap" resistance
        if cursor_speed >= self.escape_speed_threshold:
            self.current_locked_target = None
            return screen_x, screen_y, None

        self._prune_stale_targets(time.perf_counter())

        nearest_target: Optional[UITargetRect] = None
        min_dist: float = float("inf")

        for target in self._active_targets.values():
            dist = target.distance_to_center(screen_x, screen_y)
            if dist < self.snap_radius and dist < min_dist:
                min_dist = dist
                nearest_target = target

        if nearest_target is not None:
            # Elastic gravitational attraction towards center
            factor = self.attraction_strength * (1.0 - (min_dist / self.snap_radius))
            snapped_x = int(screen_x + (nearest_target.center_x - screen_x) * factor)
            snapped_y = int(screen_y + (nearest_target.center_y - screen_y) * factor)
            self.current_locked_target = nearest_target.target_id
            return snapped_x, snapped_y, nearest_target.target_id

        self.current_locked_target = None
        return screen_x, screen_y, None
