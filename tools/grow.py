#!/usr/bin/env python3
"""The gardener: witness -> learn -> distill -> promote.  (Gen-3 v3)
Every sub-command now writes a ledger receipt. Promotion verifies the
rebuild. Exit codes: 0 ok · 1 drift/fail · 2 environment.
"""
import json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from saem.core import Core
from tools.ledger import append as ledger_append

GROWN = ROOT / "grown"
PROMOTED = GROWN / "PROMOTED.md"
CASES = ROOT / "knowledge" / "cases.jsonl"   # migrated from TSV → JSONL
SCHEMA_VERSION = 3

# ---------------------------------------------------------------- helpers
def _receipt(op, **kw):
    kw.setdefault("op", op)
    kw["schema_version"] = SCHEMA_VERSION
    kw["iso_ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ledger_append(kw)

def _body_id():
    r = subprocess.run([sys.executable, str(ROOT/"tools"/"build.py"), "id"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"

# ---------------------------------------------------------------- cases I/O (JSONL)
def read_cases(method=None):
    if not CASES.exists():
        return []
    out = []
    for line in CASES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if method is None or rec.get("method") == method:
            out.append(rec)
    return out

def append_case(rec):
    CASES.parent.mkdir(parents=True, exist_ok=True)
    with CASES.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ---------------------------------------------------------------- commands
def cmd_witness(method, args_json):
    args = json.loads(args_json)
    body = _body_id()
    with Core() as c:
        result = c.result(method, **args)
        c.result("grow.learn", method=method, args=args, result=result, witness=body)
    _receipt("grow_witness", method=method, body=body)
    print(f"[grow] learned {method} under body {body[:12]}")
    return 0

def cmd_seed(path):
    body = _body_id()
    n = 0
    with Core() as c:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            c.result("grow.learn", method=e["method"], args=e["args"],
                     result=e["result"], witness=body)
            n += 1
    _receipt("grow_seed", count=n, body=body)
    print(f"[grow] seeded {n} cases")
    return 0

def cmd_distill(name, min_cases=3):
    with Core() as c:
        r = c.result("grow.distill", name=name, min=min_cases)
    _receipt("grow_distill", name=name, ok=r.get("ok", False))
    print(json.dumps(r))
    return 0 if r.get("ok") else 1

def cmd_promote(name):
    cases = read_cases(name)
    if not cases:
        print(f"[grow] no cases for {name}")
        _receipt("grow_promote_fail", name=name, error="no_cases")
        return 1

    src = GROWN / f"{name}.cpp"
    dst = ROOT / "core" / "src" / f"grown_{name}.cpp"
    if not src.exists():
        print(f"[grow] {src} missing; distill first")
        _receipt("grow_promote_fail", name=name, error="missing_source")
        return 1

    dst.write_bytes(src.read_bytes())
    try:
        r = subprocess.run([sys.executable, str(ROOT/"tools"/"build.py"), "cli"],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            raise RuntimeError(f"build failed: {r.stderr[-500:]}")

        with Core() as c:
            boot = c.result("qcos.boot")
            if not boot["self"]["ok"]:
                raise RuntimeError(f"self-test failed: {boot['self']['failed']}")
            for rec in cases:
                got = c.call(name, **json.loads(rec["args"]))
                want = json.loads(rec["out"])
                if not got.get("ok") or got.get("result") != want:
                    raise RuntimeError(f"case {rec['seq']} replay mismatch")

        subprocess.run([sys.executable, str(ROOT/"tools"/"golden_qcos.py"), "check"],
                       check=True, cwd=ROOT, capture_output=True)
    except Exception as e:
        dst.unlink(missing_ok=True)
        rb = subprocess.run([sys.executable, str(ROOT/"tools"/"build.py"), "cli"],
                            capture_output=True, text=True, cwd=ROOT)
        rv = subprocess.run([sys.executable, str(ROOT/"tools"/"build.py"), "verify"],
                            capture_output=True, text=True, cwd=ROOT)
        _receipt("grow_promote_fail", name=name, error=str(e)[:300],
                 rebuild_ok=rb.returncode == 0, verify_ok=rv.returncode == 0)
        print(f"[grow] PROMOTION REFUSED: {name}: {e}")
        return 1

    body = _body_id()
    GROWN.mkdir(exist_ok=True)
    with PROMOTED.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
                f"{name} cases={len(cases)} body={body}\n")
    _receipt("grow_promote", name=name, cases=len(cases), body=body)
    print(f"[grow] promoted {name} ({len(cases)} cases) into body {body[:12]}")
    return 0

def cmd_list():
    cases = read_cases()
    if not cases:
        print("[grow] case store empty")
        _receipt("grow_list", count=0)
        return 0
    for rec in cases:
        print(f"{rec.get('seq','?')}\t{rec.get('method','?')}\t{rec.get('key','')[:40]}")
    _receipt("grow_list", count=len(cases))
    return 0

# ---------------------------------------------------------------- selftest
def selftest():
    bad = 0
    # 1. JSONL round-trip
    tmp = ROOT / "knowledge" / "_selftest_cases.jsonl"
    rec = {"seq": 1, "method": "t", "key": "k", "args": "{}", "out": "{}", "witness": "w"}
    tmp.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    got = [json.loads(l) for l in tmp.read_text().splitlines() if l.strip()]
    if got != [rec]:
        print("[selftest] JSONL round-trip FAIL"); bad += 1
    else:
        print("[selftest] JSONL round-trip ok")
    tmp.unlink(missing_ok=True)
    print(f"[selftest] {1-bad}/1 passed")
    return 1 if bad else 0

# ---------------------------------------------------------------- main
def main():
    if "--selftest" in sys.argv:
        return selftest()
    if len(sys.argv) < 2:
        print(__doc__); return 1
    cmd = sys.argv[1]
    try:
        if cmd == "witness":  return cmd_witness(sys.argv[2], sys.argv[3])
        if cmd == "seed":     return cmd_seed(sys.argv[2])
        if cmd == "distill":  return cmd_distill(sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 3)
        if cmd == "promote":  return cmd_promote(sys.argv[2])
        if cmd == "list":     return cmd_list()
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"[grow] ENV error: {e}", file=sys.stderr)
        return 2
    print(__doc__); return 1

if __name__ == "__main__":
    sys.exit(main())
