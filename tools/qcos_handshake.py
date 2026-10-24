#!/usr/bin/env python3
"""qcos_handshake -- the four-tongue handshake.

Launches the C++ door (saem_cli), the JavaScript rulers (ref_bridge*.js),
introspects the generated Python client, and asks all of them the same
question: WHICH METHODS DO YOU SPEAK?

Names are not enough. The handshake then calls a probe set through every
live door and compares the answers byte for byte after canonicalisation,
so a number printed differently in two tongues is a refusal, not a warning.

    python3 tools/qcosc.py qcos.cxn          # emit the bindings
    python3 tools/build.py cli               # build the door
    python3 tools/qcos_handshake.py          # ask them to agree
    python3 tools/qcos_handshake.py --probe gen.make:{"id":"K1","seed":7}

Articles enforced
  A1  a number prints identically everywhere   -> canon-string compare
  A2  the door holds no hidden state           -> id echo, fresh session
  A3  the core reports its debt                -> malformed line must answer
  A5  the ledger is append-only                -> logs/handshake.jsonl
  A6  the ruler is a reference, never a fallback-> ruler is probed, not used
  R19 one canon, two builders                  -> the canon is the authority
  R22 a blind witness fails the gate           -> an empty roster is a refusal
"""
import argparse
import hashlib
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "build", "saem_cli")
SCHEMA = os.path.join(ROOT, "qcos.schema.json")
SRC = os.path.join(ROOT, "core", "src")
LEDGER = os.path.join(ROOT, "logs", "handshake.jsonl")
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
    """The diff harness says null == missing; the handshake agrees by default."""
    if isinstance(x, dict):
        return {k: strip_nulls(v) for k, v in x.items() if v is not None}
    if isinstance(x, list):
        return [strip_nulls(v) for v in x]
    return x


# ---------------------------------------------------------------- line protocol
class Door:
    """One process = one session. One JSON request per line, one answer per line."""

    def __init__(self, argv, label, timeout=25.0):
        self.label = label
        self.timeout = timeout
        self._id = 0
        self.err = tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace")
        try:
            self.p = subprocess.Popen(
                argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self.err, text=True, bufsize=1)
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
            raise Dead(self.label, "no answer in %ss -- hung on %s" % (self.timeout, method))
        if line is None:
            raise Dead(self.label, "door hung up on %s" % method)
        env = loads(line)
        if env.get("id") != rid:                       # A2: state travels in the JSON
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


class Missing(Exception):
    pass


class Dead(Exception):
    pass


# ---------------------------------------------------------------- fingerprint
def core_files(src):
    out = []
    for base, _dirs, names in os.walk(src):
        for n in names:
            if n.endswith((".cpp", ".hpp", ".inc", ".h", ".c")):
                out.append(os.path.join(base, n))
    return sorted(out, key=lambda p: os.path.relpath(p, src).replace(os.sep, "/"))


def source_id(src):
    h = hashlib.sha256()
    for p in core_files(src):
        data = open(p, "rb").read().replace(b"\r\n", b"\n")
        rel = os.path.relpath(p, src).replace(os.sep, "/")
        h.update(rel.encode() + b"\0" + str(len(data)).encode() + b"\0" + data + b"\0")
    return h.hexdigest()


# ---------------------------------------------------------------- roster
def canon_methods():
    if not os.path.exists(SCHEMA):
        raise Missing("no %s -- run: python3 tools/qcosc.py qcos.cxn" % SCHEMA)
    sc = json.load(open(SCHEMA, encoding="utf-8"))
    return sc, {m["name"] for m in sc["methods"]}


def core_roster(door):
    env = door.ask("core.methods")
    if not env.get("ok"):
        raise Dead("core", str(env.get("error")))
    got = env["result"]
    return sorted(got if isinstance(got, list) else got.get("methods", []))


def client_roster(sc):
    """Does the generated Python client define a method for every canon entry?"""
    path = os.path.join(ROOT, "saem", "client.g.py")
    if not os.path.exists(path):
        raise Missing("no %s -- run: python3 tools/qcosc.py qcos.cxn" % path)
    text = open(path, encoding="utf-8").read()
    have = set(re.findall(r"^    def ([A-Za-z_][A-Za-z0-9_]*)\(", text, re.M))
    want = {}
    for m in sc["methods"]:
        want[m["name"]] = m["name"].replace(".", "_")
    missing = sorted(n for n, sym in want.items() if sym not in have)
    extra = sorted(s for s in have if s not in set(want.values()) and s not in
                   ("__init__", "_call", "close", "__enter__", "__exit__"))
    return sorted(want), missing, extra


def sample_args(m):
    """Build a probe payload from the canon's own type declarations."""
    out = {}
    for p in m["args"]:
        if not p["required"]:
            continue
        t = p["type"]
        out[p["name"]] = {"string": "probe", "Key": "probe", "number": 1.0,
                          "Prob": 0.5, "uint32": 1, "Seed": 1, "int32": 1,
                          "bool": True, "any": {}, "Json": {}}.get(t, {})
    return out


# ---------------------------------------------------------------- report
def line(msg):
    print(msg, flush=True)


def main(argv):
    ap = argparse.ArgumentParser(prog="qcos_handshake", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cli", default=CLI)
    ap.add_argument("--ruler", action="append", default=None,
                    help="JS ruler (default: both ref_bridge*.js)")
    ap.add_argument("--no-ruler", action="store_true",
                    help="skip the JavaScript rulers (dev only; CI must not)")
    ap.add_argument("--probe", action="append", default=[],
                    help='extra probe, e.g. --probe gen.make:{"id":"K1","seed":7}')
    ap.add_argument("--strict-null", action="store_true",
                    help="do not treat null as missing")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv[1:])

    t0 = time.time()
    fails, warns, notes = [], [], []
    doors = {}

    def quiet():
        return a.quiet

    # ---- 0. the canon is the authority (R19)
    try:
        sc, want = canon_methods()
    except Missing as e:
        line("[handshake] REFUSED: %s" % e)
        return 1
    if not want:
        line("[handshake] REFUSED: canon declares zero methods (R22)")
        return 1

    # ---- 1. body fingerprint
    tree_id = source_id(SRC) if os.path.isdir(SRC) else ""
    if not os.path.exists(a.cli):
        line("[handshake] REFUSED: no %s -- run: python3 tools/build.py cli" % a.cli)
        return 1
    try:
        got_id = subprocess.run([a.cli, "--source-id"], capture_output=True,
                                text=True, timeout=10).stdout.strip()
    except Exception as e:
        line("[handshake] REFUSED: cannot run %s (%s)" % (a.cli, e))
        return 1
    if tree_id and got_id and not got_id.startswith("dev") and got_id != tree_id:
        fails.append("body: binary %s != tree %s -- rebuild" % (got_id[:10], tree_id[:10]))
    elif not quiet():
        line("  body   %s  (tree %s)" % (got_id[:10], tree_id[:10]))

    # ---- 2. open every door
    try:
        doors["core"] = Door([a.cli], "core")
    except (Missing, Dead) as e:
        line("[handshake] REFUSED: %s" % e)
        return 1
    rulers = []
    if not a.no_ruler:
        js = a.ruler or [p for p in
                         ("tools/ref_bridge.js", "tools/ref_bridge_qcos.js")
                         if os.path.exists(os.path.join(ROOT, p))]
        for j in js:
            path = os.path.join(ROOT, j)
            if not os.path.exists(path):
                warns.append("ruler %s absent" % j)
                continue
            try:
                d = Door(["node", path], "ruler:" + os.path.basename(j))
                doors[d.label] = d
                rulers.append(d.label)
            except (Missing, Dead) as e:
                fails.append(str(e))

    # ---- 3. roster: does everyone speak the same names?
    def roster(label, names, src):
        got = set(names)
        miss, extra = sorted(want - got), sorted(got - want)
        if not names:
            fails.append("%s: BLIND -- speaks no methods (R22)" % src)
        if miss or extra:
            msg = "%s: missing %s | extra %s" % (
                src, ",".join(miss) or "-", ",".join(extra) or "-")
            fails.append(msg)
        elif not quiet():
            line("  %-22s %3d methods  agree" % (src, len(got)))
        return miss, extra

    try:
        roster("core", core_roster(doors["core"]), "core")
    except Dead as e:
        fails.append("%s: %s\n         add to api.cpp:\n"
                     '         const Registrar c0("core.methods", [](const Json&) -> Json {\n'
                     "           Json o = Json::array();\n"
                     "           for (const auto& m : saem::methods()) o.push(Json(m));\n"
                     "           return o;\n"
                     "         });" % (e.label, e))
    for label in rulers:
        try:
            roster(label, core_roster(doors[label]), label)
        except Dead as e:
            fails.append("%s: %s -- add 'core.methods' to this ruler (A6)" % (e.label, e))
    try:
        _, cmiss, cextra = client_roster(sc)
        if cmiss or cextra:
            fails.append("client: missing %s | extra %s"
                         % (",".join(cmiss) or "-", ",".join(cextra) or "-"))
        elif not quiet():
            line("  %-22s %3d methods  agree" % ("client:python", len(want)))
    except Missing as e:
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

    if rulers and probes:
        agree = drift = 0
        for name, args in probes:
            try:
                ec = doors["core"].ask(name, args)
            except Dead as e:
                fails.append("core died on %s(%s): %s" % (name, json.dumps(args), e))
                break
            for label in rulers:
                try:
                    er = doors[label].ask(name, args)
                except Dead as e:
                    fails.append("%s died on %s: %s" % (label, name, e))
                    continue
                if bool(ec.get("ok")) != bool(er.get("ok")):
                    drift += 1
                    fails.append("%s: %s ok=%s but %s ok=%s" % (
                        name, "core", ec.get("ok"), label.split(":")[-1], er.get("ok")))
                    continue
                if not ec.get("ok"):
                    agree += 1
                    continue
                try:
                    lhs = dump(strip_nulls(ec["result"]) if not a.strict_null else ec["result"])
                    rhs = dump(strip_nulls(er["result"]) if not a.strict_null else er["result"])
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

    # ---- 6. verdict + ledger (A5)
    verdict = "refused" if fails else "ok"
    for f in fails:
        line("  FAIL  %s" % f)
    for w in warns:
        line("  warn  %s" % w)
    for n in notes:
        line("  note  %s" % n)
    line("[handshake] %s  (%d methods, %d doors, %.1fs)"
         % (verdict.upper(), len(want), len(doors), time.time() - t0))

    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "wall": time.time(), "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "verdict": verdict, "body": got_id[:10], "tree": tree_id[:10],
            "methods": len(want), "doors": sorted(doors), "fails": fails,
            "warns": warns}, ensure_ascii=False) + "\n")
    return 0 if verdict == "ok" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
