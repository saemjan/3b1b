#!/usr/bin/env python3
"""The one door for input (rule R33).

Sources (choose any one, the gate is the same for all):
  catalog  rows from make_batch.py (the recipe library)
  csv      an existing CSV, imported and re-gated
  ask      live interactive authoring
  audit    report goodness of the current ledger, write nothing

Every row passes schema + physics oracle + narration trust + length band
BEFORE writing. Writes only content_batch.csv, via csv.DictWriter and
json.dumps, so escaping is correct at every layer. Mobile/CI friendly:
everything works with flags, no TTY required.

    python3 tools/author.py                          # interactive menu
    python3 tools/author.py --source catalog --yes   # gate+write all recipes
    python3 tools/author.py --source catalog --ids feynman_v3_concept_twoslit --mode upsert --yes
    python3 tools/author.py --source csv --csv old.csv --mode append --yes
    python3 tools/author.py --audit
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import schema_validator
from tools.physics_oracle import validate_row as oracle_row
from tools.ledger import append as ledger_append

LEDGER_PATH = ROOT / "content_batch.csv"
HEADERS = schema_validator.REQUIRED_COLUMNS + ["beats_json", "target_duration_sec"]
JSON_FIELDS = ("equations_json", "visual_data_json", "beats_json")


# ---------- normalize & gate ----------
def normalize(src):
    row = {h: "" for h in HEADERS}
    for k, v in src.items():
        if k in JSON_FIELDS and not isinstance(v, str):
            v = json.dumps(v, ensure_ascii=False) if v else ""
        if k in row:
            row[k] = v
    return row


def goodness(row):
    errs, warns = schema_validator.validate_row(row, HEADERS, require_oracle=False)
    ok, violations = oracle_row(row)
    for v in violations:
        if "warn" in v.split("]", 1)[1][:6]:
            warns.append(v)
        else:
            errs.append(v)
    return errs, warns


def report(rows):
    hard = soft = 0
    for r in rows:
        e, w = goodness(r)
        hard += len(e)
        soft += len(w)
        tag = "OK " if not e else "BAD"
        print(f"  [{tag}] {r['video_id']:<34} {r['orientation']:<10} "
              f"errors={len(e)} warns={len(w)}")
        for x in e:
            print(f"        error: {x}")
        for x in w:
            print(f"        warn : {x}")
    print(f"goodness: {len(rows)} row(s), {hard} hard error(s), {soft} warning(s)")
    return hard == 0


# ---------- read / write ----------
def read_rows(path):
    if not Path(path).exists():
        return []
    header, rows = schema_validator.read_rows(path)
    return [normalize(r) for r in rows]


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


# ---------- sources ----------
def from_catalog(ids=None):
    import make_batch
    rows = [normalize(r) for r in make_batch.build_rows()]
    if ids:
        want = set(ids.split(","))
        rows = [r for r in rows if r["video_id"] in want]
    return rows


def from_csv(path):
    return read_rows(path)


def from_ask():
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
    visuals = {
        "1": [{"type": "energy_bar", "id": "pe", "fraction": 1.0, "pos": [-2, 0, 0]},
              {"type": "energy_bar", "id": "ke", "fraction": 0.0, "pos": [2, 0, 0]}],
        "2": [{"type": "electromagnetic_wave", "id": "wave1", "amplitude": 1,
               "frequency": 1, "speed": 2, "length": 7}],
        "3": [{"type": "two_path_interference", "id": "inter1"}],
        "4": [{"type": "text", "id": "t1", "text": "T_1 = T_2", "pos": [0, 2, 0]},
              {"type": "particle_gas", "id": "gas1", "count": 20, "pos": [-3, -1, 0]}],
        "5": [{"type": "circle", "id": "ring", "radius": 2.5, "color": "GREY"},
              {"type": "orbit", "id": "electron", "width": 5, "height": 5}],
        "6": [{"type": "energy_landscape", "id": "well", "pos": [0, 0, 0]},
              {"type": "live_label", "id": "freq", "prefix": "nu", "unit": "GHz",
               "to": 24.0, "pos": [3, 2, 0]}],
    }.get(preset, [])
    src["visual_data_json"] = json.dumps(visuals)
    return [normalize(src)]


# ---------- menu ----------
def menu():
    existing = read_rows(LEDGER_PATH)
    while True:
        print("\nINPUT GATE — content_batch.csv holds "
              f"{len(existing)} row(s)")
        print(" 1 list catalog   2 add from catalog   3 author new row")
        print(" 4 import+re-gate a csv   5 audit ledger   6 write & validate   0 quit")
        try:
            c = input("> ").strip()
        except EOFError:
            return 0
        if c == "0":
            return 0
        if c == "1":
            for r in from_catalog():
                print(f"  {r['video_id']:<34} {r['orientation']}")
        elif c == "2":
            ids = input("ids comma-separated (empty=all): ").strip()
            incoming = from_catalog(ids or None)
            if report(incoming):
                existing = merge(existing, incoming, "upsert")
                print("staged.")
            else:
                print("refused by the gate.")
        elif c == "3":
            incoming = from_ask()
            if report(incoming):
                existing = merge(existing, incoming, "upsert")
                print("staged.")
        elif c == "4":
            p = input("csv path: ").strip()
            incoming = from_csv(p)
            if report(incoming):
                existing = merge(existing, incoming, "upsert")
                print("staged.")
        elif c == "5":
            report(existing)
        elif c == "6":
            write_rows(existing, LEDGER_PATH)
            _, errs, _ = schema_validator.validate_csv(LEDGER_PATH, True)
            ledger_append({"op": "author", "rows": len(existing),
                           "errors": len(errs)})
            print("written." if not errs else "written BUT VALIDATION FAILED")
            return 0 if not errs else 1
    return 0


def main():
    ap = argparse.ArgumentParser(description="the one input gate")
    ap.add_argument("--source", choices=["catalog", "csv", "ask", "audit"])
    ap.add_argument("--ids", default="")
    ap.add_argument("--csv", default="")
    ap.add_argument("--mode", choices=["append", "upsert", "replace"], default="upsert")
    ap.add_argument("--out", default=str(LEDGER_PATH))
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--audit", action="store_true")
    a = ap.parse_args()

    if a.audit or a.source == "audit":
        rows = read_rows(LEDGER_PATH)
        return 0 if report(rows) else 1
    if a.source is None:
        return menu()

    incoming = {"catalog": lambda: from_catalog(a.ids or None),
                "csv": lambda: from_csv(a.csv),
                "ask": from_ask}[a.source]()
    if not report(incoming):
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
    existing = read_rows(a.out)
    write_rows(merge(existing, incoming, a.mode), a.out)
    _, errs, _ = schema_validator.validate_csv(a.out, True)
    ledger_append({"op": "author", "source": a.source, "mode": a.mode,
                   "rows": len(incoming), "errors": len(errs)})
    print(f"[gate] wrote {len(incoming)} row(s) to {Path(a.out).name}")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
