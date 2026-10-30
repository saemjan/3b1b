#!/usr/bin/env python3
"""Differential test: the C++ core against the JavaScript reference, case by case.

Every file in tests/diff/cases/*.jsonl holds one JSON case per line:

    {"name": "kinematics question", "method": "gen.make", "args": {"id": "K1", "seed": 7}}

Optional fields:
    "args_file"   path (relative to tests/diff/) of a JSON file to use as the args instead of "args"
    "tol"         relative tolerance for numbers (default 1e-9; absolute floor 1e-12)
    "ignore"      dotted paths to drop from both results before comparing ("result.meta.id", "result.picks.*.nudge")
    "regex"       {"path": "pattern"}: do not compare engines; require both answers at `path` to match the pattern
    "error"       true when both engines are expected to refuse (the messages are not compared)

null and a missing key are the same thing (JavaScript drops undefined fields, the core writes null).

    python3 tests/diff/run.py                 run everything
    python3 tests/diff/run.py cases_ef        only files whose name contains the text
    python3 tests/diff/run.py -k selftest     only cases whose name contains the text
    python3 tests/diff/run.py -v              show every difference, not just the first few
"""
import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def load_cases(patterns, key):
    cases = []
    for path in sorted(glob.glob(os.path.join(HERE, "cases", "*.jsonl"))):
        base = os.path.basename(path)
        if patterns and not any(p in base for p in patterns):
            continue
        for n, line in enumerate(open(path, encoding="utf-8"), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            c = json.loads(line)
            c["_src"] = "%s:%d" % (base, n)
            if "args_file" in c:
                c["args"] = json.load(open(os.path.join(HERE, c["args_file"]), encoding="utf-8"))
            if key and key not in c.get("name", ""):
                continue
            cases.append(c)
    return cases


def run_engine(cmd, cases, label):
    lines = [json.dumps({"id": i, "method": c["method"], "args": c.get("args", {})}, ensure_ascii=False) for i, c in enumerate(cases)]
    p = subprocess.run(cmd, input="\n".join(lines) + "\n", capture_output=True, text=True, encoding="utf-8", timeout=1800)
    if p.returncode:
        sys.stderr.write(p.stderr)
        raise SystemExit("%s exited with %d" % (label, p.returncode))
    out = {}
    for line in p.stdout.splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def drop(obj, parts):
    if not parts:
        return
    k, rest = parts[0], parts[1:]
    if isinstance(obj, dict):
        if not rest:
            obj.pop(k, None)
        elif k in obj:
            drop(obj[k], rest)
        elif k == "*":
            for v in obj.values():
                drop(v, parts[1:] if not rest else rest)
    elif isinstance(obj, list):
        idx = range(len(obj)) if k == "*" else ([int(k)] if k.isdigit() and int(k) < len(obj) else [])
        for i in idx:
            if not rest:
                obj[i] = None
            else:
                drop(obj[i], rest)


def norm(x):
    if isinstance(x, dict):
        return {k: norm(v) for k, v in x.items() if v is not None}
    if isinstance(x, list):
        return [norm(v) for v in x]
    return x


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def same(a, b, tol, path, diffs, limit):
    if len(diffs) >= limit:
        return
    if is_num(a) and is_num(b):
        if a == b:
            return
        if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
            return
        if abs(a - b) <= max(1e-12, tol * max(abs(a), abs(b))):
            return
        diffs.append("%s: js=%r  c++=%r" % (path, a, b))
    elif isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                diffs.append("%s.%s: only in c++ (%s)" % (path, k, short(b[k])))
            elif k not in b:
                diffs.append("%s.%s: only in js (%s)" % (path, k, short(a[k])))
            else:
                same(a[k], b[k], tol, path + "." + k, diffs, limit)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append("%s: length js=%d c++=%d" % (path, len(a), len(b)))
            n = min(len(a), len(b))
        else:
            n = len(a)
        for i in range(n):
            same(a[i], b[i], tol, "%s[%d]" % (path, i), diffs, limit)
    elif a != b or type(a) != type(b):
        if is_num(a) != is_num(b) or isinstance(a, bool) != isinstance(b, bool) or type(a) != type(b):
            diffs.append("%s: js=%s  c++=%s" % (path, short(a), short(b)))
        else:
            diffs.append("%s: js=%s  c++=%s" % (path, short(a), short(b)))


def short(x, n=110):
    s = json.dumps(x, ensure_ascii=False)
    return s if len(s) <= n else s[: n - 1] + "…"


def at(obj, path):
    for part in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part)
        elif isinstance(obj, list) and part.isdigit() and int(part) < len(obj):
            obj = obj[int(part)]
        else:
            return None
    return obj


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="only case files whose name contains one of these")
    ap.add_argument("-k", dest="key", default="", help="only cases whose name contains this")
    ap.add_argument("-v", action="store_true", help="show every difference")
    ap.add_argument("--cli", default=os.path.join(ROOT, "build", "saem_cli"))
    ap.add_argument("--no-build", action="store_true")
    a = ap.parse_args()

    if not a.no_build:
        import build
        build.build("cli", quiet=True)
    cases = load_cases(a.files, a.key)
    if not cases:
        raise SystemExit("no cases found")
    js = run_engine(["node", os.path.join(ROOT, "tools", "ref_bridge.js")], cases, "reference")
    cc = run_engine([a.cli], cases, "core")

    failed = 0
    by_file = {}
    for i, c in enumerate(cases):
        r1, r2 = js.get(i), cc.get(i)
        diffs = []
        if r1 is None or r2 is None:
            diffs.append("no answer from %s" % ("reference" if r1 is None else "core"))
        elif c.get("error"):
            if r1["ok"] or r2["ok"]:
                diffs.append("expected both to refuse; js ok=%s, c++ ok=%s" % (r1["ok"], r2["ok"]))
        elif c.get("regex"):
            for path, pat in c["regex"].items():
                for who, r in (("js", r1), ("c++", r2)):
                    v = at(r.get("result"), path) if r["ok"] else None
                    if not (isinstance(v, str) and re.search(pat, v)):
                        diffs.append("%s: %s answered %s, wanted /%s/" % (path, who, short(v), pat))
        elif r1["ok"] != r2["ok"]:
            diffs.append("js ok=%s (%s) but c++ ok=%s (%s)" % (r1["ok"], r1.get("error", ""), r2["ok"], r2.get("error", "")))
        elif r1["ok"]:
            x, y = json.loads(json.dumps(r1["result"])), json.loads(json.dumps(r2["result"]))
            for p in c.get("ignore", []):
                drop({"result": x}, p.split("."))
                drop({"result": y}, p.split("."))
            same(norm(x), norm(y), c.get("tol", 1e-9), "result", diffs, 1000 if a.v else 6)
        else:
            diffs.append("both refused: js=%r c++=%r" % (r1.get("error"), r2.get("error")))
            diffs = diffs if c.get("error") is False else []  # a shared refusal counts as agreement
        f = by_file.setdefault(c["_src"].split(":")[0], [0, 0])
        f[0] += 1
        if diffs:
            failed += 1
            f[1] += 1
            print("FAIL %s  %s  [%s]" % (c["_src"], c.get("name", ""), c["method"]))
            for d in diffs[: (1000 if a.v else 6)]:
                print("     " + d)
    print()
    for name, (n, bad) in sorted(by_file.items()):
        print("%-28s %4d cases  %s" % (name, n, "ok" if not bad else "%d differ" % bad))
    print("\n%d of %d cases agree" % (len(cases) - failed, len(cases)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
