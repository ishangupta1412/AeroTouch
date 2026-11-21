"""
AeroTouch Gaming Engine
Provides a completely isolated spatial gaming execution layer:
- Dual-hand Fist Bump (🤜🤛) gesture trigger with dwell confirmation & cooldown
- Pluggable game profile registry
- Dedicated game input mapping and low-latency dispatch
"""

from .engine import GameEngine
from .base_profile import BaseGameProfile
from .trigger import FistBumpTrigger
from .profiles.subway_surfers import SubwaySurfersProfile

__all__ = ["GameEngine", "BaseGameProfile", "FistBumpTrigger", "SubwaySurfersProfile"]
