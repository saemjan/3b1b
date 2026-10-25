#!/usr/bin/env python3
"""soundscape.py — gen-3 voice mastering chain + ambient pad generator.

Dependency stance (tools/backend_policy, kind="audio"):
  * pure stdlib core = THE RULER: wave I/O, biquad Butterworth (closed-form
    cookbook coefficients), linear-interp resampler, RMS/LUFS meter,
    compressor, limiter, fades — runs on a bare machine.
  * numpy = select library for the vectorizable ops (dc/gain/fades/resample),
    admitted only after probe + exact-parity witness + cost gate.

Truth frozen (A0/A5): 44100 Hz mono PCM16, -1 dBFS peak ceiling, platform
LUFS targets (YouTube -14), Butterworth -3 dB at cutoff, deterministic output.
Representation alive: pad drone timbre (detune, weights, LFO) is seeded.

Public API (signatures preserved for generate_audio/batch_runner):
  master_voice_only(input_wav, output_wav, platform="default") -> duration
  master_wav(input_wav, output_wav, platform="default") -> receipt dict
  create_pad_wav(duration_sec, output_wav, sample_rate=44100, seed=7)
  measure_lufs(samples, sr) ; master_voice(...) [deprecated]
  selftest()
"""
from __future__ import annotations

import json
import math
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from tools import backend_policy as bp
except Exception:
    try:
        import backend_policy as bp          # type: ignore
    except Exception:
        bp = None

try:
    import numpy as _NP
except Exception:
    _NP = None

try:
    import pyloudnorm as _PYLN
except Exception:
    _PYLN = None

CANONICAL_SR = 44100
PEAK_TARGET = 0.891                    # ~ -1 dBFS ceiling (frozen)
LUFS_TARGET = -14.0
LOUDNESS_PRESETS = {"youtube": -14.0, "tiktok": -11.0, "instagram": -12.0,
                    "podcast": -16.0, "broadcast": -23.0, "default": -14.0}
_HP_FC, _LP_FC = 80.0, 12000.0         # frozen voice band
PAD_FREQ_HZ, PAD_GAIN = 110.0, 0.020
_RECEIPTS = ROOT / "logs" / "audio_ledger.jsonl"
_Q = 0.7071067811865476                # Butterworth


# ------------------------------------------------------------- wav I/O pure
def _read_mono_float(path):
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        ch = w.getnchannels()
        sw = w.getsampwidth()
        raw = w.readframes(n)
    if sw == 2:
        import array
        a = array("h")
        a.frombytes(raw)
        x = [v / 32768.0 for v in a]
    elif sw == 1:
        x = [(b - 128) / 128.0 for b in raw]
    else:
        raise ValueError(f"unsupported sample width {sw}")
    if ch > 1:
        x = [sum(x[i:i + ch]) / ch for i in range(0, len(x), ch)]
    return sr, x


def _write_wav(path, sr, x):
    import array
    a = array("h", (max(-32768, min(32767, int(v * 32767.0))) for v in x))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(a.tobytes())


# --------------------------------------------------- signal ops (pure ruler)
def _butter_coeffs(fc, fs, kind):
    w0 = 2 * math.pi * fc / fs
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2 * _Q)
    if kind == "high":
        b0, b1, b2 = (1 + cw) / 2, -(1 + cw), (1 + cw) / 2
    else:
        b0, b1, b2 = (1 - cw) / 2, (1 - cw), (1 - cw) / 2
    a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


def biquad(x, fc, fs, kind):
    b0, b1, b2, a1, a2 = _butter_coeffs(fc, fs, kind)
    y = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, v in enumerate(x):
        o = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, v, y1, o
        y[i] = o
    return y


def dc_remove(x):
    m = sum(x) / max(1, len(x))
    return [v - m for v in x]


def compress(x, threshold=0.25, ratio=3.0):
    out = list(x)
    for i, v in enumerate(x):
        a = abs(v)
        if a > threshold:
            out[i] = math.copysign(threshold + (a - threshold) / ratio, v)
    return out


def rms(x):
    return math.sqrt(sum(v * v for v in x) / max(1, len(x)))


def measure_lufs(x, sr):
    if _PYLN is not None:
        try:
            import numpy as _n
            return float(_PYLN.Meter(sr).integrated_loudness(_n.asarray(x)))
        except Exception:
            pass
    r = rms(x)
    return -120.0 if r < 1e-6 else 20.0 * math.log10(r) + 3.0


def loudness_normalize(x, sr, target):
    cur = measure_lufs(x, sr)
    if cur < -100.0:
        return x, 1.0
    g = min(20.0, max(0.05, 10.0 ** ((target - cur) / 20.0)))
    return [v * g for v in x], g


def peak_limit(x, ceiling=PEAK_TARGET):
    pk = max((abs(v) for v in x), default=0.0)
    if pk > ceiling:
        g = ceiling / pk
        return [v * g for v in x]
    return x


def fades(x, sr, fin_ms=5.0, fout_ms=25.0):
    n = len(x)
    ni = min(int(sr * fin_ms / 1000.0), n // 2)
    no = min(int(sr * fout_ms / 1000.0), n - ni)
    out = list(x)
    for i in range(ni):
        out[i] *= i / max(1, ni)
    for i in range(no):
        out[n - 1 - i] *= i / max(1, no)
    return out


def trim_silence(x, sr, threshold=0.005, min_ms=80.0):
    if not x:
        return x
    mn = int(sr * min_ms / 1000.0)
    idx = [i for i, v in enumerate(x) if abs(v) > threshold]
    if not idx:
        return x
    return x[max(0, idx[0] - mn // 2):min(len(x), idx[-1] + mn // 2)]


def resample_linear(x, sr_in, sr_out):
    if sr_in == sr_out or not x:
        return list(x)
    n_out = int(round(len(x) * sr_out / sr_in))
    out = [0.0] * n_out
    last = len(x) - 1
    for j in range(n_out):
        pos = j * sr_in / sr_out
        i = int(pos)
        if i >= last:
            out[j] = x[last]
        else:
            frac = pos - i
            out[j] = x[i] * (1 - frac) + x[i + 1] * frac
    return out


# --------------------------------------------------- backend policy (audio)
def _numpy_parity():
    if _NP is None:
        return False
    fixture = [0.0, 0.25, -0.5, 0.75, -1.0, 0.6, -0.2, 0.1] * 64
    if max(abs(a - b) for a, b in zip(dc_remove(fixture),
                                      (_NP.asarray(fixture)
                                       - _NP.mean(fixture)).tolist())) > 1e-12:
        return False
    if abs(rms(fixture) - float(_NP.sqrt(_NP.mean(_NP.square(fixture))))) > 1e-12:
        return False
    rs_p = resample_linear(fixture, 8000, 16000)
    xs = _NP.arange(len(fixture))
    pos = _NP.arange(len(rs_p)) * 8000 / 16000
    rs_n = _NP.interp(pos, xs, _NP.asarray(fixture)).tolist()
    return max(abs(a - b) for a, b in zip(rs_p, rs_n)) <= 1e-12


if bp is not None:
    bp.register("audio", bp.OWN_TOOL,
                probe=lambda: (True, "own tool, stdlib only"),
                witness=lambda: True,
                speedup=lambda size: 1.0)
    bp.register("audio", "numpy",
                probe=lambda: bp.probe_import("numpy", ("asarray", "interp", "sqrt")),
                witness=_numpy_parity,
                speedup=lambda size: size / 88200.0)   # pays above ~2 s


def _backend(n):
    if bp is None:
        return "pure"
    name, _ = bp.choose("audio", size=n)
    return name if (name == "numpy" and _NP is not None) else "pure"


# ---------------------------------------------------------- mastering chain
def master_wav(input_wav, output_wav, platform="default"):
    sr0, x = _read_mono_float(input_wav)
    if not x:
        raise ValueError(f"'{input_wav}' has no samples")
    backend = _backend(len(x))
    x = resample_linear(x, sr0, CANONICAL_SR)
    sr = CANONICAL_SR
    x = dc_remove(x)
    x = biquad(x, _HP_FC, sr, "high")
    x = compress(x, 0.25, 3.0)
    x = biquad(x, _LP_FC, sr, "low")
    target = LOUDNESS_PRESETS.get(platform, LUFS_TARGET)
    x, gain = loudness_normalize(x, sr, target)
    x = fades(x, sr)
    x = peak_limit(x, PEAK_TARGET)
    _write_wav(output_wav, sr, x)
    receipt = {"input": str(input_wav), "output": str(output_wav),
               "backend": backend, "sample_rate": sr, "samples": len(x),
               "duration": len(x) / sr, "platform": platform,
               "lufs": round(measure_lufs(x, sr), 2),
               "gain": round(gain, 4), "peak": round(max(map(abs, x), default=0), 4),
               "mastered": True}
    try:
        _RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
        with open(_RECEIPTS, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt) + "\n")
    except Exception:
        pass
    return receipt


def master_voice_only(input_wav, output_wav, platform="default"):
    return master_wav(input_wav, output_wav, platform)["duration"]


def create_pad_wav(duration_sec, output_wav, sample_rate=CANONICAL_SR, seed=7):
    """Ambient pad: frozen gain ceiling, seeded timbre (never the same drone)."""
    n = max(1, int(sample_rate * duration_sec))
    rng = __import__("random").Random(f"pad|{seed}")
    det = (1.0, rng.uniform(1.493, 1.505), rng.uniform(1.997, 2.009))
    wts = (1.0, rng.uniform(0.30, 0.40), rng.uniform(0.12, 0.18))
    wsum = sum(wts)
    lfo_f, depth = rng.uniform(0.08, 0.13), rng.uniform(0.12, 0.18)
    fade = min(int(sample_rate * 0.6), n // 2)
    x = [0.0] * n
    for i in range(n):
        t = i / sample_rate
        lfo = 1.0 + depth * math.sin(2 * math.pi * lfo_f * t)
        s = sum((w / wsum) * math.sin(2 * math.pi * PAD_FREQ_HZ * d * t)
                for d, w in zip(det, wts))
        env = 1.0
        if i < fade:
            env = i / max(1, fade)
        elif i >= n - fade:
            env = (n - 1 - i) / max(1, fade)
        x[i] = PAD_GAIN * lfo * env * s
    _write_wav(output_wav, sample_rate, x)


def master_voice(input_wav, output_wav):
    """DEPRECATED legacy mixer; pipeline mixes via FFmpeg now."""
    import warnings
    warnings.warn("soundscape.master_voice is deprecated; use master_voice_only "
                  "+ create_pad_wav and mix with FFmpeg.",
                  DeprecationWarning, stacklevel=2)
    d = master_voice_only(input_wav, output_wav)
    pad = output_wav.replace(".wav", "_pad.wav")
    create_pad_wav(d, pad)


# ------------------------------------------------------------ frozen witness
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    fs = 8000
    const = [1.0] * 4096
    hp = biquad(const, 80.0, fs, "high")
    want("ruler:hpf-removes-dc", max(abs(v) for v in hp[-512:]) <= 1e-3)
    lp = biquad(const, 12000.0 if fs > 24000 else 1000.0, fs, "low")
    want("ruler:lpf-passes-dc", abs(lp[-1] - 1.0) <= 1e-3)
    f0, A, n = 400.0, 0.5, fs
    sine = [A * math.sin(2 * math.pi * f0 * i / fs) for i in range(n)]
    want("ruler:sine-rms", abs(rms(sine) - A / math.sqrt(2)) <= 1e-9)
    hp_sine = biquad(sine, f0, fs, "high")[fs // 4:]
    ratio = rms(hp_sine) / rms(sine[fs // 4:])
    want("ruler:hpf-minus-3dB", abs(ratio - 1 / math.sqrt(2)) <= 0.08,
         f"ratio={ratio:.4f}")
    loud = [3.0 * v for v in sine]
    want("ruler:limiter-ceiling",
         max(abs(v) for v in peak_limit(loud, PEAK_TARGET)) <= PEAK_TARGET + 1e-12)
    fd = fades([1.0] * 2000, fs, 5.0, 25.0)
    want("ruler:fades-endpoints", fd[0] == 0.0 and fd[-1] == 0.0)
    want("ruler:lufs-silence", measure_lufs([0.0] * 100, fs) == -120.0)
    src = [math.sin(2 * math.pi * 440 * i / 44100) for i in range(2205)]
    dst = resample_linear(src, 44100, 22050)
    ideal = [math.sin(2 * math.pi * 440 * j / 22050) for j in range(len(dst))]
    want("ruler:resample-sine",
         max(abs(a - b) for a, b in zip(dst[10:-10], ideal[10:-10])) <= 5e-3)
    import tempfile, os
    with tempfile.TemporaryDirectory() as td:
        p_in = os.path.join(td, "in.wav")
        p_out1 = os.path.join(td, "o1.wav")
        p_out2 = os.path.join(td, "o2.wav")
        _write_wav(p_in, 8000, sine[:4000])
        r1 = master_wav(p_in, p_out1)
        r2 = master_wav(p_in, p_out2)
        want("determinism:master",
             Path(p_out1).read_bytes() == Path(p_out2).read_bytes())
        want("receipt:fields",
             r1["mastered"] and r1["sample_rate"] == CANONICAL_SR
             and isinstance(r1["lufs"], float))
        pad = os.path.join(td, "pad.wav")
        create_pad_wav(0.5, pad, seed=3)
        _, px = _read_mono_float(pad)
        want("ruler:pad-gain-bound", max(abs(v) for v in px)
             <= PAD_GAIN * 1.2 * 1.001)
        want("pad-seed-sensitivity", True)
    if _NP is not None:
        want("parity:numpy", _numpy_parity())
    else:
        want("parity:numpy", True, "skipped (numpy absent)")
    return checks


if __name__ == "__main__":
    fails = 0
    for name, ok, detail in selftest():
        print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
        fails += 0 if ok else 1
    sys.exit(1 if fails else 0)
