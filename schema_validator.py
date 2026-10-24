#!/usr/bin/env python3
"""Pre-flight validation for content CSVs. Stdlib only (no numpy, no manim),
so the CI validate job runs without pip installs.

Gates enforced here (structure + physics):
  1. Required columns present, row arity matches header.
  2. equations_json / visual_data_json / beats_json parse as JSON (idempotent
     repair for CSV escaping: doubled backslashes, lone backslashes, empty).
  3. Every primitive type is known; coordinates inside the orientation frame.
  4. Narration word count plausible for target_duration_sec.
  5. Physics oracle (tools.physics_oracle) violations become ERRORs when
     --require-oracle is passed, WARNs otherwise.

Usage:
    python3 schema_validator.py content_batch.csv [--require-oracle]
Exit code 1 on any ERROR.
"""
import csv
import json
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
WORDS_PER_SEC = (1.87, 3.0)  # 112-180 words @60s, 337-540 @180s

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


def safe_json_loads(cell, default):
    """Idempotent JSON repair for CSV cells: well-formed passes through,
    doubled backslashes, lone backslashes, and empty cells are handled."""
    if cell is None:
        return default
    s = cell.strip()
    if not s:
        return default
    for candidate in (s, s.replace("\\\\", "\\"), re.sub(r"\\(?!\\)", r"\\\\", s)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return default


def _coords_in_frame(spec, frame):
    x0, x1, y0, y1 = frame
    for key in ("pos", "start", "end", "center", "position"):
        v = spec.get(key)
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            if not (x0 <= v[0] <= x1 and y0 <= v[1] <= y1):
                return False, key
    return True, None


def validate_row(row, header, require_oracle=False):
    """Returns (errors, warnings) for one row dict."""
    errors, warnings = [], []
    vid = row.get("video_id", "<no id>")

    if len(header) != len([k for k in row.keys() if row[k] is not None]) and \
            any(row.get(k) is None for k in header):
        errors.append(f"{vid}: row arity does not match header")

    ctype = row.get("concept_type", "")
    if ctype not in CONCEPT_TYPES:
        warnings.append(f"{vid}: concept_type '{ctype}' not in {sorted(CONCEPT_TYPES)}")
    orient = row.get("orientation", "vertical")
    if orient not in ORIENTATIONS:
        warnings.append(f"{vid}: orientation '{orient}' not in {sorted(ORIENTATIONS)}")
    frame = FRAME.get(orient, FRAME["vertical"])

    if ctype == "PYQ":
        for k in ("question_text", "option_a", "option_b", "option_c",
                  "option_d", "correct_answer"):
            if not row.get(k):
                errors.append(f"{vid}: PYQ row missing '{k}'")
    else:
        if row.get("question_text") or row.get("correct_answer"):
            warnings.append(f"{vid}: {ctype} row carries PYQ fields")

    equations = safe_json_loads(row.get("equations_json"), None)
    if equations is None:
        errors.append(f"{vid}: equations_json missing or unparseable")
    elif not isinstance(equations, list):
        errors.append(f"{vid}: equations_json must be a list")

    visuals = safe_json_loads(row.get("visual_data_json"), None)
    if visuals is None:
        errors.append(f"{vid}: visual_data_json missing or unparseable")
    elif not isinstance(visuals, list):
        errors.append(f"{vid}: visual_data_json must be a list")
    else:
        if not visuals:
            warnings.append(f"{vid}: visual_data_json empty (scene will be blank)")
        for i, spec in enumerate(visuals):
            if not isinstance(spec, dict):
                errors.append(f"{vid}: visual_data_json[{i}] not a dict")
                continue
            ptype = spec.get("type")
            if ptype not in KNOWN_PRIMITIVES:
                warnings.append(f"{vid}: unknown primitive '{ptype}' at [{i}] (will be skipped)")
                continue
            ok, key = _coords_in_frame(spec, frame)
            if not ok:
                warnings.append(f"{vid}: primitive [{i}] '{key}' outside {orient} frame")

    if row.get("beats_json"):
        beats = safe_json_loads(row.get("beats_json"), None)
        if beats is None or not isinstance(beats, list):
            errors.append(f"{vid}: beats_json present but unparseable")

    script = row.get("audio_script", "")
    target = row.get("target_duration_sec")
    if target:
        try:
            t = float(target)
            words = len(script.split())
            lo, hi = WORDS_PER_SEC[0] * t, WORDS_PER_SEC[1] * t
            if not (lo <= words <= hi):
                warnings.append(
                    f"{vid}: {words} words implausible for {t:.0f}s "
                    f"(expected {lo:.0f}-{hi:.0f})")
        except ValueError:
            warnings.append(f"{vid}: target_duration_sec not a number")
    elif not script.strip():
        errors.append(f"{vid}: audio_script empty")

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


def read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
    return header, rows


def validate_csv(path, require_oracle=False):
    path = Path(path)
    print(f"[INFO] Validating {path.name}"
          + (" (oracle required)" if require_oracle else ""))
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

    for i, row in enumerate(rows, start=2):
        errs, warns = validate_row(row, header, require_oracle)
        all_errors += [f"line {i}: {e}" for e in errs]
        all_warnings += [f"line {i}: {w}" for w in warns]

    for w in all_warnings:
        print(f"[WARN] {w}")
    for e in all_errors:
        print(f"[ERROR] {e}")
    if all_errors:
        print(f"[FAILED] {len(all_errors)} error(s).")
    else:
        print("[SUCCESS] All checks passed.")
    return rows, all_errors, all_warnings


def main():
    if len(sys.argv) < 2:
        print("usage: schema_validator.py <csv> [--require-oracle]")
        return 1
    require = "--require-oracle" in sys.argv
    _, errors, _ = validate_csv(sys.argv[1], require)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
