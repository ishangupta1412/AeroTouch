"""
AeroTouch Ollama Cortex Bridge
Direct REST client to local Ollama runtime (Qwen 2.5) for natural language OS automation.
"""

import json
import requests
from typing import Dict, Any, List, Optional
from src.cortex.tools import CortexOSTools


OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "aerotouch-qwen"
FALLBACK_MODEL = "qwen2.5:3b"

# Tool signatures for Qwen 2.5 tool-calling
CORTEX_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Opens or switches to a desktop application (e.g. spotify, chrome, vscode, notepad, calc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to open."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "snap_window",
            "description": "Snaps the active window to the left or right, maximizes, or minimizes it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["left", "right", "max", "min"],
                        "description": "Layout direction: left, right, max, or min."
                    }
                },
                "required": ["direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "media_control",
            "description": "Controls audio playback and system volume.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["volume_up", "volume_down", "mute", "play", "pause", "next", "prev"],
                        "description": "Media action to execute."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "virtual_desktop",
            "description": "Navigates between Windows 11 virtual desktops.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["next", "prev", "overview"],
                        "description": "Virtual desktop navigation command."
                    }
                },
                "required": ["action"]
            }
        }
    }
]


class OllamaCortexAgent:
    """Intelligent natural language OS agent powered by local Ollama Qwen model."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = DEFAULT_MODEL):
        self.base_url = base_url
        self.preferred_model = model
        self.active_model = self._resolve_active_model()
        self.executor = CortexOSTools()

    def _resolve_active_model(self) -> str:
        """Checks available models in local Ollama and selects best available."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                models = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
                if self.preferred_model in models or f"{self.preferred_model}:latest" in [m["name"] for m in resp.json().get("models", [])]:
                    return self.preferred_model
                elif FALLBACK_MODEL in models or f"{FALLBACK_MODEL}:latest" in [m["name"] for m in resp.json().get("models", [])]:
                    return FALLBACK_MODEL
        except Exception:
            pass
        return FALLBACK_MODEL

    def is_online(self) -> bool:
        """Tests if local Ollama daemon is reachable."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def process_command(self, user_prompt: str) -> Dict[str, Any]:
        """
        Sends user natural language command (Hinglish/English) to Qwen,
        detects tool-calls, executes them directly on Windows, and returns status.
        """
        if not self.is_online():
            return {
                "status": "error",
                "message": "Local Ollama server is offline. Please launch Ollama."
            }

        payload = {
            "model": self.active_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are AeroTouch Cortex, an autonomous spatial AI operating layer for Windows 11. "
                        "You understand English, Hindi, and Hinglish commands. "
                        "When the user asks to control apps, windows, media, or virtual desktops, "
                        "ALWAYS use the provided tools to execute the action."
                    )
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "tools": CORTEX_TOOLS_SCHEMA,
            "stream": False
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60
            )
            data = resp.json()
            message = data.get("message", {})
            tool_calls = message.get("tool_calls", [])

            executed_results = []
            if tool_calls:
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name")
                    fn_args = fn.get("arguments", {})
                    if isinstance(fn_args, str):
                        try:
                            fn_args = json.loads(fn_args)
                        except Exception:
                            fn_args = {}

                    res = self.executor.execute_tool_call(fn_name, fn_args)
                    executed_results.append({
                        "tool": fn_name,
                        "args": fn_args,
                        "result": res
                    })

                self._log_interaction(user_prompt, executed_results, "Executed OS actions")
                return {
                    "status": "success",
                    "executed_tools": executed_results,
                    "response": f"Executed {len(executed_results)} OS action(s)."
                }
            else:
                content = message.get("content", "Command acknowledged.")
                self._log_interaction(user_prompt, [], content)
                return {
                    "status": "success",
                    "executed_tools": [],
                    "response": content
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ollama execution error: {e}"
            }

    def _log_interaction(self, prompt: str, tool_results: List[Dict], response: str):
        """Persists every user command into local telemetry history for ongoing fine-tuning."""
        try:
            import os
            import time
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_dir = os.path.join(base_dir, "data")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "interaction_history.jsonl")

            entry = {
                "timestamp": time.time(),
                "user_prompt": prompt,
                "model": self.active_model,
                "tool_results": tool_results,
                "response": response
            }
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass
