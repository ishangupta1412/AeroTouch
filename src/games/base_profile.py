"""
AeroTouch Base Game Profile
Abstract contract for all pluggable games in AeroTouch Game Mode.
Each game profile implements:
  - on_enter(): State setup when entering Game Mode
  - on_exit(): Clean up keys / reset state when exiting Game Mode
  - process_frame(): Maps dual-hand landmarks to game actions
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from src.gestures.engine import HandLandmarks


class BaseGameProfile(ABC):
    """
    Abstract base class for all AeroTouch Game Profiles.
    """

    def __init__(self, game_id: str, game_name: str, description: str = ""):
        self.game_id = game_id
        self.game_name = game_name
        self.description = description
        self.is_active: bool = False

    def on_enter(self, kernel) -> None:
        """Called immediately upon entering Game Mode with this profile active."""
        self.is_active = True

    def on_exit(self, kernel) -> None:
        """Called immediately upon exiting Game Mode. Releases held keys/buttons."""
        self.is_active = False

    @abstractmethod
    def process_frame(
        self,
        right_hand: Optional[HandLandmarks],
        left_hand: Optional[HandLandmarks],
        kernel,
        timestamp: float
    ) -> Dict[str, Any]:
        """
        Processes spatial frame and sends low-latency inputs to the game.
        Returns a telemetry dictionary describing executed actions.
        """
        pass
