#!/usr/bin/env python3
"""
Physics Oracle: Validates that the physics in a CSV row is internally consistent.

This is the first gate in the honest pipeline. Before any rendering happens,
the oracle checks:
1. All primitives in visual_data_json are known
2. equations_json contains only valid LaTeX
3. Physics-engineered primitives have required fields
4. Geometry dimensions are valid
5. Projectile motion parameters are physically reasonable

Returns: (ok: bool, violations: list[str])

Usage:
    from tools.physics_oracle import validate_row
    ok, violations = validate_row(row_dict)
    if not ok:
        print(f"Physics validation failed: {violations}")
"""

import json
import re
from typing import Tuple, List, Dict, Any


# Known primitives that the renderer supports
KNOWN_PRIMITIVES = {
    # Static primitives
    "field", "vector_field", "charge", "particle", "dot", "vector", "arrow", 
    "force", "line", "rod", "segment", "arc", "angle", "angle_arc", "brace",
    "graph", "function", "curve", "secant_tangent", "calculus_graph",
    "derivative_tangent", "integral_area", "riemann_sum", "electric_field",
    "magnetic_field", "electromagnetic_wave", "linear_algebra", "fluid_dynamics",
    "rotational_motion", "shape", "lens", "circle", "rectangle", "ellipse",
    "polygon", "text", "group",
    
    # Motion primitives
    "orbit", "phasor", "ray", "particle_gas", "heat_flow", "energy_bar",
    "wave", "number_line", "pendulum", "spring",
    
    # Self-animated primitives
    "equation_morph", "live_label", "numerical_chain", "warning_box",
    "quiz_frame", "concept_map",
    
    # Physics-engineered primitives
    "polarized_wave", "dipole_radiation", "two_path_interference",
    "driven_oscillator", "wave_pulse", "harmonic_decomposition",
    "exponential_atmosphere", "energy_landscape", "angular_measurement",
    "crystal_lattice", "projectile_motion", "physics_simulation",
    
    # Advanced physics primitives
    "damped_oscillator", "radiating_wave", "two_source_waves",
    "driven_electron", "color_triangle", "thermionic_emission",
    "beat_pattern", "mirror_scene", "medium_atoms", "field_by_opacity",
    "polar_pattern", "phase_portrait", "light_wave_slice", "sliced_wave",
    "spectral_sum", "stream_field", "taylor_expand", "grid_warp",
    
    # Geometry primitive
    "geometry"
}


def validate_row(row: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate the physics in a CSV row.
    
    Args:
        row: Dictionary with keys like 'visual_data_json', 'equations_json', etc.
    
    Returns:
        (ok, violations) where ok is True if validation passed,
        and violations is a list of error messages.
    """
    violations = []
    
    # 1. Parse and validate visual_data_json
    try:
        visual_data_str = row.get("visual_data_json", "[]")
        if isinstance(visual_data_str, str):
            visuals = json.loads(visual_data_str)
        else:
            visuals = visual_data_str
    except json.JSONDecodeError as e:
        return False, [f"visual_data_json is not valid JSON: {e}"]
    
    if not isinstance(visuals, list):
        return False, ["visual_data_json must be a list"]
    
    # 2. Check that all primitives are known
    for i, v in enumerate(visuals):
        if not isinstance(v, dict):
            violations.append(f"visual_data_json[{i}] is not a dict")
            continue
        
        ptype = v.get("type")
        if ptype is None:
            violations.append(f"visual_data_json[{i}] missing 'type' field")
            continue
        
        if ptype not in KNOWN_PRIMITIVES:
            violations.append(f"Unknown primitive '{ptype}' in visual_data_json[{i}]")
    
    # 3. Parse and validate equations_json
    try:
        equations_str = row.get("equations_json", "[]")
        if isinstance(equations_str, str):
            equations = json.loads(equations_str)
        else:
            equations = equations_str
    except json.JSONDecodeError as e:
        return False, [f"equations_json is not valid JSON: {e}"]
    
    if not isinstance(equations, list):
        return False, ["equations_json must be a list"]
    
    for i, eq in enumerate(equations):
        if not isinstance(eq, str):
            violations.append(f"equations_json[{i}] must be a string, got {type(eq).__name__}")
            continue
        
        # Basic LaTeX check: balanced braces
        if eq.count("{") != eq.count("}"):
            violations.append(f"Unbalanced braces in equations_json[{i}]: {eq[:50]}...")
        
        # Check for common LaTeX errors
        if "\\" in eq and not re.search(r"\\[a-zA-Z]+", eq):
            violations.append(f"Possible LaTeX error in equations_json[{i}]: backslash without command")
    
    # 4. Validate physics-engineered primitives
    for i, v in enumerate(visuals):
        if not isinstance(v, dict):
            continue
        
        ptype = v.get("type")
        
        # Projectile motion validation
        if ptype == "projectile_motion":
            required = ["v0", "angle", "g"]
            for field in required:
                if field not in v:
                    violations.append(f"projectile_motion in visual_data_json[{i}] missing required field '{field}'")
            
            # Check physical reasonableness
            if "v0" in v and isinstance(v["v0"], (int, float)):
                if v["v0"] < 0:
                    violations.append(f"projectile_motion in visual_data_json[{i}]: v0 must be non-negative")
                if v["v0"] > 1000:
                    violations.append(f"projectile_motion in visual_data_json[{i}]: v0={v['v0']} m/s seems unreasonably high")
            
            if "angle" in v and isinstance(v["angle"], (int, float)):
                if v["angle"] < 0 or v["angle"] > 90:
                    violations.append(f"projectile_motion in visual_data_json[{i}]: angle should be 0-90 degrees")
            
            if "g" in v and isinstance(v["g"], (int, float)):
                if v["g"] < 0:
                    violations.append(f"projectile_motion in visual_data_json[{i}]: g must be positive")
        
        # Geometry validation
        if ptype == "geometry":
            dim = v.get("dimension", 2)
            if dim not in [1, 2, 3]:
                violations.append(f"geometry in visual_data_json[{i}]: dimension must be 1, 2, or 3, got {dim}")
            
            kind = v.get("kind")
            if kind is None:
                violations.append(f"geometry in visual_data_json[{i}] missing 'kind' field")
            
            # 3D kinds require dimension=3
            if kind in ["sphere", "cube", "cylinder", "cone"] and dim != 3:
                violations.append(f"geometry in visual_data_json[{i}]: kind '{kind}' requires dimension=3")
        
        # Electric field validation
        if ptype == "electric_field":
            if "charges" not in v:
                violations.append(f"electric_field in visual_data_json[{i}] missing 'charges' field")
            elif isinstance(v["charges"], list):
                for j, charge in enumerate(v["charges"]):
                    if not isinstance(charge, dict):
                        violations.append(f"electric_field.charges[{j}] in visual_data_json[{i}] must be a dict")
                        continue
                    if "position" not in charge:
                        violations.append(f"electric_field.charges[{j}] in visual_data_json[{i}] missing 'position'")
                    if "charge" not in charge:
                        violations.append(f"electric_field.charges[{j}] in visual_data_json[{i}] missing 'charge'")
        
        # Linear algebra validation
        if ptype == "linear_algebra":
            op = v.get("operation")
            if op is None:
                violations.append(f"linear_algebra in visual_data_json[{i}] missing 'operation'")
            
            if op in ["vectors", "dot", "cross"]:
                if "a" not in v or "b" not in v:
                    violations.append(f"linear_algebra.{op} in visual_data_json[{i}] requires 'a' and 'b'")
            
            if op in ["matrix_vector", "transform", "solve"]:
                if "matrix" not in v:
                    violations.append(f"linear_algebra.{op} in visual_data_json[{i}] requires 'matrix'")
    
    # 5. Check for empty scenes
    if len(visuals) == 0:
        violations.append("visual_data_json is empty: scene will be blank")
    
    return len(violations) == 0, violations


def main():
    """Test the oracle with a sample row."""
    sample_row = {
        "visual_data_json": json.dumps([
            {
                "type": "projectile_motion",
                "v0": 20,
                "angle": 45,
                "g": 9.8
            }
        ]),
        "equations_json": json.dumps([
            "v = v_0 \\sin(\\theta) - gt"
        ])
    }
    
    ok, violations = validate_row(sample_row)
    print(f"Validation {'passed' if ok else 'failed'}")
    if violations:
        print("Violations:")
        for v in violations:
            print(f"  - {v}")


if __name__ == "__main__":
    main()
