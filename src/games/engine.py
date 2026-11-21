"""
AeroTouch Gaming Engine
Central orchestrator for Game Mode:
- Manages Game Mode activation lifecycle
- Integrates the 🤜🤛 FistBumpTrigger
- Dispatches spatial tracking frames to the active game profile
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from src.gestures.engine import HandLandmarks
from .base_profile import BaseGameProfile
from .trigger import FistBumpTrigger

logger = logging.getLogger("AeroTouch.GameEngine")


class DefaultArcadeProfile(BaseGameProfile):
    """
    Default pluggable profile: Virtual arcade steering and action triggers.
    Left hand tilt/position controls steering/WASD, Right hand pinch/fist controls fire/jump.
    """

    def __init__(self):
        super().__init__(
            game_id="default_arcade",
            game_name="Universal Arcade Controller",
            description="Default spatial controller profile for arcade, platformers, and racing games."
        )

    def process_frame(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        kernel,
        timestamp: float
    ) -> Dict[str, Any]:
        executed = []
        # Profile-specific mappings will be dispatched here
        return {
            "game_id": self.game_id,
            "actions": executed,
            "is_gaming": True
        }


class GameEngine:
    """
    Autonomous gaming execution sub-system.
    Keeps all game-specific control and development cleanly segregated.
    """

    def __init__(self):
        self.is_active: bool = False
        self.trigger: FistBumpTrigger = FistBumpTrigger(
            bump_distance_threshold=0.16,
            dwell_duration=0.35,
            cooldown=1.5
        )
        self._profiles: Dict[str, BaseGameProfile] = {}
        self.active_profile_id: Optional[str] = None

        # Register default fallback profile
        default_profile = DefaultArcadeProfile()
        self.register_profile(default_profile)
        self.active_profile_id = default_profile.game_id

    def register_profile(self, profile: BaseGameProfile) -> None:
        """Registers a new game profile into the engine."""
        self._profiles[profile.game_id] = profile
        logger.info(f"[GameEngine]: Registered game profile '{profile.game_name}' ({profile.game_id})")

    def get_profile(self, game_id: str) -> Optional[BaseGameProfile]:
        """Retrieves a registered game profile by id."""
        return self._profiles.get(game_id)

    def list_profiles(self) -> List[Dict[str, str]]:
        """Lists all registered games."""
        return [
            {"id": p.game_id, "name": p.game_name, "description": p.description}
            for p in self._profiles.values()
        ]

    def set_active_profile(self, game_id: str, kernel=None) -> bool:
        """Switches the active game profile."""
        if game_id not in self._profiles:
            logger.warning(f"[GameEngine]: Unknown game profile '{game_id}'")
            return False

        if self.is_active and self.active_profile_id and self.active_profile_id in self._profiles:
            self._profiles[self.active_profile_id].on_exit(kernel)

        self.active_profile_id = game_id
        if self.is_active:
            self._profiles[game_id].on_enter(kernel)
        return True

    def toggle(self, kernel=None) -> bool:
        """Toggles Game Mode on/off."""
        self.is_active = not self.is_active
        active_prof = self._profiles.get(self.active_profile_id)

        if active_prof:
            if self.is_active:
                active_prof.on_enter(kernel)
            else:
                active_prof.on_exit(kernel)

        state_str = "ENABLED" if self.is_active else "DISABLED"
        logger.info(f"[GameEngine]: Game Mode {state_str}")
        return self.is_active

    def evaluate_trigger(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        timestamp: Optional[float] = None
    ) -> Tuple[bool, float]:
        """
        Evaluates frame for the dual-hand fist bump trigger.
        Returns:
            (toggled: bool, progress: float)
        """
        triggered, progress = self.trigger.update(right_hand, left_hand, timestamp)
        return triggered, progress

    def process_frame(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        kernel,
        timestamp: float
    ) -> Dict[str, Any]:
        """
        Dispatches spatial frame to the active game profile if Game Mode is active.
        """
        if not self.is_active or not self.active_profile_id:
            return {"is_gaming": False}

        profile = self._profiles.get(self.active_profile_id)
        if not profile:
            return {"is_gaming": False}

        return profile.process_frame(right_hand, left_hand, kernel, timestamp)
