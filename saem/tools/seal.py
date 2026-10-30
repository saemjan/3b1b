#!/usr/bin/env python3
"""The release tool for the QCOS seal, written independently of the C code so the two can check each other.

The seal is one SHA-256 digest over everything that defines what a core IS: its capacity limits (read from core/c17/cos_limits.h),
a build id, the constitution articles and the method table. The tag signs the digest: HMAC-SHA-256(key, "QCOS-SEAL-TAG-V1" + digest).
The C core (core/c17/cos_seal.c) recomputes the digest and refuses to start, or freezes, if it differs from what was signed here.

    python3 tools/seal.py digest SPEC.json                      print the digest (hex)
    python3 tools/seal.py tag    SPEC.json --key-hex HEX        print the tag (hex)           (or --key-file FILE holding hex)
    python3 tools/seal.py emit-c SPEC.json --prefix P --out F   write C tables + digest [+ tag] for the core to compile in
    python3 tools/seal.py limits                                print the nine limits that go into the seal

SPEC.json:
    {"build_id": "...",
     "articles": [{"id": 1, "title": "...", "text": "..."}, ...],          ids strictly increasing, 0..65535
     "methods":  [{"id": 1, "name": "forecast.run", "flags": ["json"], "max_len": 4096}, ...]}   ids strictly increasing, 0..255

Canonical encoding (all integers little-endian; str = u32 byte length, then the UTF-8 bytes):
    "QCOS-SEAL-V1\\0" | nine u32 limits | str build_id | u32 n_articles, each (u16 id, str title, str text)
    | u32 n_methods, each (u16 id, u8 flags, u32 max_len, str name)

Honest limit: HMAC is symmetric, so whoever can read the key on a device can forge a tag. A public-key signature (Ed25519) replaces it in phase 2.
The key is never stored in this repository; test vectors use a labelled test key.
"""
import argparse
import hashlib
import hmac
import json
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMITS_H = os.path.join(ROOT, "core", "c17", "cos_limits.h")
LIMIT_NAMES = ["COS_WORKING_LIMIT", "COS_EPISODIC_RING", "COS_REG_DATA", "COS_BLOCK_SIZE", "COS_LOG_BLOCKS",
               "COS_MAX_INPUT", "COS_MAX_DEPTH", "COS_MAX_METHODS", "COS_QUARANTINE_AFTER"]
FLAGS = {"json": 1}
NAME_RE = re.compile(r"^[a-z][a-z0-9_.\-]{0,62}$")


class SpecError(ValueError):
    pass


def read_limits(path=LIMITS_H):
    """The nine limits, parsed from the C header so the two can never drift apart."""
    text = open(path, encoding="utf-8").read()
    out = []
    for name in LIMIT_NAMES:
        m = re.search(r"^#define\s+" + name + r"\s+(\d+)u?\b", text, re.M)
        if not m:
            raise SpecError("%s is not a plain number in %s" % (name, path))
        out.append(int(m.group(1)))
    return out


def _check_text(what, s):
    if not isinstance(s, str):
        raise SpecError("%s must be a string" % what)
    if "\x00" in s:
        raise SpecError("%s contains NUL: the C core reads strings up to the first NUL, so the digests would differ" % what)
    try:
        s.encode("utf-8")  # strict: refuses lone surrogates
    except UnicodeEncodeError:
        raise SpecError("%s is not valid Unicode" % what)
    return s


def validate(spec):
    if not isinstance(spec, dict):
        raise SpecError("the spec must be an object")
    _check_text("build_id", spec.get("build_id"))
    if not spec["build_id"]:
        raise SpecError("build_id is empty")
    arts = spec.get("articles")
    meths = spec.get("methods")
    if not isinstance(arts, list) or not isinstance(meths, list):
        raise SpecError("articles and methods must be lists")
    prev = -1
    for a in arts:
        if not isinstance(a.get("id"), int) or not 0 <= a["id"] <= 0xFFFF:
            raise SpecError("article id out of range: %r" % (a.get("id"),))
        if a["id"] <= prev:
            raise SpecError("article ids must be strictly increasing (at %d)" % a["id"])
        prev = a["id"]
        _check_text("article %d title" % a["id"], a.get("title"))
        _check_text("article %d text" % a["id"], a.get("text"))
    if len(meths) > read_limits()[LIMIT_NAMES.index("COS_MAX_METHODS")]:
        raise SpecError("too many methods")
    prev = -1
    for m in meths:
        if not isinstance(m.get("id"), int) or not 0 <= m["id"] <= 255:
            raise SpecError("method id out of range: %r" % (m.get("id"),))
        if m["id"] <= prev:
            raise SpecError("method ids must be strictly increasing (at %d): the core finds methods by binary search" % m["id"])
        prev = m["id"]
        if not isinstance(m.get("name"), str) or not NAME_RE.match(m["name"]):
            raise SpecError("method %d has a bad name %r" % (m["id"], m.get("name")))
        for f in m.get("flags", []):
            if f not in FLAGS:
                raise SpecError("method %d: unknown flag %r" % (m["id"], f))
        ml = m.get("max_len", 0)
        if not isinstance(ml, int) or not 0 <= ml <= 0xFFFFFFFF:
            raise SpecError("method %d: max_len out of range" % m["id"])


def _str(s):
    b = s.encode("utf-8")
    return struct.pack("<I", len(b)) + b


def canonical(spec, limits=None):
    """The exact byte string that is hashed."""
    validate(spec)
    limits = read_limits() if limits is None else limits
    out = [b"QCOS-SEAL-V1\x00"]
    out += [struct.pack("<I", v) for v in limits]
    out.append(_str(spec["build_id"]))
    out.append(struct.pack("<I", len(spec["articles"])))
    for a in spec["articles"]:
        out += [struct.pack("<H", a["id"]), _str(a["title"]), _str(a["text"])]
    out.append(struct.pack("<I", len(spec["methods"])))
    for m in spec["methods"]:
        flags = 0
        for f in m.get("flags", []):
            flags |= FLAGS[f]
        out += [struct.pack("<HBI", m["id"], flags, m.get("max_len", 0)), _str(m["name"])]
    return b"".join(out)


def digest(spec, limits=None):
    return hashlib.sha256(canonical(spec, limits)).digest()


def tag(key, dig):
    return hmac.new(key, b"QCOS-SEAL-TAG-V1" + dig, hashlib.sha256).digest()


def c_string(s):
    """A C string literal for any text: printable ASCII as is, everything else as 3-digit octal escapes (which cannot swallow the next digit)."""
    out = ['"']
    for b in s.encode("utf-8"):
        ch = chr(b)
        if 0x20 <= b <= 0x7E and ch not in '"\\?':
            out.append(ch)
        else:
            out.append("\\%03o" % b)
    out.append('"')
    return "".join(out)


def c_bytes(name, data):
    rows = []
    for i in range(0, len(data), 8):
        rows.append("  " + ", ".join("0x%02x" % b for b in data[i:i + 8]))
    return "static const uint8_t %s[%d] = {\n%s\n};\n" % (name, len(data), ",\n".join(rows))


def emit_c(spec, prefix, key=None, source="spec"):
    dig = digest(spec)
    lines = ["/* Generated by tools/seal.py from %s. Do not edit: change the spec and generate again. */" % source,
             "/* include after cos_seal.h */", ""]
    arts = spec["articles"]
    lines.append("static const CosArticle %s_ARTICLES[] = {" % prefix)
    for a in arts:
        lines.append("  {%du, %s, %s}," % (a["id"], c_string(a["title"]), c_string(a["text"])))
    if not arts:
        lines.append("  {0u, \"\", \"\"}, /* placeholder: n_articles is 0 */")
    lines.append("};")
    lines.append("static const CosMethodRule %s_METHODS[] = {" % prefix)
    for m in spec["methods"]:
        f = " | ".join({"json": "COS_FLAG_JSON"}[x] for x in m.get("flags", [])) or "0"
        lines.append("  {%du, %s, %du, %s}," % (m["id"], f, m.get("max_len", 0), c_string(m["name"])))
    if not spec["methods"]:
        lines.append("  {0u, 0, 0u, \"\"}, /* placeholder: n_methods is 0 */")
    lines.append("};")
    lines.append("static const CosSealInput %s_SEAL = {%s_ARTICLES, %du, %s_METHODS, %du, %s};" % (
        prefix, prefix, len(arts), prefix, len(spec["methods"]), c_string(spec["build_id"])))
    lines.append("")
    lines.append("/* digest of the canonical encoding (computed here, in Python, independently of cos_seal.c) */")
    lines.append(c_bytes(prefix + "_DIGEST", dig))
    if key is not None:
        lines.append("/* HMAC-SHA-256(key, \"QCOS-SEAL-TAG-V1\" + digest) */")
        lines.append(c_bytes(prefix + "_TAG", tag(key, dig)))
    return "\n".join(lines) + "\n"


def load_spec(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_key(args):
    if args.key_hex:
        return bytes.fromhex(args.key_hex)
    if args.key_file:
        return bytes.fromhex(open(args.key_file).read().strip())
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("digest", "tag", "emit-c"):
        p = sub.add_parser(name)
        p.add_argument("spec")
        p.add_argument("--key-hex")
        p.add_argument("--key-file")
        if name == "emit-c":
            p.add_argument("--prefix", required=True)
            p.add_argument("--out", required=True)
    sub.add_parser("limits")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "limits":
            for n, v in zip(LIMIT_NAMES, read_limits()):
                print("%s %d" % (n, v))
            return 0
        spec = load_spec(args.spec)
        if args.cmd == "digest":
            print(digest(spec).hex())
        elif args.cmd == "tag":
            key = get_key(args)
            if key is None:
                raise SpecError("tag needs --key-hex or --key-file")
            print(tag(key, digest(spec)).hex())
        else:
            text = emit_c(spec, args.prefix, get_key(args), os.path.relpath(args.spec, ROOT))
            with open(args.out, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
    except (SpecError, OSError, ValueError, KeyError) as e:
        print("seal.py: %s" % e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
