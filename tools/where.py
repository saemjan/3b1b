#!/usr/bin/env python3
"""where.py — the resume compass (live state probe).

docs/STATUS.md can go stale when a session ends mid-step. This script cannot:
it looks at the files, asks both doors (C++ core, JS ruler) which methods they
serve, reads the last step receipt from the append-only ledger, and prints the
Phase-A artifact checklist. Observation only: it writes nothing and receipts
nothing — outcomes are receipted by the gates themselves (A5).

    python3 tools/where.py            # files, artifacts, step pointer, debts
    python3 tools/where.py --diff     # also run the differential gate
    python3 tools/where.py --selftest

Exit codes: 0 printed · 1 selftest drift · 2 probe machinery broken.
Gen-3: stdlib only, deterministic, fail-closed (a silent door is printed debt).
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PHASE_A_ARTIFACTS = [
    ("qcos.schema.json", "step 1"),
    ("core/src/api_registry.g.cpp", "step 1"),
    ("saem/client.g.py", "step 1"),
    ("SaemQcos/Client.g.cs", "step 1"),
    ("tools/ref_bridge.gen.js", "step 1"),
    ("tests/diff/cases/canon.jsonl", "step 1"),
    ("reference/src/ef.js", "step 2"),
    ("reference/src/cbt.js", "step 2"),
    ("reference/src/gen.js", "step 2"),
    ("reference/src/cos.js", "step 2"),
    ("tests/corpus/requests.jsonl", "step 3"),
    ("tests/corpus/deferred.json", "step 3"),
    ("tests/corpus/canon_queue.json", "step 3"),
    ("knowledge_base/curriculum/feynman_vol2.json", "step 4"),
    ("grown/.gitkeep", "step 4"),
]


def methods(cmd, timeout=60):
    """Ask a JSON-line door which methods it serves. None if it cannot answer."""
    try:
        p = subprocess.run(cmd,
                           input='{"id":1,"method":"core.methods","args":{}}\n',
                           capture_output=True, text=True, timeout=timeout,
                           cwd=ROOT)
        return set(json.loads(p.stdout.splitlines()[0])["result"])
    except Exception:
        return None


def line_count(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def last_step(ledger=None):
    path = Path(ledger) if ledger else ROOT / "logs" / "render_ledger.jsonl"
    out = None
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("op") == "step":
                out = e
    except OSError:
        return None
    return out


def group_by_prefix(names):
    groups = {}
    for m in sorted(names):
        g, _, rest = m.partition(".")
        groups.setdefault(g, []).append(rest)
    return groups


def main(argv):
    if "--selftest" in argv:
        return selftest()
    print("== files (lines) ==")
    for pat in ("core/src/*.cpp", "core/src/*.hpp", "saem/*.py",
                "tests/corpus/*.json*", "docs/*.md"):
        found = sorted(glob.glob(str(ROOT / pat)))
        if found:
            print(pat)
            for f in found:
                print("   %-38s %5d" % (os.path.basename(f), line_count(f)))
    print("   tools/*.py count: %d   root engines: %d"
          % (len(glob.glob(str(ROOT / "tools" / "*.py"))),
             len(glob.glob(str(ROOT / "*_engine.py"))) + 1))

    print("\n== phase A artifacts ==")
    for rel, step in PHASE_A_ARTIFACTS:
        print("  [%-7s] %-46s (%s)"
              % ("ok" if (ROOT / rel).exists() else "MISSING", rel, step))

    st = last_step()
    print("\n== step pointer (ledger) ==")
    if st:
        print("  last receipted: step %s phase %s exit %s"
              % (st.get("n"), st.get("phase"), st.get("exit")))
    else:
        print("  no step receipt yet — begin at §21 step 1")

    ref = methods(["node", str(ROOT / "tools" / "ref_bridge.js")])
    cc = methods([str(ROOT / "build" / ("saem_cli.exe" if os.name == "nt"
                                        else "saem_cli"))])
    print("\n== methods (doors asked live) ==")
    if ref is None:
        print("  [debt] JS ruler silent (node or reference/src missing) -> step 2")
    if cc is None:
        print("  [debt] build/saem_cli silent -> run tools/build.py cli (step 1/5)")
    if ref is not None and cc is not None:
        print("  C++ serves %d of %d reference methods" % (len(ref & cc), len(ref)))
        for g, rest in group_by_prefix(ref - cc).items():
            print("    missing in C++: %s -> %s" % (g, ",".join(rest)))
        extra = sorted(cc - ref)
        if extra:
            print("    only in C++: %s" % ",".join(extra))

    if "--diff" in argv:
        print("\n== differential gate ==")
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "parity_line.py")],
                           cwd=ROOT)
        return r.returncode if r.returncode in (0, 1) else 2
    return 0


def selftest():
    import tempfile
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    g = group_by_prefix(["gen.make", "core.hash", "gen.fmt"])
    want("group-prefix", g == {"core": ["hash"], "gen": ["fmt", "make"]}, str(g))
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        f = td / "x.py"
        f.write_text("a\nb\nc\n", encoding="utf-8")
        want("line-count", line_count(str(f)) == 3)
        want("line-count-missing", line_count(str(td / "nope")) == 0)
        led = td / "led.jsonl"
        led.write_text('{"op":"other"}\n{"op":"step","n":3,"phase":"A","exit":0}\n'
                       '{"op":"step","n":4,"phase":"A","exit":0}\n', encoding="utf-8")
        st = last_step(led)
        want("last-step", st is not None and st["n"] == 4, str(st))
        want("last-step-missing", last_step(td / "nope.jsonl") is None)
        door = td / "door.py"
        door.write_text('import sys,json\nfor l in sys.stdin:\n'
                        '    print(json.dumps({"id":1,"ok":True,"result":["a.b","a.c"]}))\n',
                        encoding="utf-8")
        want("methods-door", methods([sys.executable, str(door)]) == {"a.b", "a.c"})
        want("methods-silent", methods([str(td / "no-binary")]) is None)
    fails = 0
    for name, ok, detail in checks:
        print("[selftest] %-22s %s %s" % (name, "ok" if ok else "DRIFT", detail))
        fails += 0 if ok else 1
    print("[selftest] %d/%d passed" % (len(checks) - fails, len(checks)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
