#!/usr/bin/env python3
"""Factory input compiler: the Python input method for the workflow.

Layers (CSV_AUTHORING §12):
    workflow knobs -> this file -> CSV (fluid) -> gates (frozen code)

Modes (env FACTORY_MODE):
    csv         use FACTORY_CSV as-is (old behaviour)
    run         run FACTORY_GENERATOR_CMD first, then use its CSV
    synthesize  build rows here from topics/orientation/duration/seed

Always:
    - retunes target_duration_sec to the narration word count when
      FACTORY_AUTOFIX_DURATION=true (writer = csv.DictWriter, rule 1)
    - re-validates every row with schema_validator before emitting
    - writes reports/factory_manifest.json + GITHUB_OUTPUT csv=<path>
"""
import csv
import json
import math
import os
import random
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import schema_validator as sv

WPS_LO, WPS_HI = sv.WORDS_PER_SEC          # (1.87, 3.0)
RATE = 2.4                                  # comfortable middle of the band

TOPIC_PRIMS = {
    "kinematics": [{"type": "projectile_motion", "v0": 20, "angle": 45}],
    "emwave": [{"type": "electromagnetic_wave"}],
    "twoslit": [{"type": "two_path_interference"}],
    "ratchet": [{"type": "driven_oscillator"}],
    "betatron": [{"type": "orbit"}],
    "masers": [{"type": "energy_bar", "fraction": 0.8}],
}
PHRASES = [
    "watch how the idea moves from picture to equation",
    "feynman asks what actually happens step by step",
    "the picture carries the physics, the numbers only confirm it",
    "notice the symmetry, then notice what breaks it",
    "we build the scene slowly so the eye can follow the cause",
    "each arrow is a claim, each claim is computed never guessed",
    "strip the algebra and the geometry still tells the story",
    "this is the whole lesson in one moving diagram",
]


def env(name, dflt=""):
    return os.environ.get(name, dflt)


def retune_duration(row):
    words = len((row.get("audio_script") or "").split())
    if not words:
        return row, None
    lo, hi = words / WPS_HI, words / WPS_LO          # feasible seconds band
    t = min(hi - 0.5, max(lo + 0.5, round(words / RATE)))
    row["target_duration_sec"] = f"{t:.0f}"
    return row, t


def synthesize_rows():
    topics = [t.strip() for t in env("FACTORY_TOPICS", "kinematics").split(",") if t.strip()]
    per = max(1, int(env("FACTORY_ROWS_PER_TOPIC", "1")))
    orient = env("FACTORY_ORIENTATION", "vertical")
    dur = float(env("FACTORY_TARGET_DURATION", "60"))
    seed = int(env("FACTORY_SEED", "7"))
    ctype = env("FACTORY_CONCEPT_TYPE", "GENERIC")
    rng = random.Random(seed)

    rows = []
    for topic in topics:
        for k in range(per):
            want = int(rng.uniform(WPS_LO + 0.3, WPS_HI - 0.3) * dur)
            script, bank = [], list(PHRASES)
            rng.shuffle(bank)
            while len(" ".join(script).split()) < want:
                script.append(bank.pop() if bank else PHRASES[rng.randrange(len(PHRASES))])
            script = " ".join(script)
            rows.append({
                "video_id": f"wf_{topic}_{k}_{seed}",
                "concept_type": ctype,
                "header_title": f"Feynman · {topic}",
                "tagline": "NEET · JEE · MIT",
                "question_text": "", "option_a": "", "option_b": "",
                "option_c": "", "option_d": "", "correct_answer": "",
                "equations_json": json.dumps(["E = mc^2"]),
                "visual_data_json": json.dumps(TOPIC_PRIMS.get(topic, [{"type": "dot"}])),
                "audio_script": script,
                "orientation": orient,
                "beats_json": "",
                "target_duration_sec": f"{dur:.0f}",
            })
    return rows


def write_csv(path, rows):
    fields = sv.REQUIRED_COLUMNS + [c for c in sv.OPTIONAL_COLUMNS]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def read_csv(path):
    header, rows = sv.read_rows(path)
    return rows


def main():
    mode = env("FACTORY_MODE", "csv")
    out = ROOT / env("FACTORY_OUT", "content_batch.csv")

    if mode == "run":
        cmd = shlex.split(env("FACTORY_GENERATOR_CMD"))
        if not cmd:
            raise SystemExit("[factory] mode=run needs FACTORY_GENERATOR_CMD")
        subprocess.run(cmd, cwd=ROOT, check=True)
        rows = read_csv(ROOT / env("FACTORY_CSV", "content_batch.csv"))
    elif mode == "synthesize":
        rows = synthesize_rows()
    else:
        rows = read_csv(ROOT / env("FACTORY_CSV", "content_batch.csv"))

    retuned = []
    if env("FACTORY_AUTOFIX_DURATION", "true") == "true":
        fixed = []
        for r in rows:
            r, t = retune_duration(r)
            if t is not None:
                fixed.append((r.get("video_id"), len(r["audio_script"].split()), t))
        retuned = fixed

    write_csv(out, rows)

    errs, warns = [], []
    for i, r in enumerate(rows, start=2):
        e, w = sv.validate_row(r, sv.REQUIRED_COLUMNS, False)
        errs += [f"line {i}: {x}" for x in e]
        warns += [f"line {i}: {x}" for x in w]

    manifest = {
        "mode": mode, "out": str(out), "rows": len(rows),
        "retuned": retuned, "errors": errs, "warnings": warns,
    }
    (ROOT / "reports").mkdir(parents=True, exist_ok=True)
    (ROOT / "reports" / "factory_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    summary = Path(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null"))
    with summary.open("a", encoding="utf-8") as f:
        f.write("## 🎛️ Factory input compiler\n\n")
        f.write(f"- mode: `{mode}` → `{out.relative_to(ROOT)}` ({len(rows)} rows)\n")
        if retuned:
            f.write("- retuned durations (words → seconds):\n")
            for vid, words, t in retuned:
                f.write(f"  - `{vid}`: {words}w → {t:.0f}s\n")
        f.write(f"- post-write errors: {len(errs)}, warnings: {len(warns)}\n")

    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a", encoding="utf-8") as f:
            f.write(f"csv={out.relative_to(ROOT)}\n")

    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
