#!/usr/bin/env python3
"""The gardener: witness -> learn -> distill -> promote.

Grown code lives in grown/ (quarantine). Promotion copies it into
core/src/, rebuilds the body, replays EVERY witnessed case through the
live binary, runs the 12-point self-test and the golden fixtures, and
only then records the promotion in the ledger and grown/PROMOTED.md.
A grown library that fails any witness is deleted and the body rebuilt:
the canon never absorbs an unwitnessed rule.

    python3 tools/grow.py witness <method> '<args json>'   # run + learn
    python3 tools/grow.py seed <cases.jsonl>               # bulk learn
    python3 tools/grow.py distill <name> [min_cases]
    python3 tools/grow.py promote <name>
    python3 tools/grow.py list
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from saem.core import Core            # one door, source-id checked
from tools.ledger import append as ledger_append

GROWN = ROOT / "grown"
PROMOTED = GROWN / "PROMOTED.md"


def read_cases(method=None):
    store = ROOT / "knowledge" / "cases.tsv"
    out = []
    if not store.exists():
        return out
    for line in store.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        f = line.split("\t")
        if len(f) != 7:
            continue
        rec = {"seq": int(f[0]), "method": unesc(f[1]), "key": unesc(f[2]),
               "args": unesc(f[3]), "out": unesc(f[4]), "witness": f[5]}
        if method is None or rec["method"] == method:
            out.append(rec)
    return out


def unesc(s):
    return s.replace("\\\\", "\x00").replace("\\t", "\t").replace("\\n", "\n") \
            .replace("\\r", "\r").replace("\x00", "\\")


def cmd_witness(method, args_json):
    args = json.loads(args_json)
    with Core() as c:
        body = subprocess.run([sys.executable, str(ROOT / "tools" / "build.py"), "id"],
                              capture_output=True, text=True).stdout.strip()
        result = c.result(method, **args)
        c.result("grow.learn", method=method, args=args, result=result, witness=body)
    print(f"[grow] learned {method} under body {body[:12]}")
    return 0


def cmd_seed(path):
    n = 0
    with Core() as c:
        body = subprocess.run([sys.executable, str(ROOT / "tools" / "build.py"), "id"],
                              capture_output=True, text=True).stdout.strip()
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            c.result("grow.learn", method=e["method"], args=e["args"],
                     result=e["result"], witness=body)
            n += 1
    print(f"[grow] seeded {n} cases")
    return 0


def cmd_distill(name, min_cases=3):
    with Core() as c:
        r = c.result("grow.distill", name=name, min=min_cases)
    print(json.dumps(r))
    return 0 if r["ok"] else 1


def cmd_promote(name):
    cases = read_cases(name)
    if not cases:
        print(f"[grow] no cases for {name}")
        return 1
    src = GROWN / f"{name}.cpp"
    dst = ROOT / "core" / "src" / f"grown_{name}.cpp"
    if not src.exists():
        print(f"[grow] {src} missing; distill first")
        return 1
    dst.write_bytes(src.read_bytes())
    try:
        subprocess.run([sys.executable, str(ROOT / "tools" / "build.py"), "cli"],
                       check=True, cwd=ROOT)
        with Core() as c:
            boot = c.result("qcos.boot")
            if not boot["self"]["ok"]:
                raise RuntimeError(f"self-test failed: {boot['self']['failed']}")
            for rec in cases:
                got = c.call(name, **json.loads(rec["args"]))
                want = json.loads(rec["out"])
                if not got.get("ok") or got.get("result") != want:
                    raise RuntimeError(f"case {rec['seq']} replay mismatch")
        subprocess.run([sys.executable, str(ROOT / "tools" / "golden_qcos.py"), "check"],
                       check=True, cwd=ROOT)
    except Exception as e:
        dst.unlink(missing_ok=True)
        subprocess.run([sys.executable, str(ROOT / "tools" / "build.py"), "cli"],
                       check=True, cwd=ROOT)
        ledger_append({"op": "promote_fail", "name": name, "error": str(e)[:300]})
        print(f"[grow] PROMOTION REFUSED: {name}: {e}")
        return 1
    body = subprocess.run([sys.executable, str(ROOT / "tools" / "build.py"), "id"],
                          capture_output=True, text=True).stdout.strip()
    GROWN.mkdir(exist_ok=True)
    with open(PROMOTED, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
                f"{name} cases={len(cases)} body={body}\n")
    ledger_append({"op": "promote", "name": name, "cases": len(cases), "body": body})
    print(f"[grow] promoted {name} ({len(cases)} cases) into body {body[:12]}")
    return 0


def cmd_list():
    for rec in read_cases():
        print(f"{rec['seq']}\t{rec['method']}\t{rec['key'][:40]}")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "witness":
        return cmd_witness(sys.argv[2], sys.argv[3])
    if cmd == "seed":
        return cmd_seed(sys.argv[2])
    if cmd == "distill":
        return cmd_distill(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3)
    if cmd == "promote":
        return cmd_promote(sys.argv[2])
    if cmd == "list":
        return cmd_list()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
