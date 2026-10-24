#!/usr/bin/env python3
"""Derive the master CSVs from the ledger. READ-ONLY on intent (R33/R34):
this file never writes content_batch.csv; it only splits the validated
ledger into content/master_horizontal.csv and content/master_vertical.csv
for CI and sharded renders. The only writer of intent is tools/author.py.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import schema_validator

LEDGER = ROOT / "content_batch.csv"
OUTDIR = ROOT / "content"
HEADERS = schema_validator.REQUIRED_COLUMNS + ["beats_json", "target_duration_sec"]


def split_rows(rows):
    horiz, vert = [], []
    for r in rows:
        orient = (r.get("orientation") or "vertical").strip().lower()
        (horiz if orient == "horizontal" else vert).append(r)
    return horiz, vert


def write(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in HEADERS})


def main():
    if not LEDGER.exists():
        print(f"[masters] ledger missing: {LEDGER}; run tools/author.py first")
        return 1
    _, rows = schema_validator.read_rows(LEDGER)
    horiz, vert = split_rows(rows)
    write(horiz, OUTDIR / "master_horizontal.csv")
    write(vert, OUTDIR / "master_vertical.csv")
    print(f"[masters] horizontal={len(horiz)} vertical={len(vert)} "
          f"(derived from {LEDGER.name}; intent untouched)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
