#!/usr/bin/env python3
"""sound_design.py — gen-3 procedural, royalty-free audio cues.

Dependency stance: pure stdlib synthesis is the ruler (math + wave + array);
numpy is never required (cues are < 1 s, cost is trivial). Truth frozen:
WAV format (44100 Hz, mono, PCM16), peak ceiling, duration bounds,
determinism per (cue, seed). Representation alive: timbre (base pitch,
harmonic blend, decay, noise color) is seeded, so no two lessons share an
ear-print — the audio analogue of the style genome.

Public API:
    design_cue(name, seed=0, cache_dir=None) -> Path     # synthesize + receipt
    attach(scene, name, gain_db=0.0, seed=0) -> bool     # manim hook, lazy
    selftest()                                           # frozen witnesses (A5)
"""
from __future__ import annotations

import json
import math
import random
import sys
import wave
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAMPLE_RATE = 44100
PEAK_CEILING = 8000                    # int16 amplitude cap (<= ~ -12 dBFS)
CUE_LIBRARY = {"tick": 0.10, "whoosh": 0.55, "drone": 0.90, "chime": 0.65}
_DEFAULT_CACHE = ROOT / "logs" / "audio_cues"


# ------------------------------------------------------------ pure synthesis
def _envelope_exp(n, decay):
    return [math.exp(-decay * i / SAMPLE_RATE) for i in range(n)]


def _envelope_sin(n, power=1.0):
    return [math.sin(math.pi * i / max(1, n - 1)) ** power for i in range(n)]


def _design_params(name, seed):
    """Seeded timbre: bounded variation, never the same ear-print twice."""
    rng = random.Random(f"cue|{name}|{seed}")
    if name == "tick":
        return {"f": 1200 * rng.uniform(0.92, 1.10),
                "f2_ratio": rng.uniform(1.45, 1.65),
                "w": (0.65, 0.35), "decay": rng.uniform(30, 46)}
    if name == "whoosh":
        return {"sweep": (150 * rng.uniform(0.9, 1.1), 420 * rng.uniform(0.9, 1.1)),
                "lp": rng.uniform(0.14, 0.22), "power": rng.uniform(1.2, 1.8)}
    if name == "drone":
        return {"f": 110 * rng.uniform(0.98, 1.02),
                "detune": (1.0, rng.uniform(1.493, 1.505), rng.uniform(1.997, 2.009)),
                "w": (1.0, rng.uniform(0.30, 0.40), rng.uniform(0.12, 0.18)),
                "lfo": rng.uniform(0.08, 0.13), "depth": rng.uniform(0.12, 0.18)}
    if name == "chime":
        return {"f": 523.25 * rng.uniform(0.97, 1.03),
                "ratios": (1.0, rng.uniform(1.255, 1.265), rng.uniform(1.495, 1.505)),
                "w": (0.50, 0.32, 0.18), "decay": rng.uniform(4.8, 6.2)}
    raise ValueError(f"unknown cue '{name}'; library={sorted(CUE_LIBRARY)}")


def synthesize(name, seed=0):
    """Pure ruler: deterministic int16 samples for a cue."""
    if name not in CUE_LIBRARY:
        raise ValueError(f"unknown cue '{name}'; library={sorted(CUE_LIBRARY)}")
    dur = CUE_LIBRARY[name]
    n = int(SAMPLE_RATE * dur)
    p = _design_params(name, seed)
    out = [0.0] * n

    if name == "tick":
        env = _envelope_exp(n, p["decay"])
        for i in range(n):
            t = i / SAMPLE_RATE
            out[i] = env[i] * (p["w"][0] * math.sin(2 * math.pi * p["f"] * t)
                               + p["w"][1] * math.sin(2 * math.pi * p["f"] * p["f2_ratio"] * t))
    elif name == "whoosh":
        env = _envelope_sin(n, p["power"])
        rng = random.Random(f"noise|{name}|{seed}")
        prev = 0.0
        f0, f1 = p["sweep"]
        phase = 0.0
        for i in range(n):
            frac = i / max(1, n - 1)
            prev = (1 - p["lp"]) * prev + p["lp"] * rng.uniform(-1, 1)
            phase += 2 * math.pi * (f0 + (f1 - f0) * frac) / SAMPLE_RATE
            out[i] = env[i] * (0.62 * prev + 0.20 * math.sin(phase))
    elif name == "drone":
        env = _envelope_sin(n, 0.6)
        wsum = sum(abs(w) for w in p["w"])
        for i in range(n):
            t = i / SAMPLE_RATE
            lfo = 1.0 + p["depth"] * math.sin(2 * math.pi * p["lfo"] * t)
            s = 0.0
            for det, w in zip(p["detune"], p["w"]):
                s += (w / wsum) * math.sin(2 * math.pi * p["f"] * det * t)
            out[i] = env[i] * lfo * s
    else:  # chime
        env = _envelope_exp(n, p["decay"])
        for i in range(n):
            t = i / SAMPLE_RATE
            out[i] = env[i] * sum(w * math.sin(2 * math.pi * p["f"] * r * t)
                                  for r, w in zip(p["ratios"], p["w"]))

    peak = max((abs(v) for v in out), default=0.0)
    if peak > 0:
        scale = min(1.0, (PEAK_CEILING / 32767.0) / peak)
        out = [v * scale for v in out]
    return array("h", (max(-32767, min(32767, int(v * 32767))) for v in out))


# ----------------------------------------------------------- cache + receipt
def design_cue(name, seed=0, cache_dir=None):
    cache = Path(cache_dir) if cache_dir else _DEFAULT_CACHE
    tag = abs(hash((name, seed))) % (16 ** 6)
    path = cache / f"{name}_{seed}_{tag:06x}.wav"
    if path.exists():
        return path
    samples = synthesize(name, seed)
    cache.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(samples.tobytes())
    peak = max((abs(s) for s in samples), default=0)
    (cache / (path.stem + ".json")).write_text(
        json.dumps({"cue": name, "seed": seed, "sample_rate": SAMPLE_RATE,
                    "channels": 1, "duration": len(samples) / SAMPLE_RATE,
                    "peak_int16": peak}, indent=2), encoding="utf-8")
    return path


def attach(scene, name, gain_db=0.0, seed=0):
    """Manim hook; scene.add_sound is resolved at call time only."""
    try:
        scene.add_sound(str(design_cue(name, seed)), gain=float(gain_db))
        return True
    except Exception:
        return False


# ------------------------------------------------------------ frozen witness
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    want("library-known", set(CUE_LIBRARY) == {"tick", "whoosh", "drone", "chime"})
    a = synthesize("tick", 7)
    b = synthesize("tick", 7)
    want("determinism", a.tobytes() == b.tobytes())
    c = synthesize("tick", 8)
    want("seed-sensitivity", a.tobytes() != c.tobytes())
    for name in CUE_LIBRARY:
        s = synthesize(name, 3)
        dur = len(s) / SAMPLE_RATE
        want(f"duration:{name}", abs(dur - CUE_LIBRARY[name]) < 0.01, f"{dur:.3f}")
        want(f"peak:{name}", max(abs(v) for v in s) <= PEAK_CEILING)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p1 = design_cue("chime", 5, cache_dir=td)
        want("receipt-manifest", (p1.parent / (p1.stem + ".json")).exists())
        with wave.open(str(p1), "rb") as w:
            want("wav-format", (w.getnchannels(), w.getsampwidth(),
                                w.getframerate()) == (1, 2, SAMPLE_RATE))
    try:
        synthesize("nope", 1)
        want("guard:unknown-cue", False)
    except ValueError:
        want("guard:unknown-cue", True)
    return checks


if __name__ == "__main__":
    fails = 0
    for name, ok, detail in selftest():
        print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
        fails += 0 if ok else 1
    sys.exit(1 if fails else 0)
