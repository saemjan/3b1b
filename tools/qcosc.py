#!/usr/bin/env python3
"""qcosc -- the QCOS protocol compiler.

One canon (qcos.cxn) in; four tongues out (C++, Python, C#, JavaScript),
plus the parity harness, the runtime schema, and a handshake that proves
all four clients agree on the same door.

The compiler exists because hand-written bindings drift, and in a
constitutional core drift is not a style problem -- it is a broken
article. Every type, every argument ORDER, every default and every
validation rule is declared once and emitted everywhere identically.

    python3 tools/qcosc.py qcos.cxn
    python3 tools/qcosc.py qcos.cxn --verify
    python3 tools/qcosc.py qcos.cxn --emit cpp
    python3 tools/qcosc.py qcos.cxn --handshake

Zero dependencies. Deterministic: the same canon always yields
byte-identical output, so the compiler itself obeys article A1.
"""
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field

# ----------------------------------------------------------------------
# diagnostics
# ----------------------------------------------------------------------
class LexError(Exception):
    pass


class ParseError(Exception):
    pass


class CanonError(Exception):
    """A constitutional violation detected at compile time. Fail closed."""


# ----------------------------------------------------------------------
# 1. lexer
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
# 2. AST
# ----------------------------------------------------------------------
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
    dir: str          # "in" | "out"
    name: str
    ty: TypeRef


@dataclass
class Method:
    name: str
    params: list
    kind: str         # pure | resident | gate
    impl: dict        # backend -> expression string
    line: int


@dataclass
class Canon:
    version: str = "0"
    articles: dict = field(default_factory=dict)
    caps: dict = field(default_factory=dict)
    types: dict = field(default_factory=dict)      # alias -> TypeRef base
    structs: dict = field(default_factory=dict)    # name -> [Param]
    methods: list = field(default_factory=list)


# ----------------------------------------------------------------------
# 3. parser (recursive descent)
# ----------------------------------------------------------------------
class Parser:
    def __init__(self, toks):
        self.t = toks
        self.i = 0

    def peek(self, k=0):
        return self.t[self.i + k]

    def kind(self):
        return self.t[self.i][0]

    def val(self):
        return self.t[self.i][1]

    def line(self):
        return self.t[self.i][2]

    def eat(self, kind=None, val=None):
        tok = self.t[self.i]
        if kind and tok[0] != kind:
            raise ParseError("line %d: expected %s, got %r" % (tok[2], kind, tok[1]))
        if val and tok[1] != val:
            raise ParseError("line %d: expected %r, got %r" % (tok[2], val, tok[1]))
        self.i += 1
        return tok

    # -- top -------------------------------------------------------------
    def parse(self):
        c = Canon()
        while self.kind() != "EOF":
            self.eat("AT")
            name = self.eat("IDENT")[1]
            if name == "core":
                c.version = unquote(self.eat("STRING")[1])
            elif name == "article":
                key = self.eat("IDENT")[1]
                c.articles[key] = unquote(self.eat("STRING")[1])
            elif name == "cap":
                key = self.eat("IDENT")[1]
                c.caps[key] = self._literal()
            elif name == "type":
                self._type(c)
            elif name == "struct":
                self._struct(c)
            elif name == "method":
                c.methods.append(self._method(c))
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
        if kind == "PUNCT" and val == "{":          # empty-object default
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
            ty.default = self._literal()
            ty.has_default = True
        return ty

    def _type(self, c):
        name = self.eat("IDENT")[1]
        c.types[name] = self._tyref()

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

    def _method(self, c):
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
            backend = self.eat("IDENT")[1]
            impl[backend] = unquote(self.eat("STRING")[1])
        return Method(name, params, kind, impl, line)


# ----------------------------------------------------------------------
# 4. semantic layer -- the constitutional gate, applied to the build
# ----------------------------------------------------------------------
BUILTIN = {"string", "number", "bool", "uint32", "int32", "any", "Json"}


class Checker:
    def __init__(self, c):
        self.c = c
        self.err = []

    def resolve(self, ty):
        seen = 0
        while ty.name not in BUILTIN and ty.name in self.c.types and seen < 8:
            base = self.c.types[ty.name]
            ty = TypeRef(base.name, ty.required, ty.finite or base.finite,
                         ty.max_len or base.max_len,
                         ty.default if ty.has_default else base.default,
                         ty.has_default or base.has_default)
            seen += 1
        if ty.name not in BUILTIN and ty.name not in self.c.structs:
            self.err.append("unknown type %r (fail closed -- declare it or remove it)" % ty.name)
        return ty

    def check(self):
        c = self.c
        if not c.articles:
            self.err.append("no articles: a core with no constitution is not a core")
        for cap in ("MAXP", "KEY_MAX"):
            if cap not in c.caps:
                self.err.append("missing cap %s -- the gate cannot be compiled" % cap)
        names = set()
        for m in c.methods:
            if m.name in names:
                self.err.append("duplicate method %s" % m.name)
            names.add(m.name)
            ins = [p for p in m.params if p.dir == "in"]
            outs = [p for p in m.params if p.dir == "out"]
            if not outs:
                self.err.append("%s: a method must declare an 'out'" % m.name)
            seen_in = set()
            for p in ins:
                p.ty = self.resolve(p.ty)
                if p.name in seen_in:
                    self.err.append("%s: duplicate arg %r" % (m.name, p.name))
                seen_in.add(p.name)
                if p.ty.required and p.ty.has_default:
                    self.err.append("%s.%s: cannot be both required and defaulted"
                                    % (m.name, p.name))
                if p.ty.has_default:
                    self._default_ok(m, p)
            # A0: nothing may be computed from nothing.
            if ins and all(not p.ty.required for p in ins):
                self.err.append("%s: A0 violation -- every argument optional means "
                                "the answer is not computed from the question" % m.name)
            if m.kind == "resident" and "cpp" not in m.impl:
                self.err.append("%s: resident method needs a cpp impl (state lives in the core)"
                                % m.name)
        return self.err

    def _default_ok(self, m, p):
        d, t = p.ty.default, p.ty.name
        ok = {
            "string": lambda: isinstance(d, str),
            "Key":    lambda: isinstance(d, str),
            "number": lambda: isinstance(d, (int, float)),
            "Prob":   lambda: isinstance(d, (int, float)),
            "uint32": lambda: isinstance(d, int) and 0 <= d < 2 ** 32,
            "Seed":   lambda: isinstance(d, int) and 0 <= d < 2 ** 32,
            "bool":   lambda: isinstance(d, bool),
            "any":    lambda: True,
            "Json":   lambda: True,
        }.get(t, lambda: True)
        if not ok():
            self.err.append("%s.%s: default %r does not type-check as %s"
                            % (m.name, p.name, d, t))


# ----------------------------------------------------------------------
# 5. type maps
# ----------------------------------------------------------------------
CPP  = {"string": "std::string", "Key": "std::string", "number": "double",
        "Prob": "double", "bool": "bool", "uint32": "uint32_t", "Seed": "uint32_t",
        "int32": "int32_t", "any": "Json", "Json": "Json"}
PY   = {"string": "str", "Key": "str", "number": "float", "Prob": "float",
        "bool": "bool", "uint32": "int", "Seed": "int", "int32": "int",
        "any": "Any", "Json": "Any"}
CS   = {"string": "string", "Key": "string", "number": "double", "Prob": "double",
        "bool": "bool", "uint32": "uint", "Seed": "uint", "int32": "int",
        "any": "JsonElement", "Json": "JsonElement"}
JS   = {"string": "string", "Key": "string", "number": "number", "Prob": "number",
        "bool": "boolean", "uint32": "number", "Seed": "number", "int32": "number",
        "any": "any", "Json": "any"}


def py_name(m):
    return m.replace(".", "_")


def cs_name(m):
    a, b = m.split(".", 1)
    return a.capitalize() + "." + b[0].upper() + b[1:]


def header(c, body, backend):
    h = hashlib.sha256(body.encode()).hexdigest()[:10]
    return ("// AUTO-GENERATED by qcosc from qcos.cxn (v%s, canon %s, backend %s)\n"
            "// DO NOT EDIT -- edit qcos.cxn and re-run: python3 tools/qcosc.py qcos.cxn\n"
            % (c.version, h, backend)).replace("//", "#") if backend == "py" else \
           ("// AUTO-GENERATED by qcosc from qcos.cxn (v%s, canon %s, backend %s)\n"
            "// DO NOT EDIT -- edit qcos.cxn and re-run: python3 tools/qcosc.py qcos.cxn\n"
            % (c.version, h, backend))


# ----------------------------------------------------------------------
# 6. backends
# ----------------------------------------------------------------------
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
        L.append('const Registrar R_%s("%s", [](const Json& a) -> Json {' % (py_name(m.name), m.name))
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
                 '  throw std::runtime_error("NOT_IMPLEMENTED: %s has no cpp impl in qcos.cxn");' % m.name)
        L.append("});\n")
    L.append("}  // namespace\n}  // namespace saem\n")
    return "\n".join(L)


def emit_py(c):
    L = [header(c, "py", "py").replace("//", "#"),
         '"""Typed client for the QCOS door. Generated -- one method per canon entry.',
         'Defaults and argument order come from qcos.cxn, never from this file."""',
         "from typing import Any, Dict\nimport json\n",
         "class QcosClient:\n"
         '    """One saem_cli process = one OS session. A2: no state lives here."""\n\n'
         "    def __init__(self, proc):\n"
         "        self._p = proc\n        self._id = 0\n\n"
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
        L.append("    public JsonElement %s(%s)" % (cs_name(m.name).replace(".", ""), sig))
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
         "'use strict';",
         "const MISSING = Symbol('missing');\n",
         "const CANON = {"]
    for m in c.methods:
        ins = [p for p in m.params if p.dir == "in"]
        spec = ", ".join('%s: {t:"%s", req:%s, d:%s}'
                         % (p.name, p.ty.name, "true" if p.ty.required else "false",
                            json.dumps(p.ty.default)) for p in ins)
        L.append('  "%s": {%s},   // order: [%s]' % (m.name, spec,
                 ", ".join(p.name for p in ins)))
    L.append("};\nmodule.exports = { CANON };\n")
    return "\n".join(L)


def emit_diff(c):
    """A5: rules without machine checks remain hypotheses. Emit the witnesses."""
    out = []
    for m in c.methods:
        ins = [p for p in m.params if p.dir == "in"]
        happy = {"name": "%s happy" % m.name, "method": m.name, "args": {}}
        for p in ins:
            happy["args"][p.name] = (p.ty.default if p.ty.has_default
                                     else {"string": "x", "Key": "k", "number": 1.0,
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
        "version": c.version,
        "articles": c.articles,
        "caps": c.caps,
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

TARGETS = {"cpp": "core/src/api_registry.g.cpp", "py": "saem/client.g.py",
           "cs": "SaemQcos/Client.g.cs", "js": "tools/ref_bridge.gen.js",
           "diff": "tests/diff/cases/canon.jsonl", "schema": "qcos.schema.json"}


# ----------------------------------------------------------------------
# 7. driver
# ----------------------------------------------------------------------
def build(path):
    src = open(path, encoding="utf-8").read()
    canon = Parser(tokenize(src)).parse()
    errs = Checker(canon).check()
    if errs:
        raise CanonError("\n".join("  %s" % e for e in errs))
    return src, canon


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a[2:] for a in argv[1:] if a.startswith("--")}
    if not args:
        print(__doc__)
        return 2
    src, canon = build(args[0])
    body = hashlib.sha256(src.encode()).hexdigest()

    if "verify" in flags:
        bad = []
        for name, fn in BACKENDS.items():
            want = fn(canon)
            p = TARGETS[name]
            have = open(p, encoding="utf-8").read() if os.path.exists(p) else None
            if have != want:
                bad.append(p)
        if bad:
            print("[qcosc] STALE bindings -- rebuild: python3 tools/qcosc.py %s" % args[0])
            for b in bad:
                print("   stale:", b)
            return 1
        print("[qcosc] in sync. canon %s, %d methods, %d articles"
              % (body[:10], len(canon.methods), len(canon.articles)))
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
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        open(p, "w", encoding="utf-8", newline="\n").write(text)
        print("[qcosc] %-7s -> %-34s %5d lines" % (name, p, text.count("\n")))
    print("[qcosc] canon body %s (compile this into SAEM_SOURCE_ID)" % body[:10])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except (LexError, ParseError, CanonError) as e:
        print("[qcosc] REFUSED:\n%s" % e)
        sys.exit(1)
