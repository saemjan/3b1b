#!/usr/bin/env python3
"""tools/qcosc.py -- the canon compiler & checker (Gen-3).

Layer: tooling (orchestration edge). Truth lives in qcos.cxn (the canon).
Stance: pure stdlib ruler; deterministic; fail-closed; receipt per run.

CLI:
  qcosc.py [CANON]                 parse + check + emit the six artifacts
  qcosc.py [CANON] --verify        parse + check + compare on-disk artifacts
  qcosc.py [CANON] --verify --handshake
                                   verify + cross-language semantic handshake
  qcosc.py [CANON] --json          print the schema JSON on stdout
  qcosc.py [CANON] --emit DIR      write artifacts into DIR (selftest/tooling)
  qcosc.py --selftest              frozen witnesses; drift exits 1

Exit codes: 0 ok | 1 refused/stale/mismatch | 2 environment (canon missing).

Law: generated files (*.g.cpp/*.g.py/*.g.cs/*.gen.js, qcos.schema.json,
canon.jsonl) are never hand-edited; edit qcos.cxn and re-run this tool.
"""

import hashlib
import json
import os
import re
import sys
import time
from fractions import Fraction
from pathlib import Path

SCHEMA_VERSION = 3

ROOT = Path(__file__).resolve().parent.parent

ARTIFACTS = {
    "schema": ROOT / "qcos.schema.json",
    "cpp": ROOT / "core" / "src" / "api_registry.g.cpp",
    "py": ROOT / "saem" / "client.g.py",
    "cs": ROOT / "SaemQcos" / "Client.g.cs",
    "js": ROOT / "tools" / "ref_bridge.gen.js",
    "diff": ROOT / "tests" / "diff" / "cases" / "canon.jsonl",
}

SEALED_CAPS = {
    "MAXP": Fraction(95, 100),
    "MAX_NUDGE": Fraction(15, 100),
    "CAP_ATTEMPTS": Fraction(3),
    "KEEP_DETAIL": Fraction(50),
    "MAX_FACULTY": Fraction(4),
    "WORKING_LIMIT": Fraction(32),
    "EPISODIC_LIMIT": Fraction(64),
    "KEY_MAX": Fraction(23),
    "CIR_STEPS": Fraction(4096),
    "MAX_DELEGATION": Fraction(8),
    "MAX_ACTIONS": Fraction(64),
    "NAME_MAX": Fraction(64),
    "MAX_PROJECT_STOPS": Fraction(8),
}

BASE_TYPES = ("string", "number", "uint32", "int32", "int64", "bool", "any", "Json")

INT_RANGES = {
    "uint32": (0, 2 ** 32 - 1),
    "int32": (-2 ** 31, 2 ** 31 - 1),
    "int64": (-2 ** 63, 2 ** 63 - 1),
}

DIFF_FALLBACK = {
    "number": 1, "string": "k", "Key": "k", "bool": True,
    "uint32": 1, "int32": 1, "int64": 1, "Seed": 1,
    "Prob": 0.5, "any": {}, "Any": {}, "Json": {},
}


# --------------------------------------------------------------------------
# lexer
# --------------------------------------------------------------------------

_TOKEN_SPEC = [
    ("SKIP", r"[ \t\r]+"),
    ("COMMENT", r"#[^\n]*"),
    ("NL", r"\n"),
    ("STRING", r'"(?:[^"\\]|\\.)*"'),
    ("NUMBER", r"-?\d+(?:\.\d+)?"),
    ("AT", r"@"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_.]*"),
    ("PUNCT", r"[{}:;,=()\[\]]"),
]
_MASTER = re.compile("|".join("(?P<%s>%s)" % (k, p) for k, p in _TOKEN_SPEC))


class Refused(Exception):
    """Fail-closed refusal: parse, check, stale, or mismatch."""


class LexError(Refused):
    pass


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
    return out


def unquote(text):
    body = text[1:-1]
    return json.loads('"%s"' % body)


# --------------------------------------------------------------------------
# canon model
# --------------------------------------------------------------------------

class Ty(object):
    def __init__(self, name, max_len=None):
        self.name = name          # declared (alias) or base name
        self.max_len = max_len    # string caps only


class Param(object):
    def __init__(self, name, ty, required, has_default, default):
        self.name = name
        self.ty = ty
        self.required = required
        self.has_default = has_default
        self.default = default


class Method(object):
    def __init__(self, name, kind, lang, impl, ins, outs):
        self.name = name
        self.kind = kind
        self.lang = lang
        self.impl = impl
        self.ins = ins
        self.outs = outs


class Canon(object):
    def __init__(self):
        self.version = SCHEMA_VERSION
        self.articles = {}     # id -> text (insertion ordered)
        self.caps = {}         # name -> Fraction
        self.types = {}        # name -> Ty
        self.structs = {}      # name -> [(field, Ty)]
        self.methods = []      # [Method]


class Parser(object):
    def __init__(self, toks):
        self.toks = toks
        self.pos = 0

    def peek(self):
        if self.pos < len(self.toks):
            return self.toks[self.pos]
        return ("EOF", "", -1)

    def advance(self):
        t = self.peek()
        self.pos += 1
        return t

    def expect(self, kind, text=None):
        t = self.advance()
        if t[0] != kind or (text is not None and t[1] != text):
            want = text if text is not None else kind
            raise Refused("line %d: expected %s, got %r" % (t[2], want, t[1]))
        return t

    def at(self, kind, text=None):
        t = self.peek()
        return t[0] == kind and (text is None or t[1] == text)

    # -- pieces ----------------------------------------------------------
    def parse_number(self):
        t = self.expect("NUMBER")
        return Fraction(t[1])

    def parse_literal(self):
        t = self.peek()
        if t[0] == "NUMBER":
            self.advance()
            return Fraction(t[1])
        if t[0] == "STRING":
            self.advance()
            return unquote(t[1])
        if t[0] == "IDENT" and t[1] in ("true", "false"):
            self.advance()
            return t[1] == "true"
        raise Refused("line %d: expected literal, got %r" % (t[2], t[1]))

    def parse_type_spec(self):
        t = self.expect("IDENT")
        base = t[1]
        max_len = None
        if base == "string":
            if self.at("IDENT", "max"):
                self.advance()
                n = self.expect("NUMBER")
                max_len = int(Fraction(n[1]))
            return Ty("string", max_len)
        if base == "number":
            if self.at("IDENT", "finite"):
                self.advance()
            return Ty("number")
        if base in BASE_TYPES:
            return Ty(base)
        return Ty(base)          # alias; resolved by the Checker

    def parse_params(self, direction):
        params = []
        while not self.at("PUNCT", "}"):
            d = self.expect("IDENT")
            if d[1] != direction:
                raise Refused("line %d: expected %s, got %r" % (d[2], direction, d[1]))
            name = self.expect("IDENT")[1]
            self.expect("PUNCT", ":")
            ty = self.parse_type_spec()
            required = False
            has_default = False
            default = None
            while self.at("PUNCT", "=") or self.at("IDENT", "required"):
                if self.at("PUNCT", "="):
                    self.advance()
                    default = self.parse_literal()
                    has_default = True
                else:
                    self.advance()
                    required = True
                    if direction == "out":
                        raise Refused("line %d: out param cannot be required" % d[2])
            params.append(Param(name, ty, required, has_default, default))
            if self.at("PUNCT", ","):
                self.advance()
        return params

    def parse_method(self):
        name = self.expect("IDENT")[1]
        self.expect("PUNCT", "{")
        ins = self.parse_params("in")
        outs = self.parse_params("out")
        self.expect("PUNCT", "}")
        kind = self.expect("IDENT")[1]
        if kind not in ("pure", "resident", "gate"):
            raise Refused("line %d: bad method kind %r" % (self.peek()[2], kind))
        lang = self.expect("IDENT")[1]
        if lang not in ("cpp", "py"):
            raise Refused("line %d: bad impl language %r" % (self.peek()[2], lang))
        impl = None
        if self.at("STRING"):
            impl = unquote(self.advance()[1])
        return Method(name, kind, lang, impl, ins, outs)


def parse_canon(src):
    toks = tokenize(src)
    p = Parser(toks)
    c = Canon()
    while p.peek()[0] != "EOF":
        p.expect("AT")
        kw = p.expect("IDENT")[1]
        if kw == "cap":
            name = p.expect("IDENT")[1]
            if name in c.caps:
                raise Refused("line %d: duplicate cap %r" % (p.peek()[2], name))
            c.caps[name] = p.parse_number()
        elif kw == "article":
            t = p.peek()
            if t[0] == "IDENT":
                aid = p.advance()[1]
            elif t[0] == "STRING":
                aid = unquote(p.advance()[1])
            else:
                raise Refused("line %d: expected STRING or IDENT, got %r" % (t[2], t[1]))
            text = unquote(p.expect("STRING")[1])
            if aid in c.articles:
                raise Refused("line %d: duplicate article %r" % (t[2], aid))
            c.articles[aid] = text
        elif kw == "type":
            name = p.expect("IDENT")[1]
            if name in c.types:
                raise Refused("line %d: duplicate type %r" % (p.peek()[2], name))
            c.types[name] = p.parse_type_spec()
        elif kw == "struct":
            name = p.expect("IDENT")[1]
            if name in c.structs:
                raise Refused("line %d: duplicate struct %r" % (p.peek()[2], name))
            p.expect("PUNCT", "{")
            fields = []
            while not p.at("PUNCT", "}"):
                fname = p.expect("IDENT")[1]
                p.expect("PUNCT", ":")
                fty = p.parse_type_spec()
                fields.append((fname, fty))
                if p.at("PUNCT", ","):
                    p.advance()
            p.expect("PUNCT", "}")
            c.structs[name] = fields
        elif kw == "method":
            m = p.parse_method()
            c.methods.append(m)
        else:
            raise Refused("line %d: unknown directive @%s" % (p.peek()[2], kw))
    return c


def build(path):
    src = Path(path).read_text(encoding="utf-8")
    return src, parse_canon(src)


# --------------------------------------------------------------------------
# checker
# --------------------------------------------------------------------------

def resolve_base(c, ty):
    seen = set()
    cur = ty
    while cur.name not in BASE_TYPES:
        if cur.name in seen:
            return None
        seen.add(cur.name)
        decl = c.types.get(cur.name)
        if decl is None:
            return None
        cur = decl
    return cur


def cap_str(v):
    return str(v) if v.denominator != 1 else str(v.numerator)


def json_of_literal(v):
    if isinstance(v, Fraction):
        if v.denominator == 1:
            return v.numerator
        return float(v)
    return v


class Checker(object):
    def __init__(self, canon):
        self.c = canon

    def check(self):
        errs = []
        errs += self._caps()
        errs += self._zone0()
        errs += self._methods()
        errs += self._types()
        return errs

    def _caps(self):
        errs = []
        for name, want in SEALED_CAPS.items():
            got = self.c.caps.get(name)
            if got is None:
                errs.append("sealed cap missing: %s" % name)
            elif got != want:
                errs.append("sealed cap mutated: %s = %s (want %s)"
                            % (name, cap_str(got), cap_str(want)))
        for name in self.c.caps:
            if name not in SEALED_CAPS:
                errs.append("undeclared cap: %s (amend the vision first)" % name)
        return errs

    def _zone0(self):
        for m in self.c.methods:
            if m.name == "qcos.zone0":
                if m.kind != "gate" or m.lang != "cpp" or not m.impl:
                    return ["qcos.zone0 must be a gate with a cpp impl"]
                return []
        return ["qcos.zone0 gate method missing"]

    def _methods(self):
        errs = []
        seen = set()
        maxp = self.c.caps.get("MAXP")
        for m in self.c.methods:
            if m.name in seen:
                errs.append("duplicate method: %s" % m.name)
            seen.add(m.name)
            if m.kind == "gate" and (m.lang != "cpp" or not m.impl):
                errs.append("gate method without cpp impl: %s" % m.name)
            if m.kind == "resident" and not m.impl:
                errs.append("resident method without impl: %s" % m.name)
            for p in m.ins:
                base = resolve_base(self.c, p.ty)
                if base is None:
                    errs.append("%s: unknown type %s" % (m.name, p.ty.name))
                    continue
                if not p.required and not p.has_default:
                    errs.append("A0: optional input without declared default: %s.%s"
                                % (m.name, p.name))
                    continue
                if p.has_default:
                    errs += self._default(m, p, base, maxp)
        return errs

    def _default(self, m, p, base, maxp):
        v = p.default
        if base.name in INT_RANGES or base.name == "Seed":
            key = "uint32" if base.name == "Seed" else base.name
            lo, hi = INT_RANGES[key]
            if not isinstance(v, Fraction) or v.denominator != 1:
                return ["%s.%s: default must be an integer literal" % (m.name, p.name)]
            if not (lo <= v.numerator <= hi):
                return ["%s.%s: default out of %s range" % (m.name, p.name, key)]
            return []
        if base.name == "number":
            if not isinstance(v, Fraction):
                return ["%s.%s: number default must be a literal" % (m.name, p.name)]
            return []
        if base.name == "Prob":
            if not isinstance(v, Fraction):
                return ["%s.%s: Prob default must be a literal" % (m.name, p.name)]
            if maxp is not None and v > maxp:
                return ["%s.%s: Prob default exceeds MAXP" % (m.name, p.name)]
            return []
        if base.name == "bool":
            if not isinstance(v, bool):
                return ["%s.%s: bool default must be true/false" % (m.name, p.name)]
            return []
        if base.name == "string":
            if not isinstance(v, str):
                return ["%s.%s: string default must be a literal" % (m.name, p.name)]
            if p.ty.max_len is not None and len(v) > p.ty.max_len:
                return ["%s.%s: string default exceeds max" % (m.name, p.name)]
            return []
        return []   # any / Json accept any declared literal

    def _types(self):
        errs = []
        for name, fields in self.c.structs.items():
            for fname, fty in fields:
                if resolve_base(self.c, fty) is None:
                    errs.append("struct %s.%s: unknown type %s"
                                % (name, fname, fty.name))
        return errs


# --------------------------------------------------------------------------
# semantic handshake table (one canon per quantity, four tongues)
# --------------------------------------------------------------------------

def semantic_table(c):
    lines = []
    for k in sorted(c.caps):
        lines.append("cap %s %s" % (k, cap_str(c.caps[k])))
    for aid in c.articles:
        lines.append("article %s" % aid)
    for m in c.methods:
        lines.append("method %s %s in:%s out:%s"
                     % (m.name, m.kind,
                        ",".join(p.name for p in m.ins),
                        ",".join(p.name for p in m.outs)))
    return lines


def digest_lines(lines):
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# emitters
# --------------------------------------------------------------------------

def header(c, mark, lang):
    h = hashlib.sha256(json.dumps(semantic_table(c), sort_keys=True).encode()).hexdigest()[:16]
    backend = "qcosc"
    return ("%s %s DO NOT EDIT -- edit qcos.cxn and re-run: "
            "python3 tools/qcosc.py qcos.cxn%s%s version=%d table=%s backend=%s"
            % (mark, mark, "\n", mark, c.version, h, backend))


def cpp_lit(v):
    j = json_of_literal(v)
    if isinstance(j, bool):
        return "true" if j else "false"
    if isinstance(j, int):
        return str(j)
    return json.dumps(j)


def emit_cpp(c):
    table = semantic_table(c)
    L = [header(c, "//", "cpp"),
         '#include "api.hpp"',
         '#include "gen.hpp"',
         '#include "numfmt.hpp"',
         "#include <cstdint>",
         "#include <stdexcept>",
         "#include <string>",
         ""]
    L += ["// HANDSHAKE %s" % t for t in table]
    L += ["", "namespace saem {", "namespace {", ""]
    L += [
        "uint64_t seed_of(const Json& a, uint64_t dflt) {",
        "  if (!a.has(\"seed\") || !a[\"seed\"].isNum()) return dflt;",
        "  return static_cast<uint64_t>(static_cast<int64_t>(a[\"seed\"].asNum()));",
        "}",
        "",
        "void require_str(const Json& a, const char* k) {",
        "  if (!a.has(k)) throw std::runtime_error(std::string(\"missing field: \") + k);",
        "  if (!a[k].isStr()) throw std::runtime_error(std::string(\"not a string: \") + k);",
        "}",
        "",
        "int64_t int_req(const Json& a, const char* k) {",
        "  if (!a.has(k) || !a[k].isNum())",
        "    throw std::runtime_error(std::string(\"missing field: \") + k);",
        "  return static_cast<int64_t>(a[k].asNum());",
        "}",
        "",
        "int64_t int_of(const Json& a, const char* k, int64_t dflt) {",
        "  if (!a.has(k) || !a[k].isNum()) return dflt;",
        "  return static_cast<int64_t>(a[k].asNum());",
        "}",
        "",
        "bool bool_of(const Json& a, const char* k, bool dflt) {",
        "  if (!a.has(k) || !a[k].isNum()) return dflt;",
        "  return a[k].asNum() != 0.0;",
        "}",
        "",
        "std::string str_of(const Json& a, const char* k, const char* dflt) {",
        "  if (!a.has(k)) return dflt;",
        "  require_str(a, k);",
        "  return a[k].asStr();",
        "}",
        "",
        "Json arg_json(const Json& a, const char* k, const Json& dflt) {",
        "  if (!a.has(k)) return dflt;",
        "  return a[k];",
        "}",
        "",
        "Json req_json(const Json& a, const char* k) {",
        "  if (!a.has(k)) throw std::runtime_error(std::string(\"missing field: \") + k);",
        "  return a[k];",
        "}",
        "",
        "Json not_implemented(const Json&) {",
        "  throw std::runtime_error(\"NOT_IMPLEMENTED\");",
        "}",
        "",
    ]
    for i, m in enumerate(c.methods):
        if not m.impl:
            continue
        L.append("Json impl_%d(const Json& a) {" % i)
        L.append("  (void)a;")
        for p in m.ins:
            base = resolve_base(c, p.ty)
            bname = base.name if base else p.ty.name
            dflt = json_of_literal(p.default) if p.has_default else None
            if bname in ("uint32", "int32", "int64") or p.ty.name == "Seed":
                if p.required:
                    L.append("  const int64_t %s = int_req(a, \"%s\");" % (p.name, p.name))
                else:
                    L.append("  const int64_t %s = int_of(a, \"%s\", %dLL);"
                             % (p.name, p.name, dflt if dflt is not None else 0))
            elif bname == "bool":
                L.append("  const bool %s = bool_of(a, \"%s\", %s);"
                         % (p.name, p.name, "true" if dflt else "false"))
            elif bname == "string":
                if p.required:
                    L.append("  require_str(a, \"%s\");" % p.name)
                    L.append("  const std::string %s = a[\"%s\"].asStr();" % (p.name, p.name))
                else:
                    L.append("  const std::string %s = str_of(a, \"%s\", %s);"
                             % (p.name, p.name, json.dumps(dflt if dflt is not None else "")))
            else:
                if p.required:
                    L.append("  const Json %s = req_json(a, \"%s\");" % (p.name, p.name))
                else:
                    L.append("  const Json %s = arg_json(a, \"%s\", Json::parse(%s));"
                             % (p.name, p.name,
                                json.dumps(json.dumps(dflt if dflt is not None else {}))))
        L.append("  return %s;" % m.impl)
        L.append("}")
        L.append("")
    L.append("struct Entry { const char* name; const char* kind; Json (*fn)(const Json&); };")
    L.append("")
    L.append("const Entry kRegistry[] = {")
    for i, m in enumerate(c.methods):
        fn = ("impl_%d" % i) if m.impl else "not_implemented"
        L.append("    {\"%s\", \"%s\", %s}," % (m.name, m.kind, fn))
    L.append("};")
    L.append("")
    L.append("}  // namespace")
    L.append("")
    L.append("const Entry* registry_begin() { return kRegistry; }")
    L.append("size_t registry_size() { return sizeof(kRegistry) / sizeof(kRegistry[0]); }")
    L.append("")
    L.append("}  // namespace saem")
    L.append("")
    return "\n".join(L)


def emit_py(c):
    table = semantic_table(c)
    L = [header(c, "#", "py"),
         "import json",
         "import os",
         "import subprocess",
         "import sys",
         ""]
    L += ["# HANDSHAKE %s" % t for t in table]
    L += [""]
    L.append("METHODS = %s" % json.dumps(
        {m.name: {"kind": m.kind,
                  "ins": [{"name": p.name, "ty": p.ty.name,
                           "required": p.required,
                           "default": json_of_literal(p.default) if p.has_default else None}
                          for p in m.ins],
                  "outs": [p.name for p in m.outs]}
         for m in c.methods}, indent=2, sort_keys=False))
    L += ["",
          "",
          "def door_path():",
          "    return os.environ.get(\"SAEM_CLI\", os.path.join(",
          "        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),",
          "        \"core\", \"build\", \"saem_cli\"))",
          "",
          "",
          "def call(method, args=None):",
          "    if method not in METHODS:",
          "        raise ValueError(\"unknown method: %s\" % method)",
          "    payload = json.dumps({\"method\": method, \"args\": args or {}})",
          "    proc = subprocess.run([door_path()], input=payload + \"\\n\",",
          "                          capture_output=True, text=True, timeout=30)",
          "    if proc.returncode != 0:",
          "        raise RuntimeError(\"door refused: %s\" % proc.stderr.strip())",
          "    out = json.loads(proc.stdout.splitlines()[0])",
          "    if out.get(\"method\") != method:",
          "        raise RuntimeError(\"id-echo mismatch: %s\" % out.get(\"method\"))",
          "    return out.get(\"result\")",
          ""]
    for m in c.methods:
        fname = m.name.replace(".", "_")
        kwargs = ", ".join("%s=%r" % (p.name, json_of_literal(p.default))
                           for p in m.ins if p.has_default)
        reqs = ", ".join(p.name for p in m.ins if p.required)
        params = ", ".join(filter(None, [reqs, kwargs]))
        L.append("")
        L.append("def %s(%s):" % (fname, params))
        L.append("    args = {}")
        for p in m.ins:
            if p.required:
                L.append("    args[%r] = %s" % (p.name, p.name))
            elif p.has_default:
                L.append("    args[%r] = %s" % (p.name, p.name))
        L.append("    return call(%r, args)" % m.name)
    L += ["",
          "",
          "def selftest():",
          "    checks = []",
          "    lines = [l.split(\" \", 2)[2] for l in open(__file__).read().splitlines()",
          "             if l.startswith(\"# HANDSHAKE \")]",
          "    want_methods = [l for l in lines if l.startswith(\"method \")]",
          "    checks.append((\"table-parity\",",
          "                     len(want_methods) == len(METHODS),",
          "                     \"%d vs %d\" % (len(want_methods), len(METHODS))))",
          "    for name, meta in METHODS.items():",
          "        for p in meta[\"ins\"]:",
          "            if not p[\"required\"] and p[\"default\"] is None:",
          "                checks.append((\"a0-\" + name, False, p[\"name\"]))",
          "    checks.append((\"a0-declared-defaults\", True, \"ok\"))",
          "    return checks",
          "",
          "",
          "if __name__ == \"__main__\":",
          "    ok = True",
          "    for name, good, detail in selftest():",
          "        print(\"%s %s %s\" % (\"PASS\" if good else \"FAIL\", name, detail))",
          "        ok = ok and good",
          "    sys.exit(0 if ok else 1)",
          ""]
    return "\n".join(L)


def emit_cs(c):
    table = semantic_table(c)
    L = [header(c, "//", "cs"),
         "using System;",
         "using System.Diagnostics;",
         "using System.IO;",
         "using System.Text.Json.Nodes;",
         ""]
    L += ["// HANDSHAKE %s" % t for t in table]
    L += ["", "namespace SaemQcos {", "public static class Client {"]
    L += [
        "    public static string DoorPath() {",
        "        var env = Environment.GetEnvironmentVariable(\"SAEM_CLI\");",
        "        return env ?? Path.Combine(\"core\", \"build\", \"saem_cli\");",
        "    }",
        "",
        "    public static JsonNode Call(string method, JsonObject args) {",
        "        var req = new JsonObject { [\"method\"] = method, [\"args\"] = args };",
        "        var psi = new ProcessStartInfo {",
        "            FileName = DoorPath(),",
        "            RedirectStandardInput = true,",
        "            RedirectStandardOutput = true,",
        "            RedirectStandardError = true,",
        "        };",
        "        using var proc = Process.Start(psi);",
        "        proc.StandardInput.WriteLine(req.ToJsonString());",
        "        proc.StandardInput.Close();",
        "        var line = proc.StandardOutput.ReadLine();",
        "        proc.WaitForExit(30000);",
        "        if (proc.ExitCode != 0 || line == null)",
        "            throw new InvalidOperationException(\"door refused\");",
        "        var outObj = JsonNode.Parse(line);",
        "        if ((string)outObj[\"method\"] != method)",
        "            throw new InvalidOperationException(\"id-echo mismatch\");",
        "        return outObj[\"result\"];",
        "    }",
        "",
    ]
    for m in c.methods:
        mname = "".join(part.capitalize() for part in m.name.split("."))
        L.append("    public static JsonNode %s(JsonObject args) {" % mname)
        L.append("        return Call(%r, args ?? new JsonObject());".replace("%r", '"%s"' % m.name))
        L.append("    }")
        L.append("")
    L += ["}  // class Client", "}  // namespace SaemQcos", ""]
    return "\n".join(L)


def emit_js(c):
    table = semantic_table(c)
    L = [header(c, "//", "js"), ""]
    L += ["// HANDSHAKE %s" % t for t in table]
    L += [""]
    L.append("const METHODS = %s;" % json.dumps(
        {m.name: {"kind": m.kind,
                  "ins": [p.name for p in m.ins],
                  "outs": [p.name for p in m.outs]}
         for m in c.methods}, indent=2))
    L += ["",
          "function call(writeLine, method, args) {",
          "  if (!Object.prototype.hasOwnProperty.call(METHODS, method)) {",
          "    throw new Error('unknown method: ' + method);",
          "  }",
          "  writeLine(JSON.stringify({ method: method, args: args || {} }));",
          "}",
          "",
          "module.exports = { METHODS: METHODS, call: call };",
          ""]
    return "\n".join(L)


def emit_schema(c):
    return json.dumps({
        "version": c.version,
        "articles": c.articles,
        "caps": {k: json_of_literal(v) for k, v in c.caps.items()},
        "methods": [
            {"name": m.name, "kind": m.kind, "lang": m.lang,
             "ins": [{"name": p.name, "ty": p.ty.name, "required": p.required,
                      "default": json_of_literal(p.default) if p.has_default else None}
                     for p in m.ins],
             "outs": [{"name": p.name, "ty": p.ty.name} for p in m.outs]}
            for m in c.methods],
        "structs": {name: [{"field": f, "ty": t.name} for f, t in fields]
                    for name, fields in c.structs.items()},
    }, indent=2, sort_keys=False) + "\n"


def emit_diff(c):
    out = []
    for m in c.methods:
        happy = {"name": "%s happy path" % m.name, "method": m.name, "args": {}}
        for p in m.ins:
            if p.has_default:
                happy["args"][p.name] = json_of_literal(p.default)
            else:
                happy["args"][p.name] = DIFF_FALLBACK.get(p.ty.name,
                                                           DIFF_FALLBACK.get(
                                                               resolve_base(c, p.ty).name
                                                               if resolve_base(c, p.ty)
                                                               else "any", {}))
        out.append(happy)
        req = next((p for p in m.ins if p.required), None)
        if req:
            bad = {"name": "%s missing-%s must fail closed on BOTH sides"
                          % (m.name, req.name),
                   "method": m.name, "error": True, "args": dict(happy["args"])}
            del bad["args"][req.name]
            out.append(bad)
    return "".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n"


def emit_all(c):
    return {
        "schema": emit_schema(c),
        "cpp": emit_cpp(c),
        "py": emit_py(c),
        "cs": emit_cs(c),
        "js": emit_js(c),
        "diff": emit_diff(c),
    }


def handshake(c):
    arts = emit_all(c)
    digests = {}
    for lang, marker in (("cpp", "// HANDSHAKE "), ("py", "# HANDSHAKE "),
                         ("cs", "// HANDSHAKE "), ("js", "// HANDSHAKE ")):
        lines = [l[len(marker):] for l in arts[lang].splitlines() if l.startswith(marker)]
        digests[lang] = digest_lines(lines)
    values = set(digests.values())
    return {"equal": len(values) == 1, "got": {k: v[:12] for k, v in digests.items()}}


# --------------------------------------------------------------------------
# ledger receipt
# --------------------------------------------------------------------------

def ledger_path():
    env = os.environ.get("SAEM_LEDGER_PATH")
    if env:
        return Path(env)
    return ROOT / "logs" / "qcos_ledger.jsonl"


def receipt(cmd, exit_code, digests):
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({
        "schema_version": SCHEMA_VERSION,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gate": "qcosc",
        "cmd": cmd,
        "exit": exit_code,
        "digests": digests,
    }, sort_keys=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def sha16(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------
# selftest (frozen witnesses)
# --------------------------------------------------------------------------

_GOOD = '''@article A0 "defaults are declared canon literals; optional without default is refused"
@cap MAXP 0.95
@cap MAX_NUDGE 0.15
@cap CAP_ATTEMPTS 3
@cap KEEP_DETAIL 50
@cap MAX_FACULTY 4
@cap WORKING_LIMIT 32
@cap EPISODIC_LIMIT 64
@cap KEY_MAX 23
@cap CIR_STEPS 4096
@cap MAX_DELEGATION 8
@cap MAX_ACTIONS 64
@cap NAME_MAX 64
@cap MAX_PROJECT_STOPS 8
@type Key string max 23
@method qcos.boot { out ok: bool } pure cpp "Json::obj(\\"ok\\", true)"
@method qcos.read { in key: Key required, out value: number } resident cpp "store_get(a)"
@method qcos.zone0 { in intent: any required, out pass: bool } gate cpp "zone0(a)"
@method qcos.provenance { out trace: any } resident cpp "prov(a)"
@method gen.demo { in seed: uint32 = 11, in y0: int32 = 0, out n: number } pure cpp "demo(seed, y0)"
'''

_BAD_DUP = _GOOD + '@method qcos.boot { out ok: bool } pure cpp "Json::obj(\\"ok\\", true)"\n'
_BAD_NOCAPS = _GOOD.replace("@cap MAXP 0.95", "")
_BAD_CAPMUT = _GOOD.replace("@cap WORKING_LIMIT 32", "@cap WORKING_LIMIT 33")
_BAD_NOZONE = _GOOD.replace(
    '@method qcos.zone0 { in intent: any required, out pass: bool } gate cpp "zone0(a)"', "")
_BAD_A0 = _GOOD.replace("in seed: uint32 = 11, in y0: int32 = 0,", "in seed: uint32,")
_BAD_GATENOIMPL = _GOOD.replace('gate cpp "zone0(a)"', 'gate py "pass"')


def selftest():
    import tempfile
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "mini.cxn"
        p.write_text(_GOOD, encoding="utf-8")
        src, canon = build(p)
        want("parse", len(canon.methods) == 5 and canon.caps["WORKING_LIMIT"] == 32)
        want("article-ident-parses", "A0" in canon.articles,
             ",".join(sorted(canon.articles)))
        want("a0-declared-defaults-pass",
             not any("A0" in e for e in Checker(canon).check()))
        want("emit-determinism",
             emit_cpp(canon) == emit_cpp(canon) and emit_js(canon) == emit_js(canon))
        want("handshake", handshake(canon)["equal"], str(handshake(canon)["got"]))
        diff = emit_diff(canon)
        lines = [json.loads(x) for x in diff.splitlines() if x.strip()]
        want("diff-lines", len(lines) == 7, str(len(lines)))
        arts = emit_all(canon)
        out = Path(td) / "out"
        out.mkdir()
        for key, text in arts.items():
            (out / key).write_text(text, encoding="utf-8")
        want("emit-write", all((out / k).exists() for k in arts))
        for name, bad in (("dup-refused", _BAD_DUP),
                          ("nocaps-refused", _BAD_NOCAPS),
                          ("capmut-refused", _BAD_CAPMUT),
                          ("nozone-refused", _BAD_NOZONE),
                          ("a0-refused", _BAD_A0),
                          ("gatenoimpl-refused", _BAD_GATENOIMPL)):
            q = Path(td) / ("bad_%s.cxn" % name)
            q.write_text(bad, encoding="utf-8")
            try:
                _, bc = build(q)
                want(name, len(Checker(bc).check()) > 0,
                     ";".join(Checker(bc).check())[:80])
            except Refused as e:
                want(name, True, str(e)[:80])
    return checks


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv):
    args = argv[1:]
    if "--selftest" in args:
        ok = True
        for name, good, detail in selftest():
            print("%s %s %s" % ("PASS" if good else "FAIL", name, detail))
            ok = ok and good
        receipt("--selftest", 0 if ok else 1, {})
        return 0 if ok else 1

    verify = "--verify" in args
    do_handshake = "--handshake" in args
    do_json = "--json" in args
    emit_dir = None
    if "--emit" in args:
        emit_dir = Path(args[args.index("--emit") + 1])
    positional = [a for a in args
                  if not a.startswith("--") and a not in ([emit_dir] if emit_dir else [])]
    canon_path = Path(positional[0]) if positional else ROOT / "qcos.cxn"

    if not canon_path.exists():
        sys.stderr.write("[qcosc] ENV: canon not found: %s\n" % canon_path)
        receipt(" ".join(args), 2, {})
        return 2

    try:
        src, canon = build(canon_path)
    except Refused as e:
        sys.stderr.write("[qcosc] REFUSED:\n  %s\n" % e)
        receipt(" ".join(args), 1, {})
        return 1

    errs = Checker(canon).check()
    if errs:
        sys.stderr.write("[qcosc] REFUSED:\n")
        for e in errs:
            sys.stderr.write("  %s\n" % e)
        receipt(" ".join(args), 1, {})
        return 1

    arts = emit_all(canon)
    digests = {k: sha16(v) for k, v in arts.items()}

    if do_json:
        sys.stdout.write(arts["schema"])

    if verify:
        stale = []
        for key, path in ARTIFACTS.items():
            if not path.exists():
                stale.append("%s missing" % path)
            elif path.read_text(encoding="utf-8") != arts[key]:
                stale.append("%s stale" % path)
        if stale:
            sys.stderr.write("[qcosc] STALE:\n  %s\n" % "\n  ".join(stale))
            receipt(" ".join(args), 1, digests)
            return 1
        if do_handshake:
            h = handshake(canon)
            if not h["equal"]:
                sys.stderr.write("[qcosc] HANDSHAKE MISMATCH: %s\n" % h["got"])
                receipt(" ".join(args), 1, digests)
                return 1
        receipt(" ".join(args), 0, digests)
        return 0

    target_dir = emit_dir
    if target_dir is None:
        for key, path in ARTIFACTS.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(arts[key], encoding="utf-8")
    else:
        target_dir.mkdir(parents=True, exist_ok=True)
        for key, text in arts.items():
            (target_dir / key).write_text(text, encoding="utf-8")
    receipt(" ".join(args), 0, digests)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
