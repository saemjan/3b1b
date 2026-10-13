#!/usr/bin/env python3
"""Legacy migration tool: add an `orientation` column to a CSV.

⚠️  DEPRECATED — As of v2.2, `generate_csv.py` already includes
    `orientation` in the header. This script only exists for migrating
    pre-v2.2 CSVs that lack the column.

Usage:
    python tools/legacy/add_orientation.py [CSV] [--default V]
                                                 [--in-place]

Examples:
    # Write to content_batch.csv.new (safe, original untouched)
    python tools/legacy/add_orientation.py content_batch.csv

    # Overwrite the original atomically
    python tools/legacy/add_orientation.py content_batch.csv --in-place

    # Use horizontal as the default for every row
    python tools/legacy/add_orientation.py content_batch.csv --default horizontal
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("csv", nargs="?", default="content_batch.csv",
                   help="Path to the input CSV (default: content_batch.csv).")
    p.add_argument("--default", default="vertical",
                   choices=["vertical", "horizontal"],
                   help="Value to insert for missing/empty orientation cells.")
    p.add_argument("--in-place", action="store_true",
                   help="Overwrite the input file atomically (default: write .new).")
    return p.parse_args()


def add_orientation(csv_path: Path, default: str, in_place: bool) -> int:
    if not csv_path.exists():
        print(f"[ERROR] {csv_path} not found.", file=sys.stderr)
        return 2

    # utf-8-sig strips a BOM if present; works with plain UTF-8 too.
    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if not fieldnames:
        print(f"[ERROR] {csv_path} has no header.", file=sys.stderr)
        return 3

    already_present = "orientation" in fieldnames
    if already_present and rows:
        missing = [i for i, r in enumerate(rows, start=2)
                   if not (r.get("orientation") or "").strip()]
        if not missing:
            print(f"[INFO] {csv_path}: `orientation` column already "
                  f"populated on every row. Nothing to do.")
            return 0
        print(f"[INFO] {csv_path}: `orientation` column exists; "
              f"filling {len(missing)} empty cell(s) with "
              f"'{default}'.")
    else:
        print(f"[INFO] {csv_path}: adding `orientation` column with "
              f"default '{default}'.")

    if not already_present:
        fieldnames.append("orientation")

    n_filled = 0
    for r in rows:
        if not (r.get("orientation") or "").strip():
            r["orientation"] = default
            n_filled += 1

    # ---- Write atomically --------------------------------------------
    target = csv_path if in_place else csv_path.with_suffix(
        csv_path.suffix + ".new")
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames,
                               quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

    print(f"[OK]   {target}: {len(rows)} rows, {n_filled} cell(s) filled.")
    if not in_place:
        print(f"       Rename with: mv '{target}' '{csv_path}'")
    return 0


def main():
    args = parse_args()
    return add_orientation(Path(args.csv), args.default, args.in_place)


if __name__ == "__main__":
    sys.exit(main())
