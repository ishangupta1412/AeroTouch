"""
AeroTouch Cortex Subsystem
Natural Language AI Copilot powered by local Ollama models (Qwen 2.5).
"""

from src.cortex.ollama_bridge import OllamaCortexAgent
from src.cortex.tools import CortexOSTools

__all__ = ["OllamaCortexAgent", "CortexOSTools"]
