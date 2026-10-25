#!/usr/bin/env python3
"""ledger.py — gen-3 append-only outcome ledger (the A5 backbone).

Constitutional rules enforced by construction:
  A2  no hidden state: path is explicit (env SAEM_LEDGER_PATH, else
      <repo>/logs/render_ledger.jsonl); records carry schema version +
      timestamps; callers' dicts are NEVER mutated.
  A3  overwrite/delete are irreversible and must be priced: clear() is
      gone; the only shrinking operation is rotate(), which atomically
      archives the ledger and opens the new one with a tombstone record
      that prices the debt (bytes moved + sha).
  A5  append-only: one write() per record under an OS lock when available
      (degrades gracefully); malformed lines are counted as debt, never
      silently dropped; verify() is a machine check over the whole file.

API: append, read, read_with_debt, rotate, summarize, export_csv, verify,
     selftest.  CLI: python3 tools/ledger.py [summarize|export P|rotate R|verify]
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 3
_SYNC = os.environ.get("SAEM_LEDGER_SYNC", "1") != "0"

try:                                   # single-writer lock; optional (degrade)
    import fcntl as _FCNTL
except Exception:
    _FCNTL = None


def default_path() -> Path:
    env = os.environ.get("SAEM_LEDGER_PATH")
    return Path(env) if env else ROOT / "logs" / "render_ledger.jsonl"


def _now():
    ts = time.time()
    return ts, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


# ------------------------------------------------------------------ append
def append(entry, ledger=None):
    """Append one record. Returns the stored record; never mutates `entry`."""
    if not isinstance(entry, dict):
        raise ValueError("ledger entries must be objects")
    path = Path(ledger) if ledger else default_path()
    ts, iso = _now()
    record = {"schema_version": SCHEMA_VERSION, "ts": ts, "iso_ts": iso}
    record.update(entry)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        if _FCNTL:
            _FCNTL.flock(f.fileno(), _FCNTL.LOCK_EX)
        try:
            f.write(line)              # one atomic append per record
            f.flush()
            if _SYNC:
                os.fsync(f.fileno())
        finally:
            if _FCNTL:
                _FCNTL.flock(f.fileno(), _FCNTL.LOCK_UN)
    return record


# ------------------------------------------------------------------- read
def read_with_debt(ledger=None):
    path = Path(ledger) if ledger else default_path()
    if not path.exists():
        return [], {"missing_file": str(path), "malformed": 0, "lines": 0}
    entries = []
    debt = {"malformed": 0, "legacy_schema": 0, "lines": 0}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            debt["lines"] += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                debt["malformed"] += 1     # counted, never hidden (A5)
                continue
            if not isinstance(obj, dict):
                debt["malformed"] += 1
                continue
            if int(obj.get("schema_version", 1)) < SCHEMA_VERSION:
                debt["legacy_schema"] += 1
            entries.append(obj)
    return entries, debt


def read(ledger=None):
    return read_with_debt(ledger)[0]


# ----------------------------------------------------------------- rotate
def rotate(reason, ledger=None):
    """The ONLY priced shrink: archive current ledger, tombstone the new."""
    path = Path(ledger) if ledger else default_path()
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError("nothing to rotate")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()[:12]
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    archive = path.parent / "archive" / f"{path.stem}-{stamp}-{digest}.jsonl"
    archive.parent.mkdir(parents=True, exist_ok=True)
    os.replace(path, archive)              # atomic; content preserved
    append({"op": "rotate", "reason": str(reason), "archive": str(archive),
            "debt_bytes": len(raw), "sha256_12": digest}, ledger=path)
    return archive


def clear(*_a, **_k):
    raise PermissionError(
        "ledger.clear() is unconstitutional (A3/A5): deletion is irreversible "
        "and unpriced. Use rotate(reason) — it archives and records the debt.")


# --------------------------------------------------------------- summarize
def summarize(ledger=None):
    entries, debt = read_with_debt(ledger)
    rep = {"entries": len(entries), "debt": debt, "status": {},
           "gate_failures": {}, "backends": {}, "failed_primitives": {},
           "lufs": [], "durations": [], "walls": [], "genomes": 0}
    genomes = set()
    for e in entries:
        st = e.get("status", e.get("op", "?"))
        rep["status"][st] = rep["status"].get(st, 0) + 1
        for g in e.get("gates") or []:
            if not g.get("ok"):
                k = str(g.get("gate", "?"))
                rep["gate_failures"][k] = rep["gate_failures"].get(k, 0) + 1
        for key in ("backend",):
            b = e.get(key)
            if b:
                rep["backends"][b] = rep["backends"].get(b, 0) + 1
        for d in e.get("backend_decisions") or []:
            b = d.get("chosen")
            if b:
                rep["backends"][b] = rep["backends"].get(b, 0) + 1
        for p in e.get("failed_primitives") or []:
            rep["failed_primitives"][p] = rep["failed_primitives"].get(p, 0) + 1
        for key, bag in (("audio_lufs", "lufs"), ("duration_sec", "durations"),
                         ("wall_sec", "walls")):
            v = e.get(key)
            if isinstance(v, (int, float)):
                rep[bag].append(v)
        g = (e.get("style") or {}).get("genome") or {}
        if g.get("seed_text"):
            genomes.add(g["seed_text"])
    rep["genomes"] = len(genomes)

    print(f"LEDGER SUMMARY  entries={rep['entries']}  debt={debt}")
    print(f"  status: {rep['status']}")
    if rep["gate_failures"]:
        print(f"  gate failures: {rep['gate_failures']}")
    if rep["backends"]:
        print(f"  backends: {rep['backends']}")
    if rep["failed_primitives"]:
        top = sorted(rep["failed_primitives"].items(), key=lambda kv: -kv[1])[:8]
        print(f"  most-failed primitives: {top}")
    if rep["lufs"]:
        print(f"  LUFS min/mean/max: {min(rep['lufs']):.1f} / "
              f"{sum(rep['lufs'])/len(rep['lufs']):.1f} / {max(rep['lufs']):.1f}")
    if rep["durations"]:
        print(f"  duration s min/mean/max: {min(rep['durations']):.1f} / "
              f"{sum(rep['durations'])/len(rep['durations']):.1f} / "
              f"{max(rep['durations']):.1f}")
    if rep["walls"]:
        print(f"  wall s mean: {sum(rep['walls'])/len(rep['walls']):.1f}")
    print(f"  distinct style genomes: {rep['genomes']}")
    return rep


# ------------------------------------------------------------------ export
def export_csv(output_path, ledger=None):
    entries, _ = read_with_debt(ledger)
    if not entries:
        print("ledger is empty")
        return 1
    keys = sorted({k for e in entries for k in e})
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for e in entries:
            w.writerow({k: (json.dumps(e[k], ensure_ascii=False, sort_keys=True)
                            if isinstance(e[k], (dict, list)) else e.get(k, ""))
                        for k in keys})
    print(f"exported {len(entries)} entries -> {output_path}")
    return 0


# ------------------------------------------------------------------ verify
def verify(ledger=None):
    """Machine check (A5): integrity + causality of the whole ledger."""
    entries, debt = read_with_debt(ledger)
    problems = []
    if debt.get("malformed"):
        problems.append(f"{debt['malformed']} malformed line(s)")
    last = 0.0
    for i, e in enumerate(entries):
        if "schema_version" not in e:
            problems.append(f"entry {i} missing schema_version")
        ts = float(e.get("ts", 0.0))
        if ts < last - 1e-9:
            problems.append(f"entry {i} timestamp goes backwards")
        last = max(last, ts)
    print("[ledger] verify:", "ok" if not problems else problems)
    return 0 if not problems else 1


# ---------------------------------------------------------------- selftest
def selftest():
    import tempfile
    import threading
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    with tempfile.TemporaryDirectory() as td:
        led = Path(td) / "led.jsonl"
        caller = {"video_id": "v1", "status": "ok"}
        rec = append(caller, ledger=led)
        want("no-caller-mutation", caller == {"video_id": "v1", "status": "ok"})
        want("schema-stamped", rec["schema_version"] == SCHEMA_VERSION)
        entries, debt = read_with_debt(led)
        want("roundtrip", len(entries) == 1 and entries[0]["video_id"] == "v1"
             and debt["malformed"] == 0)

        def worker(n):
            for k in range(25):
                append({"video_id": f"w{n}_{k}"}, ledger=led)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        entries, debt = read_with_debt(led)
        want("concurrent-integrity", len(entries) == 1 + 200
             and debt["malformed"] == 0, f"{len(entries)} lines")

        arch = rotate("selftest", ledger=led)
        entries, _ = read_with_debt(led)
        archived, _ = read_with_debt(arch)
        want("rotate-archives", len(archived) == 201
             and entries[0].get("op") == "rotate"
             and entries[0].get("debt_bytes", 0) > 0)
        try:
            clear(ledger=led)
            want("clear-forbidden", False)
        except PermissionError:
            want("clear-forbidden", True)

        with open(led, "a", encoding="utf-8") as f:
            f.write("{not json\n")
        entries, debt = read_with_debt(led)
        want("debt-counted", debt["malformed"] == 1)
        want("verify-fails-on-debt", verify(led) == 1)
        rc = export_csv(Path(td) / "out.csv", ledger=led)
        want("export", rc == 0 and (Path(td) / "out.csv").exists())
    return checks


def main():
    args = sys.argv[1:]
    if not args or args[0] == "--selftest":
        fails = 0
        for name, ok, detail in (selftest() if not args else []):
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return fails
    cmd = args[0]
    if cmd == "summarize":
        summarize()
        return 0
    if cmd == "export":
        return export_csv(Path(args[1]) if len(args) > 2 - 1 else
                          Path("logs/ledger_export.csv"))
    if cmd == "rotate":
        reason = args[1] if len(args) > 1 else "manual"
        print(f"[ledger] rotated -> {rotate(reason)}")
        return 0
    if cmd == "verify":
        return verify()
    print("usage: ledger.py [summarize|export [PATH]|rotate [REASON]|verify]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
