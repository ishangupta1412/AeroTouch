"""
AeroTouch Multimodal Voice + Spatial Intent Engine
Bridges speech recognition with spatial OS interaction:
  - "copy"       -> Ctrl + C
  - "paste"      -> Ctrl + V
  - "undo"       -> Ctrl + Z
  - "close"      -> Alt + F4
  - "maximize"   -> Win + Up
  - "minimize"   -> Win + Down
  - "screenshot" -> Win + Shift + S
  - "laser"      -> Toggles AirCanvas presentation laser pointer
  - "draw"       -> Toggles AirCanvas spatial inking
  - "clear"      -> Clears desktop drawing overlay
  - "pause"      -> Pauses spatial tracking
  - "resume"     -> Resumes spatial tracking
"""

import logging
import threading
import time
from typing import Callable, Dict, Optional

logger = logging.getLogger("AeroTouch.VoiceIntent")

# Canonical action mappings
VOICE_INTENTS: Dict[str, str] = {
    "copy": "VOICE_COPY",
    "paste": "VOICE_PASTE",
    "undo": "VOICE_UNDO",
    "close": "VOICE_CLOSE_WINDOW",
    "close window": "VOICE_CLOSE_WINDOW",
    "maximize": "VOICE_MAXIMIZE",
    "minimize": "VOICE_MINIMIZE",
    "task view": "VOICE_TASK_VIEW",
    "screenshot": "VOICE_SCREENSHOT",
    "snip": "VOICE_SCREENSHOT",
    "laser": "VOICE_TOGGLE_LASER",
    "pointer": "VOICE_TOGGLE_LASER",
    "draw": "VOICE_TOGGLE_DRAW",
    "canvas": "VOICE_TOGGLE_DRAW",
    "clear": "VOICE_CLEAR_CANVAS",
    "pause": "VOICE_PAUSE",
    "resume": "VOICE_RESUME",
    "game mode": "VOICE_TOGGLE_GAME_MODE",
    "gaming": "VOICE_TOGGLE_GAME_MODE",
    "subway surfers": "VOICE_SELECT_SUBWAY_SURFERS",
    "subway surfer": "VOICE_SELECT_SUBWAY_SURFERS",
    "racing": "VOICE_SELECT_RACING",
    "hill climb": "VOICE_SELECT_RACING",
    "car game": "VOICE_SELECT_RACING",
    "temple run": "VOICE_SELECT_TEMPLE_RUN",
    "tomb runner": "VOICE_SELECT_TEMPLE_RUN",
    "minecraft": "VOICE_SELECT_MINECRAFT",
    "sandbox": "VOICE_SELECT_MINECRAFT",
    "fruit ninja": "VOICE_SELECT_FRUIT_NINJA",
    "slice": "VOICE_SELECT_FRUIT_NINJA",
    "flappy bird": "VOICE_SELECT_FLAPPY_BIRD",
    "flappy": "VOICE_SELECT_FLAPPY_BIRD",
    "next game": "VOICE_NEXT_GAME",
}


class VoiceIntentService:
    """
    Asynchronous microphone listener for hands-free multimodal voice commands.
    """

    def __init__(self, on_intent: Optional[Callable[[str], None]] = None):
        self.on_intent = on_intent
        self.running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._recognizer = None
        self._microphone = None
        self._has_sr: bool = False

        self.last_recognized: Optional[str] = None
        self.last_intent: Optional[str] = None

        self._init_engine()

    def _init_engine(self):
        try:
            import speech_recognition as sr  # type: ignore
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 280
            self._recognizer.dynamic_energy_threshold = True
            self._microphone = sr.Microphone()
            self._has_sr = True
            logger.info("[VoiceIntent]: SpeechRecognition engine initialized.")
        except Exception as e:
            logger.info(f"[VoiceIntent]: Microphone / SR unavailable ({e}), running in event-dispatch mode.")
            self._has_sr = False

    def parse_command(self, text: str) -> Optional[str]:
        """Maps transcribed phrase to canonical voice intent."""
        cleaned = text.strip().lower()
        # Direct keyword lookup
        for phrase, intent in VOICE_INTENTS.items():
            if phrase in cleaned:
                return intent
        return None

    def dispatch_intent(self, intent: str):
        """Dispatches an intent to the orchestrator callback."""
        self.last_intent = intent
        if self.on_intent:
            try:
                self.on_intent(intent)
            except Exception as e:
                logger.warning(f"[VoiceIntent]: Callback failed: {e}")

    def start(self):
        """Starts background voice listener thread."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stops background speech listener."""
        self.running = False
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=0.4)
            except Exception:
                pass

    def _listen_loop(self):
        if not self._has_sr or not self._microphone:
            return

        import speech_recognition as sr  # type: ignore

        while self.running:
            try:
                with self._microphone as source:
                    # Short ambient calibration
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    audio = self._recognizer.listen(source, timeout=3.0, phrase_time_limit=3.0)

                if not self.running:
                    break

                try:
                    # Google Web Speech API (free tier, built into speech_recognition)
                    text = self._recognizer.recognize_google(audio).lower()
                    self.last_recognized = text
                    intent = self.parse_command(text)
                    if intent:
                        logger.info(f"[VoiceIntent]: Heard '{text}' -> Triggering {intent}")
                        self.dispatch_intent(intent)
                except sr.UnknownValueError:
                    pass
                except sr.RequestError:
                    time.sleep(1.0)

            except Exception:
                time.sleep(0.5)
