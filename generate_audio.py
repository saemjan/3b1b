#!/usr/bin/env python3
"""Voice synthesis + mastering gate.

Pipeline per row:
  1. text_normalizer prepares narration (units, greek, scientific notation).
  2. XTTS-v2 clones saem_voice_sample.wav; deterministic seed per video_id
     (SHA-256 of the id); temperature 0.65, repetition penalty 3.0;
     automatic CPU fallback on CUDA OOM; speaker latent cached per batch.
  3. Resample 24 kHz -> 44.1 kHz.
  4. MASTERING GATE: soundscape.master_voice_only (DC-remove, HPF 80 Hz,
     compress 3:1, LPF 12 kHz, LUFS target, peak limit). If soundscape is
     unavailable the raw voice is used and mastered=False is reported.
  5. Ambient pad matched to voice length.
  6. LUFS measured and returned for the ledger.

Standalone:
    python3 generate_audio.py <video_id> <script.txt> <out_voice.wav> <out_pad.wav>
"""
import hashlib
import json
import os
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMP = ROOT / "temp_audio"
SPEAKER_WAV = ROOT / "saem_voice_sample.wav"

try:
    import text_normalizer
except ImportError:
    text_normalizer = None

try:
    import soundscape
except ImportError:
    soundscape = None

try:
    from tools.visual_qa import measure_lufs
except ImportError:
    def measure_lufs(_p):
        return None

_SPEAKER_CACHE = {}


def seed_for(video_id):
    return int(hashlib.sha256(video_id.encode("utf-8")).hexdigest()[:8], 16)


def normalize_script(script):
    if text_normalizer is None:
        return script
    fn = getattr(text_normalizer, "normalize", None) or \
         getattr(text_normalizer, "normalize_text", None)
    return fn(script) if fn else script


def _resample(src, dst, rate=44100):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-ar", str(rate), "-ac", "1", str(dst)],
        check=True)


def _duration_sec(path):
    try:
        with wave.open(str(path)) as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, check=True)
        return float(out.stdout.strip())


def _master(voice_path):
    """Mastering gate. Returns True when the chain actually ran."""
    if soundscape is None:
        return False
    for name in ("master_voice_only", "master_voice", "master"):
        fn = getattr(soundscape, name, None)
        if not fn:
            continue
        try:
            if name == "master_voice_only":
                fn(str(voice_path), str(voice_path), "youtube")
            else:
                fn(str(voice_path), str(voice_path))
            return True
        except TypeError:
            try:
                fn(str(voice_path))
                return True
            except Exception:
                return False
        except Exception:
            return False
    return False


def _make_pad(pad_path, duration):
    if soundscape is not None:
        fn = getattr(soundscape, "make_pad", None) or \
             getattr(soundscape, "ambient_pad", None)
        if fn:
            try:
                fn(str(pad_path), duration)
                return
            except Exception:
                pass
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi",
         "-i", f"anoisesrc=color=pink:duration={duration:.2f}:seed=7",
         "-af", "lowpass=f=320,volume=0.02", str(pad_path)],
        check=True)


def synthesize(row, out_voice, out_pad, speaker_wav=SPEAKER_WAV):
    """Full audio gate for one row. Returns dict(duration, lufs, mastered)."""
    video_id = row["video_id"]
    script = normalize_script(row.get("audio_script", ""))
    TEMP.mkdir(parents=True, exist_ok=True)
    out_voice, out_pad = Path(out_voice), Path(out_pad)

    if not Path(speaker_wav).exists():
        raise RuntimeError(f"missing voice reference: {speaker_wav}")

    raw = TEMP / f"{video_id}_raw.wav"
    seed = seed_for(video_id)
    tts = _load_tts(speaker_wav)
    try:
        tts["synth"].tts_to_file(
            text=script,
            speaker_wav=str(speaker_wav),
            language=row.get("language", "en"),
            file_path=str(raw),
            temperature=0.65,
            repetition_penalty=3.0,
            seed=seed,
        )
    except RuntimeError as e:
        if "CUDA" not in str(e).upper() and "out of memory" not in str(e).lower():
            raise
        print("[audio] CUDA OOM; retrying on CPU")
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        tts = _load_tts(speaker_wav, force_cpu=True)
        tts["synth"].tts_to_file(
            text=script, speaker_wav=str(speaker_wav),
            language=row.get("language", "en"), file_path=str(raw),
            temperature=0.65, repetition_penalty=3.0, seed=seed)

    _resample(raw, out_voice, 44100)
    mastered = _master(out_voice)
    duration = _duration_sec(out_voice)
    _make_pad(out_pad, duration)
    lufs = measure_lufs(out_voice)
    return {"duration": duration, "lufs": lufs, "mastered": mastered}


def _load_tts(speaker_wav, force_cpu=False):
    key = ("cpu" if force_cpu else "any", str(speaker_wav))
    if key in _SPEAKER_CACHE:
        return _SPEAKER_CACHE[key]
    from TTS.api import TTS
    import torch
    device = "cpu" if (force_cpu or not torch.cuda.is_available()) else "cuda"
    synth = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    entry = {"synth": synth, "device": device}
    _SPEAKER_CACHE[key] = entry
    return entry


def main():
    if len(sys.argv) < 5:
        print("usage: generate_audio.py <video_id> <script.txt> "
              "<out_voice.wav> <out_pad.wav>")
        return 1
    vid, script_path, voice, pad = sys.argv[1:5]
    script = Path(script_path).read_text(encoding="utf-8")
    info = synthesize({"video_id": vid, "audio_script": script}, voice, pad)
    print(json.dumps(info))
    return 0


if __name__ == "__main__":
    sys.exit(main())
