#!/usr/bin/env python3
"""batch_runner.py — factory orchestrator with a gate ladder (gen-3).

Per row, in order (nothing ships that a promoted gate rejected):
  Gate 0 schema  : schema_validator.validate_row      (--require-schema)
  Gate 1 oracle  : tools.physics_oracle               (--require-oracle)
  Gate 2 core    : saem_cli body id == tree id        (--require-core, fail closed)
  Gate 3 audio   : generate_audio.synthesize (mastered, LUFS recorded)
  Gate 4 render  : manim render_universal + SAEM_JOB + SAEM_SOURCE_ID
  Gate 5 QA      : tools.visual_qa.check_video        (--require-qa)

Ledger (A5, append-only): every outcome -> logs/render_ledger.jsonl with
schema_version 3 and full provenance (core_source_id, narration_hash,
engines_used, routing_parity, style generation, per-gate verdicts).

Style memory (teacher rule: never the same lesson twice):
  successful genomes are echoed to logs/style_ledger.jsonl (the novelty gate's
  memory) and QA evidence updates logs/style_beliefs.json via style_belief
  (Bernoulli log-odds; promotion only at moral certainty, exploration on the
  least-certain gene).

Deterministic verdicts are never retried; only crashes are.

Usage:
    python3 batch_runner.py [--csv content_batch.csv] [--only ID[,ID...]]
        [--chunk N --total-chunks M] [--draft] [--retries K] [--dry-run]
        [--require-schema] [--require-oracle] [--require-core]
        [--require-qa] [--require-routes] [--require-novelty]
        [--format short|lecture|all]
"""
import argparse
import json
import os
import shutil
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
from tools.visual_qa import check_video

OUTPUT = ROOT / "output_shorts"
MEDIA = ROOT / "media"
JOBS = ROOT / "temp_jobs"
REPORTS = ROOT / "logs" / "reports"
STYLE_LEDGER = ROOT / "logs" / "style_ledger.jsonl"
BELIEFS = ROOT / "logs" / "style_beliefs.json"
SCHEMA_VERSION = 3

_BELIEFS = {}


def log(msg):
    print(msg, flush=True)


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def tree_id():
    return _read(ROOT / "build" / "source_id.txt")


def body_id():
    exe = ROOT / "build" / ("saem_cli.exe" if os.name == "nt" else "saem_cli")
    if not exe.exists():
        return ""
    try:
        r = subprocess.run([str(exe), "--source-id"], capture_output=True,
                           text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def parse_args():
    p = argparse.ArgumentParser(description="Saem batch runner with gates")
    p.add_argument("--csv", default="content_batch.csv")
    p.add_argument("--only", default="")
    p.add_argument("--chunk", type=int, default=0)
    p.add_argument("--total-chunks", type=int, default=1)
    p.add_argument("--draft", action="store_true")
    p.add_argument("--retries", type=int, default=1)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--require-schema", action="store_true")
    p.add_argument("--require-oracle", action="store_true")
    p.add_argument("--require-core", action="store_true")
    p.add_argument("--require-qa", action="store_true")
    p.add_argument("--require-routes", action="store_true")
    p.add_argument("--require-novelty", action="store_true")
    p.add_argument("--format", choices=["short", "lecture", "all"], default="all")
    return p.parse_args()


def select_rows(args):
    csv_path = ROOT / args.csv if not Path(args.csv).is_absolute() else Path(args.csv)
    header, rows = schema_validator.read_rows(csv_path)
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


def render_row(row, audio, args, source_id):
    """Run manim on the row's job file. Returns (mp4_path, report)."""
    JOBS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    job_path = JOBS / f"{row['video_id']}.json"
    report_path = REPORTS / f"{row['video_id']}.json"
    orient = row.get("orientation", "vertical")
    if args.draft:
        res, fps = (("854", "480"), "15") if orient == "horizontal" \
            else (("480", "854"), "15")
    else:
        res, fps = (("1920", "1080"), "30") if orient == "horizontal" \
            else (("1080", "1920"), "30")
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
    if source_id:
        env["SAEM_SOURCE_ID"] = source_id      # provenance receipt (A5)
    cmd = [sys.executable, "-m", "manim",
           "--media_dir", str(MEDIA),
           "--resolution", f"{res[0]},{res[1]}",
           "--fps", fps, "--disable_caching",
           "render_universal.py", scene]
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.splitlines()[-15:])
        raise RuntimeError(f"manim failed:\n{tail}")
    cands = sorted(MEDIA.rglob(f"{scene}.mp4"), key=lambda p: p.stat().st_mtime)
    if not cands:
        raise RuntimeError("manim produced no mp4")
    report = {}
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            report = {}
    return cands[-1], report


def stitch(row, silent_mp4, audio, out_mp4):
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH (selected stitch tool)")
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


def _remember_style(report, vid, qa_ok):
    """Echo genome to novelty memory; feed QA evidence to style beliefs."""
    style = (report or {}).get("style") or {}
    genome = style.get("genome")
    if not genome:
        return None
    try:
        STYLE_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(STYLE_LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps({"video_id": vid, "genome": genome,
                                "generation": style.get("generation"),
                                "qa_ok": qa_ok, "ts": time.time()},
                               ensure_ascii=False) + "\n")
    except Exception as e:
        log(f"[style-warn] ledger echo failed: {e}")
    global _BELIEFS
    try:
        from tools import style_belief as sb
        if not _BELIEFS:
            _BELIEFS = sb.load(BELIEFS)
        for gene in ("palette_family", "layout_family", "motion_family",
                     "voice", "entrance"):
            _BELIEFS = sb.observe(_BELIEFS, f"{gene}={genome.get(gene)}", qa_ok)
    except Exception:
        pass
    return style.get("generation")


def process_row(row, header, args, core):
    vid = row.get("video_id", "<no id>")
    t0 = time.time()
    entry = {"schema_version": SCHEMA_VERSION, "video_id": vid,
             "status": "error", "gates": [], "retryable": False}

    def gate(name, ok, promoted, detail=""):
        entry["gates"].append({"gate": name, "ok": bool(ok),
                               "promoted": bool(promoted),
                               "detail": detail[:300]})
        return ok or not promoted

    try:
        # Gate 0: schema
        errs, warns = schema_validator.validate_row(row, header,
                                                    require_routes=args.require_routes)
        for w in warns[:5]:
            log(f"[schema-warn] {vid}: {w}")
        if errs:
            for e in errs[:5]:
                log(f"[schema] {vid}: {e}")
            if not gate("schema", False, args.require_schema, "; ".join(errs)):
                entry.update(status="rejected", error="schema")
                return entry
        else:
            gate("schema", True, args.require_schema)

        # Gate 1: physics oracle
        ok, violations = oracle_validate(row)
        if not ok:
            for v in violations[:5]:
                log(f"[oracle] {vid}: {v}")
            if not gate("oracle", False, args.require_oracle, "; ".join(violations)):
                entry.update(status="rejected", error="oracle",
                             failed_primitives=violations)
                return entry
        else:
            gate("oracle", True, args.require_oracle)

        # Gate 2: core body vs tree (stale binary = fail closed)
        if core["mismatch"]:
            detail = f"body={core['body'][:12]} tree={core['tree'][:12]}"
            if not gate("core", False, args.require_core, detail):
                entry.update(status="rejected", error="stale-core")
                return entry
        else:
            gate("core", True, args.require_core, f"id={core['body'][:12]}")

        # Gate 3: audio (mastered)
        voice = generate_audio.TEMP / f"{vid}_voice.wav"
        pad = generate_audio.TEMP / f"{vid}_pad.wav"
        info = generate_audio.synthesize(row, voice, pad)
        audio = {"voice": voice, "pad": pad, "duration": info["duration"]}
        log(f"[audio] {vid}: {info['duration']:.1f}s lufs={info['lufs']} "
            f"mastered={info['mastered']}")
        gate("audio", True, False, f"lufs={info['lufs']}")
        if args.dry_run:
            entry.update(status="dry-run", duration_sec=info["duration"],
                         audio_lufs=info["lufs"])
            return entry

        # Gate 4: render (carries SAEM_SOURCE_ID into the report)
        silent_mp4, report = render_row(row, audio, args, core["body"])
        gate("render", True, False,
             f"primitives={report.get('primitive_count', 0)} "
             f"failed={len(report.get('failed_primitives', []))}")
        if report.get("failed_primitives"):
            log(f"[render-warn] {vid}: degraded primitives "
                f"{report['failed_primitives'][:4]}")

        # Gate 5: stitch + visual QA
        final = OUTPUT / f"{vid}_final.mp4"
        stitch(row, silent_mp4, audio, final)
        qa_ok, qa_issues = check_video(final)
        if not qa_ok:
            log(f"[qa] {vid}: {qa_issues}")
        if not gate("qa", qa_ok, args.require_qa, "; ".join(map(str, qa_issues))):
            entry.update(status="rejected", error="visual_qa", issues=qa_issues)
            return entry

        generation = _remember_style(report, vid, qa_ok)
        entry.update(
            status="ok",
            duration_sec=info["duration"],
            audio_lufs=info["lufs"],
            mastered=info["mastered"],
            failed_primitives=report.get("failed_primitives", []),
            primitive_count=report.get("primitive_count", 0),
            engines_used=report.get("engines_used", []),
            routing_parity=report.get("routing_parity", {}),
            core_source_id=report.get("core_source_id") or core["body"] or None,
            narration_hash=report.get("narration_hash"),
            style_generation=generation,
            visual_qa_passed=qa_ok,
            wall_sec=round(time.time() - t0, 1),
        )
        log(f"[ok] {vid} -> {final}")
    except Exception as e:
        entry.update(error=str(e)[:300], wall_sec=round(time.time() - t0, 1),
                     retryable=True)          # only crashes are retryable
        log(f"[error] {vid}: {e}")
    return entry


def main():
    args = parse_args()
    header, rows = select_rows(args)
    if not rows:
        log("[runner] no rows selected")
        return 0

    # batch-level novelty gate before spending a single TTS second
    for promote, msg in schema_validator.detect_clones(rows, args.require_novelty):
        log(("[clone-error] " if promote else "[clone-warn] ") + msg)
        if promote:
            return 1

    tree, body = tree_id(), body_id()
    mismatch = bool(tree) and body != tree
    core = {"tree": tree, "body": body, "mismatch": mismatch}
    if mismatch:
        msg = f"[core] STALE binary body={body[:12]} != tree={tree[:12]}"
        if args.require_core:
            log(msg + " ; --require-core set: aborting")
            return 1
        log(msg + " ; warning only (add --require-core to fail closed)")
    elif body:
        log(f"[core] body id ok {body[:12]}")
    else:
        log("[core] no built core found; reports carry core_source_id=null")

    log(f"[runner] {len(rows)} row(s); draft={args.draft} "
        f"require: schema={args.require_schema} oracle={args.require_oracle} "
        f"core={args.require_core} qa={args.require_qa} "
        f"routes={args.require_routes} novelty={args.require_novelty}")

    results = []
    for row in rows:
        attempt = 0
        while True:
            entry = process_row(row, header, args, core)
            if not entry.get("retryable") or attempt >= args.retries:
                break
            attempt += 1
            log(f"[runner] retry {attempt} for {row.get('video_id')}")
        ledger_append(entry)
        results.append(entry)

    if _BELIEFS:
        try:
            from tools import style_belief as sb
            sb.save(BELIEFS, _BELIEFS)
            expl = sb.next_to_explore(_BELIEFS)
            if expl:
                log(f"[style] least-certain gene (mutate next batch): {expl}")
        except Exception:
            pass

    ok = sum(1 for r in results if r.get("status") == "ok")
    dry = sum(1 for r in results if r.get("status") == "dry-run")
    rej = sum(1 for r in results if r.get("status") == "rejected")
    log(f"[runner] done: {ok} ok, {dry} dry-run, {rej} rejected, "
        f"{len(results) - ok - dry - rej} crashed")
    for r in results:
        if r.get("status") not in ("ok", "dry-run"):
            log(f"  failed: {r.get('video_id')}: {r.get('error', r.get('status'))}")
    return 0 if (ok + dry) == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
