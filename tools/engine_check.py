#!/usr/bin/env python3
"""engine_check.py — gen-3 CI gate: import, route parity, frozen witnesses.

Three machine checks in one headless process (A5):
  1 IMPORT   every visual engine imports with manim stubbed (bare-machine
             safe); numpy is NOT stubbed — gen-3 cores are pure stdlib and
             must prove they run with or without it
  2 ROUTES   union(engine ROUTE_TABLEs) ∪ render_universal.routed_types()
             must cover schema_validator.KNOWN_PRIMITIVES (no silent skips);
             surplus routes warn; schema canon must equal oracle canon;
             jee_model_engine.live_parity() manifest must be fully routed
  3 WITNESS  every engine/tool exposing selftest() must return all-ok;
             a crashing selftest is a failure, never a skip

Exit codes: 0 clean | 1 gate failure | 2 environment (stub machinery broke)
Usage: python3 tools/engine_check.py [--github-summary] [--json]
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ENGINES = [
    "calculus_engine", "electromagnetics_engine", "fluid_dynamics_engine",
    "geometry_engine", "linear_algebra_engine", "rotational_motion_engine",
    "physics_simulation", "jee_model_engine",
]
TOOLS = [
    "text_normalizer", "soundscape", "sound_design", "generate_audio",
    "schema_validator", "physics_oracle", "visual_qa", "ledger",
    "golden_qcos",
]


# ------------------------------------------------------------- manim stub
class _Dummy:
    """Survives any builder call: construct, call, attribute, arithmetic."""

    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return _Dummy()

    def __getattr__(self, n):
        return _Dummy()

    def __mul__(self, o):
        return _Dummy()

    def __rmul__(self, o):
        return _Dummy()

    def __add__(self, o):
        return _Dummy()

    def __radd__(self, o):
        return _Dummy()

    def __sub__(self, o):
        return _Dummy()

    def __rsub__(self, o):
        return _Dummy()

    def __neg__(self):
        return _Dummy()

    def __getitem__(self, i):
        return _Dummy()

    def __iter__(self):
        return iter(())


def _stub(name):
    mod = types.ModuleType(name)

    def __getattr__(attr):
        cls = type(attr, (_Dummy,), {})
        setattr(mod, attr, cls)
        return cls

    mod.__getattr__ = __getattr__
    mod.__version__ = "0.0.0-stub"
    return mod


def install_stubs():
    for name in ("manim", "torch", "TTS", "stable_whisper"):
        if name not in sys.modules:
            try:
                importlib.import_module(name)
            except Exception:
                sys.modules[name] = _stub(name)
    rf = types.ModuleType("manim.rate_functions")
    rf.__getattr__ = lambda attr: (lambda x: x)
    sys.modules["manim.rate_functions"] = rf
    manim = sys.modules.get("manim")
    if manim is not None:
        manim.rate_functions = rf


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def routes_of(mod):
    found = set()
    for attr in ("ROUTE_TABLE", "ROUTES", "PRIMITIVES", "BUILDERS"):
        table = getattr(mod, attr, None)
        if isinstance(table, dict):
            found |= set(table.keys())
    return found


def run_witness(mod, name):
    fn = getattr(mod, "selftest", None)
    if not callable(fn):
        return []
    try:
        out = fn()
    except Exception as e:
        return [(f"{name}:selftest-crash", False, f"{type(e).__name__}: {e}")]
    if isinstance(out, int):            # legacy boolean-style selftest
        return [(f"{name}:selftest", out == 0, "")]
    return [(f"{name}:{n}", bool(ok), d) for n, ok, d in out]


# ---------------------------------------------------------------- the gate
def collect():
    errors, warnings, routed = [], [], set()
    witness_fails = []
    loaded = {}

    for name in ENGINES + TOOLS:
        p = ROOT / f"{name}.py"
        if not p.exists():
            warnings.append(f"{name}.py missing")
            continue
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            errors.append(f"{name}.py SyntaxError line {e.lineno}: {e.msg}")
            continue
        try:
            mod = load(p)
        except Exception as e:
            errors.append(f"{name}.py import failed: {type(e).__name__}: {e}")
            continue
        loaded[name] = mod
        got = routes_of(mod)
        routed |= got
        print(f"[engine] {name}: import ok, routes={sorted(got) or 'none'}")
        for wn, ok, detail in run_witness(mod, name):
            if not ok:
                witness_fails.append((wn, detail))
            print(f"[witness] {'ok ' if ok else 'FAIL'} {wn} "
                  f"{'' if ok else detail}")

    # renderer inline primitives + engine routes, via its own API
    ru = ROOT / "render_universal.py"
    if ru.exists():
        try:
            mod = load(ru)
            fn = getattr(mod, "routed_types", None)
            inline = set(fn()) if callable(fn) else set()
            routed |= inline
            print(f"[engine] render_universal: routes={len(inline)}")
            for wn, ok, detail in run_witness(mod, "render_universal"):
                if not ok:
                    witness_fails.append((wn, detail))
        except Exception as e:
            errors.append(f"render_universal.py import failed: "
                          f"{type(e).__name__}: {e}")
    else:
        errors.append("render_universal.py missing")

    # canon parity: schema vs oracle (one truth, two gates)
    sv, po = loaded.get("schema_validator"), loaded.get("physics_oracle")
    if sv and po:
        diff = set(sv.KNOWN_PRIMITIVES) ^ set(po.KNOWN_PRIMITIVES)
        if diff:
            errors.append(f"schema/oracle primitive canon drifted: "
                          f"{sorted(diff)}")
        known = set(sv.KNOWN_PRIMITIVES)
    elif sv:
        known = set(sv.KNOWN_PRIMITIVES)
    else:
        known = set()
        errors.append("schema_validator unavailable; canon unchecked")

    # jee manifest parity (content layer may only emit routed primitives)
    jee = loaded.get("jee_model_engine")
    if jee and hasattr(jee, "live_parity"):
        lp = jee.live_parity()
        for t in lp.get("unrouted_manifest", []):
            errors.append(f"jee manifest type '{t}' routed nowhere")

    unrouted = sorted(known - routed)
    surplus = sorted(routed - known)
    for u in unrouted:
        errors.append(f"primitive '{u}' promised by schema but routed "
                      f"nowhere (silent skip at render)")
    for u in surplus:
        warnings.append(f"route '{u}' exists but schema does not list it")
    for wn, detail in witness_fails:
        errors.append(f"witness failed: {wn} {detail}")

    report = {
        "engines_imported": len(loaded),
        "routed_cover": f"{len(routed & known)}/{len(known)}",
        "unrouted": unrouted,
        "surplus": surplus,
        "witness_fails": [w for w, _ in witness_fails],
        "errors": errors,
        "warnings": warnings,
    }
    return report


def main():
    try:
        install_stubs()
    except Exception as e:
        print(f"[engine] stub machinery broke: {e}")
        return 2
    report = collect()
    md = ["## 🧩 Engine health, routing parity & witnesses (gen-3)", ""]
    md.append(f"- engines/tools imported: {report['engines_imported']}/"
              f"{len(ENGINES) + len(TOOLS) + 1}")
    md.append(f"- routed primitives: {report['routed_cover']}")
    if report["unrouted"]:
        md.append("- ❌ unrouted: " + ", ".join(f"`{u}`"
                                                for u in report["unrouted"]))
    if report["surplus"]:
        md.append("- ⚠️ not in schema: " + ", ".join(f"`{u}`"
                                                     for u in report["surplus"]))
    if report["witness_fails"]:
        md.append("- ❌ witnesses: " + ", ".join(report["witness_fails"]))
    if not report["errors"]:
        md.append("- ✅ imports clean, canon aligned, all witnesses ok")
    text = "\n".join(md)
    print(text)
    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False))
    if "--github-summary" in sys.argv and os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a",
                  encoding="utf-8") as f:
            f.write(text + "\n")
    try:
        from tools.ledger import append
        append({"gate": "engine_check", "schema_version": 3,
                "status": "pass" if not report["errors"] else "fail",
                "unrouted": report["unrouted"],
                "witness_fails": report["witness_fails"],
                "routed_cover": report["routed_cover"]})
    except Exception:
        pass
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
