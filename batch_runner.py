"""
batch_runner.py — Subprocess orchestrator & FFmpeg audio/video stitcher.
v2: incremental, oracle-verified, KPI-logging production runner.

Per row:
  1. Pre-flight schema validation (schema_validator)
  2. Row-hash incremental cache (.render_cache.json) — unchanged rows skip
  3. Math Brain oracle gate (build/saemcli): solve() + soul fingerprint (R14/R15)
  4. Voice synthesis (generate_audio, XTTS-v2) with WAV cache keyed by script hash
  5. render_universal.py subprocess (Manim)
  6. FFmpeg stitch (voice + pad + raw) -> atomic .part -> validate -> replace
  7. KPI-rich JSON run log (logs/run_<ts>.json + logs/last_run.json)

Flags (v1 flags kept for CI compatibility, plus):
  --dry-run --csv --only --format --duration --resume --chunk --total-chunks
  --retries --draft --quality --no-voiceover --skip-audio --skip-stitch
  --orientation --log-file
  --force             Ignore row-hash cache; re-render everything selected
  --require-soul      Fail (not warn) when Math Brain soul fingerprint drifts
  --oracle-warn-only  Downgrade oracle solve() mismatches to warnings
  --codex             Append KPI line to THINK.md via tools/think_loop.py
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import wave
from datetime import datetime
from pathlib import Path


def ensure_supported_python() -> None:
    version = sys.version_info
    if not (3, 9) <= (version.major, version.minor) < (3, 13):
        raise SystemExit(
            "Unsupported Python version. This project requires Python 3.9-3.12 "
            "(recommended: 3.12) to match the pinned Manim/TTS stack."
        )


ensure_supported_python()

# ────────────────────────────────────────────────────────────────────────
# Paths and constants
# ────────────────────────────────────────────────────────────────────────
OUTPUT_DIR       = Path("output_shorts")
DEFAULT_CSV_FILE = Path("content_batch.csv")
VOICE_SAMPLE     = Path("saem_voice_sample.wav")
MEDIA_DIR        = Path("media")
TEMP_AUDIO       = Path("temp_audio")
VOICE_CACHE      = TEMP_AUDIO / "cache"
CACHE_FILE       = Path(".render_cache.json")
LOGS_DIR         = Path("logs")
RECEIPTS_DIR     = Path("content") / "receipts"
SAEMCLI          = Path("build") / "saemcli"
RENDERER_VERSION = "ru-v1"          # bump when render_universal visuals change

FFMPEG_PRESET    = "veryfast"
FFMPEG_CRF       = "20"
DEFAULT_FPS      = 30
CLOSING_CARD_SEC = 5.0
MIN_VALID_MP4_MB = 1.0
RENDER_QUALITIES = (
    "draft", "720p", "1080p", "1080p60", "4k", "4k60",
    "l", "m", "h", "h60", "k",
)


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────
def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.strip())


def str_val(row: dict, key: str) -> str:
    v = row.get(key)
    return str(v).strip() if v is not None else ""


def sha_hex(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def find_rendered_file(vid_id: str):
    for p in MEDIA_DIR.rglob(f"{vid_id}.mp4"):
        return p
    return None


def probe_fps(video: Path) -> int:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        num, den = out.split("/")
        return max(1, int(round(float(num) / float(den))))
    except Exception:
        return DEFAULT_FPS


def is_valid_output(path: Path, min_mb: float = MIN_VALID_MP4_MB) -> bool:
    if not path.exists():
        return False
    try:
        return path.stat().st_size >= int(min_mb * 1024 * 1024)
    except OSError:
        return False


def _has_audio_stream(path: Path) -> bool:
    try:
        result = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
            stderr=subprocess.DEVNULL,
        )
        return bool(result.decode().strip())
    except (OSError, subprocess.CalledProcessError):
        return False


def _wav_duration(path) -> float:
    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 0.0


# ────────────────────────────────────────────────────────────────────────
# Incremental cache
# ────────────────────────────────────────────────────────────────────────
def _load_cache() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def row_cache_key(row: dict, args) -> str:
    payload = {k: (row.get(k) or "") for k in sorted(row.keys())}
    payload["__renderer__"] = RENDERER_VERSION
    payload["__draft__"] = bool(args.draft)
    payload["__quality__"] = args.quality or str_val(row, "quality") or "1080p"
    payload["__orientation__"] = (
        args.orientation or str_val(row, "orientation") or "vertical").lower()
    payload["__duration__"] = args.duration
    payload["__skip_audio__"] = bool(args.skip_audio)
    return sha_hex(json.dumps(payload, sort_keys=True))


def voice_cache_key(row: dict) -> str:
    material = (str_val(row, "audio_script") + "|" + str_val(row, "language")
                + "|" + str(VOICE_SAMPLE.stat().st_mtime
                            if VOICE_SAMPLE.exists() else 0))
    return sha_hex(material)[:32]


# ────────────────────────────────────────────────────────────────────────
# Math Brain oracle (R14/R15)
# ────────────────────────────────────────────────────────────────────────
def _saem(*cmd: str):
    r = subprocess.run([str(SAEMCLI), *cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"saemcli {' '.join(cmd)} failed: {r.stderr.strip()}")
    return json.loads(r.stdout)


def _answers_match(got, want) -> bool:
    if isinstance(got, (int, float)) and isinstance(want, (int, float)):
        return abs(float(got) - float(want)) <= 1e-6
    return str(got).strip() == str(want).strip()


def oracle_gate(vid_id: str, warn_only: bool, require_soul: bool) -> str:
    """Returns 'checked' | 'skipped'. Raises on hard failure."""
    rec_path = RECEIPTS_DIR / f"{vid_id}.json"
    if not rec_path.exists():
        return "skipped"
    if not SAEMCLI.exists():
        print(f"[{_ts()}]   [oracle] saemcli not built — receipt unchecked ({vid_id})")
        return "skipped"
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    soul_now = _saem("soul")["soul"]
    if rec.get("soul") != soul_now:
        msg = (f"[oracle] soul drift {vid_id}: receipt {str(rec.get('soul'))[:12]}… "
               f"≠ engine {soul_now[:12]}…")
        if require_soul:
            raise RuntimeError(msg)
        print(f"[{_ts()}]   [WARN] {msg}")
    qid = rec.get("id")
    if qid and _saem("known", qid).get("known"):
        got = _saem("solve", qid, json.dumps(rec.get("params", {})))
        if not _answers_match(got, rec.get("answer")):
            msg = f"[oracle] solve() mismatch {vid_id}: engine={got} receipt={rec.get('answer')}"
            if warn_only:
                print(f"[{_ts()}]   [WARN] {msg}")
            else:
                raise RuntimeError(msg)
    return "checked"


def trust_warn(row: dict, vid_id: str) -> None:
    try:
        from trust_layer import TrustLayer
    except Exception:
        return
    try:
        res = TrustLayer().validate_script(str_val(row, "audio_script"))
        for issue in res.get("physics", {}).get("issues", []):
            print(f"[{_ts()}]   [WARN] [trust] {vid_id}: {issue}")
    except Exception:
        pass


def duration_honesty_warn(row: dict, vid_id: str) -> None:
    words = len(str_val(row, "audio_script").split())
    if not words:
        return
    expected = words / 2.5
    try:
        target = float(str_val(row, "target_duration_sec"))
    except ValueError:
        return
    if target > 0 and abs(target - expected) / max(expected, 1.0) > 0.20:
        print(f"[{_ts()}]   [WARN] [R4] {vid_id}: target_duration_sec={target:.0f}s "
              f"but speech≈{expected:.0f}s ({words} words).")


# ────────────────────────────────────────────────────────────────────────
# FFmpeg mux
# ────────────────────────────────────────────────────────────────────────
def stitch_av(raw_video: Path, voice: Path, pad: Path, out: Path):
    fps = probe_fps(raw_video)
    pad_samples = int(44100 * CLOSING_CARD_SEC)
    filter_complex = (
        "[1:a][2:a]amix=inputs=2:duration=first:dropout_transition=0:"
        "normalize=0[bed];"
    )
    if _has_audio_stream(raw_video):
        filter_complex += (
            "[0:a]volume=0.35[fx];"
            "[bed][fx]amix=inputs=2:duration=first:dropout_transition=0:"
            "normalize=0[amix];"
        )
    else:
        filter_complex += "[bed]anull[amix];"
    filter_complex += (
        f"[amix]apad=pad_len={pad_samples}[apadded];"
        "[apadded]alimiter=limit=0.97[aout];"
        f"[0:v]tpad=stop_mode=clone:stop_duration={CLOSING_CARD_SEC},"
        f"fps={fps}[vout]"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(raw_video), "-i", str(voice), "-i", str(pad),
         "-filter_complex", filter_complex,
         "-map", "[vout]", "-map", "[aout]",
         "-c:v", "libx264", "-preset", FFMPEG_PRESET, "-crf", FFMPEG_CRF,
         "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
         "-pix_fmt", "yuv420p", "-shortest", str(out)],
        check=True,
    )


# ────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        description="Batch production runner for Manim physics videos (v2).")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only", type=str, default="")
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV_FILE)
    p.add_argument("--quality", choices=("", *RENDER_QUALITIES), default="")
    p.add_argument("--format", choices=["short", "lecture", "both"],
                   default="both",
                   help="short=vertical 9:16 (~60s), lecture=horizontal 16:9 (~180s).")
    p.add_argument("--duration", type=float, default=0.0)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--chunk", type=int, default=0)
    p.add_argument("--total-chunks", type=int, default=1)
    p.add_argument("--log-file", type=str, default="")
    p.add_argument("--retries", type=int, default=2)
    p.add_argument("--draft", action="store_true")
    p.add_argument("--no-voiceover", action="store_true")
    p.add_argument("--skip-audio", action="store_true")
    p.add_argument("--skip-stitch", action="store_true")
    p.add_argument("--orientation", default="",
                   choices=["", "vertical", "horizontal"])
    p.add_argument("--force", action="store_true",
                   help="Ignore row-hash cache; re-render selected rows.")
    p.add_argument("--require-soul", action="store_true")
    p.add_argument("--oracle-warn-only", action="store_true")
    p.add_argument("--codex", action="store_true",
                   help="Append KPI line to THINK.md via tools/think_loop.py.")
    return p.parse_args()


# ────────────────────────────────────────────────────────────────────────
# Pre-flight
# ────────────────────────────────────────────────────────────────────────
def preflight_csv(csv_file: Path) -> None:
    try:
        from schema_validator import validate_csv
    except ImportError as e:
        print(f"[WARN] Could not import schema_validator ({e}); skipping pre-flight.")
        return
    print(f"[{_ts()}] [preflight] Validating {csv_file}…")
    if not validate_csv(str(csv_file)):
        print(f"[{_ts()}] [preflight] FATAL — schema validation failed.")
        sys.exit(1)
    print(f"[{_ts()}] [preflight] OK.")


# ────────────────────────────────────────────────────────────────────────
# Single-row pipeline
# ────────────────────────────────────────────────────────────────────────
def _make_silent_audio(row: dict, vid_id: str):
    try:
        duration = float(str_val(row, "target_duration_sec"))
    except ValueError:
        duration = 0.0
    if duration <= 0:
        duration = max(10.0, len(str_val(row, "audio_script").split()) / 2.5)
    sample_rate = 44100
    path = TEMP_AUDIO / f"{vid_id}_voice.wav"
    pad_path = TEMP_AUDIO / f"{vid_id}_pad.wav"
    n_frames = int(duration * sample_rate)
    for out in (path, pad_path):
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sample_rate)
            w.writeframes(b"\x00\x00" * n_frames)
    return str(path), str(pad_path), duration


def _render_one(row: dict, vid_id: str, final_output: Path, args,
                stats: dict):
    voice = pad = None
    to_clean = []
    raw_output = OUTPUT_DIR / f"{vid_id}_raw.mp4"
    part_output = final_output.with_suffix(".part.mp4")
    try:
        # ---- 1. Audio (with WAV cache) --------------------------------
        if args.skip_audio:
            voice, pad, duration = _make_silent_audio(row, vid_id)
            to_clean += [voice, pad]
        else:
            vkey = voice_cache_key(row)
            cvoice = VOICE_CACHE / f"{vkey}_voice.wav"
            cpad = VOICE_CACHE / f"{vkey}_pad.wav"
            if cvoice.exists() and cpad.exists():
                voice, pad = str(cvoice), str(cpad)
                duration = _wav_duration(cvoice)
                stats["voice_cache"] = "hit"
                print(f"[{_ts()}]   [tts] voice cache hit ({vkey[:8]})")
            else:
                from generate_audio import synthesize_audio_for_row
                v0, p0, duration = synthesize_audio_for_row(
                    row, speaker_wav=str(VOICE_SAMPLE),
                    output_dir=str(TEMP_AUDIO))
                VOICE_CACHE.mkdir(parents=True, exist_ok=True)
                shutil.copy2(v0, cvoice); shutil.copy2(p0, cpad)
                to_clean += [v0, p0]
                voice, pad = str(cvoice), str(cpad)
                stats["voice_cache"] = "miss"

        duration = args.duration if args.duration > 0 else duration
        stats["duration_sec"] = round(duration, 2)

        # ---- 2. Render -------------------------------------------------
        ori = (args.orientation or str_val(row, "orientation")
               or "vertical").lower()
        if ori not in ("vertical", "horizontal"):
            ori = "vertical"
        options = [o for o in (str_val(row, f"option_{c}") for c in "abcd") if o]

        cmd = [
            sys.executable, "render_universal.py",
            "--video_id",         vid_id,
            "--header_title",     str_val(row, "header_title"),
            "--tagline",          str_val(row, "tagline"),
            "--question_text",    str_val(row, "question_text"),
            "--correct_answer",   str_val(row, "correct_answer"),
            "--equations_json",   str_val(row, "equations_json") or "[]",
            "--visual_data_json", str_val(row, "visual_data_json") or "[]",
            "--beats_json",       str_val(row, "beats_json") or "[]",
            "--bindings_json",    str_val(row, "bindings_json") or "[]",
            "--concept_type",     str_val(row, "concept_type") or "GENERIC",
            "--quality",          args.quality or str_val(row, "quality") or "1080p",
            "--orientation",      ori,
            "--duration",         f"{duration:.3f}",
            "--options_json",     json.dumps(options),
            "--output",           str(raw_output),
        ]
        fs = str_val(row, "formula_sheet_json")
        if fs:
            cmd += ["--formula_sheet_json", fs]
        mp = str_val(row, "manifest_path")
        if mp:
            cmd += ["--manifest_path", mp]
        if args.draft:
            cmd += ["--draft"]
        cmd += ["--no_voiceover"]
        env = {**os.environ, "SAEM_ORIENTATION": ori}

        print(f"[{_ts()}]   [render_universal] invoking renderer ({ori})…")
        try:
            subprocess.run(cmd, check=True,
                           stdout=sys.stdout, stderr=sys.stderr, env=env)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"render_universal.py exited {e.returncode}. "
                f"Command: {' '.join(cmd)}") from e
        if not raw_output.exists():
            raise FileNotFoundError(f"Renderer did not produce {raw_output}")

        # ---- 3. Stitch (atomic) ----------------------------------------
        if args.skip_stitch:
            raw_output.replace(final_output)
            print(f"[{_ts()}]   → SKIP-STITCH: {final_output}\n")
            return
        print(f"[{_ts()}]   [FFmpeg] Stitching audio/video…")
        stitch_av(raw_output, Path(voice), Path(pad), part_output)
        if not is_valid_output(part_output):
            raise RuntimeError(f"Stitched output too small/corrupt: {part_output}")
        part_output.replace(final_output)
        print(f"[{_ts()}]   → SUCCESS: {final_output}\n")
    finally:
        for p in to_clean:
            if p and Path(p).exists():
                Path(p).unlink(missing_ok=True)
        if raw_output.exists():
            raw_output.unlink(missing_ok=True)
        if part_output.exists():
            part_output.unlink(missing_ok=True)


# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────
def process_batch():
    args = parse_args()
    csv_file = args.csv
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMP_AUDIO.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file '{csv_file}' not found.")
    if not args.dry_run:
        preflight_csv(csv_file)

    if not VOICE_SAMPLE.exists():
        if args.skip_audio or args.dry_run:
            print(f"[{_ts()}] [WARN] {VOICE_SAMPLE} missing — continuing "
                  f"(--skip-audio/--dry-run).")
        else:
            raise FileNotFoundError(
                f"Reference voice sample '{VOICE_SAMPLE}' not found. "
                f"Place it in the repo root, or use --skip-audio.")

    with csv_file.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # FIXED mapping: short = vertical 9:16, lecture = horizontal 16:9
    target_orientation = {"short": "vertical",
                          "lecture": "horizontal"}.get(args.format)
    if target_orientation is not None:
        rows = [r for r in rows
                if (str_val(r, "orientation") or "vertical").lower()
                == target_orientation]
        if not rows:
            print(f"[{_ts()}] [FATAL] --format {args.format} matched no rows.")
            sys.exit(1)

    only_set = {sanitize_filename(x) for x in args.only.split(",") if x.strip()}
    if only_set:
        rows = [r for r in rows
                if sanitize_filename(str_val(r, "video_id")) in only_set]
        if not rows:
            print(f"[{_ts()}] [FATAL] --only matched no rows: {sorted(only_set)}")
            sys.exit(1)

    rows.sort(key=lambda r: str_val(r, "video_id"))
    if args.total_chunks > 1:
        rows = [r for i, r in enumerate(rows)
                if i % args.total_chunks == args.chunk]

    total = len(rows)
    print(f"\n{'=' * 60}")
    print(f"  Production Engine v2 — {total} video(s)")
    if args.total_chunks > 1:
        print(f"  Chunk {args.chunk + 1}/{args.total_chunks}")
    print(f"{'=' * 60}\n")

    cache = _load_cache()
    runlog: list[dict] = []
    t_start = time.time()
    n_ok = n_fail = n_skip = n_cached = 0

    try:
        for idx, row in enumerate(rows, 1):
            vid_id = sanitize_filename(str_val(row, "video_id")) or f"row_{idx}"
            concept = str_val(row, "concept_type").upper() or "GENERIC"
            final_output = OUTPUT_DIR / f"{vid_id}_final.mp4"
            entry = {"video_id": vid_id, "concept_type": concept,
                     "orientation": (args.orientation
                                     or str_val(row, "orientation")
                                     or "vertical").lower(),
                     "words": len(str_val(row, "audio_script").split())}
            t_row = time.time()

            if args.resume and is_valid_output(final_output):
                print(f"[{_ts()}] [{idx}/{total}] SKIP (Resume)  {vid_id}")
                entry.update(status="skipped"); runlog.append(entry)
                n_skip += 1; continue

            key = row_cache_key(row, args)
            if (not args.force) and cache.get(vid_id) == key \
                    and is_valid_output(final_output):
                print(f"[{_ts()}] [{idx}/{total}] SKIP (Cached)   {vid_id}")
                entry.update(status="cached"); runlog.append(entry)
                n_cached += 1; continue

            if args.dry_run:
                print(f"[{_ts()}] [{idx}/{total}] DRY RUN  {vid_id}  ({concept})")
                duration_honesty_warn(row, vid_id)
                entry.update(status="dry_run"); runlog.append(entry)
                continue

            print(f"[{_ts()}] [{idx}/{total}] BUILD {vid_id}  ({concept})")
            duration_honesty_warn(row, vid_id)
            trust_warn(row, vid_id)

            last_err = None
            for attempt in range(1, args.retries + 2):
                stats: dict = {}
                try:
                    oracle_gate(vid_id, args.oracle_warn_only, args.require_soul)
                    entry["oracle"] = "checked"
                    _render_one(row, vid_id, final_output, args, stats)
                    entry.update(stats)
                    cache[vid_id] = key
                    _save_cache(cache)
                    entry.update(status="ok", attempt=attempt,
                                 wall_sec=round(time.time() - t_row, 1))
                    runlog.append(entry)
                    n_ok += 1
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    print(f"[{_ts()}]   ! Attempt {attempt} failed: {e}")
                    if attempt <= args.retries:
                        backoff = 2 ** attempt
                        print(f"[{_ts()}]   ... Retrying in {backoff}s")
                        time.sleep(backoff)
            if last_err is not None:
                entry.update(status="error",
                             error=f"{type(last_err).__name__}: {last_err}",
                             wall_sec=round(time.time() - t_row, 1))
                runlog.append(entry)
                n_fail += 1
                traceback.print_exc()
    except KeyboardInterrupt:
        print(f"\n[{_ts()}] [WARN] Interrupted — writing partial run log.")

    elapsed = time.time() - t_start
    rendered = max(n_ok, 1)
    min_per_video = round(elapsed / 60.0 / rendered, 2)
    print(f"\n{'=' * 60}")
    print(f"  Done in {elapsed/60:.1f} min  —  {n_ok} ok, {n_fail} failed, "
          f"{n_skip} resumed, {n_cached} cached")
    print(f"{'=' * 60}\n")
    print(f"[kpi] wall={elapsed/60:.1f}m ok={n_ok} fail={n_fail} "
          f"skip={n_skip} cache={n_cached} min_per_video={min_per_video}")

    log_obj = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "csv": str(csv_file),
        "elapsed_sec": round(elapsed, 1),
        "summary": {"ok": n_ok, "failed": n_fail,
                    "skipped": n_skip, "cached": n_cached,
                    "min_per_video": min_per_video},
        "entries": runlog,
    }
    paths = [LOGS_DIR / "last_run.json",
             LOGS_DIR / f"run_{datetime.now():%Y%m%d_%H%M%S}.json"]
    if args.log_file:
        paths.append(Path(args.log_file))
    for lp in paths:
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text(json.dumps(log_obj, indent=2), encoding="utf-8")

    if args.codex and Path("tools/think_loop.py").exists():
        subprocess.run([sys.executable, "tools/think_loop.py",
                        f"local-{datetime.now():%H%M%S}",
                        f"gate={'success' if n_fail == 0 else 'failure'}",
                        str(LOGS_DIR / 'last_run.json')], check=False)

    if TEMP_AUDIO.exists() and not any(TEMP_AUDIO.iterdir()):
        TEMP_AUDIO.rmdir()
    if n_fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    process_batch()
