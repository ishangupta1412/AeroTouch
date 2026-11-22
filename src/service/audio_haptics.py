"""
AeroTouch Spatial Audio Haptic Illusion Engine
Synthesizes crisp, sub-millisecond tactile audio illusions using in-memory PCM waveforms.
Simulates mechanical mouse switches, glass clicks, and scroll ratchets directly on Windows.
Features:
- Zero external dependencies (uses native Python math + winsound in-memory playback)
- Fully asynchronous (zero impact on 60/120 FPS vision pipeline)
- Tactile acoustic profiles: MECHANICAL_CLICK, GLASS_RELEASE, SCROLL_RATCHET, SNAP_PING
"""

import io
import math
import struct
import wave
from enum import Enum, auto
from typing import Dict, Optional


class HapticCue(Enum):
    MECHANICAL_CLICK = auto()   # Crisp switch click on pinch down
    GLASS_RELEASE = auto()      # Soft release click on pinch up
    SCROLL_RATCHET = auto()     # Mechanical wheel notch click during kinetic scroll
    SNAP_PING = auto()          # Subtle suction pop when snapping to a UI button
    LOCK_CHIME = auto()         # System state change chime


class AudioHapticsEngine:
    """
    Sub-millisecond audio haptics synthesizer and async player.
    """

    def __init__(self, enabled: bool = True, volume: float = 0.85):
        self.enabled = enabled
        self.volume = max(0.0, min(1.0, volume))
        self._sample_rate = 44100
        self._sound_buffers: Dict[HapticCue, bytes] = {}

        # Pre-synthesize all in-memory PCM wave buffers at startup
        self._synthesize_all_cues()

    def _generate_pcm_wave(self, samples: list) -> bytes:
        """Packages float samples [-1.0, 1.0] into an in-memory 16-bit mono WAV byte string."""
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wav:
            wav.setnchannels(1)        # Mono
            wav.setsampwidth(2)        # 16-bit
            wav.setframerate(self._sample_rate)
            raw_frames = bytearray()
            for s in samples:
                val = max(-1.0, min(1.0, s)) * self.volume
                int_val = int(val * 32767.0)
                raw_frames.extend(struct.pack('<h', int_val))
            wav.writeframes(raw_frames)
        return buf.getvalue()

    def _synthesize_all_cues(self) -> None:
        """Pre-renders acoustic impulse responses for all tactile cues."""
        sr = self._sample_rate

        # 1. Mechanical Switch Click (14ms fast exponential decay impulse at 2100Hz)
        click_duration = 0.014
        click_samples = []
        n_click = int(sr * click_duration)
        for i in range(n_click):
            t = i / sr
            decay = math.exp(-t * 350.0)
            wave_val = math.sin(2.0 * math.pi * 2100.0 * t) * decay
            click_samples.append(wave_val)
        self._sound_buffers[HapticCue.MECHANICAL_CLICK] = self._generate_pcm_wave(click_samples)

        # 2. Glass Release Click (9ms soft release at 3400Hz)
        release_duration = 0.009
        release_samples = []
        n_release = int(sr * release_duration)
        for i in range(n_release):
            t = i / sr
            decay = math.exp(-t * 500.0)
            wave_val = math.sin(2.0 * math.pi * 3400.0 * t) * decay * 0.65
            release_samples.append(wave_val)
        self._sound_buffers[HapticCue.GLASS_RELEASE] = self._generate_pcm_wave(release_samples)

        # 3. Scroll Ratchet Tick (6ms wooden notch click at 900Hz)
        ratchet_duration = 0.006
        ratchet_samples = []
        n_ratchet = int(sr * ratchet_duration)
        for i in range(n_ratchet):
            t = i / sr
            decay = math.exp(-t * 700.0)
            wave_val = math.sin(2.0 * math.pi * 900.0 * t) * decay * 0.50
            ratchet_samples.append(wave_val)
        self._sound_buffers[HapticCue.SCROLL_RATCHET] = self._generate_pcm_wave(ratchet_samples)

        # 4. Snap Ping (18ms subtle magnetic suction pop at 550Hz rising to 700Hz)
        snap_duration = 0.018
        snap_samples = []
        n_snap = int(sr * snap_duration)
        for i in range(n_snap):
            t = i / sr
            freq = 550.0 + (150.0 * (i / max(1, n_snap)))
            decay = math.exp(-t * 220.0)
            wave_val = math.sin(2.0 * math.pi * freq * t) * decay * 0.70
            snap_samples.append(wave_val)
        self._sound_buffers[HapticCue.SNAP_PING] = self._generate_pcm_wave(snap_samples)

        # 5. Lock / State Change Chime (45ms dual harmonic chime)
        chime_duration = 0.045
        chime_samples = []
        n_chime = int(sr * chime_duration)
        for i in range(n_chime):
            t = i / sr
            decay = math.exp(-t * 90.0)
            wave_val = (
                0.7 * math.sin(2.0 * math.pi * 880.0 * t) +
                0.3 * math.sin(2.0 * math.pi * 1760.0 * t)
            ) * decay
            chime_samples.append(wave_val)
        self._sound_buffers[HapticCue.LOCK_CHIME] = self._generate_pcm_wave(chime_samples)

    def trigger(self, cue: HapticCue) -> bool:
        """
        Triggers an audio tactile illusion cue asynchronously without blocking.
        """
        if not self.enabled:
            return False

        wav_data = self._sound_buffers.get(cue)
        if not wav_data:
            return False

        try:
            import winsound
            winsound.PlaySound(wav_data, winsound.SND_MEMORY | winsound.SND_ASYNC)
            return True
        except Exception:
            return False
