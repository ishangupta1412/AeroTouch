"""
AeroTouch Rolling Vision Intelligence Pipeline
===============================================
Architecture:
  Every 4 seconds → mss screenshot (5MB)
      ↓
  Moondream 2 inference (~300ms) → context JSON (1KB)
      ↓ DELETE screenshot immediately
  Buffer accumulates up to BATCH_SIZE (10) context JSONs
      ↓ when full
  Qwen batch analysis → parameter recommendations
      ↓ DELETE all context JSONs
  user_profile.json updated + live orchestrator notified
  Few-shot memory written → next batch gets smarter
  Buffer resets → repeat

Memory guarantee:
  Peak: 1 screenshot at a time (5MB) + model VRAM
  After delete: ~10KB JSON buffer max, then 0 after flush
"""

import json
import logging
import os
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional

# Guarantee project root is in sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logger = logging.getLogger("aerotouch.vision_analyst")

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
SCREENSHOT_INTERVAL_SECONDS = 4.0   # How often to grab a frame
BATCH_SIZE = 10                      # Flush to Qwen every N context JSONs
MEMORY_FILE = os.path.join(_ROOT, "data", "vision_memory.jsonl")  # Few-shot store
MEMORY_MAX_EXAMPLES = 20             # Keep last N successful (context, params) pairs
TEMP_SCREENSHOT_DIR = os.path.join(_ROOT, "data", ".vision_tmp")   # Always cleaned up


# ─────────────────────────────────────────────
# Moondream Wrapper
# ─────────────────────────────────────────────

class MoondreamWrapper:
    """
    Wraps Moondream 2 (1.8B, ~900MB 4-bit) for lightweight screen understanding.
    Loads once, stays resident. Processes one frame at a time.
    """

    QUESTIONS = [
        "What type of application or software is shown on this screen?",
        "Are the user interface buttons and controls large or small and dense?",
        "What is the user most likely doing? (e.g. coding, browsing, video editing, writing)",
        "Does this screen require fine precise cursor control or coarse navigation?",
    ]

    def __init__(self):
        self._model = None
        self._loaded = False
        self._load_error: Optional[str] = None

    def _lazy_load(self) -> bool:
        """Load Moondream on first use. Returns True if successful."""
        if self._loaded:
            return True
        if self._load_error:
            return False

        api_key = os.environ.get("MOONDREAM_API_KEY")
        if not api_key:
            # Avoid HTTP 401 Unauthorized spam if user hasn't set an API key
            self._load_error = "MOONDREAM_API_KEY not configured"
            logger.info("[VisionAnalyst]: MOONDREAM_API_KEY not set. Using native Win32 window context engine (zero-overhead offline mode).")
            return False

        try:
            import moondream as md  # type: ignore
            self._model = md.vl(api_key=api_key, model="moondream-2B-int8")
            self._loaded = True
            logger.info("[VisionAnalyst]: Moondream 2 cloud vision engine loaded successfully.")
            return True
        except ImportError:
            self._load_error = "moondream package not installed (pip install moondream)"
            logger.warning(f"[VisionAnalyst]: {self._load_error}")
            return False
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"[VisionAnalyst]: Moondream initialization failed: {e}")
            return False

    def analyze_screenshot(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Runs Moondream VQA on a screenshot file.
        Returns a structured context dict. Screenshot is NOT deleted here —
        caller must delete it after this returns.
        """
        if not self._lazy_load():
            return self._fallback_context(image_path)

        try:
            from PIL import Image  # type: ignore
            img = Image.open(image_path).convert("RGB")
            # Resize to 512px wide for speed (Moondream works well at this res)
            w, h = img.size
            if w > 512:
                scale = 512 / w
                img = img.resize((512, int(h * scale)), Image.LANCZOS)

            encoded = self._model.encode_image(img)

            answers = {}
            for q in self.QUESTIONS:
                ans = self._model.query(encoded, q)["answer"].strip()
                answers[q[:40]] = ans  # Truncate key for compact JSON

            context = self._parse_answers(answers)
            context["timestamp"] = time.time()
            context["raw"] = answers
            return context

        except Exception as e:
            logger.warning(f"[VisionAnalyst]: Moondream inference failed: {e}")
            return self._fallback_context(image_path)

    def _parse_answers(self, answers: Dict[str, str]) -> Dict[str, Any]:
        """Heuristic mapping of Moondream answers to structured context tags."""
        import re
        vals = " ".join(answers.values()).lower()

        def has_word(word: str) -> bool:
            """True if `word` appears as a whole token (word boundary match)."""
            return bool(re.search(r'\b' + re.escape(word) + r'\b', vals))

        def has_any(*words) -> bool:
            return any(has_word(w) for w in words)

        # App category — evaluated from most specific to most general
        app_type = "general"
        if has_any("vscode", "pycharm", "visual studio", "code editor") or (
            has_word("code") and not has_word("video")
        ) or has_word("editor") or has_word("ide"):
            # Guard: "ide" inside "video" is a known false-positive; skip if video wins
            if not has_any("video", "youtube", "player", "premiere", "davinci"):
                app_type = "code_editor"
        if app_type == "general" and has_any("photoshop", "illustrator", "figma", "gimp", "affinity", "image edit"):
            app_type = "image_editor"
        if app_type == "general" and has_any("browser", "chrome", "firefox", "edge", "safari", "web"):
            app_type = "web_browser"
        if app_type == "general" and has_any("video", "premiere", "davinci", "resolve", "youtube", "vlc", "player"):
            app_type = "video"
        if app_type == "general" and has_any("word", "document", "writer", "note", "writing"):
            app_type = "document"
        if app_type == "general" and has_any("game", "gaming", "play"):
            app_type = "game"
        if app_type == "general" and has_any("spreadsheet", "excel", "sheets", "calc"):
            app_type = "spreadsheet"
        # Re-evaluate code_editor now that video guard has been applied
        if app_type == "general" and has_any("vscode", "pycharm", "visual studio", "code editor", "editor", "ide"):
            app_type = "code_editor"

        # UI density
        ui_density = "medium"
        if any(w in vals for w in ["small", "dense", "compact", "tiny", "crowded", "many"]):
            ui_density = "high"
        elif any(w in vals for w in ["large", "spacious", "big", "wide", "minimal", "few"]):
            ui_density = "low"

        # Precision demand mapping
        precision_map = {
            "code_editor": "high",
            "image_editor": "high",
            "spreadsheet": "high",
            "web_browser": "medium",
            "document": "medium",
            "video": "low",
            "game": "low",
            "general": "medium",
        }
        precision_demand = precision_map.get(app_type, "medium")

        # Override: if UI is dense, always bump precision up
        if ui_density == "high" and precision_demand == "low":
            precision_demand = "medium"

        return {
            "app_type": app_type,
            "ui_density": ui_density,
            "precision_demand": precision_demand,
        }

    def _fallback_context(self, image_path: str) -> Dict[str, Any]:
        """Returns a neutral context when Moondream is unavailable (Win32 fallback)."""
        app_name = _get_foreground_window_title()
        app_type = "general"
        if any(w in app_name.lower() for w in ["code", "pycharm", "studio", "vim"]):
            app_type = "code_editor"
        elif any(w in app_name.lower() for w in ["chrome", "firefox", "edge", "browser"]):
            app_type = "web_browser"
        elif any(w in app_name.lower() for w in ["photoshop", "gimp", "figma"]):
            app_type = "image_editor"
        return {
            "app_type": app_type,
            "ui_density": "medium",
            "precision_demand": "medium",
            "timestamp": time.time(),
            "source": "win32_title_fallback",
            "window_title": app_name,
        }


# ─────────────────────────────────────────────
# Win32 Helper
# ─────────────────────────────────────────────

def _get_foreground_window_title() -> str:
    """Returns the title of the currently active window (zero-cost Win32 call)."""
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(512)
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
        return buf.value or "Unknown"
    except Exception:
        return "Unknown"


# ─────────────────────────────────────────────
# Screenshot Helper
# ─────────────────────────────────────────────

def _take_screenshot(output_dir: str) -> Optional[str]:
    """
    Captures the primary monitor screenshot using mss (fastest Python screenshotter, <5ms).
    Falls back to PIL ImageGrab if mss is unavailable.
    Returns absolute path to saved PNG file.
    """
    os.makedirs(output_dir, exist_ok=True)
    fname = os.path.join(output_dir, f"frame_{int(time.time()*1000)}.png")

    try:
        import mss  # type: ignore
        import mss.tools
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            img = sct.grab(monitor)
            mss.tools.to_png(img.rgb, img.size, output=fname)
        return fname
    except ImportError:
        pass

    try:
        from PIL import ImageGrab
        shot = ImageGrab.grab()
        shot.save(fname, "PNG")
        return fname
    except Exception as e:
        logger.warning(f"[VisionAnalyst]: Screenshot failed: {e}")
        return None


# ─────────────────────────────────────────────
# Few-Shot Memory
# ─────────────────────────────────────────────

class VisionMemory:
    """
    Stores (batch_summary, recommended_params) pairs as few-shot examples.
    Each Qwen call gets the last N successful examples to improve over time.
    Tiny footprint: ~2KB per batch entry, capped at MEMORY_MAX_EXAMPLES.
    """

    def __init__(self, path: str = MEMORY_FILE):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def append(self, batch_summary: Dict, recommendations: Dict) -> None:
        """Saves a successful (context, recommendations) pair."""
        entry = {
            "timestamp": time.time(),
            "batch_summary": batch_summary,
            "recommendations": recommendations,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        self._trim()

    def get_examples(self, n: int = 5) -> List[Dict]:
        """Returns the last N successful examples for few-shot prompting."""
        if not os.path.exists(self.path):
            return []
        examples = []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            examples.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception:
            pass
        return examples[-n:]

    def _trim(self) -> None:
        """Keep only the last MEMORY_MAX_EXAMPLES entries."""
        examples = self.get_examples(n=10000)
        if len(examples) > MEMORY_MAX_EXAMPLES:
            keep = examples[-MEMORY_MAX_EXAMPLES:]
            with open(self.path, "w", encoding="utf-8") as f:
                for ex in keep:
                    f.write(json.dumps(ex) + "\n")


# ─────────────────────────────────────────────
# Core Rolling Vision Analyst
# ─────────────────────────────────────────────

class RollingVisionAnalyst:
    """
    Rolling micro-batch vision intelligence daemon.

    Lifecycle:
      start() → background thread captures + analyzes screenshots continuously
      Every BATCH_SIZE contexts → flush_to_qwen() → params updated + JSONs deleted
      stop() → gracefully drains buffer and exits

    Callbacks:
      on_params_updated(recommendations: Dict) → called in background thread
        when Qwen produces new parameter recommendations. Wire to
        SpatialOrchestrator.apply_context_profile() for live updates.
    """

    def __init__(
        self,
        on_params_updated: Optional[Callable[[Dict[str, Any]], None]] = None,
        screenshot_interval: float = SCREENSHOT_INTERVAL_SECONDS,
        batch_size: int = BATCH_SIZE,
    ):
        self.moondream = MoondreamWrapper()
        self.memory = VisionMemory()
        self.on_params_updated = on_params_updated
        self.screenshot_interval = screenshot_interval
        self.batch_size = batch_size

        self._buffer: List[Dict[str, Any]] = []
        self._buffer_lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._batches_processed = 0

    def start(self) -> None:
        """Starts the background rolling vision daemon."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="AeroTouchVisionDaemon"
        )
        self._thread.start()
        logger.info("[VisionAnalyst]: Rolling Vision Intelligence daemon started.")

    def stop(self) -> None:
        """Signals the daemon to stop and waits for clean shutdown."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10.0)
        self._cleanup_tmp()
        logger.info("[VisionAnalyst]: Vision daemon stopped cleanly.")

    def _loop(self) -> None:
        """Main background loop: capture → analyze → buffer → flush."""
        while self._running:
            loop_start = time.time()

            screenshot_path = None
            try:
                # Step 1: Capture screenshot
                screenshot_path = _take_screenshot(TEMP_SCREENSHOT_DIR)
                if not screenshot_path:
                    time.sleep(self.screenshot_interval)
                    continue

                # Step 2: Moondream inference (~200–400ms)
                context = self.moondream.analyze_screenshot(screenshot_path)

                # Step 3: DELETE screenshot immediately (5MB freed)
                try:
                    os.remove(screenshot_path)
                    screenshot_path = None
                except OSError:
                    pass

                if context is None:
                    continue

                # Step 4: Add to buffer
                with self._buffer_lock:
                    self._buffer.append(context)
                    buffer_len = len(self._buffer)

                logger.debug(
                    f"[VisionAnalyst]: Context captured [{buffer_len}/{self.batch_size}] "
                    f"| App: {context.get('app_type', '?')} "
                    f"| Precision: {context.get('precision_demand', '?')}"
                )

                # Step 5: Flush when batch is full
                if buffer_len >= self.batch_size:
                    self._flush_batch()

            except Exception as e:
                logger.warning(f"[VisionAnalyst]: Loop error: {e}")
            finally:
                # Always clean up screenshot if still present
                if screenshot_path and os.path.exists(screenshot_path):
                    try:
                        os.remove(screenshot_path)
                    except OSError:
                        pass

            # Throttle to interval
            elapsed = time.time() - loop_start
            sleep_time = max(0.0, self.screenshot_interval - elapsed)
            time.sleep(sleep_time)

    def _flush_batch(self) -> None:
        """
        Takes the current buffer (BATCH_SIZE context JSONs),
        sends to Qwen for analysis, applies recommendations, then clears buffer.
        Memory freed: BATCH_SIZE * ~1KB of JSON.
        """
        with self._buffer_lock:
            batch = self._buffer.copy()
            self._buffer.clear()   # Free buffer memory immediately

        if not batch:
            return

        try:
            batch_summary = self._summarize_batch(batch)
            examples = self.memory.get_examples(n=5)
            recommendations = self._call_qwen(batch_summary, examples)

            if recommendations:
                self._batches_processed += 1
                self.memory.append(batch_summary, recommendations)

                if self.on_params_updated:
                    try:
                        self.on_params_updated(recommendations)
                    except Exception as e:
                        logger.warning(f"[VisionAnalyst]: Callback error: {e}")

                logger.info(
                    f"[VisionAnalyst]: Batch {self._batches_processed} flushed. "
                    f"Dominant: {batch_summary['dominant_app']} | "
                    f"Precision: {batch_summary['dominant_precision']} | "
                    f"Params updated: {list(recommendations.keys())}"
                )
            else:
                logger.info("[VisionAnalyst]: Batch analyzed — no parameter changes needed.")

        except Exception as e:
            logger.warning(f"[VisionAnalyst]: Batch flush error: {e}")

    def _summarize_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarizes 10 context JSONs into a single compact summary for Qwen.
        Prevents Qwen from getting 10KB of raw context data.
        """
        from collections import Counter

        app_types = [c.get("app_type", "general") for c in batch]
        precisions = [c.get("precision_demand", "medium") for c in batch]
        densities = [c.get("ui_density", "medium") for c in batch]

        app_counter = Counter(app_types)
        dominant_app = app_counter.most_common(1)[0][0]
        dominant_precision = Counter(precisions).most_common(1)[0][0]
        dominant_density = Counter(densities).most_common(1)[0][0]

        # Time span of the batch
        timestamps = [c.get("timestamp", 0) for c in batch if c.get("timestamp")]
        duration_seconds = (max(timestamps) - min(timestamps)) if len(timestamps) >= 2 else 0

        return {
            "batch_size": len(batch),
            "duration_seconds": round(duration_seconds, 1),
            "dominant_app": dominant_app,
            "app_distribution": dict(app_counter),
            "dominant_precision": dominant_precision,
            "dominant_density": dominant_density,
            "precision_distribution": dict(Counter(precisions)),
        }

    def _call_qwen(
        self,
        batch_summary: Dict[str, Any],
        examples: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """
        Sends batch summary + few-shot examples to Qwen via Ollama.
        Returns recommended parameter adjustments or None.
        """
        import requests

        OLLAMA_URL = "http://localhost:11434"
        SYSTEM_PROMPT = (
            "You are AeroTouch Visual Precision Coach. "
            "You receive a summary of what the user has been doing on-screen (detected by a vision model). "
            "Your ONLY job: return a JSON object with parameter adjustments that optimize "
            "hand-tracking cursor precision for the detected usage context.\n\n"
            "Precision demand guide:\n"
            "  high (code editor, Photoshop, spreadsheet): lower ballistics gain, tighter deadband\n"
            "  medium (browser, documents): balanced defaults\n"
            "  low (video player, games): faster ballistics, relaxed deadband\n\n"
            "Available parameters you can adjust:\n"
            "  ballistics_precision_gain: float 0.3-0.8 (lower = more precise, slower)\n"
            "  ballistics_max_multiplier: float 1.5-2.5 (higher = faster sweeps)\n"
            "  deadband: float 0.001-0.008 (higher = more stillness, less jitter)\n"
            "  scroll_sensitivity: float 8.0-25.0 (higher = faster scroll)\n"
            "  reasoning: string explaining your choices\n\n"
            "Rules:\n"
            "- If dominant_precision is 'high': set precision_gain 0.35-0.45, deadband 0.003-0.005\n"
            "- If dominant_precision is 'low': set precision_gain 0.55-0.75, deadband 0.001-0.003\n"
            "- If video context: raise scroll_sensitivity to 18-22\n"
            "- Never make drastic changes. 10-20% shifts only.\n"
            "- If context is unclear or mixed, return: {\"reasoning\": \"Mixed context. No changes.\"}\n"
            "Return ONLY valid JSON."
        )

        # Build few-shot context from memory
        few_shot_text = ""
        if examples:
            few_shot_text = "\n\nPrevious successful adaptations (learn from these):\n"
            for ex in examples[-3:]:
                few_shot_text += (
                    f"  Context: {json.dumps(ex.get('batch_summary', {}))}\n"
                    f"  Params applied: {json.dumps(ex.get('recommendations', {}))}\n"
                )

        prompt = (
            f"Screen context batch summary:\n{json.dumps(batch_summary, indent=2)}"
            f"{few_shot_text}\n\n"
            f"Analyze and return parameter adjustment JSON."
        )

        try:
            # Resolve model
            resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
            model = "qwen2.5:3b"
            if resp.status_code == 200:
                names = [m["name"] for m in resp.json().get("models", [])]
                for candidate in ["aerotouch-qwen", "aerotouch-qwen:latest", "qwen2.5:3b"]:
                    if candidate in names:
                        model = candidate
                        break

            resp = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
                timeout=90,
            )

            content = resp.json().get("message", {}).get("content", "")
            return self._parse_qwen_json(content)

        except requests.exceptions.ConnectionError:
            logger.info("[VisionAnalyst]: Ollama offline — skipping Qwen analysis.")
            return None
        except Exception as e:
            logger.warning(f"[VisionAnalyst]: Qwen call failed: {e}")
            return None

    def _parse_qwen_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extracts JSON from Qwen response robustly."""
        import re
        # Try direct JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        # Try markdown code block
        m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        # Try raw JSON object
        m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return None

    def _cleanup_tmp(self) -> None:
        """Removes all leftover temporary screenshots on shutdown."""
        if not os.path.exists(TEMP_SCREENSHOT_DIR):
            return
        for fname in os.listdir(TEMP_SCREENSHOT_DIR):
            if fname.endswith(".png"):
                try:
                    os.remove(os.path.join(TEMP_SCREENSHOT_DIR, fname))
                except OSError:
                    pass

    @property
    def status(self) -> Dict[str, Any]:
        """Returns current daemon status."""
        with self._buffer_lock:
            buf_len = len(self._buffer)
        return {
            "running": self._running,
            "buffer_fill": f"{buf_len}/{self.batch_size}",
            "batches_processed": self._batches_processed,
            "moondream_loaded": self.moondream._loaded,
        }
