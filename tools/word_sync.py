#!/usr/bin/env python3
"""word_sync.py — gen-3 beat alignment: measured words, priced degradation.

Layering (one ruler, gated devices):
  * OWN TOOL (pure, witnessed): FOCUS_LEXICON, extract_focus_word,
    find_word_time, equal_slice_times, align_beats_with_timings — the
    alignment mathematics, frozen and machine-checked against a fixture
  * SELECTED LIBRARIES (backend_policy kind="align"): stable_whisper then
    whisper_timestamped — measurement devices only; absence degrades to the
    equal-slice ruler with the reason receipted, never to a guess
  * TRUTH (A0): audio duration comes from ffprobe or the caller's
    known_duration; legacy's "180.0 on failure" guess is gone — unknown
    duration raises inside the ruler and degrades explicitly outside

Receipt (A5): align_beats_with_receipt -> (beats, receipt) with backend,
duration_source, aligned/equal/unaligned counts; one ledger line per call.

Usage:
    from tools.word_sync import align_beats          # legacy-compatible
    python3 tools/word_sync.py <audio.wav> <beats.json> [--script TEXT]
    python3 tools/word_sync.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

try:
    from tools import backend_policy as bp
except Exception:
    bp = None
try:
    from tools.ledger import append as _ledger
except Exception:
    _ledger = None

# SPEC-as-data: focus-id prefix -> spoken word (readable by authoring/growth)
FOCUS_LEXICON = {
    "mass": "mass", "eq": "equation", "vector": "vector", "wave": "wave",
    "particle": "particle", "field": "field", "energy": "energy",
    "force": "force", "graph": "graph", "angle": "angle",
    "spring": "spring", "orbit": "orbit",
}


# ------------------------------------------------------------- pure ruler
def extract_focus_word(beat, script=None):
    focus = beat.get("focus")
    if not focus:
        return None
    f = str(focus).lower()
    for pref, word in FOCUS_LEXICON.items():
        if f.startswith(pref):
            return word
    parts = re.sub(r"[_\d]", " ", f).split()
    return parts[0].lower() if parts else None


def find_word_time(target, word_timings):
    t = (target or "").lower()
    if not t:
        return None
    for wt in word_timings:
        if wt["word"] == t:
            return wt["start"]
    for wt in word_timings:
        if t in wt["word"]:
            return wt["start"]
    for wt in word_timings:
        if wt["word"] in t:
            return wt["start"]
    return None


def equal_slice_times(n_beats, duration):
    if duration is None:
        raise ValueError("duration unknown; the ruler refuses to guess (A0)")
    if n_beats == 0:
        return []
    if n_beats == 1:
        return [duration / 2]
    step = duration / n_beats
    return [i * step for i in range(n_beats)]


def align_beats_with_timings(beats, word_timings, script=None):
    """Pure: map each beat's focus word to its measured start time."""
    out = []
    for beat in beats:
        b = dict(beat)
        word = extract_focus_word(b, script)
        t = find_word_time(word, word_timings) if word else None
        if t is not None:
            b["time"] = t
            b["aligned"] = True
        else:
            b["aligned"] = False
        out.append(b)
    return out


# ------------------------------------------------- measurement (selected)
def get_audio_duration(audio_path):
    """Measured duration or None. Never a default guess."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(audio_path)],
            capture_output=True, text=True, check=True)
        return float(r.stdout.strip())
    except Exception:
        return None


def _timings_stable(path):
    import stable_whisper
    model = stable_whisper.load_model("base")
    res = model.transcribe(str(path))
    return [{"word": w.word.strip().lower(), "start": w.start, "end": w.end}
            for seg in res.segments for w in seg.words]


def _timings_wts(path):
    import whisper_timestamped as whisper
    model = whisper.load_model("base")
    res = whisper.transcribe(model, str(path))
    return [{"word": w["text"].strip().lower(), "start": w["start"],
             "end": w["end"]} for seg in res["segments"] for w in seg["words"]]


def _probe_stable():
    try:
        import stable_whisper            # noqa: F401
        return True, "ok"
    except Exception as e:
        return False, f"import: {type(e).__name__}"


def _probe_wts():
    try:
        import whisper_timestamped       # noqa: F401
        return True, "ok"
    except Exception as e:
        return False, f"import: {type(e).__name__}"


_FIXTURE_TIMINGS = [
    {"word": "consider", "start": 0.0, "end": 0.4},
    {"word": "a", "start": 0.4, "end": 0.5},
    {"word": "mass", "start": 1.5, "end": 1.9},
    {"word": "falling", "start": 2.4, "end": 2.9},
]


def _witness_ruler():
    b = align_beats_with_timings([{"type": "hook", "focus": "mass_1"}],
                                 _FIXTURE_TIMINGS)
    return bool(b) and b[0]["aligned"] and abs(b[0]["time"] - 1.5) < 1e-9


if bp is not None:
    bp.register("align", bp.OWN_TOOL,
                probe=lambda: (True, "own tool, stdlib only"),
                witness=_witness_ruler, speedup=lambda size: 1.0)
    bp.register("align", "stable_whisper", probe=_probe_stable,
                witness=_witness_ruler, speedup=lambda size: 1.0)
    bp.register("align", "whisper_timestamped", probe=_probe_wts,
                witness=_witness_ruler, speedup=lambda size: 0.9)


def get_word_timings_with_backend(audio_path):
    order = ["stable_whisper", "whisper_timestamped"]
    if bp is not None:
        chosen, _ = bp.choose("align", size=1)
        if chosen in order:
            order = [chosen] + [o for o in order if o != chosen]
    reasons = []
    for name in order:
        try:
            if name == "stable_whisper":
                return _timings_stable(audio_path), name
            return _timings_wts(audio_path), name
        except Exception as e:
            reasons.append(f"{name}: {type(e).__name__}")
    return [], "none:" + ";".join(reasons) if reasons else "none"


def get_word_timings(audio_path, script=None):
    """Legacy-compatible."""
    return get_word_timings_with_backend(audio_path)[0]


# ------------------------------------------------------------ orchestrate
def align_beats_with_receipt(audio_path, beats, script="",
                             known_duration=None, fallback_to_equal=True):
    timings, backend = get_word_timings_with_backend(audio_path)
    measured = get_audio_duration(audio_path)
    if measured is not None:
        duration, dsrc = measured, "ffprobe"
    elif known_duration is not None:
        duration, dsrc = float(known_duration), "job"
    else:
        duration, dsrc = None, "none"
    aligned = align_beats_with_timings(beats, timings, script)
    un = [b for b in aligned if not b.get("aligned")]
    n_equal = 0
    if un and fallback_to_equal and duration is not None:
        times = equal_slice_times(len(un), duration)
        for b, t in zip(un, times):
            b["time"] = t
            b["aligned"] = False
            b["equal_slice"] = True
        n_equal = len(un)
    receipt = {"gate": "word_sync", "schema_version": 3,
               "backend": backend, "duration_source": dsrc,
               "duration": duration,
               "n_aligned": sum(1 for b in aligned if b.get("aligned")),
               "n_equal": n_equal,
               "n_unaligned": len(un) - n_equal}
    if _ledger is not None:
        try:
            _ledger(receipt)
        except Exception:
            pass
    return aligned, receipt


def align_beats(audio_path, beats, script="", fallback_to_equal=True):
    """Legacy-compatible entry point."""
    return align_beats_with_receipt(audio_path, beats, script,
                                    fallback_to_equal=fallback_to_equal)[0]


# ---------------------------------------------------------------- witness
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    want("lexicon-data", FOCUS_LEXICON["eq"] == "equation"
         and extract_focus_word({"focus": "mass_1"}) == "mass")
    want("focus-generic",
         extract_focus_word({"focus": "theta_marker"}) == "theta")
    t = find_word_time("mass", _FIXTURE_TIMINGS)
    want("find-exact", t == 1.5)
    want("find-partial", find_word_time("fall", _FIXTURE_TIMINGS) == 2.4)
    want("find-miss", find_word_time("quark", _FIXTURE_TIMINGS) is None)
    e = equal_slice_times(4, 8.0)
    want("equal-math", e == [0.0, 2.0, 4.0, 6.0])
    want("equal-single", equal_slice_times(1, 6.0) == [3.0])
    try:
        equal_slice_times(2, None)
        want("equal-refuses-guess", False)
    except ValueError:
        want("equal-refuses-guess", True)
    a = align_beats_with_timings(
        [{"type": "law", "focus": "mass_1"}, {"type": "cta", "focus": "zz"}],
        _FIXTURE_TIMINGS)
    want("ruler-align", a[0]["aligned"] and a[0]["time"] == 1.5
         and not a[1]["aligned"])
    a2 = align_beats_with_timings(
        [{"type": "law", "focus": "mass_1"}], _FIXTURE_TIMINGS)
    want("determinism", a2[0]["time"] == a[0]["time"])
    want("duration-missing-none",
         get_audio_duration(Path("/nonexistent/x.wav")) is None)
    if bp is not None:
        want("witness-ruler", _witness_ruler())
    return checks


def main():
    ap = argparse.ArgumentParser(description="word-level beat sync (gen-3)")
    ap.add_argument("audio", nargs="?")
    ap.add_argument("beats", nargs="?")
    ap.add_argument("--script", default="")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0
    if not a.audio or not a.beats:
        print("usage: word_sync.py <audio.wav> <beats.json> [--script S]")
        return 1
    beats = json.loads(Path(a.beats).read_text(encoding="utf-8"))
    aligned, receipt = align_beats_with_receipt(
        a.audio, beats, a.script, known_duration=a.duration)
    for b in aligned:
        tag = "aligned" if b.get("aligned") else (
            "equal" if b.get("equal_slice") else "UNALIGNED")
        print(f"  {b.get('type', '?'):<16} t={b.get('time', -1):6.2f}s [{tag}]")
    if a.json:
        print(json.dumps({"receipt": receipt, "beats": aligned},
                         ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
