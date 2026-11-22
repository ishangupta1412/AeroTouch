"""
AeroTouch Game Profiles Package
Isolated modular game profiles.
"""

from .subway_surfers import SubwaySurfersProfile
from .racing_wheel import RacingWheelProfile
from .temple_run import TempleRunProfile
from .minecraft import MinecraftProfile
from .fruit_ninja import FruitNinjaProfile
from .flappy_bird import FlappyBirdProfile

__all__ = [
    "SubwaySurfersProfile",
    "RacingWheelProfile",
    "TempleRunProfile",
    "MinecraftProfile",
    "FruitNinjaProfile",
    "FlappyBirdProfile",
]
