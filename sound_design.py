"""Procedural, royalty-free audio cues for Manim scene transitions."""
from __future__ import annotations

import math
import random
import tempfile
import wave
from array import array
from pathlib import Path


_CUE_DIR = Path(tempfile.gettempdir()) / "saem_render_cues"
_DURATIONS = {"tick": 0.10, "whoosh": 0.55, "drone": 0.90, "chime": 0.65}
_SAMPLE_RATE = 44100


def _cue_path(name: str) -> Path:
    path = _CUE_DIR / f"{name}.wav"
    if path.exists():
        return path

    duration = _DURATIONS[name]
    count = int(_SAMPLE_RATE * duration)
    samples = array("h")
    rng = random.Random(109 + sum(ord(char) for char in name))
    previous_noise = 0.0

    for index in range(count):
        time = index / _SAMPLE_RATE
        phase = time / duration
        if name == "tick":
            envelope = math.exp(-38.0 * time)
            value = envelope * (
                0.65 * math.sin(2 * math.pi * 1200 * time)
                + 0.35 * math.sin(2 * math.pi * 1850 * time)
            )
        elif name == "whoosh":
            envelope = math.sin(math.pi * phase) ** 1.5
            noise = rng.uniform(-1.0, 1.0)
            previous_noise = 0.82 * previous_noise + 0.18 * noise
            sweep_hz = 150.0 + 420.0 * phase
            value = envelope * (
                0.62 * previous_noise
                + 0.20 * math.sin(2 * math.pi * sweep_hz * time)
            )
        elif name == "drone":
            envelope = math.sin(math.pi * phase) ** 0.6
            value = envelope * (
                0.60 * math.sin(2 * math.pi * 110.0 * time)
                + 0.25 * math.sin(2 * math.pi * 164.81 * time)
                + 0.15 * math.sin(2 * math.pi * 220.0 * time)
            )
        else:
            envelope = math.exp(-5.5 * time)
            value = envelope * (
                0.50 * math.sin(2 * math.pi * 523.25 * time)
                + 0.32 * math.sin(2 * math.pi * 659.25 * time)
                + 0.18 * math.sin(2 * math.pi * 783.99 * time)
            )
        samples.append(max(-32767, min(32767, int(value * 7200))))

    _CUE_DIR.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(_SAMPLE_RATE)
        wav_file.writeframes(samples.tobytes())
    return path


def add(scene, name: str, gain_db: float = 0.0) -> bool:
    """Add a cached, synthesized cue to a Manim scene."""
    cue = str(name).lower()
    if cue not in _DURATIONS:
        return False
    try:
        scene.add_sound(str(_cue_path(cue)), gain=gain_db)
        return True
    except Exception:
        return False