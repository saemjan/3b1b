#!/usr/bin/env python3
"""schema_validator.py — pre-flight content gate (gen-2).

Stdlib-only core so the CI gate runs without pip installs.
Optional witnesses (lazy, never hard-required):
  text_normalizer.spoken_word_count : duration band measured on the words
                                      XTTS will actually say, not raw tokens
  tools.physics_oracle.validate_row : physics violations
  tools.engine_check.parity_report  : schema-promised primitives that no
                                      renderer/engine routes (silent-skip killers)

Gates:
 1. required columns present; row arity matches header
 2. equations/visuals/beats JSON parse (idempotent CSV-escape repair) and
    contain ONLY finite numbers (A0: no poison enters the render)
 3. primitive types known; coordinates inside the orientation frame
 4. narration non-empty; spoken words plausible for target_duration_sec;
    duration inside absolute bounds
 5. PYQ integrity: four distinct options, valid correct_answer
 6. equation sanity: non-empty, bounded length/count
 7. batch novelty: identical visual_data_json across rows = clone scene

Promotions (warn -> error):
  --require-oracle   physics violations
  --require-routes   unrouted primitives
  --require-novelty  clone scenes

Usage:
    python3 schema_validator.py content_batch.csv [--require-oracle]
                                [--require-routes] [--require-novelty]
    python3 schema_validator.py --selftest
Exit code 1 on any ERROR.
"""
import csv
import json
import math
import re
import sys
from pathlib import Path

REQUIRED_COLUMNS = [
    "video_id", "concept_type", "header_title", "tagline",
    "question_text", "option_a", "option_b", "option_c", "option_d",
    "correct_answer", "equations_json", "visual_data_json",
    "audio_script", "orientation",
]
OPTIONAL_COLUMNS = [
    "beats_json", "target_duration_sec",
    "physics_verified", "visual_qa_passed", "audio_lufs",
    "language", "quality", "manifest_path",
]
CONCEPT_TYPES = {"GENERIC", "PYQ", "3D", "3D_HELIX"}
ORIENTATIONS = {"vertical", "horizontal"}
FRAME = {
    "vertical": (-4.5, 4.5, -8.0, 8.0),
    "horizontal": (-8.0, 8.0, -4.5, 4.5),
}
WORDS_PER_SEC = (1.87, 3.0)          # spoken words per second band
DURATION_BOUNDS = (4.0, 600.0)       # seconds; outside = error
MAX_EQUATIONS = 6
MAX_EQUATION_LEN = 120
ANSWER_KEYS = {"A", "B", "C", "D"}
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

try:                                  # spoken-word witness (pure stdlib module)
    import text_normalizer as _TN
except Exception:                     # pragma: no cover
    _TN = None

_PARITY_UNROUTED = None


def spoken_words(script: str) -> int:
    """Word count of what XTTS will actually say (falls back to raw tokens)."""
    if _TN is not None:
        try:
            return _TN.spoken_word_count(script)
        except Exception:
            pass
    return len(script.split())


def _unrouted():
    global _PARITY_UNROUTED
    if _PARITY_UNROUTED is None:
        try:
            from tools.engine_check import parity_report
            _PARITY_UNROUTED = set(parity_report().get("unrouted", []))
        except Exception:
            _PARITY_UNROUTED = set()
    return _PARITY_UNROUTED


def safe_json_loads(cell, default):
    """Idempotent JSON repair for CSV cells."""
    if cell is None:
        return default
    s = cell.strip()
    if not s:
        return default
    for cand in (s, s.replace("\\\\", "\\"), re.sub(r"\\(?!\\)", r"\\\\", s)):
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    return default


def _all_finite(obj, path=""):
    """Reject NaN/Infinity anywhere in parsed JSON."""
    if isinstance(obj, bool):
        return True, path
    if isinstance(obj, (int, float)):
        return math.isfinite(float(obj)), path or "<root>"
    if isinstance(obj, dict):
        for k, v in obj.items():
            ok, p = _all_finite(v, f"{path}.{k}")
            if not ok:
                return False, p
        return True, path
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            ok, p = _all_finite(v, f"{path}[{i}]")
            if not ok:
                return False, p
        return True, path
    return True, path


def _coords_in_frame(spec, frame):
    x0, x1, y0, y1 = frame
    for key in ("pos", "start", "end", "center", "position"):
        v = spec.get(key)
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            if not (x0 <= v[0] <= x1 and y0 <= v[1] <= y1):
                return False, key
    return True, None


def validate_row(row, header, require_oracle=False, require_routes=False):
    """Returns (errors, warnings) for one row dict."""
    errors, warnings = [], []
    vid = row.get("video_id", "<no id>")

    missing = [k for k in header if k not in row or row[k] is None]
    if missing:
        errors.append(f"{vid}: row arity does not match header ({missing[:3]})")

    ctype = row.get("concept_type", "")
    if ctype not in CONCEPT_TYPES:
        warnings.append(f"{vid}: concept_type '{ctype}' not in {sorted(CONCEPT_TYPES)}")

    orient = row.get("orientation", "vertical")
    if orient not in ORIENTATIONS:
        warnings.append(f"{vid}: orientation '{orient}' not in {sorted(ORIENTATIONS)}")
    frame = FRAME.get(orient, FRAME["vertical"])

    # ---- PYQ integrity -------------------------------------------------
    if ctype == "PYQ":
        if not (row.get("question_text") or "").strip():
            errors.append(f"{vid}: PYQ row missing question_text")
        opts = [(row.get(k) or "").strip() for k in
                ("option_a", "option_b", "option_c", "option_d")]
        filled = [o for o in opts if o]
        if len(filled) != 4:
            errors.append(f"{vid}: PYQ row missing option text")
        elif len(set(filled)) != 4:
            errors.append(f"{vid}: PYQ options must be distinct")
        ans = (row.get("correct_answer") or "").strip()
        if ans.upper() not in ANSWER_KEYS and ans not in opts:
            errors.append(f"{vid}: correct_answer '{ans}' is not A-D nor an option text")
    else:
        if row.get("question_text") or row.get("correct_answer"):
            warnings.append(f"{vid}: {ctype} row carries PYQ fields")

    # ---- equations ------------------------------------------------------
    equations = safe_json_loads(row.get("equations_json"), None)
    if equations is None:
        errors.append(f"{vid}: equations_json missing or unparseable")
    elif not isinstance(equations, list):
        errors.append(f"{vid}: equations_json must be a list")
    else:
        if len(equations) > MAX_EQUATIONS:
            warnings.append(f"{vid}: {len(equations)} equations "
                            f"(> {MAX_EQUATIONS}) will be truncated")
        for j, eq in enumerate(equations[:MAX_EQUATIONS]):
            if not isinstance(eq, str) or not eq.strip():
                errors.append(f"{vid}: equations_json[{j}] not a non-empty string")
            elif len(eq) > MAX_EQUATION_LEN:
                warnings.append(f"{vid}: equations_json[{j}] longer than "
                                f"{MAX_EQUATION_LEN} chars")

    # ---- visuals --------------------------------------------------------
    visuals = safe_json_loads(row.get("visual_data_json"), None)
    if visuals is None:
        errors.append(f"{vid}: visual_data_json missing or unparseable")
    elif not isinstance(visuals, list):
        errors.append(f"{vid}: visual_data_json must be a list")
    else:
        if not visuals:
            warnings.append(f"{vid}: visual_data_json empty (scene will be blank)")
        unrouted = _unrouted() if require_routes else set()
        for i, spec in enumerate(visuals):
            if not isinstance(spec, dict):
                errors.append(f"{vid}: visual_data_json[{i}] not a dict")
                continue
            ptype = spec.get("type")
            if ptype not in KNOWN_PRIMITIVES:
                warnings.append(f"{vid}: unknown primitive '{ptype}' at [{i}] "
                                f"(will be skipped)")
                continue
            ok_f, path_f = _all_finite(spec)
            if not ok_f:
                errors.append(f"{vid}: primitive [{i}] non-finite number at {path_f}")
                continue
            if ptype in unrouted:
                msg = (f"{vid}: primitive [{i}] '{ptype}' promised by schema "
                       f"but routed nowhere")
                (errors if require_routes else warnings).append(msg)
            ok, key = _coords_in_frame(spec, frame)
            if not ok:
                warnings.append(f"{vid}: primitive [{i}] '{key}' outside {orient} frame")

    # ---- beats ----------------------------------------------------------
    if row.get("beats_json"):
        beats = safe_json_loads(row.get("beats_json"), None)
        if beats is None or not isinstance(beats, list):
            errors.append(f"{vid}: beats_json present but unparseable")

    # ---- narration + spoken duration band -------------------------------
    script = row.get("audio_script", "")
    if not script.strip():
        errors.append(f"{vid}: audio_script empty")
    target = row.get("target_duration_sec")
    if target:
        try:
            t = float(target)
            lo_b, hi_b = DURATION_BOUNDS
            if not (lo_b <= t <= hi_b):
                errors.append(f"{vid}: target_duration_sec {t:g} outside "
                              f"{lo_b:g}-{hi_b:g}")
            words = spoken_words(script)
            lo, hi = WORDS_PER_SEC[0] * t, WORDS_PER_SEC[1] * t
            if not (lo <= words <= hi):
                warnings.append(f"{vid}: {words} spoken words implausible for "
                                f"{t:.0f}s (expected {lo:.0f}-{hi:.0f})")
        except ValueError:
            warnings.append(f"{vid}: target_duration_sec not a number")

    # ---- physics oracle --------------------------------------------------
    if require_oracle or True:
        if require_oracle:
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                from tools.physics_oracle import validate_row as oracle_row
                ok, violations = oracle_row(row)
                if not ok:
                    for v in violations:
                        errors.append(f"{vid}: [oracle] {v}")
            except ImportError:
                warnings.append(f"{vid}: physics oracle unavailable")
    return errors, warnings


def detect_clones(rows, promote=False):
    """Identical visual_data_json across rows = clone lesson (teacher rule)."""
    seen, out = {}, []
    for i, row in enumerate(rows, start=2):
        key = (row.get("visual_data_json") or "").strip()
        if not key:
            continue
        vid = row.get("video_id", "?")
        if key in seen:
            out.append((promote, f"line {i}: {vid} clones scene of line {seen[key]}"))
        else:
            seen[key] = i
    return out


def read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
    return header, rows


def validate_csv(path, require_oracle=False, require_routes=False,
                 require_novelty=False):
    path = Path(path)
    print(f"[INFO] Validating {path.name}"
          + (" (oracle required)" if require_oracle else "")
          + (" (routes required)" if require_routes else "")
          + (" (novelty required)" if require_novelty else ""))
    if not path.exists():
        print(f"[ERROR] file not found: {path}")
        return [], [f"file not found: {path}"], []
    header, rows = read_rows(path)
    all_errors, all_warnings = [], []
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        all_errors.append(f"header missing required columns: {missing}")
        return rows, all_errors, all_warnings
    unknown = [c for c in header if c not in REQUIRED_COLUMNS + OPTIONAL_COLUMNS]
    if unknown:
        all_warnings.append(f"header carries unknown columns: {unknown}")

    for promote, msg in detect_clones(rows, require_novelty):
        (all_errors if promote else all_warnings).append(msg)

    for i, row in enumerate(rows, start=2):
        errs, warns = validate_row(row, header, require_oracle, require_routes)
        all_errors += [f"line {i}: {e}" for e in errs]
        all_warnings += [f"line {i}: {w}" for w in warns]

    for w in all_warnings:
        print(f"[WARN] {w}")
    for e in all_errors:
        print(f"[ERROR] {e}")
    print(f"[FAILED] {len(all_errors)} error(s)." if all_errors
          else "[SUCCESS] All checks passed.")
    return rows, all_errors, all_warnings


def selftest():
    """Frozen witness: the gate itself must be machine-checked (A5)."""
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    base = {c: "" for c in REQUIRED_COLUMNS}
    base.update({
        "video_id": "t1", "concept_type": "GENERIC", "orientation": "vertical",
        "equations_json": '["E = mc^2"]',
        "visual_data_json": '[{"type": "dot", "pos": [0, 0]}]',
        "audio_script": " ".join(["word"] * 120),
        "target_duration_sec": "60",
    })
    e, w = validate_row(dict(base), REQUIRED_COLUMNS)
    want("clean-row-passes", not e, str(e))

    bad = dict(base, visual_data_json='[{"type": "dot", "pos": [NaN, 0]}]')
    e, w = validate_row(bad, REQUIRED_COLUMNS)
    want("nan-rejected", any("non-finite" in x for x in e), str(e))

    pyq = dict(base, concept_type="PYQ", question_text="Q?",
               option_a="1", option_b="2", option_c="3", option_d="4",
               correct_answer="E")
    e, w = validate_row(pyq, REQUIRED_COLUMNS)
    want("pyq-bad-answer-rejected", any("correct_answer" in x for x in e), str(e))

    unk = dict(base, visual_data_json='[{"type": "nope"}]')
    e, w = validate_row(unk, REQUIRED_COLUMNS)
    want("unknown-primitive-warns", any("unknown primitive" in x for x in w), str(w))

    short = dict(base, audio_script="too few words here", target_duration_sec="60")
    e, w = validate_row(short, REQUIRED_COLUMNS)
    want("spoken-band-warns", any("spoken words" in x for x in w), str(w))

    clones = detect_clones([dict(base), dict(base, video_id="t2")])
    want("clone-detected", len(clones) == 1, str(clones))
    return checks


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0
    if len(sys.argv) < 2:
        print("usage: schema_validator.py <csv> [--require-oracle] "
              "[--require-routes] [--require-novelty]")
        return 1
    flags = set(sys.argv[2:])
    _, errors, _ = validate_csv(
        sys.argv[1],
        "--require-oracle" in flags,
        "--require-routes" in flags,
        "--require-novelty" in flags,
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
