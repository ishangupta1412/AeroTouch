"""
AeroTouch Cortex Fine-Tuning Dataset Generator
Builds domain-specific instruction-tuning datasets for training local LLMs (Qwen 2.5)
on English, Hindi, and Hinglish spatial and operating system automation.
"""

import os
import json
from typing import List, Dict, Any


DATASET_PAIRS = [
    # Application Launches (English, Hindi, Hinglish)
    {"prompt": "open spotify", "tool": "open_application", "args": {"app_name": "spotify"}},
    {"prompt": "spotify chala do", "tool": "open_application", "args": {"app_name": "spotify"}},
    {"prompt": "bhai gaane sunne hain spotify kholo", "tool": "open_application", "args": {"app_name": "spotify"}},
    {"prompt": "open chrome browser", "tool": "open_application", "args": {"app_name": "chrome"}},
    {"prompt": "chrome khol do", "tool": "open_application", "args": {"app_name": "chrome"}},
    {"prompt": "internet chalana hai chrome open karo", "tool": "open_application", "args": {"app_name": "chrome"}},
    {"prompt": "launch visual studio code", "tool": "open_application", "args": {"app_name": "vscode"}},
    {"prompt": "code kholo", "tool": "open_application", "args": {"app_name": "vscode"}},
    {"prompt": "vs code open karo coding karni hai", "tool": "open_application", "args": {"app_name": "vscode"}},
    {"prompt": "open notepad", "tool": "open_application", "args": {"app_name": "notepad"}},
    {"prompt": "kuch likhna hai notepad kholo", "tool": "open_application", "args": {"app_name": "notepad"}},
    {"prompt": "calculator chalao", "tool": "open_application", "args": {"app_name": "calculator"}},
    {"prompt": "open calc", "tool": "open_application", "args": {"app_name": "calculator"}},
    {"prompt": "open terminal", "tool": "open_application", "args": {"app_name": "terminal"}},
    {"prompt": "command prompt open karo", "tool": "open_application", "args": {"app_name": "cmd"}},
    {"prompt": "open file explorer", "tool": "open_application", "args": {"app_name": "explorer"}},
    {"prompt": "my computer files open karo", "tool": "open_application", "args": {"app_name": "explorer"}},

    # Window Management & Snapping
    {"prompt": "snap window to left", "tool": "snap_window", "args": {"direction": "left"}},
    {"prompt": "is window ko left side me kardo", "tool": "snap_window", "args": {"direction": "left"}},
    {"prompt": "left split screen karo", "tool": "snap_window", "args": {"direction": "left"}},
    {"prompt": "snap to right side", "tool": "snap_window", "args": {"direction": "right"}},
    {"prompt": "is window ko right me chipka do", "tool": "snap_window", "args": {"direction": "right"}},
    {"prompt": "right side snap kardo", "tool": "snap_window", "args": {"direction": "right"}},
    {"prompt": "maximize window", "tool": "snap_window", "args": {"direction": "max"}},
    {"prompt": "poori screen badi kardo", "tool": "snap_window", "args": {"direction": "max"}},
    {"prompt": "full screen kardo", "tool": "snap_window", "args": {"direction": "max"}},
    {"prompt": "minimize current window", "tool": "snap_window", "args": {"direction": "min"}},
    {"prompt": "window neeche chupao minimize karo", "tool": "snap_window", "args": {"direction": "min"}},

    # Media & Audio Controls
    {"prompt": "increase volume", "tool": "media_control", "args": {"action": "volume_up"}},
    {"prompt": "awaaz badhao", "tool": "media_control", "args": {"action": "volume_up"}},
    {"prompt": "volume thoda up kardo", "tool": "media_control", "args": {"action": "volume_up"}},
    {"prompt": "volume kam karo", "tool": "media_control", "args": {"action": "volume_down"}},
    {"prompt": "decrease volume", "tool": "media_control", "args": {"action": "volume_down"}},
    {"prompt": "awaaz dheemi kardo thodi", "tool": "media_control", "args": {"action": "volume_down"}},
    {"prompt": "mute audio", "tool": "media_control", "args": {"action": "mute"}},
    {"prompt": "awaaz band karo mute", "tool": "media_control", "args": {"action": "mute"}},
    {"prompt": "pause music", "tool": "media_control", "args": {"action": "pause"}},
    {"prompt": "gaana roko", "tool": "media_control", "args": {"action": "pause"}},
    {"prompt": "play music", "tool": "media_control", "args": {"action": "play"}},
    {"prompt": "gaana chalao wapas", "tool": "media_control", "args": {"action": "play"}},
    {"prompt": "next song", "tool": "media_control", "args": {"action": "next"}},
    {"prompt": "agla gaana lagao", "tool": "media_control", "args": {"action": "next"}},
    {"prompt": "previous song", "tool": "media_control", "args": {"action": "prev"}},
    {"prompt": "pehle wala gaana bajao", "tool": "media_control", "args": {"action": "prev"}},

    # Virtual Desktops
    {"prompt": "switch to next desktop", "tool": "virtual_desktop", "args": {"action": "next"}},
    {"prompt": "agla desktop open karo", "tool": "virtual_desktop", "args": {"action": "next"}},
    {"prompt": "switch to previous desktop", "tool": "virtual_desktop", "args": {"action": "prev"}},
    {"prompt": "peeche wala desktop lao", "tool": "virtual_desktop", "args": {"action": "prev"}},
    {"prompt": "show all desktops", "tool": "virtual_desktop", "args": {"action": "overview"}},
    {"prompt": "task view kholo saare desktop dekhne hain", "tool": "virtual_desktop", "args": {"action": "overview"}}
]


def generate_jsonl_dataset(output_path: str) -> int:
    """Generates standard OpenAI / ChatML formatted JSONL file for fine-tuning."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    count = 0

    with open(output_path, "w", encoding="utf-8") as f:
        for item in DATASET_PAIRS:
            entry = {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are AeroTouch Cortex, an autonomous AI operating layer for Windows 11. "
                            "Execute desktop actions using available tools."
                        )
                    },
                    {
                        "role": "user",
                        "content": item["prompt"]
                    },
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "type": "function",
                                "function": {
                                    "name": item["tool"],
                                    "arguments": json.dumps(item["args"])
                                }
                            }
                        ]
                    }
                ]
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            count += 1

    return count


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_file = os.path.join(base_dir, "data", "fine_tune_dataset.jsonl")
    total = generate_jsonl_dataset(out_file)
    print(f"[Dataset Generator]: Successfully generated {total} instruction-tuning pairs at: {out_file}")
