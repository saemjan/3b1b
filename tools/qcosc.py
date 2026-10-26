#!/usr/bin/env python3
"""qcosc -- gen-3 QCOS protocol compiler (core tongue #1).

One canon (qcos.cxn) in; four tongues out (C++, Python, C#, JavaScript),
plus the parity witness corpus (diff), the runtime schema, and a HANDSHAKE
that proves all four emitted bindings agree on method set AND argument
order (A1/A6: the JS bridge is the ruler; binding drift is a broken article,
caught here at compile time instead of at parity_line runtime).

Gen-3 deltas:
  * paths resolve from the repo root, never the CWD (A2)
  * selftest(): frozen witnesses for lexer/parser/Checker/emitters/
    handshake/determinism (A5)
  * ledger receipt per run (gate "qcosc")
  * exit codes: 0 ok | 1 refused/stale/handshake-mismatch | 2 env (no canon)
  * --handshake / --verify / --emit X / --json / --github-summary / --selftest
Zero dependencies. Deterministic: same canon -> byte-identical output (A1).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA_VERSION = 3
try:
    from tools.ledger import append as _ledger
except Exception:
    _ledger = None


class LexError(Exception): pass
class ParseError(Exception): pass
class CanonError(Exception):
    """A constitutional violation detected at compile time. Fail closed."""


# ---------------------------------------------------------------- 1. lexer
_TOKEN_SPEC = [
    ("SKIP",    r"[ \t\r]+"),
    ("COMMENT", r"#[^\n]*"),
    ("NL",      r"\n"),
    ("STRING",  r'"(?:[^"\\]|\\.)*"'),
    ("NUMBER",  r"-?\d+(?:\.\d+)?"),
    ("AT",      r"@"),
    ("IDENT",   r"[A-Za-z_][A-Za-z0-9_.]*"),
    ("PUNCT",   r"[{}:;,=()\[\]]"),
]
_MASTER = re.compile("|".join("(?P<%s>%s)" % (k, p) for k, p in _TOKEN_SPEC))


def tokenize(src):
    out, line, pos = [], 1, 0
    while pos < len(src):
        m = _MASTER.match(src, pos)
        if not m:
            raise LexError("line %d: cannot lex %r" % (line, src[pos:pos + 20]))
        kind, text = m.lastgroup, m.group()
        pos = m.end()
        if kind == "NL":
            line += 1
            continue
        if kind in ("SKIP", "COMMENT"):
            continue
        out.append((kind, text, line))
    out.append(("EOF", "", line))
    return out


def unquote(s):
    return s[1:-1].replace('\\"', '"').replace("\\\\", "\\")


# ----------------------------------------------------------------- 2. AST
@dataclass
class TypeRef:
    name: str
    required: bool = False
    finite: bool = False
    max_len: int = None
    default: object = None
    has_default: bool = False


@dataclass
class Param:
    dir: str
    name: str
    ty: TypeRef


@dataclass
class Method:
    name: str
    params: list
    kind: str
    impl: dict
    line: int


@dataclass
class Canon:
    version: str = "0"
    articles: dict = field(default_factory=dict)
    caps: dict = field(default_factory=dict)
    types: dict = field(default_factory=dict)
    structs: dict = field(default_factory=dict)
    methods: list = field(default_factory=list)


# -------------------------------------------------------------- 3. parser
class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def kind(self): return self.t[self.i][0]
    def val(self): return self.t[self.i][1]
    def line(self): return self.t[self.i][2]

    def eat(self, kind=None, val=None):
        tok = self.t[self.i]
        if kind and tok[0] != kind:
            raise ParseError("line %d: expected %s, got %r" % (tok[2], kind, tok[1]))
        if val and tok[1] != val:
            raise ParseError("line %d: expected %r, got %r" % (tok[2], val, tok[1]))
        self.i += 1
        return tok

    def parse(self):
        c = Canon()
        while self.kind() != "EOF":
            self.eat("AT")
            name = self.eat("IDENT")[1]
            if name == "core":
                c.version = unquote(self.eat("STRING")[1])
            elif name == "article":
                c.articles[self.eat("IDENT")[1]] = unquote(self.eat("STRING")[1])
            elif name == "cap":
                c.caps[self.eat("IDENT")[1]] = self._literal()
            elif name == "type":
                c.types[self.eat("IDENT")[1]] = self._tyref()
            elif name == "struct":
                self._struct(c)
            elif name == "method":
                c.methods.append(self._method())
            else:
                raise ParseError("line %d: unknown directive @%s" % (self.line(), name))
        return c

    def _literal(self):
        kind, val, _ = self.t[self.i]
        if kind == "STRING":
            self.i += 1
            return unquote(val)
        if kind == "NUMBER":
            self.i += 1
            return float(val) if "." in val else int(val)
        if kind == "IDENT" and val in ("true", "false"):
            self.i += 1
            return val == "true"
        if kind == "PUNCT" and val == "{":
            self.i += 1
            self.eat("PUNCT", "}")
            return {}
        raise ParseError("line %d: expected literal, got %r" % (self.line(), val))

    def _tyref(self):
        ty = TypeRef(self.eat("IDENT")[1])
        while self.kind() == "IDENT":
            w = self.val()
            if w == "required":
                self.i += 1
                ty.required = True
            elif w == "finite":
                self.i += 1
                ty.finite = True
            elif w == "max":
                self.i += 1
                ty.max_len = int(self.eat("NUMBER")[1])
            else:
                break
        if self.kind() == "PUNCT" and self.val() == "=":
            self.i += 1
            ty.default, ty.has_default = self._literal(), True
        return ty

    def _struct(self, c):
        name = self.eat("IDENT")[1]
        self.eat("PUNCT", "{")
        fs = []
        while not (self.kind() == "PUNCT" and self.val() == "}"):
            fname = self.eat("IDENT")[1]
            self.eat("PUNCT", ":")
            fs.append(Param("field", fname, self._tyref()))
        self.eat("PUNCT", "}")
        c.structs[name] = fs

    def _method(self):
        line = self.line()
        name = self.eat("IDENT")[1]
        self.eat("PUNCT", "{")
        params = []
        while not (self.kind() == "PUNCT" and self.val() == "}"):
            d = self.eat("IDENT")[1]
            if d not in ("in", "out"):
                raise ParseError("line %d: param must be 'in' or 'out'" % self.line())
            pname = self.eat("IDENT")[1]
            self.eat("PUNCT", ":")
            params.append(Param(d, pname, self._tyref()))
        self.eat("PUNCT", "}")
        kind = self.eat("IDENT")[1]
        if kind not in ("pure", "resident", "gate"):
            raise ParseError("line %d: bad method kind %r" % (line, kind))
        impl = {}
        while self.kind() == "IDENT" and self.val() in ("cpp", "py", "cs", "js"):
            impl[self.eat("IDENT")[1]] = unquote(self.eat("STRING")[1])
        return Method(name, params, kind, impl, line)


# ------------------------------------------- 4. semantic constitutional gate
BUILTIN = {"string", "number", "bool", "uint32", "int32", "any", "Json"}


class Checker:
    def __init__(self, c):
        self.c, self.err = c, []

    def resolve(self, ty):
        seen = 0
        while ty.name not in BUILTIN and ty.name in self.c.types and seen < 8:
            b = self.c.types[ty.name]
            ty = TypeRef(b.name, ty.required, ty.finite or b.finite,
                         ty.max_len or b.max_len,
                         ty.default if ty.has_default else b.default,
                         ty.has_default or b.has_default)
            seen += 1
        if ty.name not in BUILTIN and ty.name not in self.c.structs:
            self.err.append("unknown type %r (fail closed)" % ty.name)
        return ty

    def check(self):
        c = self.c
        if not c.articles:
            self.err.append("no articles: a core with no constitution is not a core")
        for cap in ("MAXP", "KEY_MAX"):
            if cap not in c.caps:
                self.err.append("missing cap %s -- the gate cannot compile" % cap)
        names = set()
        for m in c.methods:
            if m.name in names:
                self.err.append("duplicate method %s" % m.name)
            names.add(m.name)
            ins = [p for p in m.params if p.dir == "in"]
            outs = [p for p in m.params if p.dir == "out"]
            if not outs:
                self.err.append("%s: a method must declare an 'out'" % m.name)
            seen = set()
            for p in ins:
                p.ty = self.resolve(p.ty)
                if p.name in seen:
                    self.err.append("%s: duplicate arg %r" % (m.name, p.name))
                seen.add(p.name)
                if p.ty.required and p.ty.has_default:
                    self.err.append("%s.%s: cannot be both required and defaulted"
                                    % (m.name, p.name))
                if p.ty.has_default:
                    self._default_ok(m, p)
            if ins and all(not p.ty.required for p in ins):
                self.err.append("%s: A0 violation -- every argument optional means "
                                "the answer is not computed from the question" % m.name)
            if m.kind == "resident" and "cpp" not in m.impl:
                self.err.append("%s: resident method needs a cpp impl" % m.name)
        return self.err

    def _default_ok(self, m, p):
        d, t = p.ty.default, p.ty.name
        ok = {"string": lambda: isinstance(d, str), "Key": lambda: isinstance(d, str),
              "number": lambda: isinstance(d, (int, float)),
              "Prob": lambda: isinstance(d, (int, float)),
              "uint32": lambda: isinstance(d, int) and 0 <= d < 2 ** 32,
              "Seed": lambda: isinstance(d, int) and 0 <= d < 2 ** 32,
              "bool": lambda: isinstance(d, bool),
              "any": lambda: True, "Json": lambda: True}.get(t, lambda: True)
        if not ok():
            self.err.append("%s.%s: default %r does not type-check as %s"
                            % (m.name, p.name, d, t))


# ------------------------------------------------------------- 5. type maps
CPP = {"string": "std::string", "Key": "std::string", "number": "double",
       "Prob": "double", "bool": "bool", "uint32": "uint32_t", "Seed": "uint32_t",
       "int32": "int32_t", "any": "Json", "Json": "Json"}
CS = {"string": "string", "Key": "string", "number": "double", "Prob": "double",
      "bool": "bool", "uint32": "uint", "Seed": "uint", "int32": "int",
      "any": "JsonElement", "Json": "JsonElement"}


def py_name(m): return m.replace(".", "_")


def cs_name(m):
    a, b = m.split(".", 1)
    return a.capitalize() + b[0].upper() + b[1:]


def header(c, body, backend):
    h = hashlib.sha256(body.encode()).hexdigest()[:10]
    mark = "#" if backend == "py" else "//"
    return ("%s AUTO-GENERATED by qcosc from qcos.cxn (v%s, canon %s, backend %s)\n"
            "%s DO NOT EDIT -- edit qcos.cxn and re-run: python3 tools/qcosc.py qcos.cxn\n"
            % (mark, c.version, h, backend, mark))


# --------------------------------------------------------------- 6. backends
def emit_cpp(c):
    L = [header(c, "cpp", "cpp"),
         '#include "api.hpp"\n#include "gen.hpp"\n#include "numfmt.hpp"\n',
         "namespace saem {\nnamespace {\n",
         "uint64_t seed_of(const Json& a, uint64_t dflt) {\n"
         "  if (!a.has(\"seed\") || !a[\"seed\"].isNum()) return dflt;\n"
         "  return static_cast<uint64_t>(static_cast<int64_t>(a[\"seed\"].asNum()));\n}\n",
         "void require_str(const Json& a, const char* k) {\n"
         "  if (!a.has(k)) throw std::runtime_error(std::string(\"missing field: \") + k);\n"
         "  if (!a[k].isStr()) throw std::runtime_error(std::string(\"field '\") + k + \"' must be a string\");\n}\n",
         "void require_num(const Json& a, const char* k) {\n"
         "  if (!a.has(k)) throw std::runtime_error(std::string(\"missing field: \") + k);\n"
         "  if (!a[k].isNum()) throw std::runtime_error(std::string(\"field '\") + k + \"' must be a number\");\n"
         "  if (!std::isfinite(a[k].asNum())) throw std::runtime_error(std::string(\"field '\") + k + \"' must be finite\");\n}\n",
         "void require_obj(const Json& a, const char* k) {\n"
         "  if (!a.has(k)) throw std::runtime_error(std::string(\"missing field: \") + k);\n"
         "  if (!a[k].isObj()) throw std::runtime_error(std::string(\"field '\") + k + \"' must be an object\");\n}\n",
         "struct MethodDoc { const char* name; const char* args; };\n",
         "const MethodDoc DOCS[] = {"]
    for m in c.methods:
        sig = ", ".join("%s%s" % (p.name, "" if p.ty.required else "?")
                        for p in m.params if p.dir == "in")
        L.append('  {"%s", "%s"},' % (m.name, sig))
    L.append('  {nullptr, nullptr}\n};\n')
    for m in c.methods:
        ins = [p for p in m.params if p.dir == "in"]
        L.append('const Registrar R_%s("%s", [](const Json& a) -> Json {'
                 % (py_name(m.name), m.name))
        for p in ins:
            if p.ty.name in ("string", "Key") and p.ty.required:
                L.append('  require_str(a, "%s");' % p.name)
            elif p.ty.name in ("number", "Prob") and p.ty.required:
                L.append('  require_num(a, "%s");' % p.name)
            elif p.ty.name in ("any", "Json") and p.ty.required:
                L.append('  require_obj(a, "%s");' % p.name)
        for p in ins:
            if p.ty.name in ("uint32", "Seed") and p.ty.has_default:
                L.append('  const uint64_t %s = seed_of(a, %s);   // canon default'
                         % (p.name, p.ty.default))
        body = m.impl.get("cpp")
        L.append('  return %s;' % body if body else
                 '  throw std::runtime_error("NOT_IMPLEMENTED: %s");' % m.name)
        L.append("});\n")
    L.append("}  // namespace\n}  // namespace saem\n")
    return "\n".join(L)


def emit_py(c):
    L = [header(c, "py", "py"),
         '"""Typed client for the QCOS door. Generated -- one method per canon entry.',
         'Defaults and argument order come from qcos.cxn, never from this file."""',
         "from typing import Any, Dict\nimport json\n",
         "class QcosClient:\n"
         '    """One saem_cli process = one OS session. A2: no state lives here."""\n'
         "    def __init__(self, proc):\n"
         "        self._p = proc\n        self._id = 0\n"
         "    def _call(self, method, args):\n"
         "        self._id += 1\n"
         '        req = {"id": self._id, "method": method, "args": args}\n'
         '        self._p.stdin.write(json.dumps(req, ensure_ascii=False) + "\\n")\n'
         "        self._p.stdin.flush()\n"
         "        line = self._p.stdout.readline()\n"
         '        if not line:\n            raise SystemExit("core closed the door")\n'
         "        env = json.loads(line)\n"
         '        if env.get("id") != self._id:\n'
         '            raise SystemExit("core answered a different question")\n'
         '        if not env.get("ok"):\n'
         '            raise ValueError(env.get("error", "unknown failure"))\n'
         '        return env["result"]\n']
    for m in c.methods:
        ins = [p for p in m.params if p.dir == "in"]
        sig = ", ".join("%s%s" % (p.name, "" if p.ty.required else "=%r" % (p.ty.default,))
                        for p in ins)
        L.append("\n    def %s(self, %s) -> Any:" % (py_name(m.name), sig))
        L.append('        """%s"""' % m.name)
        L.append("        args = {}")
        for p in ins:
            if p.ty.required:
                L.append('        if %s is None: raise ValueError("%s: %s is required")'
                         % (p.name, m.name, p.name))
                L.append('        args["%s"] = %s' % (p.name, p.name))
            else:
                L.append('        if %s is not None: args["%s"] = %s  # default %r from canon'
                         % (p.name, p.name, p.name, p.ty.default))
        L.append('        return self._call("%s", args)' % m.name)
    return "\n".join(L) + "\n"


def emit_cs(c):
    L = [header(c, "cs", "cs"),
         "using System.Collections.Generic;\nusing System.Text.Json;\n",
         "namespace SaemLabs.Qcos {\npublic sealed partial class SaemBridge {"]
    for m in c.methods:
        ins = [p for p in m.params if p.dir == "in"]
        sig = ", ".join("%s %s%s" % (CS.get(p.ty.name, "object"), p.name,
                                    "" if p.ty.required else " = default")
                        for p in ins)
        L.append("\n    /// <summary>%s (generated; signature is canon-authoritative)</summary>" % m.name)
        L.append("    public JsonElement %s(%s)" % (cs_name(m.name), sig))
        L.append("    {")
        L.append('        var args = new Dictionary<string, object>();')
        for p in ins:
            if p.ty.required and p.ty.name in ("string", "Key"):
                L.append('        if (string.IsNullOrEmpty(%s)) throw new System.ArgumentException("%s is required");'
                         % (p.name, p.name))
            L.append('        args["%s"] = %s;' % (p.name, p.name))
        L.append('        return Call("%s", JsonSerializer.Serialize(args));' % m.name)
        L.append("    }")
    L.append("}\n}\n")
    return "\n".join(L)


def emit_js(c):
    L = [header(c, "js", "js"),
         "// A6: this file is the RULER. The shipped product runs the C++ core alone.",
         "'use strict';", "const MISSING = Symbol('missing');\n", "const CANON = {"]
    for m in c.methods:
        ins = [p for p in m.params if p.dir == "in"]
        spec = ", ".join('%s: {t:"%s", req:%s, d:%s}'
                         % (p.name, p.ty.name, "true" if p.ty.required else "false",
                            json.dumps(p.ty.default)) for p in ins)
        L.append('  "%s": {%s},   // order: [%s]'
                 % (m.name, spec, ", ".join(p.name for p in ins)))
    L.append("};\nmodule.exports = { CANON };\n")
    return "\n".join(L)


def emit_diff(c):
    """A5: rules without machine checks remain hypotheses. Emit the witnesses."""
    out = []
    for m in c.methods:
        ins = [p for p in m.params if p.dir == "in"]
        happy = {"name": "%s happy" % m.name, "method": m.name, "args": {}}
        for p in ins:
            happy["args"][p.name] = (p.ty.default if p.ty.has_default else
                                     {"string": "x", "Key": "k", "number": 1.0,
                                      "Prob": 0.5, "bool": True, "uint32": 1,
                                      "Seed": 1, "int32": 1, "any": {}, "Json": {}}[p.ty.name])
        out.append(happy)
        req = next((p for p in ins if p.ty.required), None)
        if req:
            bad = {"name": "%s missing-%s must fail closed on BOTH sides" % (m.name, req.name),
                   "method": m.name, "error": True, "args": dict(happy["args"])}
            del bad["args"][req.name]
            out.append(bad)
    return "\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n"


def emit_schema(c):
    return json.dumps({
        "version": c.version, "articles": c.articles, "caps": c.caps,
        "methods": [{"name": m.name, "kind": m.kind,
                     "args": [{"name": p.name, "type": p.ty.name,
                               "required": p.ty.required,
                               "default": p.ty.default if p.ty.has_default else None,
                               "finite": p.ty.finite, "max": p.ty.max_len}
                              for p in m.params if p.dir == "in"],
                     "returns": [p.ty.name for p in m.params if p.dir == "out"]}
                    for m in c.methods],
    }, indent=2, sort_keys=False) + "\n"


BACKENDS = {"cpp": emit_cpp, "py": emit_py, "cs": emit_cs,
            "js": emit_js, "diff": emit_diff, "schema": emit_schema}
TARGETS = {k: ROOT / v for k, v in {
    "cpp": "core/src/api_registry.g.cpp", "py": "saem/client.g.py",
    "cs": "SaemQcos/Client.g.cs", "js": "tools/ref_bridge.gen.js",
    "diff": "tests/diff/cases/canon.jsonl", "schema": "qcos.schema.json"}.items()}


# ---------------------------------------------------------------- 7. driver
def build(path):
    src = Path(path).read_text(encoding="utf-8")
    canon = Parser(tokenize(src)).parse()
    errs = Checker(canon).check()
    if errs:
        raise CanonError("\n".join("  %s" % e for e in errs))
    return src, canon


def _schema_order(canon):
    return [(m.name, [p.name for p in m.params if p.dir == "in"])
            for m in canon.methods]


def handshake(canon):
    """Four-tongue agreement on method set + argument order (A1/A6)."""
    want = _schema_order(canon)
    texts = {n: fn(canon) for n, fn in BACKENDS.items() if n in ("cpp", "py", "cs", "js")}
    got = {}
    got["cpp"] = [(m, [a.rstrip("?") for a in (sig.split(", ") if sig else []) if a])
                  for m, sig in re.findall(r'\{"([\w.]+)", "([^"]*)"\},', texts["cpp"])]
    name_by_py = {py_name(m): m for m, _ in want}
    got["py"] = [(name_by_py.get(n, n),
                  [p.split("=")[0].strip() for p in (sig.split(", ") if sig else []) if p.strip()])
                 for n, sig in re.findall(r"def (\w+)\(self(?:, ([^)]*?))?\) -> Any:", texts["py"])]
    name_by_cs = {cs_name(m): m for m, _ in want}
    cs_out = []
    for cname, sig in re.findall(r"public JsonElement (\w+)\(([^)]*)\)", texts["cs"]):
        args = [part.split("=")[0].split()[-1]
                for part in (p.strip() for p in sig.split(",") if p.strip())]
        cs_out.append((name_by_cs.get(cname, cname), args))
    got["cs"] = cs_out
    got["js"] = [(m, [a.strip() for a in order.split(",") if a.strip()])
                 for m, order in re.findall(r'"([\w.]+)": \{.*?// order: \[(.*?)\]', texts["js"])]
    equal = all(got[k] == want for k in got)
    return {"equal": equal, "methods": len(want), "want": want, "got": got}


def _receipt(entry):
    if _ledger is None:
        return
    try:
        _ledger({"gate": "qcosc", "schema_version": SCHEMA_VERSION, **entry})
    except Exception:
        pass


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a[2:] for a in argv[1:] if a.startswith("--")}
    if "selftest" in flags:
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0
    if not args:
        print(__doc__)
        return 2
    canon_path = ROOT / args[0] if not Path(args[0]).is_absolute() else Path(args[0])
    if not canon_path.exists():
        print(f"[qcosc] canon missing: {canon_path}")
        _receipt({"op": "env", "status": "missing-canon"})
        return 2
    try:
        src, canon = build(canon_path)
    except (LexError, ParseError, CanonError) as e:
        print("[qcosc] REFUSED:\n%s" % e)
        _receipt({"op": "build", "status": "refused", "error": str(e)[:200]})
        return 1
    body = hashlib.sha256(src.encode("utf-8")).hexdigest()

    if "handshake" in flags:
        rep = handshake(canon)
        if "json" in flags:
            print(json.dumps(rep, ensure_ascii=False, indent=2))
        else:
            print("[qcosc] handshake %s: %d method(s) across 4 tongues"
                  % ("ok" if rep["equal"] else "MISMATCH", rep["methods"]))
            if not rep["equal"]:
                for k, v in rep["got"].items():
                    if v != rep["want"]:
                        print(f"  {k}: {v}")
        _receipt({"op": "handshake", "canon": body[:10],
                  "status": "ok" if rep["equal"] else "mismatch"})
        return 0 if rep["equal"] else 1

    if "verify" in flags:
        stale = []
        for name, fn in BACKENDS.items():
            want = fn(canon)
            p = TARGETS[name]
            have = p.read_text(encoding="utf-8") if p.exists() else None
            if have != want:
                stale.append(str(p.relative_to(ROOT)))
        if stale:
            print("[qcosc] STALE bindings -- rebuild: python3 tools/qcosc.py %s" % args[0])
            for s in stale:
                print("   stale:", s)
            _receipt({"op": "verify", "canon": body[:10], "status": "stale", "stale": stale})
            return 1
        print("[qcosc] in sync. canon %s, %d methods, %d articles"
              % (body[:10], len(canon.methods), len(canon.articles)))
        _receipt({"op": "verify", "canon": body[:10], "status": "ok"})
        return 0

    only = flags & set(BACKENDS)
    for name, fn in BACKENDS.items():
        if only and name not in only:
            continue
        text = fn(canon)
        if only:
            sys.stdout.write(text)
            continue
        p = TARGETS[name]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
        print("[qcosc] %-7s -> %-34s %5d lines"
              % (name, p.relative_to(ROOT), text.count("\n")))
    print("[qcosc] canon body %s (compile this into SAEM_SOURCE_ID)" % body[:10])
    _receipt({"op": "emit", "canon": body[:10], "status": "ok",
              "methods": len(canon.methods)})
    return 0


# --------------------------------------------------------------- 8. witness
_GOOD = '''# mini canon (frozen witness)
@core "test-1"
@article A0 "computed, never guessed"
@article A5 "rules without machine checks remain hypotheses"
@cap MAXP 8
@cap KEY_MAX 64
@type Key string max 64
@method qcos.boot { out ok: bool } pure cpp "Json::obj(\\"ok\\", true)"
@method qcos.read { in key: Key required, out value: number } resident cpp "store_get(a)"
'''
_BAD_DUP = _GOOD + '@method qcos.boot { out ok: bool } pure cpp "Json::obj(\\"ok\\", true)"\n'
_BAD_NOCAPS = _GOOD.replace("@cap MAXP 8\n", "")
_BAD_A0 = _GOOD.replace("in key: Key required,", "in key: Key,")
_BAD_RESIDENT = _GOOD.replace('resident cpp "store_get(a)"', 'resident py "pass"')


def selftest():
    import tempfile
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "mini.cxn"
        p.write_text(_GOOD, encoding="utf-8")
        src, canon = build(p)
        want("parse", len(canon.methods) == 2 and canon.caps["MAXP"] == 8)
        want("emit-determinism", emit_cpp(canon) == emit_cpp(canon)
             and emit_js(canon) == emit_js(canon))
        want("handshake", handshake(canon)["equal"],
             str(handshake(canon)["got"]))
        diff = emit_diff(canon)
        lines = [json.loads(x) for x in diff.splitlines() if x.strip()]
        want("diff-failclosed", any(l.get("error") for l in lines)
             and len(lines) == 3)
        want("schema-json", json.loads(emit_schema(canon))["version"] == "test-1")
        regs = re.findall(r'Registrar\s+\w+\s*\(\s*"([\w.]+)"', emit_cpp(canon))
        want("canon_lint-compatible", regs == [m.name for m in canon.methods], str(regs))
        for label, bad in (("dup", _BAD_DUP), ("nocaps", _BAD_NOCAPS),
                           ("a0", _BAD_A0), ("resident", _BAD_RESIDENT)):
            bp = Path(td) / f"bad_{label}.cxn"
            bp.write_text(bad, encoding="utf-8")
            try:
                build(bp)
                want(f"checker-refuses-{label}", False)
            except CanonError:
                want(f"checker-refuses-{label}", True)
    want("targets-absolute", all(t.is_absolute() for t in TARGETS.values()))
    return checks


if __name__ == "__main__":
    sys.exit(main(sys.argv))
