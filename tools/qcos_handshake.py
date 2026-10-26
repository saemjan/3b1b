#!/usr/bin/env python3
"""qcos_handshake -- gen-3 four-tongue handshake.

Asks every live door (C++ core, JS rulers, generated Python client) the same
questions and compares answers BYTE for BYTE after canonicalisation (A1).

Gen-3 deltas:
  * body fingerprint DELEGATES to tools.build.source_id -- one canon for the
    tree id, the binary's --source-id and this gate (legacy hashed rel-to-src
    and failed permanently)
  * client roster checks argument ORDER against qcos.schema.json, not names
  * exit codes unified: 0 ok | 1 truth drift | 2 environment
    (missing canon/cli/node); --no-ruler is dev-only and priced in the receipt
  * ledger: logs/handshake.jsonl written through tools.ledger (schema-stamped,
    atomic, locked) instead of a raw append
  * selftest(): frozen witnesses for the canonical-text ruler (dump/loads/
    strip_nulls) and roster diffing -- no doors spawned
Articles enforced: A1 A2 A3 A5 A6 R19 R22.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

CLI = ROOT / "build" / ("saem_cli.exe" if os.name == "nt" else "saem_cli")
SCHEMA = ROOT / "qcos.schema.json"
LEDGER = ROOT / "logs" / "handshake.jsonl"
SCHEMA_VERSION = 3

try:
    import build as _build
except Exception:
    _build = None
try:
    from tools.ledger import append as _ledger_append
except Exception:
    _ledger_append = None

INT_KEY = re.compile(r"^(0|[1-9][0-9]*)$")


# ---------------------------------------------------------------- canonical text
class Num(str):
    """A number kept as the literal text the door printed (article A1)."""


def _lit(tok):
    return Num(tok)


def loads(text):
    return json.loads(text, parse_float=_lit, parse_int=_lit)


def dump(x):
    """Mirror of kernel.hpp canon(): insertion order, jsnum text, escaped keys."""
    if isinstance(x, Num):
        return str(x)
    if x is None:
        return "null"
    if x is True:
        return "true"
    if x is False:
        return "false"
    if isinstance(x, str):
        return json.dumps(x)
    if isinstance(x, (list, tuple)):
        return "[" + ",".join(dump(v) for v in x) + "]"
    if isinstance(x, dict):
        parts = []
        for k, v in x.items():
            if INT_KEY.match(str(k)):
                raise ValueError("integer-like object key %r (JS reorders it)" % k)
            parts.append(json.dumps(str(k)) + ":" + dump(v))
        return "{" + ",".join(parts) + "}"
    return json.dumps(x)


def strip_nulls(x):
    if isinstance(x, dict):
        return {k: strip_nulls(v) for k, v in x.items() if v is not None}
    if isinstance(x, list):
        return [strip_nulls(v) for v in x]
    return x


# ---------------------------------------------------------------- line protocol
class Missing(Exception):
    pass


class Dead(Exception):
    pass


class Door:
    """One process = one session. One JSON request per line, one answer per line."""

    def __init__(self, argv, label, timeout=25.0):
        self.label = label
        self.timeout = timeout
        self._id = 0
        self.err = tempfile.TemporaryFile(mode="w+", encoding="utf-8",
                                          errors="replace")
        try:
            self.p = subprocess.Popen(argv, stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=self.err,
                                      text=True, bufsize=1, cwd=ROOT)
        except OSError as e:
            raise Missing("%s: cannot start %s (%s)" % (label, argv[0], e))
        self.q = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        try:
            for line in self.p.stdout:
                self.q.put(line)
        except Exception:
            pass
        self.q.put(None)

    def ask(self, method, args=None):
        self._id += 1
        rid = self._id
        req = {"id": rid, "method": method, "args": args or {}}
        try:
            self.p.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
            self.p.stdin.flush()
        except (BrokenPipeError, ValueError):
            raise Dead(self.label, "door closed the pipe")
        try:
            line = self.q.get(timeout=self.timeout)
        except queue.Empty:
            raise Dead(self.label, "no answer in %ss -- hung on %s"
                       % (self.timeout, method))
        if line is None:
            raise Dead(self.label, "door hung up on %s" % method)
        env = loads(line)
        if env.get("id") != rid:                      # A2: state travels in JSON
            raise Dead(self.label, "answered a different question (%s != %s)"
                       % (env.get("id"), rid))
        return env

    def raw(self, text):
        """Send a malformed line. The door must answer, never throw (A3)."""
        try:
            self.p.stdin.write(text + "\n")
            self.p.stdin.flush()
        except (BrokenPipeError, ValueError):
            raise Dead(self.label, "door closed the pipe")
        try:
            line = self.q.get(timeout=self.timeout)
        except queue.Empty:
            raise Dead(self.label, "malformed line produced no answer")
        if line is None:
            raise Dead(self.label, "malformed line killed the door")
        return line

    def stderr_tail(self, n=400):
        try:
            self.err.seek(0)
            return self.err.read()[-n:]
        except Exception:
            return ""

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


# ---------------------------------------------------------------- roster helpers
def canon_methods():
    if not SCHEMA.exists():
        raise Missing("no %s -- run: python3 tools/qcosc.py qcos.cxn" % SCHEMA)
    sc = json.loads(SCHEMA.read_text(encoding="utf-8"))
    return sc, {m["name"] for m in sc["methods"]}


def core_roster(door):
    env = door.ask("core.methods")
    if not env.get("ok"):
        raise Dead("core", str(env.get("error")))
    got = env["result"]
    return sorted(got if isinstance(got, list) else got.get("methods", []))


def client_roster(sc):
    """Names AND argument order of the generated Python client (A1)."""
    path = ROOT / "saem" / "client.g.py"
    if not path.exists():
        raise Missing("no %s -- run: python3 tools/qcosc.py qcos.cxn" % path)
    text = path.read_text(encoding="utf-8")
    defs = re.findall(r"    def ([A-Za-z_][A-Za-z0-9_]*)\(self(?:, ([^)]*?))?\)",
                      text)
    have = {n: [p.split("=")[0].strip()
                for p in (sig.split(",") if sig else []) if p.strip()]
            for n, sig in defs}
    want = {m["name"]: m["name"].replace(".", "_") for m in sc["methods"]}
    missing = sorted(n for n, sym in want.items() if sym not in have)
    extra = sorted(s for s in have
                   if s not in set(want.values())
                   and s not in ("__init__", "_call", "close",
                                 "__enter__", "__exit__"))
    order_bad = sorted(m["name"] for m in sc["methods"]
                       if want[m["name"]] in have
                       and have[want[m["name"]]] != [a["name"] for a in m["args"]])
    return sorted(want), missing, extra, order_bad


def roster_diff(want, got):
    want, got = set(want), set(got)
    return sorted(want - got), sorted(got - want)


def sample_args(m):
    out = {}
    for p in m["args"]:
        if not p["required"]:
            continue
        t = p["type"]
        out[p["name"]] = {"string": "probe", "Key": "probe", "number": 1.0,
                          "Prob": 0.5, "uint32": 1, "Seed": 1, "int32": 1,
                          "bool": True, "any": {}, "Json": {}}.get(t, {})
    return out


def line(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- the gate
def main(argv):
    ap = argparse.ArgumentParser(prog="qcos_handshake", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cli", default=str(CLI))
    ap.add_argument("--ruler", action="append", default=None)
    ap.add_argument("--no-ruler", action="store_true",
                    help="DEV ONLY: skip JS rulers; priced in the receipt (A6)")
    ap.add_argument("--probe", action="append", default=[])
    ap.add_argument("--strict-null", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv[1:])

    if a.selftest:
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0

    t0 = time.time()
    fails, warns, notes = [], [], []
    doors = {}
    rulers_skipped = bool(a.no_ruler)
    env_missing = False

    def quiet():
        return a.quiet

    # ---- 0. canon is the authority (R19)
    try:
        sc, want = canon_methods()
    except Missing as e:
        line("[handshake] REFUSED (env): %s" % e)
        return 2
    if not want:
        line("[handshake] REFUSED: canon declares zero methods (R22)")
        return 1

    # ---- 1. body fingerprint via the ONE canon (build.source_id)
    tree_id = ""
    if _build is not None and _build.src_dir() is not None:
        try:
            tree_id = _build.source_id()
        except SystemExit:
            tree_id = ""
    if not os.path.exists(a.cli):
        line("[handshake] REFUSED (env): no %s -- run: python3 tools/build.py cli"
             % a.cli)
        return 2
    try:
        got_id = subprocess.run([a.cli, "--source-id"], capture_output=True,
                                text=True, timeout=10).stdout.strip()
    except Exception as e:
        line("[handshake] REFUSED (env): cannot run %s (%s)" % (a.cli, e))
        return 2
    if tree_id and got_id and not got_id.startswith("dev") and got_id != tree_id:
        fails.append("body: binary %s != tree %s -- rebuild"
                     % (got_id[:10], tree_id[:10]))
    elif not quiet():
        line("  body   %s  (tree %s)  one canon" % (got_id[:10], tree_id[:10]))

    # ---- 2. open every door
    try:
        doors["core"] = Door([a.cli], "core")
    except (Missing, Dead) as e:
        line("[handshake] REFUSED (env): %s" % e)
        return 2
    rulers = []
    if not a.no_ruler:
        if shutil.which("node") is None:
            line("[handshake] REFUSED (env): node absent; A6 forbids running "
                 "the handshake without its ruler (use --no-ruler for dev only)")
            for d in doors.values():
                d.close()
            return 2
        js = a.ruler or [p for p in ("tools/ref_bridge.js", "tools/ref_bridge_qcos.js")
                         if (ROOT / p).exists()]
        for j in js:
            path = ROOT / j
            if not path.exists():
                warns.append("ruler %s absent" % j)
                continue
            try:
                d = Door(["node", str(path)], "ruler:" + os.path.basename(j))
                doors[d.label] = d
                rulers.append(d.label)
            except (Missing, Dead) as e:
                fails.append(str(e))
    else:
        warns.append("RULERS SKIPPED by --no-ruler (dev only; CI must not)")

    # ---- 3. roster: same names, same order
    def roster(label, names, src):
        miss, extra = roster_diff(want, names)
        if not names:
            fails.append("%s: BLIND -- speaks no methods (R22)" % src)
        if miss or extra:
            fails.append("%s: missing %s | extra %s"
                         % (src, ",".join(miss) or "-", ",".join(extra) or "-"))
        elif not quiet():
            line("  %-22s %3d methods  agree" % (src, len(set(names))))
        return miss, extra

    try:
        roster("core", core_roster(doors["core"]), "core")
    except Dead as e:
        fails.append("%s: %s -- add core.methods to api.cpp" % (e.label, e))
    for label in rulers:
        try:
            roster(label, core_roster(doors[label]), label)
        except Dead as e:
            fails.append("%s: %s -- add 'core.methods' to this ruler (A6)"
                         % (e.label, e))
    try:
        _names, cmiss, cextra, order_bad = client_roster(sc)
        if cmiss or cextra:
            fails.append("client: missing %s | extra %s"
                         % (",".join(cmiss) or "-", ",".join(cextra) or "-"))
        if order_bad:
            fails.append("client: argument ORDER drifts from canon: %s (A1)"
                         % ",".join(order_bad))
        elif not quiet():
            line("  %-22s %3d methods  agree (order checked)"
                 % ("client:python", len(want)))
    except Missing as e:
        env_missing = True
        fails.append(str(e))

    # ---- 4. liveness: same names is not the same language
    probes = []
    for m in sc["methods"]:
        if m["kind"] != "pure":
            continue
        req = [p["name"] for p in m["args"] if p["required"]]
        if not req or set(req) <= {"x", "s", "seed"}:
            probes.append((m["name"], sample_args(m)))
    for spec in a.probe:
        name, _, js = spec.partition(":")
        probes.append((name.strip(), loads(js) if js else {}))
    agree = drift = 0
    if rulers and probes:
        for name, args in probes:
            try:
                ec = doors["core"].ask(name, args)
            except Dead as e:
                fails.append("core died on %s(%s): %s"
                             % (name, json.dumps(args), e))
                break
            for label in rulers:
                try:
                    er = doors[label].ask(name, args)
                except Dead as e:
                    fails.append("%s died on %s: %s" % (label, name, e))
                    continue
                if bool(ec.get("ok")) != bool(er.get("ok")):
                    drift += 1
                    fails.append("%s: %s ok=%s but %s ok=%s"
                                 % (name, "core", ec.get("ok"),
                                    label.split(":")[-1], er.get("ok")))
                    continue
                if not ec.get("ok"):
                    agree += 1
                    continue
                try:
                    lhs = dump(strip_nulls(ec["result"])
                               if not a.strict_null else ec["result"])
                    rhs = dump(strip_nulls(er["result"])
                               if not a.strict_null else er["result"])
                except ValueError as e:
                    drift += 1
                    fails.append("%s: %s -- key order is not canon-safe" % (name, e))
                    continue
                if lhs == rhs:
                    agree += 1
                else:
                    drift += 1
                    fails.append("%s: A1 drift -- core %s\n%s:        ruler %s"
                                 % (name, lhs[:90], " " * len(name), rhs[:90]))
        if not quiet():
            line("  probes                 %d agree, %d drift" % (agree, drift))

    # ---- 5. the door must never throw (A3)
    try:
        raw = doors["core"].raw('{"id":999,"method":"gen.make","args":{')
        env = loads(raw)
        if env.get("id") != 999 or env.get("ok") is not False:
            fails.append("malformed line: door did not recover the id (A3)")
        elif not quiet():
            line("  malformed line         id recovered, error reported")
    except Dead as e:
        fails.append("A3 breach: %s" % e)
    except Exception:
        fails.append("A3 breach: malformed line produced no JSON answer")

    for d in doors.values():
        tail = d.stderr_tail(200)
        if tail:
            notes.append("%s stderr: %s" % (d.label, tail.strip().replace("\n", " | ")))
        d.close()

    # ---- 6. verdict + priced ledger (A5)
    verdict = "refused" if fails else "ok"
    for f in fails:
        line("  FAIL  %s" % f)
    for w in warns:
        line("  warn  %s" % w)
    for n in notes:
        line("  note  %s" % n)
    line("[handshake] %s  (%d methods, %d doors, %.1fs)%s"
         % (verdict.upper(), len(want), len(doors), time.time() - t0,
            "  [RULERS SKIPPED]" if rulers_skipped else ""))
    receipt = {"gate": "qcos_handshake", "schema_version": SCHEMA_VERSION,
               "verdict": verdict, "body": got_id[:10], "tree": tree_id[:10],
               "methods": len(want), "doors": sorted(doors),
               "probes_agree": agree, "probes_drift": drift,
               "rulers_skipped": rulers_skipped,
               "fails": fails, "warns": warns}
    if a.json:
        print(json.dumps(receipt, ensure_ascii=False))
    if _ledger_append is not None:
        try:
            _ledger_append(receipt, ledger=LEDGER)
        except Exception:
            pass
    if env_missing and not fails:
        return 2
    return 1 if fails else 0


# ---------------------------------------------------------------- witness
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    env = loads('{"id":1,"ok":true,"result":{"a":1.50,"b":2,"c":[3.10,null]}}')
    want("num:literal-kept", dump(env["result"])
         == '{"a":1.50,"b":2,"c":[3.10,null]}')
    want("strip_nulls", dump(strip_nulls(env["result"]))
         == '{"a":1.50,"b":2,"c":[3.10]}')
    try:
        dump({"1": 2})
        want("guard:int-key", False)
    except ValueError:
        want("guard:int-key", True)
    miss, extra = roster_diff(["a", "b"], ["b", "c"])
    want("roster_diff", miss == ["a"] and extra == ["c"])
    miss, extra = roster_diff(["a"], ["a"])
    want("roster_diff:clean", not miss and not extra)
    want("sample_args:required-only",
         sample_args({"args": [{"name": "x", "required": True, "type": "number"},
                               {"name": "y", "required": False, "type": "number"}]})
         == {"x": 1.0})
    return checks


if __name__ == "__main__":
    sys.exit(main(sys.argv))
