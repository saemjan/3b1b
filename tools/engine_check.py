#!/usr/bin/env python3
"""Engine health gate: import every engine headlessly and prove that
every primitive the schema promises is routed somewhere.

    python3 tools/engine_check.py [--github-summary]
"""
import ast
import importlib.util
import os
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ENGINES = [
    "calculus_engine", "electromagnetics_engine", "fluid_dynamics_engine",
    "geometry_engine", "linear_algebra_engine", "rotational_motion_engine",
    "physics_simulation", "sound_design", "soundscape", "text_normalizer",
]


def _stub(name):
    mod = types.ModuleType(name)

    def __getattr__(attr):
        cls = type(attr, (), {
            "__init__": lambda self, *a, **k: None,
            "__call__": lambda self, *a, **k: None,
        })
        setattr(mod, attr, cls)
        return cls

    mod.__getattr__ = __getattr__
    mod.__version__ = "0.0.0-stub"
    return mod


def install_stubs():
    for name in ("manim", "numpy", "torch", "TTS", "stable_whisper"):
        if name not in sys.modules:
            try:
                importlib.import_module(name)
            except Exception:
                sys.modules[name] = _stub(name)


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def routes_of(mod):
    found = set()
    for attr in ("ROUTES", "PRIMITIVES", "BUILDERS", "ROUTE_TABLE"):
        table = getattr(mod, attr, None)
        if isinstance(table, dict):
            found |= set(table.keys())
    for name in dir(mod):
        m = re.match(r"^(?:build|make|draw|prim)_(\w+)$", name)
        if m and callable(getattr(mod, name)):
            found.add(m.group(1))
    return found


def main():
    install_stubs()
    import schema_validator as sv

    errors, warnings, routed = [], [], set()

    for eng in ENGINES:
        p = ROOT / f"{eng}.py"
        if not p.exists():
            warnings.append(f"{eng}.py missing")
            continue
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            errors.append(f"{eng}.py SyntaxError line {e.lineno}: {e.msg}")
            continue
        try:
            mod = load(p)
            got = routes_of(mod)
            routed |= got
            print(f"[engine] {eng}: import ok, routes={sorted(got) or 'none declared'}")
        except Exception as e:
            errors.append(f"{eng}.py import failed: {type(e).__name__}: {e}")

    ru = ROOT / "render_universal.py"
    inline = set(re.findall(r"def (_prim_\w+)", ru.read_text(encoding="utf-8")))
    inline = {n[len("_prim_"):] for n in inline}
    routed |= inline

    unrouted = sorted(sv.KNOWN_PRIMITIVES - routed)
    unknown = sorted(routed - sv.KNOWN_PRIMITIVES)
    for u in unrouted:
        errors.append(f"primitive '{u}' is promised by schema but routed nowhere (silent skip at render)")
    for u in unknown:
        warnings.append(f"route '{u}' exists but schema does not list it")

    md = ["## 🧩 Engine health & routing parity", ""]
    md.append(f"- engines imported: {len(ENGINES) - sum(1 for e in errors if 'import' in e or 'Syntax' in e)}/{len(ENGINES)}")
    md.append(f"- routed primitives: {len(routed & sv.KNOWN_PRIMITIVES)}/{len(sv.KNOWN_PRIMITIVES)}")
    if unrouted:
        md.append("- ❌ unrouted: " + ", ".join(f"`{u}`" for u in unrouted))
    if unknown:
        md.append("- ⚠️ not in schema: " + ", ".join(f"`{u}`" for u in unknown))
    if not errors:
        md.append("- ✅ all engines import headlessly")
    text = "\n".join(md)
    print(text)

    if "--github-summary" in sys.argv and os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text + "\n")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
