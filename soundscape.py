#!/usr/bin/env python3
"""soundscape.py — Voice mastering chain + ambient pad generator.

Public functions used by the pipeline:
    master_voice_only(input_wav, output_wav) -> duration_sec
    create_pad_wav(duration_sec, output_wav)

Legacy `master_voice` mixes voice + pad in one file. Kept for offline use
but deprecated — batch_runner mixes via FFmpeg instead.
"""
from __future__ import annotations

import logging
import warnings
from typing import Optional

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, resample_poly

try:
    import pyloudnorm as pyln
    HAS_PYLN = True
except ImportError:
    HAS_PYLN = False


log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────────
CANONICAL_SR = 44100
PAD_FREQ_HZ  = 110.0
PAD_GAIN     = 0.020
PEAK_TARGET  = 0.891           # ≈ -1 dBFS sample-peak ceiling
LUFS_TARGET  = -14.0           # YouTube normalization target

# Slight detune for organic beating in the ambient pad
PAD_DETUNE   = (1.000, 1.499, 2.003)
PAD_WEIGHTS  = (1.00, 0.35, 0.15)

# Platform-specific loudness targets
LOUDNESS_PRESETS = {
    "youtube":   -14.0,
    "tiktok":    -11.0,
    "instagram": -12.0,
    "podcast":   -16.0,
    "broadcast": -23.0,        # EBU R128
    "default":   LUFS_TARGET,
}


# ────────────────────────────────────────────────────────────────────────
# Filter primitives
# ────────────────────────────────────────────────────────────────────────
def _highpass(sig: np.ndarray, sr: int,
              cutoff: float = 80.0) -> np.ndarray:
    nyq = sr / 2.0
    cutoff = max(1.0, min(cutoff, nyq * 0.95))
    sos = butter(2, cutoff / nyq, btype="high", output="sos")
    return sosfilt(sos, sig).astype(np.float32)


def _lowpass(sig: np.ndarray, sr: int,
             cutoff: float = 12000.0) -> np.ndarray:
    nyq = sr / 2.0
    cutoff = min(cutoff, nyq * 0.95)
    sos = butter(2, cutoff / nyq, btype="low", output="sos")
    return sosfilt(sos, sig).astype(np.float32)


def _dc_remove(sig: np.ndarray) -> np.ndarray:
    return (sig - float(sig.mean())).astype(np.float32)


def _sanitize(sig: np.ndarray) -> np.ndarray:
    """Replace NaN/Inf with 0 so downstream math can't propagate them."""
    if not np.all(np.isfinite(sig)):
        n_bad = int((~np.isfinite(sig)).sum())
        log.warning("sanitize: %d non-finite samples replaced with 0", n_bad)
        sig = np.nan_to_num(sig, nan=0.0, posinf=0.0, neginf=0.0)
    return sig.astype(np.float32)


def _compress(sig: np.ndarray, threshold: float = 0.25,
              ratio: float = 3.0) -> np.ndarray:
    """Hard-knee compressor (was misnamed _soft_compress)."""
    out = sig.copy()
    mask = np.abs(sig) > threshold
    frac = float(mask.mean())
    if frac > 0.05:
        log.debug("compress: %.1f%% over %.2f", frac * 100, threshold)
    over = np.abs(sig[mask]) - threshold
    out[mask] = np.sign(sig[mask]) * (threshold + over / ratio)
    return out


def _measure_lufs(sig: np.ndarray, sr: int) -> float:
    """Measure integrated loudness in LUFS. Uses pyloudnorm if available,
    otherwise falls back to an RMS-based approximation."""
    if HAS_PYLN:
        meter = pyln.Meter(sr)
        try:
            return float(meter.integrated_loudness(sig))
        except Exception as e:
            log.warning("pyloudnorm failed (%s); falling back to RMS", e)
    rms = float(np.sqrt(np.mean(sig ** 2) + 1e-12))
    if rms < 1e-6:
        return -120.0
    return 20.0 * np.log10(rms) + 3.0     # +3 ≈ RMS→LUFS on speech


def _loudness_normalize(sig: np.ndarray, sr: int,
                        target_lufs: float = LUFS_TARGET) -> np.ndarray:
    """Scale signal so its measured loudness hits target_lufs.
    True LUFS if pyloudnorm is installed; RMS approximation otherwise."""
    current = _measure_lufs(sig, sr)
    if current < -100.0:
        return sig
    delta_db = target_lufs - current
    gain = float(10.0 ** (delta_db / 20.0))
    gain = float(np.clip(gain, 0.05, 20.0))
    log.debug("loudness: %.1f LUFS → %.1f LUFS (gain %.2f×)",
              current, target_lufs, gain)
    return (sig * gain).astype(np.float32)


def _peak_limit(sig: np.ndarray, ceiling: float = PEAK_TARGET) -> np.ndarray:
    peak = float(np.max(np.abs(sig)))
    if peak > ceiling:
        sig = sig * (ceiling / peak)
    return sig.astype(np.float32)


def _voice_fade(sig: np.ndarray, sr: int,
                fade_in_ms: float = 5.0,
                fade_out_ms: float = 25.0) -> np.ndarray:
    """Asymmetric fade — very short in, slightly longer out."""
    n = len(sig)
    in_s = min(int(sr * fade_in_ms / 1000.0), n // 2)
    out_s = min(int(sr * fade_out_ms / 1000.0), n - in_s)
    env = np.ones(n, dtype=np.float32)
    if in_s > 0:
        env[:in_s] = np.linspace(0, 1, in_s)
    if out_s > 0:
        env[-out_s:] = np.linspace(1, 0, out_s)
    return (sig * env).astype(np.float32)


def _trim_silence(sig: np.ndarray, sr: int, threshold: float = 0.005,
                  min_silence_ms: float = 80.0) -> np.ndarray:
    """Trim leading/trailing silence below `threshold` amplitude."""
    if sig.size == 0:
        return sig
    min_n = int(sr * min_silence_ms / 1000.0)
    above = np.where(np.abs(sig) > threshold)[0]
    if above.size == 0:
        return sig
    start = max(0, int(above[0]) - min_n // 2)
    end = min(len(sig), int(above[-1]) + min_n // 2)
    return sig[start:end].astype(np.float32)


def _resample(sig: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return sig.astype(np.float32)
    g = int(np.gcd(sr_in, sr_out))
    out = resample_poly(sig, sr_out // g, sr_in // g)
    # resample_poly can overshoot ±1; clip before downstream processing
    return np.clip(out, -1.0, 1.0).astype(np.float32)


# ────────────────────────────────────────────────────────────────────────
# Ambient pad
# ────────────────────────────────────────────────────────────────────────
def generate_ambient_pad(duration_sec: float,
                         sample_rate: int = CANONICAL_SR) -> np.ndarray:
    n = max(1, int(sample_rate * duration_sec))
    t = np.linspace(0, duration_sec, n, endpoint=False, dtype=np.float64)

    # Slow LFO for organic motion
    lfo = 1.0 + 0.15 * np.sin(2 * np.pi * 0.1 * t)

    drone = np.zeros(n, dtype=np.float64)
    for detune, weight in zip(PAD_DETUNE, PAD_WEIGHTS):
        drone += weight * np.sin(2 * np.pi * PAD_FREQ_HZ * detune * t)
    drone *= lfo * PAD_GAIN
    drone = drone.astype(np.float32)

    fade = min(int(sample_rate * 0.6), n // 2)
    if fade > 0:
        env = np.ones(n, dtype=np.float32)
        env[:fade] = np.linspace(0, 1, fade)
        env[-fade:] = np.linspace(1, 0, fade)
        drone *= env
    return drone


# ────────────────────────────────────────────────────────────────────────
# WAV I/O helpers
# ────────────────────────────────────────────────────────────────────────
def _to_mono_float(data: np.ndarray, dtype) -> np.ndarray:
    if dtype == np.int16:
        out = data.astype(np.float32) / 32768.0
    elif dtype == np.int32:
        out = data.astype(np.float32) / 2147483648.0
    else:
        out = data.astype(np.float32)
    if out.ndim > 1:
        out = np.mean(out, axis=1)
    return out


def _write_int16_wav(path: str, sr: int, sig: np.ndarray) -> None:
    pcm = np.clip(sig * 32767.0, -32768, 32767).astype(np.int16)
    wavfile.write(path, sr, pcm)


# ────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────
def master_voice_only(input_wav: str, output_wav: str,
                      platform: str = "default") -> float:
    """Master a voice WAV: mono, 44.1 kHz, EBU-ish loudness, peak-limited."""
    sr, raw = wavfile.read(input_wav)
    voice = _to_mono_float(raw, raw.dtype)
    if voice.size == 0:
        raise ValueError(f"'{input_wav}' has no samples")
    voice = _resample(voice, sr, CANONICAL_SR)
    sr = CANONICAL_SR
    voice = _sanitize(voice)
    voice = _trim_silence(voice, sr)
    voice = _dc_remove(voice)
    voice = _highpass(voice, sr, 80.0)
    voice = _compress(voice, 0.25, 3.0)
    voice = _lowpass(voice, sr, 12000.0)

    target = LOUDNESS_PRESETS.get(platform, LUFS_TARGET)
    voice = _loudness_normalize(voice, sr, target)

    voice = _voice_fade(voice, sr, fade_in_ms=5.0, fade_out_ms=25.0)
    voice = _peak_limit(voice, PEAK_TARGET)

    duration = len(voice) / float(sr)
    _write_int16_wav(output_wav, sr, voice)
    return duration


def create_pad_wav(duration_sec: float, output_wav: str,
                   sample_rate: int = CANONICAL_SR) -> None:
    pad = generate_ambient_pad(duration_sec, sample_rate)
    _write_int16_wav(output_wav, sample_rate, pad)


def master_voice(input_wav: str, output_wav: str) -> None:
    """DEPRECATED. Mixes voice+pad into one file. Use master_voice_only +
    create_pad_wav instead; the pipeline now mixes via FFmpeg."""
    warnings.warn(
        "soundscape.master_voice is deprecated. "
        "Use master_voice_only() + create_pad_wav() and mix with FFmpeg.",
        DeprecationWarning, stacklevel=2,
    )
    sr, raw = wavfile.read(input_wav)
    voice = _to_mono_float(raw, raw.dtype)
    if voice.size == 0:
        raise ValueError(f"'{input_wav}' has no samples")
    voice = _resample(voice, sr, CANONICAL_SR)
    sr = CANONICAL_SR
    voice = _sanitize(voice)
    voice = _dc_remove(voice)
    voice = _highpass(voice, sr, 80.0)
    voice = _compress(voice, 0.25, 3.0)
    voice = _lowpass(voice, sr, 12000.0)
    voice = _loudness_normalize(voice, sr, LUFS_TARGET)
    voice = _voice_fade(voice, sr)
    duration = len(voice) / float(sr)
    pad = generate_ambient_pad(duration, sr)
    L = min(len(voice), len(pad))
    mixed = _peak_limit(voice[:L] + pad[:L], PEAK_TARGET)
    _write_int16_wav(output_wav, sr, mixed)
