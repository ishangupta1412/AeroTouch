"""
AeroTouch Session Analyst (Background Self-Tuner)
Reads session telemetry after each AeroTouch run, sends aggregated stats to Qwen,
receives parameter adjustment recommendations, and writes updated params to user_profile.json.
This is the ONLY Qwen integration — no text commands, no Jarvis, just precision coaching.
"""

import json
import os
import time
import statistics
from typing import Dict, Any, Optional, List

import requests


OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "aerotouch-qwen"
FALLBACK_MODEL = "qwen2.5:3b"

# System prompt: Qwen acts as a gesture precision tuning coach
ANALYST_SYSTEM_PROMPT = (
    "You are AeroTouch Precision Coach, a background parameter tuning engine. "
    "You receive gesture telemetry data from a hand-tracking spatial OS controller. "
    "Your ONLY job is to analyze the data and return a JSON object with recommended "
    "parameter adjustments to improve cursor precision, reduce false clicks, and "
    "adapt to this specific user's hand geometry.\n\n"
    "Return ONLY valid JSON with this schema (omit fields that don't need changes):\n"
    "{\n"
    '  "pinch_threshold": float (0.15-0.40),\n'
    '  "release_threshold": float (0.30-0.50),\n'
    '  "debounce_seconds": float (0.10-0.40),\n'
    '  "confirm_frames": int (1-4),\n'
    '  "deadband": float (0.001-0.008),\n'
    '  "min_cutoff": float (0.02-0.15),\n'
    '  "beta": float (0.005-0.05),\n'
    '  "reasoning": "Brief explanation of why these changes help"\n'
    "}\n\n"
    "Rules:\n"
    "- If click count is suspiciously high for a short session, raise thresholds.\n"
    "- If pinch distances cluster near the threshold boundary, widen the hysteresis gap.\n"
    "- If cursor moves very little but many frames are logged, the deadband may be too small.\n"
    "- Never make drastic changes. Incremental adjustments of 5-15% only.\n"
    "- If data looks clean, return: {\"reasoning\": \"No changes needed. Precision is nominal.\"}"
)


class SessionAnalyst:
    """Qwen-powered background self-tuner for gesture precision parameters."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        self.base_dir = base_dir
        self.profile_path = os.path.join(base_dir, "data", "user_profile.json")
        self.sessions_dir = os.path.join(base_dir, "data", "sessions")

    def _resolve_model(self) -> str:
        """Check which Qwen model is available on local Ollama."""
        try:
            resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            if resp.status_code == 200:
                names = [m["name"] for m in resp.json().get("models", [])]
                for model in [DEFAULT_MODEL, f"{DEFAULT_MODEL}:latest", FALLBACK_MODEL]:
                    if model in names:
                        return model.split(":")[0] if ":" not in model else model
        except Exception:
            pass
        return FALLBACK_MODEL

    def load_user_profile(self) -> Dict[str, Any]:
        """Loads the current user profile (learned thresholds) or returns defaults."""
        defaults = {
            "pinch_threshold": 0.28,
            "release_threshold": 0.38,
            "debounce_seconds": 0.20,
            "confirm_frames": 2,
            "deadband": 0.0025,
            "min_cutoff": 0.05,
            "beta": 0.015,
            "sessions_analyzed": 0,
            "last_updated": None
        }

        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    defaults.update(saved)
            except (json.JSONDecodeError, IOError):
                pass

        return defaults

    def save_user_profile(self, profile: Dict[str, Any]):
        """Persists updated profile to disk."""
        profile["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

    def _aggregate_session(self, session_file: str) -> Optional[Dict[str, Any]]:
        """Reads a session JSONL file and computes aggregate statistics."""
        pinch_dists: List[float] = []
        mid_pinch_dists: List[float] = []
        click_count = 0
        right_click_count = 0
        frame_count = 0
        duration = 0.0

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)

                    if entry.get("type") == "SESSION_SUMMARY":
                        duration = entry.get("duration_seconds", 0)
                        continue

                    frame_count += 1
                    pd = entry.get("pinch_dist", -1)
                    mpd = entry.get("mid_pinch_dist", -1)
                    if pd >= 0:
                        pinch_dists.append(pd)
                    if mpd >= 0:
                        mid_pinch_dists.append(mpd)

                    action = entry.get("action", "")
                    if "LEFT_CLICK" in action:
                        click_count += 1
                    elif "RIGHT_CLICK" in action:
                        right_click_count += 1

        except Exception:
            return None

        if frame_count < 30:
            return None  # Too short to analyze

        stats = {
            "session_file": os.path.basename(session_file),
            "total_frames": frame_count,
            "duration_seconds": duration,
            "left_clicks": click_count,
            "right_clicks": right_click_count,
            "clicks_per_minute": round(click_count / max(duration / 60, 0.01), 2),
        }

        if pinch_dists:
            stats["pinch_dist_mean"] = round(statistics.mean(pinch_dists), 4)
            stats["pinch_dist_std"] = round(statistics.stdev(pinch_dists) if len(pinch_dists) > 1 else 0, 4)
            stats["pinch_dist_min"] = round(min(pinch_dists), 4)
            stats["pinch_dist_p10"] = round(sorted(pinch_dists)[len(pinch_dists) // 10], 4)

        if mid_pinch_dists:
            stats["mid_pinch_dist_mean"] = round(statistics.mean(mid_pinch_dists), 4)

        return stats

    def analyze_latest_session(self) -> Dict[str, Any]:
        """Analyzes the most recent session and auto-adjusts parameters via Qwen."""
        if not os.path.exists(self.sessions_dir):
            return {"status": "skip", "reason": "No sessions directory found."}

        session_files = sorted(
            [
                os.path.join(self.sessions_dir, f)
                for f in os.listdir(self.sessions_dir)
                if f.startswith("session_")
                and f.endswith(".jsonl")
                and os.path.getsize(os.path.join(self.sessions_dir, f)) > 50
            ],
            key=os.path.getmtime
        )

        if not session_files:
            return {"status": "skip", "reason": "No session telemetry files found."}

        latest = session_files[-1]
        stats = self._aggregate_session(latest)

        if stats is None:
            return {"status": "skip", "reason": "Session too short or corrupt."}

        # Load current profile
        profile = self.load_user_profile()

        # Build prompt for Qwen
        prompt = (
            f"Session telemetry:\n{json.dumps(stats, indent=2)}\n\n"
            f"Current parameters:\n{json.dumps({k: v for k, v in profile.items() if k not in ('sessions_analyzed', 'last_updated')}, indent=2)}\n\n"
            f"Analyze and return parameter adjustment JSON."
        )

        # Call Qwen
        try:
            model = self._resolve_model()
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=120
            )

            data = resp.json()
            content = data.get("message", {}).get("content", "")

            # Parse JSON from Qwen response
            recommendations = self._extract_json(content)

            if recommendations:
                updated = self._apply_recommendations(profile, recommendations)
                self.save_user_profile(updated)
                return {
                    "status": "tuned",
                    "session": stats,
                    "recommendations": recommendations,
                    "profile_updated": True
                }
            else:
                return {
                    "status": "nominal",
                    "session": stats,
                    "raw_response": content
                }

        except requests.exceptions.ConnectionError:
            return {"status": "offline", "reason": "Ollama not running. Skipping analysis."}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extracts the first valid JSON object from Qwen's response."""
        # Try direct parse
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding raw JSON object
        match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _apply_recommendations(self, profile: Dict[str, Any], recs: Dict[str, Any]) -> Dict[str, Any]:
        """Applies Qwen's recommended parameter changes with safety clamping."""
        bounds = {
            "pinch_threshold": (0.15, 0.40),
            "release_threshold": (0.30, 0.50),
            "debounce_seconds": (0.10, 0.40),
            "confirm_frames": (1, 4),
            "deadband": (0.001, 0.008),
            "min_cutoff": (0.02, 0.15),
            "beta": (0.005, 0.05),
        }

        for key, (lo, hi) in bounds.items():
            if key in recs:
                val = recs[key]
                if isinstance(val, (int, float)):
                    clamped = max(lo, min(hi, val))
                    if key == "confirm_frames":
                        clamped = int(clamped)
                    profile[key] = clamped

        profile["sessions_analyzed"] = profile.get("sessions_analyzed", 0) + 1
        return profile
