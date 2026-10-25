#!/usr/bin/env python3
"""generate_audio.py — gen-3 narration gate.

Pipeline per row (every step receipted):
  normalize (text_normalizer, own tool)
  → chunk   (text_normalizer.chunk_for_xtts, own tool, sentence-safe ≤280 chars)
  → synth   (XTTS-v2 = SELECTED LIBRARY, device negotiated by backend_policy
             kind="tts": xtts_cuda → xtts_cpu, probe+witness+cost, OOM degrades
             with recorded reason — degradation, not deception)
  → concat  (pure stdlib wave splice — own tool, sample-exact)
  → resample 24k→44.1k (soundscape.resample_linear pure ruler; ffmpeg only if
             soundscape absent)
  → master  (soundscape.master_wav gen-3: LUFS target, peak ceiling, receipt)
  → pad     (soundscape.create_pad_wav, SEEDED per video so the drone evolves)

Frozen truth: VOICE_PARAMS, LUFS/peak targets (in soundscape), seed derivation
(SHA-256 of video_id), chunk bound. Evolving representation: pad timbre seed,
voice grammar upstream (jee_model_engine / style_genome).

Receipts: every run appends logs/audio_ledger.jsonl
  {video_id, seed, backend, chunks, duration, lufs, mastered, pad_seed,
   voice_params, wall_sec}

Standalone:
  python3 generate_audio.py <video_id> <script.txt> <out_voice.wav> <out_pad.wav>
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import wave
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

TEMP = ROOT / "temp_audio"
SPEAKER_WAV = ROOT / "saem_voice_sample.wav"
LEDGER = ROOT / "logs" / "audio_ledger.jsonl"
CANONICAL_SR = 44100
CHUNK_CHARS = 280

VOICE_PARAMS = {"temperature": 0.65, "repetition_penalty": 3.0}   # frozen

try:
    import text_normalizer as _TN
except Exception:
    _TN = None
try:
    import soundscape as _SS
except Exception:
    _SS = None
try:
    from tools import backend_policy as bp
except Exception:
    try:
        import backend_policy as bp          # type: ignore
    except Exception:
        bp = None

_TTS_CACHE = {}
_WITNESS = {}


# ------------------------------------------------------------------ own tools
def seed_for(video_id: str) -> int:
    return int(hashlib.sha256(video_id.encode("utf-8")).hexdigest()[:8], 16)


def normalize_script(script: str) -> str:
    if _TN is None:
        return script
    return _TN.normalize(script)


def chunk_script(script: str):
    if _TN is None:
        return [script.strip()] if script.strip() else []
    return _TN.chunk_for_xtts(script, CHUNK_CHARS)


def concat_wavs(paths, out) -> float:
    """Pure stdlib splice: sample-exact, format-checked, witnessable."""
    frames, meta = [], None
    for p in paths:
        with wave.open(str(p), "rb") as w:
            m = (w.getnchannels(), w.getsampwidth(), w.getframerate())
            if meta is None:
                meta = m
            elif meta != m:
                raise ValueError(f"chunk format mismatch {m} != {meta}")
            frames.append(w.readframes(w.getnframes()))
    if not meta:
        raise ValueError("nothing to concat")
    with wave.open(str(out), "wb") as w:
        w.setnchannels(meta[0]); w.setsampwidth(meta[1]); w.setframerate(meta[2])
        for f in frames:
            w.writeframes(f)
    return len(b"".join(frames)) / (meta[2] * meta[0] * meta[1])


def _read_pcm16_mono(path):
    with wave.open(str(path), "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise ValueError("expected 16-bit wav")
    a = array("h"); a.frombytes(raw)
    x = [v / 32768.0 for v in a]
    if ch > 1:
        x = [sum(x[i:i + ch]) / ch for i in range(0, len(x), ch)]
    return sr, x


def _write_pcm16_mono(path, sr, x):
    a = array("h", (max(-32768, min(32767, int(v * 32767))) for v in x))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(a.tobytes())


def resample_to(path, out, sr=CANONICAL_SR):
    src_sr, x = _read_pcm16_mono(path)
    if src_sr == sr:
        _write_pcm16_mono(out, sr, x)
        return "pure"
    if _SS is not None:
        _write_pcm16_mono(out, sr, _SS.resample_linear(x, src_sr, sr))
        return "pure"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
                    "-ar", str(sr), "-ac", "1", str(out)], check=True)
    return "ffmpeg"


def _duration_sec(path):
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


# ---------------------------------------------------- selected library gates
def _probe_tts(device):
    try:
        import TTS.api            # noqa: F401
        import torch
    except Exception as e:
        return False, f"import failed: {type(e).__name__}"
    if device == "cuda" and not torch.cuda.is_available():
        return False, "no cuda device"
    return True, "ok"


def _witness_tts(device):
    """Frozen one-word clip must synthesize with sane duration (memoized)."""
    if device in _WITNESS:
        return _WITNESS[device]
    ok = False
    try:
        if not SPEAKER_WAV.exists():
            ok = False
        else:
            synth = _load_tts(device)["synth"]
            p = TEMP / f"_witness_{device}.wav"
            _synth_chunk(synth, "Witness.", p, seed=7, language="en")
            ok = p.exists() and 0.05 < _duration_sec(p) < 10.0
    except Exception:
        ok = False
    _WITNESS[device] = ok
    return ok


if bp is not None:
    bp.register("tts", "xtts_cuda",
                probe=lambda: _probe_tts("cuda"),
                witness=lambda: _witness_tts("cuda"),
                speedup=lambda size: 4.0)
    bp.register("tts", "xtts_cpu",
                probe=lambda: _probe_tts("cpu"),
                witness=lambda: _witness_tts("cpu"),
                speedup=lambda size: 1.0)


def _choose_backend(size):
    if bp is None:
        ok, _ = _probe_tts("cuda")
        return ("xtts_cuda" if ok else "xtts_cpu"), {"chosen": "probe-only",
                                                      "reason": "backend_policy absent"}
    return bp.choose("tts", size=size)


def _load_tts(device):
    key = (device, str(SPEAKER_WAV))
    if key in _TTS_CACHE:
        return _TTS_CACHE[key]
    from TTS.api import TTS
    import torch
    synth = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(
        "cuda" if device == "xtts_cuda" else "cpu")
    entry = {"synth": synth, "device": device}
    _TTS_CACHE[key] = entry
    return entry


def _synth_chunk(synth, text, path, seed, language):
    synth.tts_to_file(text=text, speaker_wav=str(SPEAKER_WAV),
                      language=language, file_path=str(path),
                      seed=seed, **VOICE_PARAMS)


def _synth_all(chunks, backend, seed, language):
    TEMP.mkdir(parents=True, exist_ok=True)
    synth = _load_tts(backend)["synth"]
    raws = []
    for i, ch in enumerate(chunks):
        p = TEMP / f"chunk_{seed}_{i}.wav"
        _synth_chunk(synth, ch, p, seed=seed + i, language=language)
        raws.append(p)
    return raws


# ------------------------------------------------------------------ the gate
def synthesize(row, out_voice, out_pad, speaker_wav=SPEAKER_WAV):
    t0 = time.time()
    vid = row["video_id"]
    global SPEAKER_WAV
    SPEAKER_WAV = Path(speaker_wav)
    if not SPEAKER_WAV.exists():
        raise RuntimeError(f"missing voice reference: {SPEAKER_WAV}")
    script = normalize_script(row.get("audio_script", ""))
    if not script.strip():
        raise ValueError(f"{vid}: empty audio_script")
    chunks = chunk_script(script)
    seed = seed_for(vid)
    backend, decision = _choose_backend(len(script))

    try:
        raws = _synth_all(chunks, backend, seed, row.get("language", "en"))
    except RuntimeError as e:
        if backend == "xtts_cuda" and ("cuda" in str(e).lower()
                                       or "memory" in str(e).lower()):
            decision = dict(decision, chosen="xtts_cpu",
                            reason=decision.get("reason", "") + f"; OOM degrade: {e}")
            if bp is not None:
                bp.record(decision)
            backend = "xtts_cpu"
            raws = _synth_all(chunks, backend, seed, row.get("language", "en"))
        else:
            raise

    TEMP.mkdir(parents=True, exist_ok=True)
    raw_all = TEMP / f"{vid}_raw_all.wav"
    concat_wavs(raws, raw_all)
    rs = TEMP / f"{vid}_44k.wav"
    rs_backend = resample_to(raw_all, rs)

    out_voice, out_pad = Path(out_voice), Path(out_pad)
    if _SS is not None:
        mrec = _SS.master_wav(rs, out_voice, platform="youtube")
        lufs, mastered, duration = mrec["lufs"], True, mrec["duration"]
    else:
        import shutil
        shutil.copyfile(rs, out_voice)
        duration = _duration_sec(out_voice)
        lufs, mastered = None, False

    pad_seed = seed ^ int(row.get("style_generation") or 0)
    if _SS is not None:
        _SS.create_pad_wav(duration, out_pad, seed=pad_seed)
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", f"anoisesrc=color=pink:duration={duration:.2f}:seed=7",
                        "-af", "lowpass=f=320,volume=0.02", str(out_pad)], check=True)

    entry = {"video_id": vid, "seed": seed, "backend": backend,
             "resample": rs_backend, "chunks": len(chunks),
             "duration": round(duration, 2), "lufs": lufs,
             "mastered": mastered, "pad_seed": pad_seed,
             "voice_params": VOICE_PARAMS,
             "wall_sec": round(time.time() - t0, 1)}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[audio] {vid}: {duration:.1f}s lufs={lufs} backend={backend} "
          f"chunks={len(chunks)} mastered={mastered}")
    return {"duration": duration, "lufs": lufs, "mastered": mastered,
            "backend": backend, "chunks": len(chunks), "seed": seed}


# ------------------------------------------------------------ frozen witness
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    long_script = ("The block accelerates at 9.8 m/s^2. " * 12).strip()
    ch = chunk_script(normalize_script(long_script))
    want("chunk-bounds", all(len(c) <= CHUNK_CHARS for c in ch) and len(ch) > 1,
         str([len(c) for c in ch]))
    want("chunk-coverage", sum(len(c) for c in ch) > 0.5 * len(normalize_script(long_script)))

    import math as _m
    TEMP.mkdir(parents=True, exist_ok=True)
    p1, p2, pc = TEMP / "_t1.wav", TEMP / "_t2.wav", TEMP / "_tc.wav"
    for p, n in ((p1, 100), (p2, 50)):
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
            w.writeframes(array("h", [int(8000 * _m.sin(i / 8)) for i in range(n)]).tobytes())
    d = concat_wavs([p1, p2], pc)
    want("concat-math", abs(d - 150 / 8000) < 1e-9, f"{d}")
    want("concat-frames", _duration_sec(pc) == d)

    want("seed-determinism", seed_for("a1") == seed_for("a1")
         and seed_for("a1") != seed_for("a2"))
    want("params-frozen", VOICE_PARAMS == {"temperature": 0.65,
                                           "repetition_penalty": 3.0})
    try:
        synthesize({"video_id": "empty", "audio_script": "   "},
                   TEMP / "_e.wav", TEMP / "_ep.wav")
        want("guard:empty-script", False)
    except (ValueError, RuntimeError):
        want("guard:empty-script", True)
    return checks


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0
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
