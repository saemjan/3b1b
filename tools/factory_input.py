#!/usr/bin/env python3
"""factory_input.py — gen-3 factory input compiler (SIR intent → gated CSV).

Layers (CSV_AUTHORING canon):
  workflow knobs (env) -> this compiler -> CSV (fluid) -> gates (frozen code)

Modes (env FACTORY_MODE):
  csv         use FACTORY_CSV as-is (old behaviour)
  run         run FACTORY_GENERATOR_CMD first, then use its CSV
  synthesize  concept ids delegate to jee_model_engine: every number on the
              row is computed by a witnessed model (A0); topics with no
              concept fall back to the phrase bank with a RECORDED
              degradation (fallback list lands in manifest + ledger)

One ruler everywhere (parity with schema_validator / physics_oracle):
  spoken words  -> text_normalizer.spoken_word_count
  duration band -> retune_duration(), pure, band-safe, shared with author.py
  primitives    -> every emitted visual type must lie in the routed manifest
                   (witnessed in selftest; fail closed otherwise)

Receipts (A5): reports/factory_manifest.json plus one append-only ledger line
  {gate:"factory_input", schema_version:3, mode, rows, concept_rows,
   fallback_topics, retuned, errors, warnings, config}
and GITHUB_OUTPUT csv=<path> for the workflow.
"""
from __future__ import annotations

import csv
import json
import os
import random
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import schema_validator as sv

try:
    import text_normalizer as _TN
except Exception:
    _TN = None
try:
    import jee_model_engine as _JME
except Exception:
    _JME = None
try:
    from tools.ledger import append as _ledger
except Exception:
    _ledger = None

SCHEMA_VERSION = 3
WPS_LO, WPS_HI = sv.WORDS_PER_SEC
RATE = 2.4

# fallback visuals for non-concept topics (witnessed ⊆ KNOWN_PRIMITIVES)
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


# ------------------------------------------------------------- one ruler
def spoken_words(script: str) -> int:
    """The spoken-word canon: what XTTS will actually say."""
    if _TN is not None:
        fn = getattr(_TN, "spoken_word_count", None)
        if fn:
            try:
                return int(fn(script))
            except Exception:
                pass
        norm = getattr(_TN, "normalize", None)
        if norm:
            try:
                return len(norm(script).split())
            except Exception:
                pass
    return len((script or "").split())


def retune_duration(row):
    """Band-safe retune of target_duration_sec. Pure: returns a new row."""
    words = spoken_words(row.get("audio_script") or "")
    if not words:
        return dict(row), None
    lo, hi = words / WPS_HI, words / WPS_LO      # feasible seconds band
    t = min(hi - 0.5, max(lo + 0.5, round(words / RATE)))
    out = dict(row)
    out["target_duration_sec"] = f"{t:.0f}"
    return out, t


# ------------------------------------------------------------- synthesis
def _concept_ids_for(topic):
    if _JME is None:
        return []
    if topic in _JME.REGISTRY:
        return [topic]
    pref = topic.split(":")[0] + ":"
    return [c for c in _JME.REGISTRY if c.startswith(pref)]


def _phrase_row(topic, k, dur, orient, ctype, rng):
    want = int(rng.uniform(WPS_LO + 0.3, WPS_HI - 0.3) * dur)
    script, bank = [], list(PHRASES)
    rng.shuffle(bank)
    while len(" ".join(script).split()) < want:
        script.append(bank.pop() if bank else PHRASES[rng.randrange(len(PHRASES))])
    row = {c: "" for c in sv.REQUIRED_COLUMNS}
    row.update({
        "video_id": f"wf_{topic}_{k}_{rng.getrandbits(20):05x}",
        "concept_type": ctype,
        "header_title": f"Feynman · {topic}",
        "tagline": "NEET · JEE · MIT",
        "equations_json": json.dumps(["E = mc^2"]),
        "visual_data_json": json.dumps(TOPIC_PRIMS.get(topic, [{"type": "dot"}])),
        "audio_script": " ".join(script),
        "orientation": orient,
        "target_duration_sec": f"{dur:.0f}",
    })
    return row


def synthesize_rows():
    topics = [t.strip() for t in env("FACTORY_TOPICS", "phys:shm").split(",")
              if t.strip()]
    per = max(1, int(env("FACTORY_ROWS_PER_TOPIC", "1")))
    orient = env("FACTORY_ORIENTATION", "vertical")
    dur = float(env("FACTORY_TARGET_DURATION", "60"))
    seed = int(env("FACTORY_SEED", "7"))
    aud = env("FACTORY_AUDIENCE", "jee")
    ctype = env("FACTORY_CONCEPT_TYPE", "GENERIC")
    rng = random.Random(seed)
    rows, fallback, n_concept = [], [], 0
    for topic in topics:
        ids = _concept_ids_for(topic)
        if ids:
            for k, cid in enumerate(ids[:per]):
                row = _JME.generate_row(
                    cid, seed=seed + len(rows), audience=aud,
                    orientation=orient, make_quiz=(rng.random() < 0.25))
                row["video_id"] = f"wf_{cid.replace(':', '_')}_{k}_{seed}"
                if ctype != "GENERIC":
                    row["concept_type"] = ctype
                rows.append(row)
                n_concept += 1
            continue
        fallback.append(topic)
        for k in range(per):
            rows.append(_phrase_row(topic, k, dur, orient, ctype, rng))
    return rows, fallback, n_concept


# ------------------------------------------------------------- csv I/O
def write_csv(path, rows):
    fields = list(sv.REQUIRED_COLUMNS) + list(sv.OPTIONAL_COLUMNS)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def read_csv(path):
    _header, rows = sv.read_rows(path)
    return rows


# ---------------------------------------------------------------- gate run
def main():
    if "--selftest" in sys.argv:
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0

    mode = env("FACTORY_MODE", "csv")
    out = ROOT / env("FACTORY_OUT", "content_batch.csv")
    fallback, retuned, n_concept = [], [], 0
    if mode == "run":
        cmd = shlex.split(env("FACTORY_GENERATOR_CMD"))
        if not cmd:
            raise SystemExit("[factory] mode=run needs FACTORY_GENERATOR_CMD")
        subprocess.run(cmd, cwd=ROOT, check=True)
        rows = read_csv(ROOT / env("FACTORY_CSV", "content_batch.csv"))
    elif mode == "synthesize":
        rows, fallback, n_concept = synthesize_rows()
    else:
        rows = read_csv(ROOT / env("FACTORY_CSV", "content_batch.csv"))

    if env("FACTORY_AUTOFIX_DURATION", "true") == "true":
        fixed, out_rows = [], []
        for r in rows:
            r2, t = retune_duration(r)
            if t is not None:
                fixed.append((r2.get("video_id"),
                              spoken_words(r2.get("audio_script", "")), t))
            out_rows.append(r2)
        rows, retuned = out_rows, fixed

    write_csv(out, rows)
    errs, warns = [], []
    for i, r in enumerate(rows, start=2):
        e, w = sv.validate_row(r, list(sv.REQUIRED_COLUMNS), False)
        errs += [f"line {i}: {x}" for x in e]
        warns += [f"line {i}: {x}" for x in w]

    config = {k: env(k) for k in (
        "FACTORY_MODE", "FACTORY_TOPICS", "FACTORY_SEED",
        "FACTORY_ORIENTATION", "FACTORY_TARGET_DURATION",
        "FACTORY_AUDIENCE", "FACTORY_ROWS_PER_TOPIC")}
    manifest = {"schema_version": SCHEMA_VERSION, "mode": mode,
                "out": str(out), "rows": len(rows), "concept_rows": n_concept,
                "fallback_topics": fallback, "retuned": retuned,
                "errors": errs, "warnings": warns, "config": config}
    (ROOT / "reports").mkdir(parents=True, exist_ok=True)
    (ROOT / "reports" / "factory_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    if _ledger is not None:
        _ledger({"gate": "factory_input", "schema_version": SCHEMA_VERSION,
                 "mode": mode, "rows": len(rows), "concept_rows": n_concept,
                 "fallback_topics": fallback, "retuned": len(retuned),
                 "errors": len(errs), "warnings": len(warns)})

    summary = Path(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null"))
    with summary.open("a", encoding="utf-8") as f:
        f.write("## 🎛️ Factory input compiler (gen-3)\n")
        f.write(f"- mode `{mode}` → `{out.relative_to(ROOT)}` "
                f"({len(rows)} rows, {n_concept} concept-grounded)\n")
        if fallback:
            f.write(f"- ⚠️ phrase-bank fallback topics: {fallback}\n")
        if retuned:
            f.write("- retuned durations (spoken words → seconds):\n")
            for vid, words, t in retuned:
                f.write(f"  - `{vid}`: {words}w → {t:.0f}s\n")
        f.write(f"- post-write errors: {len(errs)}, warnings: {len(warns)}\n")
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a", encoding="utf-8") as f:
            f.write(f"csv={out.relative_to(ROOT)}\n")
    return 1 if errs else 0


# --------------------------------------------------------------- witness
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    for words in (30, 120, 300):
        row = {"audio_script": " ".join(["word"] * words)}
        r2, t = retune_duration(row)
        want(f"band:{words}", bool(t) and WPS_LO * t <= words <= WPS_HI * t,
             f"t={t}")
        probe = {c: "" for c in sv.REQUIRED_COLUMNS}
        probe.update({"video_id": "band", "audio_script": row["audio_script"],
                      "target_duration_sec": r2["target_duration_sec"],
                      "visual_data_json": "[]", "equations_json": "[]"})
        _e, w = sv.validate_row(probe, list(sv.REQUIRED_COLUMNS), False)
        want(f"validator-band:{words}",
             not any("implausible" in x for x in w))
    src = {"audio_script": "x y z"}
    retune_duration(src)
    want("retune-pure", "target_duration_sec" not in src)
    a, _ = retune_duration({"audio_script": " ".join(["w"] * 120)})
    b, _ = retune_duration(a)
    want("retune-idempotent",
         a["target_duration_sec"] == b["target_duration_sec"])
    types = {v["type"] for vs in TOPIC_PRIMS.values() for v in vs}
    want("prims-known", types <= set(sv.KNOWN_PRIMITIVES), str(types))

    saved = {k: os.environ.get(k) for k in
             ("FACTORY_TOPICS", "FACTORY_SEED", "FACTORY_ROWS_PER_TOPIC")}
    os.environ.update({"FACTORY_TOPICS": "phys:", "FACTORY_SEED": "11",
                       "FACTORY_ROWS_PER_TOPIC": "1"})
    try:
        r1, f1, c1 = synthesize_rows()
        r2, f2, c2 = synthesize_rows()
        want("synth-determinism", r1 == r2 and f1 == f2)
        if _JME is not None and c1:
            emitted = set()
            for r in r1:
                for v in json.loads(r["visual_data_json"]):
                    emitted.add(v["type"])
            want("synth-routed", emitted <= set(_JME.ROUTED_MANIFEST),
                 str(emitted - set(_JME.ROUTED_MANIFEST)))
            want("synth-witnessed-numbers", c1 == len(r1) - len(f1))
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return checks


if __name__ == "__main__":
    sys.exit(main())
