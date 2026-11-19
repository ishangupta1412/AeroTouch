"""
AeroTouch Kinetic Scroll Controller
macOS-grade two-finger kinetic scrolling with momentum friction decay.
Synthesizes native Win32 wheel events via user32.mouse_event.
"""

from typing import Optional


class KineticScrollController:
    """
    Simulates high-precision trackpad-grade kinetic scrolling with momentum friction decay.
    Triggered by parallel Index + Middle fingers pointing upward.
    """

    def __init__(
        self,
        sensitivity: float = 14.0,
        friction_decay: float = 0.85,
        min_velocity: float = 0.15
    ):
        self.sensitivity = sensitivity
        self.friction_decay = friction_decay
        self.min_velocity = min_velocity

        self.is_active: bool = False
        self.prev_anchor_y: Optional[float] = None
        self.current_velocity: float = 0.0
        self.last_update_time: Optional[float] = None

    def update(
        self,
        is_gesture_active: bool,
        current_y: float,
        timestamp: float
    ) -> int:
        """
        Returns integer scroll steps to pass directly to Win32 mouse_event(MOUSEEVENTF_WHEEL).
        Positive steps = Scroll UP, Negative steps = Scroll DOWN.
        """
        if is_gesture_active:
            if not self.is_active or self.prev_anchor_y is None:
                self.is_active = True
                self.prev_anchor_y = current_y
                self.current_velocity = 0.0
                self.last_update_time = timestamp
                return 0

            # In image coords, moving UP is decreasing Y (-delta)
            # Moving fingers UP -> scroll page UP (+steps)
            delta_y = -(current_y - self.prev_anchor_y)
            self.prev_anchor_y = current_y
            self.last_update_time = timestamp

            instant_vel = delta_y * self.sensitivity * 50.0
            # Exponential moving average filter for smooth wheel action
            self.current_velocity = 0.6 * self.current_velocity + 0.4 * instant_vel
            return int(round(self.current_velocity))

        else:
            # Gesture released: apply kinetic momentum friction decay
            if abs(self.current_velocity) > self.min_velocity:
                self.current_velocity *= self.friction_decay
                steps = int(round(self.current_velocity))
                if abs(steps) == 0:
                    self.current_velocity = 0.0
                    self.is_active = False
                    self.prev_anchor_y = None
                return steps
            else:
                self.current_velocity = 0.0
                self.is_active = False
                self.prev_anchor_y = None
                return 0

    def reset(self):
        self.is_active = False
        self.prev_anchor_y = None
        self.current_velocity = 0.0
        self.last_update_time = None
