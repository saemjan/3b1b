#!/usr/bin/env python3
"""author.py — gen-3 the one door for input (rule R33).

Sources (choose any one; the gate is identical for all):
  catalog  concept rows from jee_model_engine (witnessed models compute every
           number, A0) ∪ legacy make_batch recipes when importable; absence
           of both is a recorded degradation, never a crash
  csv      an existing CSV, imported and re-gated; OPTIONAL columns preserved
           (no silent data loss, A2)
  ask      live interactive authoring (presets manifest-witnessed)
  audit    report goodness of the current batch, write nothing

Every row passes schema gate + physics oracle (structured report, digest
receipted) + optional spoken-band retune (factory_input.retune_duration,
the single ruler) BEFORE writing. Writes only the target CSV via
csv.DictWriter so escaping is correct at every layer.
Receipts (A5): one append-only ledger line per write carrying row count,
error count and oracle digests.
Mobile/CI friendly: everything works with flags, no TTY required.

    python3 tools/author.py                          # interactive menu
    python3 tools/author.py --source catalog --yes --retune
    python3 tools/author.py --source catalog --ids phys:shm,math:bayes --yes
    python3 tools/author.py --source csv --csv old.csv --mode append --yes
    python3 tools/author.py --audit --json
    python3 tools/author.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import schema_validator as sv
import factory_input as FI                      # one ruler: words + retune
from tools.physics_oracle import report as oracle_report
from tools.ledger import append as ledger_append

try:
    import jee_model_engine as JME
except Exception:
    JME = None
try:
    import make_batch
except Exception:
    make_batch = None

SCHEMA_VERSION = 3
BATCH = ROOT / "content_batch.csv"
HEADERS = list(sv.REQUIRED_COLUMNS) + \
    [c for c in sv.OPTIONAL_COLUMNS if c not in sv.REQUIRED_COLUMNS]
JSON_FIELDS = ("equations_json", "visual_data_json", "beats_json")

PRESETS = {
    "1": [{"type": "energy_bar", "id": "pe", "fraction": 1.0, "pos": [-2, 0, 0]},
          {"type": "energy_bar", "id": "ke", "fraction": 0.0, "pos": [2, 0, 0]}],
    "2": [{"type": "electromagnetic_wave", "id": "wave1", "amplitude": 1,
           "frequency": 1, "speed": 2, "length": 7}],
    "3": [{"type": "two_path_interference", "id": "inter1"}],
    "4": [{"type": "text", "id": "t1", "text": "T_1 = T_2", "pos": [0, 2, 0]},
          {"type": "particle_gas", "id": "gas1", "count": 20, "pos": [-3, -1, 0]}],
    "5": [{"type": "circle", "id": "ring", "radius": 2.5},
          {"type": "orbit", "id": "electron", "width": 5, "height": 5}],
    "6": [{"type": "energy_landscape", "id": "well", "pos": [0, 0, 0]},
          {"type": "live_label", "id": "freq", "prefix": "nu", "unit": "GHz",
           "to": 24.0, "pos": [3, 2, 0]}],
}


# ------------------------------------------------------------- normalize
def normalize(src, dropped=None):
    row = {h: "" for h in HEADERS}
    for k, v in (src or {}).items():
        if k in JSON_FIELDS and not isinstance(v, str):
            v = json.dumps(v, ensure_ascii=False) if v else ""
        if k in row:
            row[k] = v
        elif dropped is not None:
            dropped.append(k)
    return row


def goodness(row):
    errs, warns = sv.validate_row(row, HEADERS, require_oracle=False)
    rep = oracle_report(row)                     # structured, no string surgery
    return errs + rep["errors"], warns + rep["warnings"], rep["digest"]


def report(rows, as_json=False):
    hard = soft = 0
    out = []
    for r in rows:
        e, w, digest = goodness(r)
        hard += len(e)
        soft += len(w)
        out.append({"video_id": r.get("video_id"), "errors": e,
                    "warnings": w, "digest": digest[:12]})
        if not as_json:
            tag = "OK " if not e else "BAD"
            print(f"  [{tag}] {r.get('video_id', '?'):<34} "
                  f"errors={len(e)} warns={len(w)} digest={digest[:12]}")
            for x in e:
                print(f"        error: {x}")
            for x in w:
                print(f"        warn : {x}")
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"goodness: {len(rows)} row(s), {hard} hard error(s), "
              f"{soft} warning(s)")
    return hard == 0


# ------------------------------------------------------------- read/write
def read_rows(path):
    if not Path(path).exists():
        return [], []
    _header, raw = sv.read_rows(path)
    dropped, rows = [], []
    for r in raw:
        rows.append(normalize(r, dropped))
    return rows, dropped


def write_rows(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in HEADERS})


def merge(existing, incoming, mode):
    if mode == "replace":
        return list(incoming)
    if mode == "append":
        ids = {r["video_id"] for r in existing}
        return existing + [r for r in incoming if r["video_id"] not in ids]
    by_id = {r["video_id"]: r for r in existing}
    order = [r["video_id"] for r in existing]
    for r in incoming:
        if r["video_id"] not in by_id:
            order.append(r["video_id"])
        by_id[r["video_id"]] = r
    return [by_id[i] for i in order]


# ---------------------------------------------------------------- sources
def from_catalog(ids=None, seed=7):
    want = set(x.strip() for x in ids.split(",")) if ids else None
    rows, notes = [], []
    if JME is not None:
        cids = [c for c in JME.REGISTRY if want is None or c in want]
        for i, cid in enumerate(cids):
            r = JME.generate_row(cid, seed=seed + i)
            r["video_id"] = f"cat_{cid.replace(':', '_')}_{seed}"
            rows.append(normalize(r))
        if want and not cids:
            notes.append("no concept id matched; falling back to recipes")
    elif want is None:
        notes.append("jee_model_engine unavailable; catalog = legacy recipes only")
    if make_batch is not None:
        legacy = [normalize(r) for r in make_batch.build_rows()]
        if want:
            legacy = [r for r in legacy if r["video_id"] in want]
        rows += legacy
    elif JME is None:
        notes.append("catalog degraded: neither jee_model_engine nor "
                     "make_batch importable")
    return rows, notes


def from_csv(path):
    rows, dropped = read_rows(path)
    notes = ([f"preserved optional columns; dropped unknown keys: "
              f"{sorted(set(dropped))}"] if dropped else [])
    return rows, notes


def from_ask(retune=False):
    print("Interactive authoring. Empty line accepts the default in [brackets].")

    def q(prompt, default=""):
        v = input(f"{prompt} [{default}]: ").strip()
        return v or default

    src = {
        "video_id": q("video_id", "my_topic_01"),
        "concept_type": q("concept_type", "GENERIC"),
        "header_title": q("header_title", "A Title"),
        "tagline": q("tagline", "A one-line subtitle."),
        "orientation": q("orientation", "vertical"),
        "target_duration_sec": q("target_duration_sec", "60"),
        "audio_script": q("audio_script", "Say something true about physics."),
        "equations_json": json.dumps([q("equation latex", "E = mc^2")]),
    }
    print("visual preset: 1 energy bars  2 em wave  3 two-slit  4 gas+text  "
          "5 orbit  6 landscape+label  0 none")
    preset = q("preset", "1")
    src["visual_data_json"] = json.dumps(PRESETS.get(preset, []))
    row = normalize(src)
    if retune:
        row, _t = FI.retune_duration(row)
    return [row], []


# ------------------------------------------------------------------- menu
def menu(retune=False):
    existing, _ = read_rows(BATCH)
    while True:
        print(f"\nINPUT GATE — content_batch.csv holds {len(existing)} row(s)")
        print(" 1 list catalog   2 add from catalog   3 author new row")
        print(" 4 import+re-gate a csv   5 audit ledger   6 write & validate  0 quit")
        try:
            c = input("> ").strip()
        except EOFError:
            return 0
        if c == "0":
            return 0
        if c == "1":
            rows, notes = from_catalog()
            for n in notes:
                print(f"  note: {n}")
            for r in rows:
                print(f"  {r['video_id']:<34} {r['orientation']}")
        elif c == "2":
            ids = input("ids comma-separated (empty=all): ").strip()
            incoming, notes = from_catalog(ids or None)
            for n in notes:
                print(f"  note: {n}")
            if retune:
                incoming = [FI.retune_duration(r)[0] for r in incoming]
            if report(incoming):
                existing = merge(existing, incoming, "upsert")
                print("staged.")
            else:
                print("refused by the gate.")
        elif c == "3":
            incoming, _notes = from_ask(retune)
            if report(incoming):
                existing = merge(existing, incoming, "upsert")
                print("staged.")
        elif c == "4":
            p = input("csv path: ").strip()
            incoming, notes = from_csv(p)
            for n in notes:
                print(f"  note: {n}")
            if report(incoming):
                existing = merge(existing, incoming, "upsert")
                print("staged.")
        elif c == "5":
            report(existing)
        elif c == "6":
            write_rows(existing, BATCH)
            _h, rows = sv.read_rows(BATCH)
            errs = []
            for r in rows:
                e, _w = sv.validate_row(normalize(r), HEADERS, True)
                errs += e
                errs += oracle_report(normalize(r))["errors"]
            digests = [goodness(r)[2][:12] for r in existing[:8]]
            ledger_append({"gate": "author", "schema_version": SCHEMA_VERSION,
                           "op": "write", "rows": len(existing),
                           "errors": len(errs), "digests": digests})
            print("written." if not errs else "written BUT VALIDATION FAILED")
            return 0 if not errs else 1
    return 0


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="the one input gate (gen-3)")
    ap.add_argument("--source", choices=["catalog", "csv", "ask", "audit"])
    ap.add_argument("--ids", default="")
    ap.add_argument("--csv", default="")
    ap.add_argument("--mode", choices=["append", "upsert", "replace"],
                    default="upsert")
    ap.add_argument("--out", default=str(BATCH))
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--retune", action="store_true",
                    help="retune target_duration_sec with the spoken-word canon")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0

    if a.audit or a.source == "audit":
        rows, _dropped = read_rows(BATCH)
        return 0 if report(rows, as_json=a.json) else 1

    if a.source is None:
        return menu(a.retune)

    notes = []
    if a.source == "catalog":
        incoming, notes = from_catalog(a.ids or None, seed=a.seed)
    elif a.source == "csv":
        incoming, notes = from_csv(a.csv)
    else:
        incoming, notes = from_ask(a.retune)
    for n in notes:
        print(f"[note] {n}")
    if a.retune and a.source != "ask":
        incoming = [FI.retune_duration(r)[0] for r in incoming]
    if not report(incoming, as_json=a.json):
        print("[gate] refused: fix the errors above, nothing was written")
        return 1
    if not a.yes:
        try:
            if input("write? [y/N]: ").strip().lower() != "y":
                print("aborted")
                return 0
        except EOFError:
            print("aborted (no TTY: pass --yes)")
            return 1
    existing, _dropped = read_rows(a.out)
    merged = merge(existing, incoming, a.mode)
    write_rows(merged, a.out)
    _h, rows = sv.read_rows(a.out)
    errs = []
    digests = []
    for r in rows:
        nr = normalize(r)
        e, _w = sv.validate_row(nr, HEADERS, True)
        errs += e
        rep = oracle_report(nr)
        errs += rep["errors"]
        digests.append(rep["digest"][:12])
    ledger_append({"gate": "author", "schema_version": SCHEMA_VERSION,
                   "op": "write", "source": a.source, "mode": a.mode,
                   "rows": len(incoming), "errors": len(errs),
                   "digests": digests[:8]})
    print(f"[gate] wrote {len(incoming)} row(s) to {Path(a.out).name}")
    return 0 if not errs else 1


# --------------------------------------------------------------- witness
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    want("headers-superset",
         set(sv.REQUIRED_COLUMNS) <= set(HEADERS))
    src = {c: "" for c in sv.REQUIRED_COLUMNS}
    src.update({"video_id": "v1", "physics_verified": "true",
                "audio_lufs": "-14.1", "bogus_key": "x"})
    dropped = []
    row = normalize(src, dropped)
    want("optional-preserved", row["physics_verified"] == "true"
         and row["audio_lufs"] == "-14.1")
    want("unknown-dropped-recorded", dropped == ["bogus_key"], str(dropped))

    ex = [normalize({"video_id": "a"}), normalize({"video_id": "b"})]
    inc = [normalize({"video_id": "b", "tagline": "new"}),
           normalize({"video_id": "c"})]
    m = merge(ex, inc, "upsert")
    want("merge-upsert", [r["video_id"] for r in m] == ["a", "b", "c"]
         and m[1]["tagline"] == "new")
    m2 = merge(ex, inc, "append")
    want("merge-append", [r["video_id"] for r in m2] == ["a", "b", "c"])
    want("merge-replace", [r["video_id"] for r in merge(ex, inc, "replace")]
         == ["b", "c"])

    bad = normalize({"video_id": "bad", "audio_script": "Bad launch.",
                     "visual_data_json": json.dumps(
                         [{"type": "projectile_motion", "id": "p",
                           "v0": -5, "angle": 45, "g": 9.8}]),
                     "equations_json": "[]"})
    e, _w, _d = goodness(bad)
    want("gate-refuses", len(e) >= 1, str(e[:1]))
    good = normalize({"video_id": "good", "audio_script": "A projectile flies.",
                      "visual_data_json": json.dumps(
                          [{"type": "projectile_motion", "id": "p",
                            "v0": 20, "angle": 45, "g": 9.8}]),
                      "equations_json": json.dumps(["y = x"])})
    e2, _w2, d2 = goodness(good)
    want("gate-accepts", e2 == [] and len(d2) == 64, str(e2[:1]))

    types = {v["type"] for vs in PRESETS.values() for v in vs}
    want("presets-known", types <= set(sv.KNOWN_PRIMITIVES), str(types))

    if JME is not None:
        c1, _n1 = from_catalog("phys:shm", seed=5)
        c2, _n2 = from_catalog("phys:shm", seed=5)
        want("catalog-determinism", c1 == c2 and len(c1) == 1)
    else:
        want("catalog-determinism", True, "skipped (jee engine absent)")
    return checks


if __name__ == "__main__":
    sys.exit(main())
