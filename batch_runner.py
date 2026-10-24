#!/usr/bin/env python3
"""Orchestrator with gates. Reads one CSV, runs every row through:

    schema gate -> physics oracle gate -> audio gate (mastered) ->
    render gate (manim) -> visual QA gate -> stitch -> ledger

Every outcome is appended to logs/render_ledger.jsonl (tools.ledger), the
machine cousin of THINK.md §3. Nothing ships that a gate rejected when the
matching --require-* flag is set; without the flag the gate warns only.

Usage:
    python3 batch_runner.py [--csv content_batch.csv] [--only ID[,ID...]]
        [--chunk N --total-chunks M] [--draft] [--retries K] [--dry-run]
        [--require-oracle] [--require-qa] [--format short|lecture|all]
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import schema_validator
import generate_audio
from tools.ledger import append as ledger_append
from tools.physics_oracle import validate_row as oracle_validate
from tools.visual_qa import check_video, measure_lufs

OUTPUT = ROOT / "output_shorts"
MEDIA = ROOT / "media"
JOBS = ROOT / "temp_jobs"
REPORTS = ROOT / "logs" / "reports"


def log(msg):
    print(msg, flush=True)


def parse_args():
    p = argparse.ArgumentParser(description="Saem batch runner with gates")
    p.add_argument("--csv", default="content_batch.csv")
    p.add_argument("--only", default="")
    p.add_argument("--chunk", type=int, default=0)
    p.add_argument("--total-chunks", type=int, default=1)
    p.add_argument("--draft", action="store_true")
    p.add_argument("--retries", type=int, default=1)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--require-oracle", action="store_true")
    p.add_argument("--require-qa", action="store_true")
    p.add_argument("--format", choices=["short", "lecture", "all"], default="all")
    return p.parse_args()


def select_rows(args):
    header, rows = schema_validator.read_rows(ROOT / args.csv if not
                                              Path(args.csv).is_absolute()
                                              else args.csv)
    if args.only:
        wanted = set(args.only.split(","))
        rows = [r for r in rows if r.get("video_id") in wanted]
    if args.total_chunks > 1:
        rows = rows[args.chunk::args.total_chunks]
    if args.format != "all":
        def is_short(r):
            try:
                return float(r.get("target_duration_sec", 180)) <= 90
            except ValueError:
                return False
        rows = [r for r in rows if (is_short(r) if args.format == "short"
                                    else not is_short(r))]
    return header, rows


def render_row(row, audio, args):
    """Run manim on the row's job file. Returns (mp4_path, report)."""
    JOBS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    job_path = JOBS / f"{row['video_id']}.json"
    report_path = REPORTS / f"{row['video_id']}.json"
    orient = row.get("orientation", "vertical")
    if args.draft:
        res, fps = ("854", "480", "15") if orient == "horizontal" else ("480", "854", "15")
    else:
        res, fps = ("1920", "1080", "30") if orient == "horizontal" else ("1080", "1920", "30")
    job = {
        "row": row,
        "audio_voice": str(audio["voice"]),
        "audio_pad": str(audio["pad"]),
        "audio_duration": audio["duration"],
        "orientation": orient,
        "draft": args.draft,
        "report_path": str(report_path),
    }
    job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

    scene = "Universal3DScene" if row.get("concept_type", "").startswith("3D") \
        else "UniversalPhysicsScene"
    env = dict(os.environ, SAEM_JOB=str(job_path))
    cmd = [sys.executable, "-m", "manim",
           "--media_dir", str(MEDIA),
           "--resolution", f"{res[0] if isinstance(res, tuple) else res},{res[1] if isinstance(res, tuple) else res[1]}",
           "--fps", fps, "--disable_caching",
           "render_universal.py", scene]
    proc = subprocess.run(cmd, cwd=ROOT, env=env,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.splitlines()[-15:])
        raise RuntimeError(f"manim failed:\n{tail}")

    cands = sorted(MEDIA.rglob(f"{scene}.mp4"), key=lambda p: p.stat().st_mtime)
    if not cands:
        raise RuntimeError("manim produced no mp4")
    report = {}
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    return cands[-1], report


def stitch(row, silent_mp4, audio, out_mp4):
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(silent_mp4),
        "-i", str(audio["voice"]),
        "-i", str(audio["pad"]),
        "-filter_complex",
        "[0:v]tpad=stop_mode=clone:stop_duration=3[v];"
        "[1:a][2:a]amix=inputs=2:duration=first:normalize=0[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{audio['duration'] + 7:.2f}",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True)


def process_row(row, args):
    vid = row.get("video_id", "<no id>")
    t0 = time.time()
    entry = {"video_id": vid, "status": "error"}
    try:
        # Gate 1: physics oracle
        ok, violations = oracle_validate(row)
        if not ok:
            log(f"[oracle] {vid}: {len(violations)} violation(s)")
            for v in violations:
                log(f"  - {v}")
            if args.require_oracle:
                entry.update(error="oracle", failed_primitives=violations)
                return entry
        # Gate 2: audio (mastered)
        voice = generate_audio.TEMP / f"{vid}_voice.wav"
        pad = generate_audio.TEMP / f"{vid}_pad.wav"
        audio_info = generate_audio.synthesize(row, voice, pad)
        audio = {"voice": voice, "pad": pad, "duration": audio_info["duration"]}
        log(f"[audio] {vid}: {audio_info['duration']:.1f}s "
            f"lufs={audio_info['lufs']} mastered={audio_info['mastered']}")
        if args.dry_run:
            entry.update(status="dry-run", duration_sec=audio_info["duration"],
                         audio_lufs=audio_info["lufs"])
            return entry
        # Gate 3: render
        silent_mp4, report = render_row(row, audio, args)
        # Gate 4: visual QA
        final = OUTPUT / f"{vid}_final.mp4"
        stitch(row, silent_mp4, audio, final)
        qa_ok, qa_issues = check_video(final)
        if not qa_ok:
            log(f"[qa] {vid}: {qa_issues}")
            if args.require_qa:
                entry.update(error="visual_qa", issues=qa_issues)
                return entry
        entry.update(
            status="ok",
            duration_sec=audio_info["duration"],
            audio_lufs=audio_info["lufs"],
            mastered=audio_info["mastered"],
            failed_primitives=report.get("failed_primitives", []),
            primitive_count=report.get("primitive_count", 0),
            visual_qa_passed=qa_ok,
            wall_sec=round(time.time() - t0, 1),
        )
        log(f"[ok] {vid} -> {final}")
    except Exception as e:
        entry.update(error=str(e)[:300], wall_sec=round(time.time() - t0, 1))
        log(f"[error] {vid}: {e}")
    return entry


def main():
    args = parse_args()
    header, rows = select_rows(args)
    if not rows:
        log("[runner] no rows selected")
        return 0
    log(f"[runner] {len(rows)} row(s); draft={args.draft} "
        f"require_oracle={args.require_oracle} require_qa={args.require_qa}")

    results = []
    for row in rows:
        attempt = 0
        while True:
            entry = process_row(row, args)
            if entry.get("status") == "ok" or attempt >= args.retries:
                break
            attempt += 1
            log(f"[runner] retry {attempt} for {row.get('video_id')}")
        ledger_append(entry)
        results.append(entry)

    ok = sum(1 for r in results if r.get("status") == "ok")
    log(f"[runner] done: {ok}/{len(results)} ok")
    for r in results:
        if r.get("status") != "ok":
            log(f"  failed: {r.get('video_id')}: {r.get('error', r.get('status'))}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
