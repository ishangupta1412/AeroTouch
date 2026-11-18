"""
AeroTouch Cortex Subsystem
Background Qwen-powered gesture precision self-tuner.
Analyzes session telemetry and auto-adjusts parameters over time.
No text commands. No Jarvis. Pure precision coaching.
"""

from src.cortex.session_analyst import SessionAnalyst

__all__ = ["SessionAnalyst"]
