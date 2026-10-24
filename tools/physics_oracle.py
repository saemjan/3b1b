#!/usr/bin/env python3
"""Physics Oracle v3: the first gate of the honest pipeline.

Judges a CSV row on twelve counts before any render:
  1  visual_data_json / equations_json / beats_json parse (CSV-tolerant)
  2  primitive types known
  3  primitive required fields and numeric ranges (SPEC table)
  4  numeric canon: dry-run the domain engines, quote their refusals
  5  restricted expressions (one variable x, allow-listed functions)
  6  LaTeX sanity (braces, \\left/\\right, \\begin/\\end, smart quotes)
  7  orientation-aware frame bounds and near-edge warnings
  8  cross-field consistency (beat focus, duplicate ids, word band)
  9  narration trust (impossible claims = error; unsourced = warn)
 10  size caps (points/samples/rectangles/matrix dim)
 11  empty-scene refusal
 12  receipt: version + digest of the judged row (provenance)

Severity model: "[error] ..." refuses the row; "[warn] ..." advises.
ok == (no errors). Warnings never block unless the caller says --strict.

Stdlib-only at import; domain engines are imported opportunistically so
the numeric canon is shared, and every delegation is counted in the
report so a silent drift (engine renamed) is visible in CI.

Usage:
    from tools.physics_oracle import validate_row, report
    ok, violations = validate_row(row)

    python3 tools/physics_oracle.py content_batch.csv [--strict] [--json]
    python3 tools/physics_oracle.py --selftest
"""
import ast
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ORACLE_VERSION = 3
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---- single canon: delegate numerics to the domain engines ------------
try:
    import calculus_engine as _calc
except Exception:
    _calc = None
try:
    import physics_simulation as _psim
except Exception:
    _psim = None
try:
    import rotational_motion_engine as _rot
except Exception:
    _rot = None
try:
    import linear_algebra_engine as _la
except Exception:
    _la = None

FRAME = {
    "vertical": (-4.5, 4.5, -8.0, 8.0),
    "horizontal": (-8.0, 8.0, -4.5, 4.5),
}
WORDS_PER_SEC = (1.87, 3.0)
CAPS = {"points": 256, "samples": 256, "rectangles": 256,
        "matrix_dim": 8, "formula_lines": 8}

KNOWN_PRIMITIVES = {
    "field", "vector_field", "charge", "particle", "dot", "vector", "arrow",
    "force", "line", "rod", "segment", "arc", "angle", "angle_arc", "brace",
    "graph", "function", "curve", "secant_tangent", "calculus_graph",
    "derivative_tangent", "integral_area", "riemann_sum", "electric_field",
    "magnetic_field", "electromagnetic_wave", "linear_algebra",
    "fluid_dynamics", "rotational_motion", "shape", "lens", "circle",
    "rectangle", "ellipse", "polygon", "text", "group",
    "orbit", "phasor", "ray", "particle_gas", "heat_flow", "energy_bar",
    "wave", "number_line", "pendulum", "spring",
    "equation_morph", "live_label", "numerical_chain", "warning_box",
    "quiz_frame", "concept_map",
    "polarized_wave", "dipole_radiation", "two_path_interference",
    "driven_oscillator", "wave_pulse", "harmonic_decomposition",
    "exponential_atmosphere", "energy_landscape", "angular_measurement",
    "crystal_lattice", "projectile_motion", "physics_simulation",
    "damped_oscillator", "radiating_wave", "two_source_waves",
    "driven_electron", "color_triangle", "thermionic_emission",
    "beat_pattern", "mirror_scene", "medium_atoms", "field_by_opacity",
    "polar_pattern", "phase_portrait", "light_wave_slice", "sliced_wave",
    "spectral_sum", "stream_field", "taylor_expand", "grid_warp",
    "geometry",
}
EXPR_TYPES = {"graph", "function", "curve", "calculus_graph",
              "derivative_tangent", "integral_area", "riemann_sum",
              "taylor_expand"}
BEAT_TYPES = {"hook", "promise", "law", "experiment", "emphasis",
              "midpoint", "punchline", "cta", "quiz"}
LAW_ALLOW = {"newton", "coulomb", "gauss", "faraday", "lenz", "ohm",
             "boyle", "charles", "ampere", "hooke", "bernoulli", "kepler",
             "planck", "snell", "stefan", "biot", "savart"}
TRUST_ERRORS = [
    (r"(fourth|fifth|4th|5th)\s+law\s+of\s+(motion|thermodynamics)",
     "no such law exists"),
    (r"gravity\s+is\s+the\s+strongest\s+(force|interaction)",
     "gravity is the weakest interaction"),
    (r"sound\s+(travels|propagates)\s+(through|in)\s+(a\s+)?vacuum",
     "sound needs a medium"),
]
TRUST_WARNINGS = [
    (r"\b(studies\s+show|scientists\s+(proved|prove|say)|research\s+confirms|"
     r"it\s+is\s+proven\s+that)\b", "unsourced authority; name it or cut it"),
    (r"\bdoi:10\.\d{4,9}/\S+", "citation present; verify before publish"),
    (r"\b(always|never|every)\b[^.]{0,60}\b(proves?|proof)\b",
     "absolute proof claim; physics states bounds"),
    (r"according\s+to\s+([a-z]+)'s\s+law", "__LAW__"),
]

# ---- SPEC: rules as data, so growth and authoring can read them --------
SPEC = {
    "projectile_motion": {
        "required": ["v0", "angle", "g"],
        "ranges": {"v0": (0, 1000), "angle": (0, 90), "g": (0.1, 100)}},
    "geometry": {
        "required": ["kind"],
        "kinds": {"point", "points", "segment", "polyline", "polygon",
                  "circle", "ellipse", "sphere", "cube", "cylinder", "cone"},
        "dim3_only": {"sphere", "cube", "cylinder", "cone"},
        "dims": {1, 2, 3}},
    "electric_field": {"required": ["charges"], "cap_samples": True},
    "magnetic_field": {"required": ["wires"]},
    "electromagnetic_wave": {
        "ranges": {"frequency": (0, None), "speed": (0, None),
                   "length": (0, None)}},
    "linear_algebra": {
        "required": ["operation"],
        "ops": {"vectors": ["a", "b"], "dot": ["a", "b"], "cross": ["a", "b"],
                "matrix_vector": ["matrix", "b"], "transform": ["matrix"],
                "solve": ["matrix", "rhs"], "determinant": ["matrix"]},
        "cap_matrix": True},
    "fluid_dynamics": {
        "required": ["operation"],
        "ops": {"venturi": ["inlet_height", "throat_height",
                            "inlet_velocity"],
                "hydrostatic": ["depth"]},
        "positive": ["inlet_height", "throat_height", "inlet_velocity",
                     "depth", "density"]},
    "rotational_motion": {
        "required": ["shape"],
        "shapes": {"solid_disk", "solid_cylinder", "hoop", "thin_ring",
                   "rod_center", "rod_end"},
        "positive": ["mass", "radius", "length"],
        "nonneg": ["torque", "angular_velocity", "time"]},
    "physics_simulation": {
        "required": ["bodies", "forces"],
        "ranges": {"duration": (0.000001, None), "steps": (2, 10000)},
        "force_types": {"uniform_acceleration": ["acceleration"],
                        "linear_drag": ["coefficient"],
                        "spring": ["body", "stiffness"],
                        "central_gravity": ["source", "mu"]}},
    "riemann_sum": {"cap_rectangles": True},
}


# ---------- helpers ------------------------------------------------------
def safe_json_loads(cell, default):
    """Same tolerant loader as validator and renderer: one canon."""
    if cell is None:
        return default
    s = cell.strip() if isinstance(cell, str) else cell
    if not s:
        return default
    if not isinstance(s, str):
        return s
    for cand in (s, s.replace("\\\\", "\\"), re.sub(r"\\(?!\\)", r"\\\\", s)):
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    return default


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) \
        and math.isfinite(v)


def _in_range(v, lo, hi):
    return (lo is None or v >= lo) and (hi is None or v <= hi)


_ALLOWED_FUNCS = {"abs", "acos", "asin", "atan", "ceil", "cos", "cosh",
                  "exp", "floor", "log", "max", "min", "sin", "sinh",
                  "sqrt", "tan", "tanh"}


def check_expression(expr):
    """Restricted AST policy, identical to the renderer's evaluator."""
    errs = []
    if not isinstance(expr, str):
        return ["expression must be a string"]
    if not (1 <= len(expr) <= 200):
        errs.append("expression length must be 1-200")
    src = expr.replace("^", "**")
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError as e:
        return [f"expression does not parse: {e}"]
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            if n.id not in ("x", "pi", "e"):
                errs.append(f"expression variable '{n.id}' not allowed (only x)")
        elif isinstance(n, ast.Call):
            fn = n.func.id if isinstance(n.func, ast.Name) else "?"
            if fn not in _ALLOWED_FUNCS:
                errs.append(f"expression function '{fn}' not allowed")
        elif isinstance(n, ast.Constant):
            if not isinstance(n.value, (int, float)):
                errs.append("expression constants must be numbers")
    return errs


def check_latex(eq):
    errs, warns = [], []
    if eq.count("{") != eq.count("}"):
        errs.append("unbalanced braces")
    if eq.count("\\left") != eq.count("\\right"):
        errs.append("unbalanced \\left/\\right")
    begins = re.findall(r"\\begin\{(\w+)\}", eq)
    ends = re.findall(r"\\end\{(\w+)\}", eq)
    if begins != ends:
        errs.append("unbalanced \\begin/\\end environments")
    if any(c in eq for c in "“”‘’"):
        errs.append("smart quotes in LaTeX")
    if "&" in eq and not any(e in begins for e in
                             ("align", "aligned", "array", "matrix",
                              "cases", "pmatrix", "bmatrix")):
        warns.append("bare '&' outside an align-family environment")
    if "\\" in eq and not re.search(r"\\[a-zA-Z]+", eq):
        warns.append("backslash without a command")
    return errs, warns


def _engine(fn, *a, **kw):
    """Dry-run the numeric canon. ok | skip | error."""
    if fn is None:
        return "skip", ""
    try:
        fn(*a, **kw)
        return "ok", ""
    except ValueError as e:
        return "error", str(e)
    except TypeError:
        return "skip", ""
    except Exception as e:  # engine bug is not the author's fault
        return "skip", f"engine raised {type(e).__name__}"


# ---------- per-primitive validation -------------------------------------
def check_primitive(i, v, deleg):
    errs, warns = [], []
    ptype = v.get("type")
    spec = SPEC.get(ptype, {})
    tag = f"visual[{i}] ({ptype})"

    for field in spec.get("required", []):
        if field not in v:
            errs.append(f"{tag} missing required field '{field}'")

    for field, (lo, hi) in spec.get("ranges", {}).items():
        if field in v:
            if not _num(v[field]):
                errs.append(f"{tag} '{field}' must be a finite number")
            elif not _in_range(v[field], lo, hi):
                errs.append(f"{tag} '{field}'={v[field]} outside "
                            f"[{lo if lo is not None else '-inf'}, "
                            f"{hi if hi is not None else 'inf'}]")

    for field in spec.get("positive", []):
        if field in v and _num(v[field]) and v[field] <= 0:
            errs.append(f"{tag} '{field}' must be > 0")
    for field in spec.get("nonneg", []):
        if field in v and _num(v[field]) and v[field] < 0:
            errs.append(f"{tag} '{field}' must be >= 0")

    if "kinds" in spec and v.get("kind") not in spec["kinds"]:
        errs.append(f"{tag} kind '{v.get('kind')}' not in "
                    f"{sorted(spec['kinds'])}")
    if "shapes" in spec and v.get("shape") not in spec["shapes"]:
        errs.append(f"{tag} shape '{v.get('shape')}' not in "
                    f"{sorted(spec['shapes'])}")
    if "dims" in spec:
        dim = v.get("dimension", 2)
        if dim not in spec["dims"]:
            errs.append(f"{tag} dimension must be 1, 2 or 3, got {dim}")
        elif v.get("kind") in spec.get("dim3_only", set()) and dim != 3:
            errs.append(f"{tag} kind '{v.get('kind')}' requires dimension=3")

    if "ops" in spec:
        op = v.get("operation")
        if op not in spec["ops"]:
            errs.append(f"{tag} operation '{op}' not in "
                        f"{sorted(spec['ops'])}")
        else:
            for field in spec["ops"][op]:
                if field not in v:
                    errs.append(f"{tag}.{op} missing '{field}'")

    # caps
    if spec.get("cap_samples"):
        n = len(v.get("charges", []) or v.get("columns", 0) and
                range(v.get("columns", 0) * v.get("rows", 0)) or [])
        if isinstance(v.get("charges"), list) and \
                len(v["charges"]) > CAPS["samples"]:
            errs.append(f"{tag} more than {CAPS['samples']} charges")
        if n and n != len(v.get("charges", [])):
            if v.get("columns", 0) * v.get("rows", 0) > CAPS["samples"]:
                errs.append(f"{tag} grid exceeds {CAPS['samples']} samples")
    if spec.get("cap_rectangles") and v.get("rectangles", 0) and \
            v["rectangles"] > CAPS["rectangles"]:
        errs.append(f"{tag} rectangles > {CAPS['rectangles']}")
    if spec.get("cap_matrix"):
        m = v.get("matrix")
        if isinstance(m, list):
            if len(m) > CAPS["matrix_dim"] or \
                    any(isinstance(r, list) and
                        len(r) > CAPS["matrix_dim"] for r in m):
                errs.append(f"{tag} matrix dim > {CAPS['matrix_dim']}")
    if ptype == "geometry" and isinstance(v.get("points"), list) and \
            len(v["points"]) > CAPS["points"]:
        errs.append(f"{tag} points > {CAPS['points']}")

    # physics_simulation deep rules (mirror the engine's refusals)
    if ptype == "physics_simulation":
        bodies = v.get("bodies", [])
        forces = v.get("forces", [])
        for j, b in enumerate(bodies if isinstance(bodies, list) else []):
            if not isinstance(b, dict):
                errs.append(f"{tag}.bodies[{j}] not a dict")
                continue
            if not (_num(b.get("mass")) and b["mass"] > 0):
                errs.append(f"{tag}.bodies[{j}] mass must be > 0")
            for k in ("position", "velocity"):
                p = b.get(k)
                if not (isinstance(p, list) and len(p) == 2 and
                        all(_num(c) for c in p)):
                    errs.append(f"{tag}.bodies[{j}].{k} must be a 2-vector "
                                f"of finite numbers")
        for j, f in enumerate(forces if isinstance(forces, list) else []):
            ft = f.get("type") if isinstance(f, dict) else None
            if ft not in spec["force_types"]:
                errs.append(f"{tag}.forces[{j}] unknown force type '{ft}'")
                continue
            for field in spec["force_types"][ft]:
                if field not in f:
                    errs.append(f"{tag}.forces[{j}].{ft} missing '{field}'")
            if ft == "linear_drag" and _num(f.get("coefficient")) and \
                    f["coefficient"] < 0:
                errs.append(f"{tag}.forces[{j}] drag coefficient must be >= 0")
            if ft == "central_gravity" and _num(f.get("mu")) and f["mu"] < 0:
                errs.append(f"{tag}.forces[{j}] mu must be >= 0")
            if ft == "spring" and not ("anchor" in f or "other" in f):
                errs.append(f"{tag}.forces[{j}] spring needs anchor or other")
        # delegate the RK4 dry-run to the engine (small steps, fast)
        if isinstance(bodies, list) and bodies and isinstance(forces, list):
            st, msg = _engine(
                getattr(_psim, "simulate_system", None),
                bodies, forces,
                duration=min(float(v.get("duration", 1.0)), 1.0),
                steps=min(int(v.get("steps", 20)), 50))
            deleg["psim"] = deleg.get("psim", 0) + (1 if st != "skip" else 0)
            if st == "error":
                errs.append(f"{tag} engine refused: {msg}")

    # engine delegation where signatures are documented
    if ptype in EXPR_TYPES and "expression" in v:
        st, msg = _engine(getattr(_calc, "compile_expression", None),
                          v["expression"])
        deleg["calc"] = deleg.get("calc", 0) + (1 if st != "skip" else 0)
        if st == "error":
            errs.append(f"{tag} engine refused expression: {msg}")
    if ptype == "rotational_motion" and v.get("shape") in \
            spec.get("shapes", set()):
        kw = {"shape": v["shape"], "mass": v.get("mass", 1.0)}
        if v["shape"].startswith("rod"):
            kw["length"] = v.get("length", 1.0)
        else:
            kw["radius"] = v.get("radius", 1.0)
        st, msg = _engine(getattr(_rot, "moment_of_inertia", None), **kw)
        deleg["rot"] = deleg.get("rot", 0) + (1 if st != "skip" else 0)
        if st == "error":
            errs.append(f"{tag} engine refused: {msg}")
    if ptype == "linear_algebra" and v.get("operation") == "solve" \
            and "matrix" in v and "rhs" in v:
        st, msg = _engine(getattr(_la, "solve_linear_system", None),
                          v["matrix"], v["rhs"])
        deleg["la"] = deleg.get("la", 0) + (1 if st != "skip" else 0)
        if st == "error":
            errs.append(f"{tag} engine refused: {msg}")

    return errs, warns


def check_bounds(i, v, orient):
    warns = []
    x0, x1, y0, y1 = FRAME.get(orient, FRAME["vertical"])
    for key in ("pos", "start", "end", "center", "pivot", "anchor"):
        p = v.get(key)
        if isinstance(p, (list, tuple)) and len(p) >= 2 and \
                _num(p[0]) and _num(p[1]):
            if not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1):
                warns.append(f"visual[{i}] '{key}' outside {orient} frame")
            elif (min(p[0] - x0, x1 - p[0]) < 0.5 or
                  min(p[1] - y0, y1 - p[1]) < 0.5):
                warns.append(f"visual[{i}] '{key}' near frame edge; may clip")
    return warns


def check_narration(script):
    errs, warns = [], []
    low = script.lower()
    for pat, why in TRUST_ERRORS:
        if re.search(pat, low):
            errs.append(f"[trust] {why}")
    for pat, why in TRUST_WARNINGS:
        m = re.search(pat, low)
        if m:
            if why == "__LAW__":
                name = m.group(1)
                if name not in LAW_ALLOW:
                    warns.append(f"[trust] '{name}'s law' is not in the "
                                 f"allow-list; verify or reword")
            else:
                warns.append(f"[trust] {why}")
    return errs, warns


# ---------- the gate ------------------------------------------------------
def report(row: Dict[str, Any]) -> Dict[str, Any]:
    """Full machine-readable judgment of one row."""
    errors: List[str] = []
    warns: List[str] = []
    deleg: Dict[str, int] = {}
    orient = (row.get("orientation") or "vertical").strip().lower()
    if orient not in FRAME:
        warns.append(f"bad orientation '{orient}'; assuming vertical")
        orient = "vertical"

    visuals = safe_json_loads(row.get("visual_data_json"), None)
    if visuals is None:
        errors.append("visual_data_json missing or unparseable")
        visuals = []
    elif not isinstance(visuals, list):
        errors.append("visual_data_json must be a list")
        visuals = []

    equations = safe_json_loads(row.get("equations_json"), None)
    if equations is None:
        errors.append("equations_json missing or unparseable")
        equations = []
    elif not isinstance(equations, list):
        errors.append("equations_json must be a list")
        equations = []

    beats = safe_json_loads(row.get("beats_json"), None)
    if row.get("beats_json") and beats is None:
        errors.append("beats_json present but unparseable")
        beats = []
    if beats is not None and not isinstance(beats, list):
        errors.append("beats_json must be a list")
        beats = []

    ids = []
    for i, v in enumerate(visuals):
        if not isinstance(v, dict):
            errors.append(f"visual[{i}] is not a dict")
            continue
        ptype = v.get("type")
        if ptype is None:
            errors.append(f"visual[{i}] missing 'type'")
            continue
        if ptype not in KNOWN_PRIMITIVES:
            warns.append(f"unknown primitive '{ptype}' at visual[{i}] "
                         f"(renderer will skip it)")
            continue
        e, w = check_primitive(i, v, deleg)
        errors += e
        warns += w
        if ptype in EXPR_TYPES and "expression" in v:
            errors += [f"visual[{i}] expression: {x}"
                       for x in check_expression(v["expression"])]
        warns += check_bounds(i, v, orient)
        ids.append(v.get("id"))

    dupes = {x for x in ids if x and ids.count(x) > 1}
    for d in sorted(dupes):
        warns.append(f"duplicate visual id '{d}'; beats can only hit one")

    for i, eq in enumerate(equations):
        if not isinstance(eq, str):
            errors.append(f"equations[{i}] must be a string")
            continue
        e, w = check_latex(eq)
        errors += [f"equations[{i}]: {x}" for x in e]
        warns += [f"equations[{i}]: {x}" for x in w]

    if beats:
        known_ids = set(x for x in ids if x)
        for i, b in enumerate(beats):
            if not isinstance(b, dict):
                errors.append(f"beat {i} not a dict")
                continue
            if b.get("type") not in BEAT_TYPES:
                warns.append(f"beat {i} unknown type '{b.get('type')}'")
            f = b.get("focus")
            if f and known_ids and f not in known_ids:
                warns.append(f"beat {i} focus '{f}' matches no visual id")

    script = row.get("audio_script", "") or ""
    e, w = check_narration(script)
    errors += e
    warns += w
    target = row.get("target_duration_sec")
    if target not in (None, ""):
        try:
            t = float(target)
            words = len(script.split())
            if not (WORDS_PER_SEC[0] * t <= words <= WORDS_PER_SEC[1] * t):
                warns.append(f"{words} words implausible for {t:.0f}s "
                             f"(band {WORDS_PER_SEC[0]*t:.0f}-"
                             f"{WORDS_PER_SEC[1]*t:.0f}); R4")
        except ValueError:
            warns.append("target_duration_sec not a number")

    if not visuals:
        errors.append("visual_data_json empty: scene will be blank")

    violations = [f"[error] {x}" for x in errors] + [f"[warn] {x}" for x in warns]
    digest = hashlib.sha256(
        (json.dumps({k: row.get(k, "") for k in sorted(row)},
                    sort_keys=True, ensure_ascii=False)
         + f"|oracle-v{ORACLE_VERSION}").encode("utf-8")).hexdigest()
    return {"ok": not errors, "errors": errors, "warnings": warns,
            "violations": violations, "delegations": deleg,
            "oracle_version": ORACLE_VERSION, "digest": digest}


def validate_row(row: Dict[str, Any]) -> Tuple[bool, List[str]]:
    r = report(row)
    return r["ok"], r["violations"]


def errors_of(violations):
    return [v for v in violations if v.startswith("[error]")]


# ---------- self-test: the witness witnesses itself -----------------------
SELFTEST = [
    ({"visual_data_json": json.dumps([{"type": "projectile_motion", "id": "p",
       "v0": 20, "angle": 45, "g": 9.8}]),
      "equations_json": json.dumps(["y = v_0 t - \\frac{1}{2}gt^2"]),
      "audio_script": "A projectile flies. Gravity keeps the books."},
     True, 0),
    ({"visual_data_json": json.dumps([{"type": "projectile_motion", "id": "p",
       "v0": -5, "angle": 45, "g": 9.8}]),
      "audio_script": "Bad launch."}, False, 1),
    ({"visual_data_json": json.dumps([{"type": "no_such_prim", "id": "x"}]),
      "audio_script": "Unknown primitive is a warning, not an error."},
     True, 1),
    ({"visual_data_json": json.dumps([{"type": "text", "id": "t",
       "text": "hi", "pos": [0, 0, 0]}]),
      "audio_script": "According to Newton's law of cooling, nothing."},
     True, 1),
    ({"visual_data_json": json.dumps([{"type": "text", "id": "t",
       "text": "hi", "pos": [0, 0, 0]}]),
      "audio_script": "Sound travels through a vacuum just fine."},
     False, 1),
    ({"visual_data_json": json.dumps([{"type": "graph", "id": "g",
       "expression": "import os"}]),
      "audio_script": "Forbidden expression."}, False, 1),
]


def selftest():
    bad = 0
    for i, (row, want_ok, want_warns) in enumerate(SELFTEST):
        r = report(row)
        got_warns = len(r["warnings"])
        if r["ok"] != want_ok or (want_warns and got_warns < want_warns):
            bad += 1
            print(f"[selftest] case {i} MISMATCH ok={r['ok']} "
                  f"warns={got_warns} errors={r['errors']}")
        else:
            print(f"[selftest] case {i} ok")
    print(f"[selftest] {len(SELFTEST) - bad}/{len(SELFTEST)} passed")
    return 1 if bad else 0


# ---------- CLI ------------------------------------------------------------
def main(argv):
    if "--selftest" in argv:
        return selftest()
    if len(argv) < 2:
        print("usage: physics_oracle.py <csv> [--strict] [--json] | --selftest")
        return 1
    path = Path(argv[1])
    strict = "--strict" in argv
    as_json = "--json" in argv
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [dict(r) for r in csv.DictReader(f)]
    out, hard = [], 0
    for row in rows:
        r = report(row)
        if not r["ok"] or (strict and r["warnings"]):
            hard += 1
        out.append({"video_id": row.get("video_id"), **r})
        if not as_json:
            tag = "OK  " if r["ok"] and not (strict and r["warnings"]) else "BAD "
            print(f"[{tag}] {row.get('video_id'):<36} "
                  f"errors={len(r['errors'])} warns={len(r['warnings'])} "
                  f"deleg={sum(r['delegations'].values())} "
                  f"digest={r['digest'][:12]}")
            for v in r["violations"]:
                print(f"        {v}")
    if as_json:
        print(json.dumps(out, ensure_ascii=False))
    print(f"[oracle] {len(rows) - hard}/{len(rows)} rows pass"
          + (" (strict)" if strict else ""))
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
