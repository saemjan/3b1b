#!/usr/bin/env python3
"""
generate_csv.py — Full-capability batch for the SaemLabs video engine.

Produces content_batch.csv with:
    * 10 vertical 180-second lectures  (9:16, frame x∈[-4.5,4.5], y∈[-8,8])
    * 10 horizontal 60-second shorts   (16:9, frame x∈[-8,8], y∈[-4.5,4.5])

Orientation convention follows CSV_AUTHORING.md:
    vertical   → lecture   (180 s)
    horizontal → short     ( 60 s)

Engines and modules exercised:
    calculus_engine        — calculus_graph, derivative_tangent,
                             integral_area, riemann_sum
    linear_algebra_engine  — vectors, dot, cross, determinant,
                             matrix_vector, transform, solve
    geometry_engine        — segment, polyline, polygon, circle
    rotational_motion_eng  — solid_disk, hoop, rod_center, rod_end
    fluid_dynamics_engine  — venturi, hydrostatic
    electromagnetics_eng   — electric_field, magnetic_field,
                             electromagnetic_wave
    physics_simulation     — uniform_acceleration, linear_drag,
                             spring, central_gravity
    visual_kit             — annotate, spotlight, kinetic_title,
                             term_bind, camera_shake, ambient,
                             cinematic_transition
    sound_design           — tick, whoosh, drone, chime

Beats use the schema_validator vocabulary:
    promise, hook, analogy, experiment, law, midpoint,
    emphasis, annotate, shake, punchline

Run:
    python3 generate_csv.py                    # content_batch.csv
    python3 generate_csv.py --out batch.csv    # custom path
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


# ===========================================================================
# 1. Schema
# ===========================================================================

COLUMNS: tuple[str, ...] = (
    "video_id", "concept_type", "header_title", "tagline", "question_text",
    "option_a", "option_b", "option_c", "option_d", "correct_answer",
    "equations_json", "visual_data_json", "audio_script", "orientation",
    "beats_json", "target_duration_sec",
)

LECTURE = "vertical"
SHORT   = "horizontal"

# Semantic palette — do not add colours without a matching meaning.
PRIMARY = "#4CC9F0"   # subject of the story
ACCENT  = "#F1C40F"   # contrast or second body
OK      = "#2ECC71"   # closure
WARM    = "#E74C3C"   # warnings and pathological cases
NEUTRAL = "#8A8F9C"   # axes, floors, guides


# ===========================================================================
# 2. Beat vocabulary
# ===========================================================================

def beat(kind: str, focus: str, transition: str | None = None) -> dict[str, Any]:
    b: dict[str, Any] = {"type": kind, "focus": focus}
    if transition:
        b["transition"] = transition
    return b


def arc_lecture(focus: str, *,
                analogy: str | None = None,
                experiment: str | None = None,
                law: str | None = None,
                midpoint: str | None = None,
                emphasis: str | None = None) -> list[dict[str, Any]]:
    """Feynman arc: promise → hook → [analogy] → [experiment] → law →
       [midpoint] → [emphasis] → punchline."""
    beats: list[dict[str, Any]] = [
        beat("promise", focus),
        beat("hook", focus),
    ]
    if analogy:
        beats.append(beat("analogy", analogy))
    if experiment:
        beats.append(beat("experiment", experiment))
    beats.append(beat("law", law or focus, transition="wipe"))
    if midpoint:
        beats.append(beat("midpoint", midpoint))
    if emphasis:
        beats.append(beat("emphasis", emphasis))
    beats.append(beat("punchline", focus))
    return beats


def arc_short(focus: str, *, annotate: str | None = None,
              law: str | None = None, shake: str | None = None,
              punch: str | None = None) -> list[dict[str, Any]]:
    """Tight arc for a 60 s short."""
    return [
        beat("hook", focus),
        beat("annotate", annotate or focus),
        beat("law", law or focus, transition="wipe"),
        beat("shake", shake or focus),
        beat("punchline", punch or focus),
    ]


# ===========================================================================
# 3. Engine primitive builders
# ===========================================================================

# --- calculus_engine ------------------------------------------------------

def calculus_graph(id_, expr, xr, yr, xl=6.0, yl=3.0,
                   ctr=(0.0, 0.0, 0.0), color=PRIMARY):
    return {"type": "calculus_graph", "id": id_, "expression": expr,
            "x_range": list(xr), "y_range": list(yr),
            "x_length": xl, "y_length": yl, "center": list(ctr),
            "color": color}


def derivative_tangent(id_, expr, xr, yr, x0, delta,
                       xl=7.0, yl=3.0, ctr=(0.0, 0.0, 0.0)):
    return {"type": "derivative_tangent", "id": id_, "expression": expr,
            "x_range": list(xr), "y_range": list(yr),
            "x_length": xl, "y_length": yl, "center": list(ctr),
            "x0": x0, "delta": delta}


def integral_area(id_, expr, xr, yr, a, b, color=PRIMARY):
    return {"type": "integral_area", "id": id_, "expression": expr,
            "x_range": list(xr), "y_range": list(yr),
            "a": a, "b": b, "color": color}


def riemann_sum(id_, expr, xr, yr, a, b, n=8, sample="midpoint",
                color=ACCENT):
    return {"type": "riemann_sum", "id": id_, "expression": expr,
            "x_range": list(xr), "y_range": list(yr), "a": a, "b": b,
            "rectangles": n, "sample": sample, "area_color": color}


# --- linear_algebra_engine ------------------------------------------------

def la_vectors(id_, a, b, center=(0.0, 0.0, 0.0), scale=1.0):
    return {"type": "linear_algebra", "id": id_, "operation": "vectors",
            "a": list(a), "b": list(b), "center": list(center),
            "scale": scale}


def la_dot(id_, a, b, center=(0.0, 0.0, 0.0)):
    return {"type": "linear_algebra", "id": id_, "operation": "dot",
            "a": list(a), "b": list(b), "center": list(center)}


def la_cross(id_, a, b, center=(0.0, 0.0, 0.0)):
    return {"type": "linear_algebra", "id": id_, "operation": "cross",
            "a": list(a), "b": list(b), "center": list(center)}


def la_det(id_, matrix, center=(0.0, 0.0, 0.0), scale=1.0):
    return {"type": "linear_algebra", "id": id_, "operation": "determinant",
            "matrix": [list(r) for r in matrix], "center": list(center),
            "scale": scale}


def la_transform(id_, matrix, vector, center=(0.0, 0.0, 0.0), scale=1.0):
    return {"type": "linear_algebra", "id": id_, "operation": "transform",
            "matrix": [list(r) for r in matrix], "vector": list(vector),
            "center": list(center), "scale": scale}


def la_solve(id_, matrix, rhs, center=(0.0, 0.0, 0.0)):
    return {"type": "linear_algebra", "id": id_, "operation": "solve",
            "matrix": [list(r) for r in matrix], "rhs": list(rhs),
            "center": list(center)}


# --- geometry_engine ------------------------------------------------------

def geo_polyline(id_, points, color=PRIMARY, stroke=2.5):
    return {"type": "geometry", "id": id_, "dimension": 2,
            "kind": "polyline", "points": [list(p) for p in points],
            "color": color, "stroke_width": stroke}


def geo_polygon(id_, points, color=PRIMARY, opacity=0.18):
    return {"type": "geometry", "id": id_, "dimension": 2,
            "kind": "polygon", "points": [list(p) for p in points],
            "color": color, "fill_opacity": opacity}


def geo_circle(id_, position, radius, color=PRIMARY, opacity=0.10):
    return {"type": "geometry", "id": id_, "dimension": 2,
            "kind": "circle", "position": list(position),
            "radius": radius, "color": color, "fill_opacity": opacity}


def geo_segment(id_, points, color=PRIMARY, stroke=2.0):
    return {"type": "geometry", "id": id_, "dimension": 2,
            "kind": "segment", "points": [list(p) for p in points],
            "color": color, "stroke_width": stroke}


# --- rotational_motion_engine ---------------------------------------------

def rotor(id_, shape, mass, radius, omega, torque=0.0,
          center=(0.0, 0.0, 0.0), color=PRIMARY):
    return {"type": "rotational_motion", "id": id_, "shape": shape,
            "mass": mass, "radius": radius, "angular_velocity": omega,
            "torque": torque, "center": list(center), "color": color}


# --- fluid_dynamics_engine ------------------------------------------------

def venturi(id_, ih=1.6, th=0.8, iv=2.0, dens=1000.0, ip=200000.0,
            center=(0.0, 3.0, 0.0), color=PRIMARY):
    return {"type": "fluid_dynamics", "id": id_, "operation": "venturi",
            "inlet_height": ih, "throat_height": th,
            "inlet_velocity": iv, "density": dens,
            "inlet_pressure": ip, "center": list(center), "color": color}


def hydrostatic(id_, dens=1000.0, max_depth=3.0,
                center=(0.0, -2.0, 0.0)):
    return {"type": "fluid_dynamics", "id": id_, "operation": "hydrostatic",
            "density": dens, "max_depth": max_depth, "center": list(center)}


# --- electromagnetics_engine ----------------------------------------------

def e_field(id_, charges, xr=(-4.0, 4.0), yr=(-3.5, 3.5),
            cols=11, rows=9, color=PRIMARY):
    return {"type": "electric_field", "id": id_, "charges": charges,
            "x_range": list(xr), "y_range": list(yr),
            "columns": cols, "rows": rows, "color": color}


def m_field(id_, wires, xr=(-4.0, 4.0), yr=(-3.5, 3.5),
            cols=11, rows=9, color=ACCENT):
    return {"type": "magnetic_field", "id": id_, "wires": wires,
            "x_range": list(xr), "y_range": list(yr),
            "columns": cols, "rows": rows, "color": color}


def em_wave(id_, amp=0.9, freq=1.0, speed=2.0, length=5.0):
    return {"type": "electromagnetic_wave", "id": id_,
            "amplitude": amp, "frequency": freq, "speed": speed,
            "length": length}


# --- physics_simulation ---------------------------------------------------

def sim(id_, bodies, forces, duration=6.0, playback=None, loop=False,
        color=PRIMARY):
    d = {"type": "physics_simulation", "id": id_,
         "bodies": bodies, "forces": forces, "duration": duration,
         "color": color}
    if playback is not None:
        d["playback_duration"] = playback
    if loop:
        d["loop"] = True
    return d


def body(mass, position, velocity=(0.0, 0.0), label="m", color=PRIMARY):
    return {"mass": mass, "position": list(position),
            "velocity": list(velocity), "label": label, "color": color}


# --- direct primitives ----------------------------------------------------

def wave_(id_, amp, wl, freq, xr, color=PRIMARY):
    return {"type": "wave", "id": id_, "amplitude": amp,
            "wavelength": wl, "frequency": freq, "x_range": list(xr),
            "color": color}


def wave_pulse(id_, color=PRIMARY):
    return {"type": "wave_pulse", "id": id_, "color": color}


def momentum(id_, m1, m2, v1, v2, color=PRIMARY):
    return {"type": "momentum_exchange", "id": id_, "mass1": m1,
            "mass2": m2, "v1": v1, "v2": v2, "color": color}


def pendulum(id_, length, gravity=9.8, angle=18.0, color=PRIMARY):
    return {"type": "pendulum", "id": id_, "length": length,
            "gravity": gravity, "angle": angle, "color": color}


def projectile(id_, v0, angle, g=9.8, color=PRIMARY):
    return {"type": "projectile_motion", "id": id_, "v0": v0,
            "angle": angle, "g": g, "color": color}


def orbit(id_, radius, color=PRIMARY):
    return {"type": "orbit", "id": id_, "radius": radius, "color": color}


def gas(id_, count=80, box=(6.0, 2.5), color=PRIMARY):
    return {"type": "particle_gas", "id": id_, "count": count,
            "box_size": list(box), "color": color}


def heat_flow(id_, color=WARM):
    return {"type": "heat_flow", "id": id_, "color": color}


def pv_tracker(id_, color=PRIMARY):
    return {"type": "pv_diagram_tracker", "id": id_, "color": color}


def landscape(id_, expression, xr=(-3.0, 3.0), yr=(-1.0, 4.0),
              color=PRIMARY):
    return {"type": "energy_landscape", "id": id_, "expression": expression,
            "x_range": list(xr), "y_range": list(yr), "color": color}


# Alias kept for chapter compatibility.
potential_well = landscape


def induction_coil(id_, color=ACCENT):
    return {"type": "induction_coil", "id": id_, "color": color}


def compass_grid(id_, color=ACCENT):
    return {"type": "compass_grid", "id": id_, "color": color}


def interference(id_, color=PRIMARY, pos=(0.0, 0.0, 0.0),
                 num_bright=6, width=None, height=None):
    d = {"type": "interference_pattern", "id": id_,
         "num_bright": num_bright, "bright_color": color,
         "pos": list(pos)}
    if width is not None:
        d["width"] = width
    if height is not None:
        d["height"] = height
    return d


def two_beam(id_, color=PRIMARY):
    return {"type": "two_beam_splitter", "id": id_,
            "beam_color": color}


def bohr(id_, color=PRIMARY):
    return {"type": "bohr_orbit_photon", "id": id_, "color": color}


def crystal(id_, color=PRIMARY):
    return {"type": "crystal_lattice", "id": id_, "color": color}


def rolling(id_, color=PRIMARY):
    return {"type": "rolling_wheel_cycloid", "id": id_, "color": color}


def torsion(id_, color=PRIMARY):
    return {"type": "torsion_rod", "id": id_, "color": color}


def pipe_gauge(id_, color=PRIMARY):
    return {"type": "pipe_with_gauge", "id" : id_, "color": color}


def wave_packet(id_, color=PRIMARY):
    return {"type": "wave_packet_tunneling", "id": id_, "color": color}


def accretion(id_, pos=(0.0, 3.0, 0.0), color=PRIMARY):
    return {"type": "accretion_disk", "id": id_, "pos": list(pos),
            "color": color}


def random_walk(id_, color=PRIMARY):
    return {"type": "random_walk", "id": id_, "color": color}


def heat_(id_, color=WARM):
    return heat_flow(id_, color=color)


def live_label(id_, var_fn, fmt, pos=(0.0, 0.0, 0.0), font_size=22,
               color=PRIMARY):
    return {"type": "live_label", "id": id_, "var_fn": var_fn,
            "format": fmt, "pos": list(pos),
            "font_size": font_size, "color": color}


def numerical_chain(id_, steps, pos=(0.0, 0.0, 0.0), font_size=28,
                    color=PRIMARY):
    return {"type": "numerical_chain", "id": id_, "steps": list(steps),
            "pos": list(pos), "font_size": font_size, "color": color}


def equation_morph(id_, steps, pos=(0.0, 0.0, 0.0), font_size=28,
                   color=PRIMARY):
    return {"type": "equation_morph", "id": id_, "steps": list(steps),
            "pos": list(pos), "font_size": font_size, "color": color}


def warning_box(id_, txt, pos=(0.0, 0.0, 0.0)):
    return {"type": "warning_box", "id": id_, "text": txt,
            "pos": list(pos)}


def quiz_frame(id_, question, options, correct=0, pause=3.0):
    return {"type": "quiz_frame", "id": id_, "question": question,
            "options": list(options), "correct": correct,
            "pause": pause}


def stream_field(id_, charges, xr=(-4.0, 4.0), yr=(1.0, 5.0),
                 color=OK):
    return {"type": "stream_field", "id": id_, "charges": charges,
            "x_range": list(xr), "y_range": list(yr), "color": color}


def field_by_opacity(id_, sources, wavelength=0.6, omega=1.5, density=10,
                     width=6.0, height=4.0, color=PRIMARY):
    return {"type": "field_by_opacity", "id": id_, "sources": sources,
            "wavelength": wavelength, "omega": omega, "density": density,
            "width": width, "height": height, "color": color}


def energy_bar(id_, pos, fill, label="E", width=5.0, color=OK):
    return {"type": "energy_bar", "id": id_, "pos": list(pos),
            "width": width, "fill": fill, "label": label, "color": color}


def number_line(id_, rng, markers, length=6.0, color=PRIMARY):
    return {"type": "number_line", "id": id_, "range": list(rng),
            "markers": list(markers), "length": length, "color": color}


def damped_oscillator(id_, anchor, rest_length, amplitude, omega, gamma,
                      color=PRIMARY):
    return {"type": "damped_oscillator", "id": id_,
            "anchor": list(anchor), "rest_length": rest_length,
            "amplitude": amplitude, "omega": omega, "gamma": gamma,
            "color": color}


def two_source(id_, source_a, source_b, wavelength=0.6, speed=1.5,
               max_radius=5.0, num_rings=5):
    return {"type": "two_source_waves", "id": id_,
            "source_a": list(source_a), "source_b": list(source_b),
            "num_rings": num_rings, "wavelength": wavelength,
            "speed": speed, "max_radius": max_radius}


def beat_pattern(id_, f1, f2, amplitude=0.8, x_range=(0.0, 6.0)):
    return {"type": "beat_pattern", "id": id_, "f1": f1, "f2": f2,
            "amplitude": amplitude, "x_range": list(x_range)}


def harmonic_decomposition(id_, length=6.0, n_terms=5, color=OK):
    return {"type": "harmonic_decomposition", "id": id_,
            "length": length, "n_terms": n_terms, "color": color}


def spectral_sum(id_, components, x_max=6.0,
                 show_components=True, show_sum=True):
    return {"type": "spectral_sum", "id": id_,
            "components": list(components), "x_max": x_max,
            "show_components": show_components, "show_sum": show_sum}


def sliced_wave(id_, interface_origin=(0.0, 2.0, 0.0), index=1.5, c=2.0,
                frequency=0.3, amplitude=1.0, color=PRIMARY):
    return {"type": "sliced_wave", "id": id_,
            "interface_origin": list(interface_origin), "index": index,
            "c": c, "frequency": frequency, "amplitude": amplitude,
            "color": color}


def two_path_interference(id_, start, end_a, end_b, color=PRIMARY):
    return {"type": "two_path_interference", "id": id_,
            "start": list(start), "end_a": list(end_a),
            "end_b": list(end_b), "color": color}


def grid_warp(id_, mass=1.5, mass_pos=(0.0, 3.0, 0.0), divisions=16,
              color=PRIMARY):
    return {"type": "grid_warp", "id": id_, "mass": mass,
            "mass_pos": list(mass_pos), "divisions": divisions,
            "color": color}


def taylor_expand(id_, expr, xr, max_terms=5, term_time=0.7, color=ACCENT):
    return {"type": "taylor_expand", "id": id_, "expr": expr,
            "x_range": list(xr), "max_terms": max_terms,
            "term_time": term_time, "color": color}


def exponential_atmosphere(id_, num_particles=30, height=3.0,
                           scale_height=1.0):
    return {"type": "exponential_atmosphere", "id": id_,
            "num_particles": num_particles, "height": height,
            "scale_height": scale_height}


def phase_portrait(id_, amplitude=2.0, gamma=0.3, omega=3.0):
    return {"type": "phase_portrait", "id": id_,
            "amplitude": amplitude, "gamma": gamma, "omega": omega}


def color_triangle(id_, points=None, labels=("red", "green", "blue"),
                   colors=("#FF4B4B", "#2ECC71", "#3498DB")):
    return {"type": "color_triangle", "id": id_,
            "triangle_points": [list(p) for p in (
                points or [(-3.0, -2.0, 0.0),
                           (3.0, -2.0, 0.0),
                           (0.0, 2.0, 0.0)])],
            "labels": list(labels), "colors": list(colors)}


def polar_pattern(id_, pattern="dipole", radius_max=2.0, sweep=False,
                  color=ACCENT):
    return {"type": "polar_pattern", "id": id_, "pattern": pattern,
            "radius_max": radius_max, "sweep": sweep, "color": color}


def text_(id_, txt, pos=(0.0, 3.8, 0.0), color=PRIMARY):
    return {"type": "text", "id": id_, "text": txt, "pos": list(pos),
            "color": color}


def dot_(id_, pos, color=ACCENT, label=None):
    d = {"type": "dot", "id": id_, "pos": list(pos), "color": color}
    if label:
        d["label"] = label
    return d


# ===========================================================================
# 4. Row assembly
# ===========================================================================

def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(**kw: Any) -> None:
        row: dict[str, Any] = {c: "" for c in COLUMNS}
        for key in ("equations_json", "visual_data_json", "beats_json"):
            if key in kw and isinstance(kw[key], (list, dict)):
                kw[key] = json.dumps(kw[key], ensure_ascii=False)
        row.update(kw)
        missing = [c for c in COLUMNS if c not in row]
        if missing:
            raise ValueError(f"row {kw.get('video_id')!r} missing {missing}")
        rows.append(row)

    # =====================================================================
    # VERTICAL LECTURES (180 s) — 10 rows
    # =====================================================================

    # -------------------------------------------------- L1. Kinematics 1D
    add(
        video_id="lecture_kinematics_1d",
        concept_type="GENERIC",
        header_title="The Speedometer's Secret",
        tagline="Instantaneous speed is a limit, not a reading",
        question_text="What does the dial actually measure?",
        equations_json=[
            r"v=\lim_{\Delta t\to 0}\frac{\Delta x}{\Delta t}",
            r"x(t)=x_0+v_0 t+\tfrac{1}{2}at^2",
        ],
        visual_data_json=[
            derivative_tangent("curve", "x**2/2",
                               (-3.0, 3.0), (-1.0, 5.0),
                               x0=2.0, delta=0.6,
                               xl=7.0, yl=3.0,
                               ctr=(0.0, 3.5, 0.0)),
            sim("fall",
                bodies=[body(1.0, (0.0, 3.0), (0.0, 0.0), label="ball",
                             color=PRIMARY)],
                forces=[{"type": "uniform_acceleration",
                         "acceleration": [0.0, -9.8]}],
                duration=1.0, playback=4.0),
            live_label("readout",
                       var_fn="0.5*9.8*t*t",
                       fmt="x = {v:.2f} m",
                       pos=(0.0, -2.0, 0.0),
                       font_size=22),
            numerical_chain("chain",
                            steps=[r"F = m a", r"a = g",
                                   r"v = g t",
                                   r"x = \frac{1}{2} g t^2"],
                            pos=(0.0, -5.0, 0.0)),
            geo_segment("axis", [(-3.5, 3.0), (3.5, 3.0)],
                        color=NEUTRAL, stroke=1.5),
        ],
        audio_script=(
            "I am going to show you what a speedometer actually measures. "
            "Not a single reading, but a limit of many readings. Watch a "
            "ball fall. At the top the speed is zero. A fraction of a "
            "second later it is faster. Faster still. The graph on screen "
            "shows the same motion, drawn as a curve of position versus "
            "time. On that curve, the average speed over any interval is "
            "the slope of a secant line. Shrink the interval and the secant "
            "pivots. Shrink it again. In the limit, it becomes the tangent. "
            "The tangent slope is the instantaneous speed. Every dial is a "
            "derivative in disguise. The chain on the right is not the "
            "derivation of motion. It is the derivation of the derivative "
            "itself. Force equals mass times acceleration. Rearranged, "
            "acceleration is g. Integrate once and you get velocity. "
            "Integrate again and you get position. The live readout shows "
            "what the mathematical answer looks like as the ball falls. "
            "Everything in kinematics is built on this single limiting "
            "idea."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture(
            "curve",
            analogy="fall",
            experiment="readout",
            law="chain",
            midpoint="readout",
        ),
        target_duration_sec=180,
    )

    # -------------------------------------------------- L2. Rigid rotation
    add(
        video_id="lecture_rigid_rotation",
        concept_type="GENERIC",
        header_title="Why the Disk Always Wins",
        tagline="Mass distribution sets the race",
        question_text="A hoop and a disk roll down the same ramp. Which wins?",
        equations_json=[
            r"K=\tfrac{1}{2}mv^2+\tfrac{1}{2}I\omega^2",
            r"I_{disk}=\tfrac{1}{2}MR^2",
            r"I_{hoop}=MR^2",
        ],
        visual_data_json=[
            rotor("disk", "solid_disk", 2.0, 1.2, 2.0, 0.0,
                  center=(-2.0, 4.0, 0.0), color=PRIMARY),
            rotor("hoop", "hoop", 2.0, 1.2, 2.0, 0.0,
                  center=(2.0, 4.0, 0.0), color=ACCENT),
            calculus_graph("energy_curve", "0.5*x**2",
                           (-3.0, 3.0), (0.0, 5.0),
                           xl=6.0, yl=2.5, ctr=(0.0, -2.0, 0.0)),
            energy_bar("ke_bar", pos=(0.0, -5.5, 0.0),
                       fill=0.7, label="K_total", width=5.0),
            equation_morph("eq",
                           steps=[r"I_{disk} = \frac{1}{2} M R^2",
                                  r"I_{hoop} = M R^2",
                                  r"I_{hoop} > I_{disk}"],
                           pos=(0.0, -7.0, 0.0),
                           font_size=26),
        ],
        audio_script=(
            "I am going to show you why the disk always wins. Same mass, "
            "same radius, same ramp. Release. The disk reaches the bottom "
            "first. Every time. Both lose the same potential energy. Both "
            "end with the same total kinetic energy. But kinetic energy "
            "has two flavours. Translational and rotational. For rolling "
            "without slipping, the rotational share depends on the moment "
            "of inertia. The hoop keeps its mass at the rim, far from the "
            "axis. Its inertia is the full m r squared. The disk spreads "
            "its mass out. Its inertia is only one half m r squared. A "
            "bigger fraction of the hoop's energy goes into spinning. Less "
            "is left for moving forward. The equation on screen morphs "
            "from the disk's formula to the hoop's formula to the "
            "inequality that follows. That single symbol change is the "
            "whole physics. Where the mass lives decides the race."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture(
            "disk",
            analogy="energy_curve",
            law="eq",
            midpoint="ke_bar",
        ),
        target_duration_sec=180,
    )

    # -------------------------------------------------- L3. Waves
    add(
        video_id="lecture_waves",
        concept_type="GENERIC",
        header_title="A Wave Is Not the Medium",
        tagline="The pattern travels while the particles stay put",
        question_text="Does the string travel with the wave?",
        equations_json=[
            r"v=\lambda f",
            r"y(x,t)=A\cos(kx-\omega t)",
        ],
        visual_data_json=[
            wave_("wave", 1.0, 3.0, 1.0, (-4.0, 4.0), color=PRIMARY),
            wave_pulse("pulse", color=ACCENT),
            harmonic_decomposition("harmonics", length=6.0, n_terms=5),
            spectral_sum("spectrum",
                         components=[
                             {"amplitude": 1.0, "frequency": 1.0,
                              "phase": 0.0, "color": PRIMARY},
                             {"amplitude": 0.5, "frequency": 3.0,
                              "phase": 0.0, "color": ACCENT},
                             {"amplitude": 0.2, "frequency": 5.0,
                              "phase": 0.0, "color": OK},
                         ],
                         x_max=6.0),
            calculus_graph("envelope", "cos(x)*exp(-x**2/20)",
                           (-4.0, 4.0), (-1.5, 1.5),
                           xl=6.0, yl=2.0, ctr=(0.0, -4.5, 0.0)),
        ],
        audio_script=(
            "I am going to show you one of the most confusing ideas in "
            "wave physics. Pluck a string. A pattern travels from one end "
            "to the other. Now watch a single point on that string. It "
            "moves up and down. It does not travel. The wave is the "
            "pattern. The medium stays in place. The bottom graph shows "
            "this as an envelope over many small oscillations. Each crest "
            "and trough travels left or right, but the particles only bob. "
            "On the right, a Fourier sum builds a square wave from odd "
            "harmonics. That is not decoration. Every wave, no matter how "
            "complicated, is a sum of simple sines. The wave is the "
            "message. The medium is the messenger."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture(
            "wave",
            analogy="envelope",
            experiment="harmonics",
            law="spectrum",
        ),
        target_duration_sec=180,
    )

    # -------------------------------------------------- L4. Fluids
    add(
        video_id="lecture_fluids",
        concept_type="GENERIC",
        header_title="Blow Across a Sheet of Paper",
        tagline="Fast air pushes less. You would have guessed more.",
        question_text="Why does the paper rise?",
        equations_json=[
            r"p+\tfrac{1}{2}\rho v^2+\rho g h=\text{constant}",
            r"A_1 v_1 = A_2 v_2",
        ],
        visual_data_json=[
            venturi("venturi", center=(0.0, 3.0, 0.0)),
            hydrostatic("tank", center=(0.0, -2.0, 0.0)),
            pipe_gauge("gauge", color=ACCENT),
            stream_field("streams",
                         charges=[{"pos": [-1.5, 3.0, 0.0], "charge": 1.0},
                                  {"pos": [1.5, 3.0, 0.0], "charge": -1.0}],
                         xr=(-4.0, 4.0), yr=(1.0, 5.0)),
            geo_polyline("pipe_outline",
                         [(-4.0, 3.8), (-2.0, 3.8), (-1.0, 3.0),
                          (1.0, 3.0), (2.0, 3.8), (4.0, 3.8)],
                         color=NEUTRAL, stroke=1.5),
        ],
        audio_script=(
            "I am going to show you something that contradicts intuition. "
            "Hold a sheet of paper by its edge. Blow across the top. It "
            "rises. You expected it to sink. The reason is energy. A fast "
            "fluid element has more kinetic energy than a slow one. If "
            "nothing pushes energy in, pressure must drop. Pressure plus "
            "half rho v squared plus rho g h is constant along a "
            "streamline. Where the speed goes up, pressure goes down. "
            "Watch the venturi. The pipe narrows. Continuity forces the "
            "fluid to speed up. The gauge on the right shows the pressure "
            "rising in the throat. Below, the hydrostatic tank shows how "
            "pressure grows with depth. Every atomizer, carburetor, "
            "curveball and wing uses this same fact."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture(
            "venturi",
            analogy="pipe_outline",
            experiment="streams",
            law="gauge",
            midpoint="tank",
        ),
        target_duration_sec=180,
    )

    # -------------------------------------------------- L5. Electric field
    add(
        video_id="lecture_electric_field",
        concept_type="GENERIC",
        header_title="The Field Is the Messenger",
        tagline="Action at a distance becomes local action",
        question_text="How does one charge know another is nearby?",
        equations_json=[
            r"E=F/q",
            r"E=kQ/r^2",
        ],
        visual_data_json=[
            e_field("dipole",
                    charges=[{"position": [-1.5, 3.0, 0.0], "charge": 2.0},
                             {"position": [1.5, 3.0, 0.0], "charge": -2.0}],
                    xr=(-4.0, 4.0), yr=(0.5, 5.5),
                    cols=11, rows=9),
            la_vectors("vec", (2.0, 1.0), (-1.0, 2.0),
                       center=(0.0, -2.0, 0.0), scale=1.2),
            la_dot("dot", (2.0, 1.0), (-1.0, 2.0),
                   center=(0.0, -4.5, 0.0)),
            warning_box("warn",
                        "Field lines start on + and end on −. "
                        "They never cross.",
                        pos=(0.0, -6.5, 0.0)),
            field_by_opacity("lines",
                             sources=[[-1.5, 3.0, 0.0], [1.5, 3.0, 0.0]],
                             wavelength=0.6, omega=1.5, density=10,
                             width=6.0, height=4.0),
        ],
        audio_script=(
            "I am going to show you how one charge knows another is "
            "nearby. It cannot see. Yet bring two opposite charges "
            "together and they attract. Faraday gave us a way to think "
            "about this without action at a distance. Each charge creates "
            "something in the space around it. That something is the "
            "electric field. The colored lines on screen show the field "
            "of a dipole. The opacity map below shows the same thing "
            "numerically. Where the field is strong, the glow is bright. "
            "Where it is weak, the glow fades. In the middle, two vectors "
            "and their dot product show how two field contributions add. "
            "The warning box reminds you of the two rules every field "
            "diagram obeys."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture(
            "dipole",
            analogy="lines",
            law="dot",
            emphasis="warn",
        ),
        target_duration_sec=180,
    )

    # -------------------------------------------------- L6. Magnetic
    add(
        video_id="lecture_magnetic_field",
        concept_type="GENERIC",
        header_title="Magnetism Is Electricity in Disguise",
        tagline="Special relativity explains the magnetic force",
        question_text="Why do parallel currents attract?",
        equations_json=[
            r"F_m=\mu_0\epsilon_0 v^2 F_e",
            r"B=\mu_0 I/2\pi r",
        ],
        visual_data_json=[
            m_field("wires",
                    wires=[{"start": [-3.5, 2.0, 0.0],
                            "end": [3.5, 2.0, 0.0], "current": 5.0},
                           {"start": [-3.5, -2.0, 0.0],
                            "end": [3.5, -2.0, 0.0], "current": 5.0}],
                    xr=(-4.0, 4.0), yr=(-3.5, 3.5),
                    cols=11, rows=9),
            compass_grid("compass", color=ACCENT),
            induction_coil("coil", color=OK),
            la_cross("cross", (2.0, 1.0), (-1.0, 2.0),
                     center=(0.0, -6.0, 0.0)),
            em_wave("emw", amp=0.8, freq=1.0, speed=2.0, length=4.0),
        ],
        audio_script=(
            "I am going to show you that magnetism is not a separate "
            "force. Two wires carry current in the same direction. They "
            "attract. Both contain moving electrons. Like charges should "
            "repel. So why do the wires pull together? Take the rest "
            "frame of the electrons in one wire. The other wire is not "
            "neutral in that frame. Length contraction packs the positive "
            "ions closer. Net charge imbalance. Electric field. "
            "Attraction. What we call magnetism in the lab frame, an "
            "observer riding on the electrons calls electricity. The "
            "compass needles on screen show the same field the wires "
            "produce. The coil below shows the same physics packaged for "
            "practical use. Every magnet on your refrigerator is a "
            "relativistic artifact."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture(
            "wires",
            analogy="compass",
            experiment="coil",
            law="emw",
            emphasis="cross",
        ),
        target_duration_sec=180,
    )

    # -------------------------------------------------- L7. Thermo
    add(
        video_id="lecture_thermo",
        concept_type="GENERIC",
        header_title="Why You Cannot Unstir Coffee",
        tagline="Entropy counts arrangements",
        question_text="Why does heat flow one way?",
        equations_json=[
            r"S=k_B\ln W",
            r"\Delta S\geq 0",
        ],
        visual_data_json=[
            pv_tracker("cycle"),
            gas("gas", count=80, box=(6.0, 2.5), color=ACCENT),
            random_walk("walk", color=OK),
            integral_area("area", "0.5*x**2+1",
                          (0.0, 2.0), (0.0, 3.0), 0.0, 2.0),
            riemann_sum("strips", "0.5*x**2+1",
                        (0.0, 2.0), (0.0, 3.0), 0.0, 2.0,
                        n=8, sample="midpoint"),
        ],
        audio_script=(
            "I am going to show you why you cannot un-stir coffee. Put a "
            "drop of ink in water. It spreads. It stays spread. Now try to "
            "gather it back into one corner. You cannot. Every collision "
            "between ink and water is reversible. But the number of ways "
            "to arrange the molecules in one corner is astronomically "
            "smaller than the number of ways to spread them out. The gas "
            "on screen is doing that calculation in real time. The random "
            "walk below is the same idea made visible. The integral and "
            "the rectangles to its right show the same bookkeeping in "
            "continuous form. Entropy counts arrangements. The second law "
            "is not a law of mechanics. It is a statistical "
            "near-certainty."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture(
            "gas",
            analogy="area",
            experiment="strips",
            law="cycle",
            midpoint="walk",
        ),
        target_duration_sec=180,
    )

    # -------------------------------------------------- L8. Optics
    add(
        video_id="lecture_optics",
        concept_type="GENERIC",
        header_title="The Bent Straw",
        tagline="Light slows down in glass and bends",
        question_text="Why does a straw look broken?",
        equations_json=[r"n_1\sin\theta_1=n_2\sin\theta_2"],
        visual_data_json=[
            sliced_wave("refract", interface_origin=(0.0, 2.0, 0.0),
                        index=1.5, c=2.0, frequency=0.3, amplitude=1.0),
            two_beam("mich", color=ACCENT),
            interference("fringes", num_bright=5),
            two_path_interference("paths",
                                  start=(-2.0, 0.0, 0.0),
                                  end_a=(2.0, 0.5, 0.0),
                                  end_b=(2.0, -0.5, 0.0)),
            geo_polygon("prism",
                        [(-2.0, -3.0), (2.0, -3.0), (0.0, 1.0)],
                        color=NEUTRAL, opacity=0.15),
        ],
        audio_script=(
            "I am going to show you why a straw looks broken in a glass of "
            "water. Light slows down when it enters water. The speed of "
            "light in a medium is c over n. When light crosses a boundary "
            "at an angle, the change in speed bends the ray. Snell's law. "
            "Into a denser medium, the ray bends toward the normal. Out of "
            "one, away. The refraction on screen shows this in one "
            "continuous wave. The prism below bends each wavelength "
            "differently, which is why white light becomes a rainbow. The "
            "Michelson interferometer and the two-path diagram show the "
            "same idea in a different guise. Every lens, every camera, "
            "every telescope is an application of the same physics."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture(
            "refract",
            analogy="prism",
            experiment="mich",
            law="fringes",
            midpoint="paths",
        ),
        target_duration_sec=180,
    )

    # -------------------------------------------------- L9. Quantum
    add(
        video_id="lecture_quantum",
        concept_type="GENERIC",
        header_title="The Bohr Ladder",
        tagline="Energy levels are quantized",
        question_text="Why do atoms emit only certain colours?",
        equations_json=[r"E_n=-13.6/n^2\text{ eV}"],
        visual_data_json=[
            bohr("atom"),
            wave_packet("tunnel"),
            potential_well("well", "0.5*x**2",
                           (-3.0, 3.0), (0.0, 5.0)),
            calculus_graph("psi", "sin(2*x)*exp(-x**2/20)",
                           (-3.0, 3.0), (-1.5, 1.5),
                           xl=6.0, yl=2.0, ctr=(0.0, -6.0, 0.0)),
            quiz_frame("quiz",
                       question="Which quantum number sets the energy?",
                       options=["n", "l", "m", "s"],
                       correct=0, pause=3.0),
        ],
        audio_script=(
            "I am going to show you why atoms emit only certain colours. "
            "Heat a gas. It glows. Not with a rainbow. With sharp lines. "
            "Bohr's answer was that the electron can only orbit at certain "
            "radii. Each orbit has a specific energy. Transitions emit a "
            "photon with energy equal to the difference. The atom on "
            "screen jumps inward. A photon flies out. The wave packet "
            "below shows a different quantum effect. A particle tunnelling "
            "through a barrier it does not have the energy to cross. "
            "Classically impossible. Quantum mechanically routine. The "
            "potential well and the wavefunction on the left show the same "
            "physics in a one-dimensional approximation. This is the "
            "ladder every chemistry student climbs."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture(
            "atom",
            analogy="well",
            experiment="tunnel",
            law="atom",
            midpoint="quiz",
            emphasis="psi",
        ),
        target_duration_sec=180,
    )

    # -------------------------------------------------- L10. Relativity
    add(
        video_id="lecture_relativity",
        concept_type="GENERIC",
        header_title="The Proton That Shortcuts Spacetime",
        tagline="Time dilates at high speed",
        question_text="Why do fast clocks run slow?",
        equations_json=[r"\Delta t'=\Delta t\sqrt{1-v^2/c^2}"],
        visual_data_json=[
            grid_warp("warp", mass=1.5, mass_pos=(0.0, 3.0, 0.0),
                      divisions=16),
            accretion("disk", pos=(0.0, 3.0, 0.0)),
            taylor_expand("series", "1/sqrt(1-x**2)",
                          (-0.8, 0.8), max_terms=5, term_time=0.7),
            exponential_atmosphere("atmo",
                                   num_particles=30,
                                   height=3.0,
                                   scale_height=1.0),
            geo_circle("ring", (0.0, -4.0, 0.0), 1.5, color=OK,
                       opacity=0.10),
        ],
        audio_script=(
            "I am going to show you how a proton crosses the galaxy in "
            "under five hundred years. At zero point nine nine nine nine "
            "nine c. The Milky Way is a hundred thousand light years "
            "across in its rest frame. On the proton's clock, only four "
            "hundred fifty years. The Lorentz factor is three hundred "
            "sixteen. From the proton's view, the galaxy contracts to "
            "three hundred twenty light years. It never breaks the speed "
            "of light. It takes a shortcut through spacetime. The curved "
            "grid on screen shows a related idea from general relativity. "
            "Mass warps space itself. The Taylor series to the right shows "
            "how special relativity reduces to Newtonian mechanics at low "
            "speeds. The same math, but only the first term survives."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture(
            "warp",
            analogy="series",
            law="ring",
            midpoint="atmo",
        ),
        target_duration_sec=180,
    )

    # =====================================================================
    # HORIZONTAL SHORTS (60 s) — 10 rows
    # =====================================================================

    # -------------------------------------------------- S1. Pendulum
    add(
        video_id="short_pendulum",
        concept_type="GENERIC",
        header_title="Pendulum Period",
        tagline="No mass, no amplitude",
        question_text="A one metre pendulum swings. What is its period?",
        option_a="0.5 s", option_b="1.0 s",
        option_c="2.0 s", option_d="4.0 s",
        correct_answer="Correct Answer: (C)",
        equations_json=[r"T=2\pi\sqrt{L/g}"],
        visual_data_json=[
            pendulum("swing", length=1.0, gravity=9.8, angle=15.0),
            number_line("timeline", (0.0, 4.0), (2.0,), length=6.0),
            live_label("readout",
                       var_fn="2*pi*sqrt(1/9.8)",
                       fmt="T = {v:.2f} s",
                       pos=(0.0, -3.5, 0.0),
                       font_size=22),
        ],
        audio_script=(
            "A pendulum one metre long. Period equals two pi times the "
            "square root of L over g. Plug in L equals one, g equals nine "
            "point eight. Two seconds. No mass. No amplitude. That is why "
            "pendulums were clocks for three centuries. Answer C."
        ),
        orientation=SHORT,
        beats_json=arc_short("swing", annotate="timeline",
                             law="readout", shake="swing"),
        target_duration_sec=60,
    )

    # -------------------------------------------------- S2. Projectile
    add(
        video_id="short_projectile",
        concept_type="GENERIC",
        header_title="Projectile Range",
        tagline="30 and 60 give the same range",
        question_text="A ball launches at 20 m/s at 30 degrees. Range?",
        option_a="17 m", option_b="35 m",
        option_c="40 m", option_d="70 m",
        correct_answer="Correct Answer: (B)",
        equations_json=[r"R=\frac{v_0^2\sin 2\theta}{g}"],
        visual_data_json=[
            projectile("path", v0=20.0, angle=30.0),
            la_vectors("launch", (17.3, 10.0), (0.0, -9.8),
                       center=(0.0, -2.5, 0.0), scale=0.15),
            calculus_graph("height",
                           "20*sin(pi/6)*x/20/cos(pi/6)"
                           "-9.8*(x/20/cos(pi/6))**2/2",
                           (0.0, 35.0), (0.0, 6.0),
                           xl=7.0, yl=2.0, ctr=(0.0, -1.0, 0.0)),
        ],
        audio_script=(
            "A ball launches at twenty metres per second, thirty degrees. "
            "Range equals v zero squared sine two theta over g. Sine sixty "
            "is about zero point eight six six. Twenty squared is four "
            "hundred. Divide by nine point eight. About thirty five "
            "metres. Answer B."
        ),
        orientation=SHORT,
        beats_json=arc_short("path", annotate="launch",
                             law="height", shake="path"),
        target_duration_sec=60,
    )

    # -------------------------------------------------- S3. Collision
    add(
        video_id="short_collision",
        concept_type="GENERIC",
        header_title="Ballistic Pendulum",
        tagline="Conservation of momentum in one line",
        question_text=("A 20 g bullet at 300 m/s embeds in a 500 g block. "
                       "Block speed?"),
        option_a="7.5 m/s", option_b="11.5 m/s",
        option_c="15 m/s", option_d="20 m/s",
        correct_answer="Correct Answer: (B)",
        equations_json=[r"m_1 v_1=(m_1+m_2)v'"],
        visual_data_json=[
            momentum("collision", 0.02, 0.5, 300.0, 0.0),
            phase_portrait("phase", amplitude=2.0, gamma=0.3, omega=3.0),
            la_dot("dot", (0.02, 0.5), (300.0, 0.0),
                   center=(0.0, -3.0, 0.0)),
        ],
        audio_script=(
            "A twenty gram bullet at three hundred metres per second hits "
            "a stationary five hundred gram block. Embeds. Momentum is "
            "conserved. Before, six kilogram metres per second. After, "
            "combined mass zero point five two kilograms. Six over zero "
            "point five two. Eleven point five. Answer B."
        ),
        orientation=SHORT,
        beats_json=arc_short("collision", annotate="dot",
                             law="collision", shake="collision",
                             punch="phase"),
        target_duration_sec=60,
    )

    # -------------------------------------------------- S4. Orbit
    add(
        video_id="short_orbit",
        concept_type="GENERIC",
        header_title="Kepler's Third Law",
        tagline="Double the radius wait longer",
        question_text=("If the orbital radius doubles by what factor does "
                       "the period change?"),
        option_a=r"\sqrt{2}", option_b="2",
        option_c=r"2\sqrt{2}", option_d="4",
        correct_answer="Correct Answer: (C)",
        equations_json=[r"T^2\propto r^3"],
        visual_data_json=[
            sim("orbit",
                bodies=[body(1.0, (-2.0, 0.0), (0.0, 1.8),
                             label="Moon", color=PRIMARY),
                        body(1.0, (0.0, 0.0), (0.0, 0.0),
                             label="Earth", color=ACCENT)],
                forces=[{"type": "central_gravity",
                         "source": 1, "mu": 14.0}],
                duration=12.0, playback=5.0),
            orbit("guide", radius=2.0, color=NEUTRAL),
            calculus_graph("curve", "x**1.5",
                           (0.5, 3.0), (0.0, 5.0),
                           xl=5.0, yl=2.0, ctr=(0.0, -3.0, 0.0)),
            numerical_chain("chain",
                            steps=[r"T^2 \propto r^3",
                                   r"T \propto r^{3/2}",
                                   r"r \to 2r \Rightarrow T \to 2^{3/2}"],
                            pos=(4.0, 2.0, 0.0)),
        ],
        audio_script=(
            "Double the radius. Kepler says the period scales as r to the "
            "three halves. Two to the three halves is two root two. "
            "Answer C."
        ),
        orientation=SHORT,
        beats_json=arc_short("orbit", annotate="curve",
                             law="chain", shake="orbit",
                             punch="guide"),
        target_duration_sec=60,
    )

    # -------------------------------------------------- S5. SHM
    add(
        video_id="short_shm",
        concept_type="GENERIC",
        header_title="Spring With Damping",
        tagline="Energy leaks out of the oscillator",
        question_text=("A spring with damping is released from amplitude A. "
                       "How does the amplitude decay?"),
        option_a="linearly", option_b="exponentially",
        option_c="quadratically", option_d="it does not",
        correct_answer="Correct Answer: (B)",
        equations_json=[r"x(t)=A e^{-\gamma t/2}\cos(\omega t)"],
        visual_data_json=[
            sim("spring",
                bodies=[body(1.0, (0.0, 1.5), (0.0, 0.0), label="m")],
                forces=[{"type": "spring", "body": 0,
                         "anchor": [0.0, 0.0],
                         "stiffness": 4.0, "rest_length": 1.0,
                         "damping": 0.4}],
                duration=8.0, playback=4.0),
            damped_oscillator("damped",
                              anchor=(4.0, 1.5, 0.0),
                              rest_length=1.0, amplitude=0.6,
                              omega=3.0, gamma=0.4),
            energy_bar("energy", pos=(-3.5, -3.0, 0.0),
                       fill=0.6, label="E", width=2.5),
            la_solve("solve",
                     matrix=[[4.0, -1.0], [-1.0, 3.0]],
                     rhs=[1.0, 2.0],
                     center=(0.0, -3.0, 0.0)),
        ],
        audio_script=(
            "A damped spring. The energy does not decay linearly. It "
            "decays exponentially. Every cycle loses a fixed fraction. "
            "Answer B."
        ),
        orientation=SHORT,
        beats_json=arc_short("spring", annotate="energy",
                             law="solve", shake="damped",
                             punch="damped"),
        target_duration_sec=60,
    )

    # -------------------------------------------------- S6. Interference
    add(
        video_id="short_interference",
        concept_type="GENERIC",
        header_title="Two-Slit Fringes",
        tagline="Two sources one pattern",
        question_text=("Two identical slits are illuminated. What kind of "
                       "pattern appears on the screen?"),
        option_a="single bright band",
        option_b="alternating bright and dark bands",
        option_c="two separate bands",
        option_d="no pattern",
        correct_answer="Correct Answer: (B)",
        equations_json=[r"d\sin\theta=m\lambda"],
        visual_data_json=[
            wave_("wave", 1.0, 2.0, 1.0, (-4.0, 4.0)),
            two_source("sources",
                       source_a=(-2.0, 1.0, 0.0),
                       source_b=(-2.0, -1.0, 0.0),
                       wavelength=0.6, speed=1.5, max_radius=5.0),
            beat_pattern("beats", f1=5.0, f2=4.0, amplitude=0.8),
            interference("fringes", num_bright=6, color=ACCENT,
                         pos=(3.0, 0.0, 0.0),
                         width=2.0, height=6.0),
        ],
        audio_script=(
            "Two slits. Two sources. The waves overlap. Where crests meet "
            "crests, bright. Where crests meet troughs, dark. Alternating "
            "bright and dark bands. Answer B."
        ),
        orientation=SHORT,
        beats_json=arc_short("sources", annotate="wave",
                             law="fringes", shake="beats",
                             punch="fringes"),
        target_duration_sec=60,
    )

    # -------------------------------------------------- S7. Doppler
    add(
        video_id="short_doppler",
        concept_type="GENERIC",
        header_title="Doppler Shift",
        tagline="Moving sources compress their own waves",
        question_text=("A train whistle at 440 Hz approaches you. Is the "
                       "observed frequency higher or lower?"),
        option_a="higher", option_b="lower",
        option_c="same", option_d="depends on speed",
        correct_answer="Correct Answer: (A)",
        equations_json=[r"f'=f_0\frac{v}{v-v_s}"],
        visual_data_json=[
            wave_("wave", 0.9, 2.0, 440.0, (-4.0, 4.0)),
            beat_pattern("beats", f1=6.0, f2=5.5, amplitude=0.6),
            number_line("line", (400.0, 500.0), (440.0,), length=5.0),
            color_triangle("ct"),
        ],
        audio_script=(
            "A train whistle at four hundred forty hertz approaches you. "
            "Higher or lower? The train moves toward you. Each crest "
            "launches from a closer position. Crests compress. Shorter "
            "wavelength. Higher frequency. Answer A."
        ),
        orientation=SHORT,
        beats_json=arc_short("wave", annotate="line",
                             law="beats", shake="ct",
                             punch="wave"),
        target_duration_sec=60,
    )

    # -------------------------------------------------- S8. Photoelectric
    add(
        video_id="short_photoelectric",
        concept_type="GENERIC",
        header_title="Threshold Wavelength",
        tagline="Below it nothing ejects",
        question_text=("Potassium has a work function of 2.0 eV. Below "
                       "what wavelength does ejection stop?"),
        option_a="624 nm", option_b="400 nm",
        option_c="250 nm", option_d="900 nm",
        correct_answer="Correct Answer: (A)",
        equations_json=[r"\lambda=hc/\phi"],
        visual_data_json=[
            wave_pulse("packet"),
            numerical_chain("chain",
                            steps=[r"E=hf", r"\phi=hf_0",
                                   r"\lambda_0=hc/\phi"],
                            pos=(0.0, -2.0, 0.0)),
            warning_box("warn",
                        "Brightness does not matter. Only frequency does.",
                        pos=(0.0, 2.0, 0.0)),
            polar_pattern("lobe", pattern="dipole",
                          radius_max=2.0, sweep=False),
        ],
        audio_script=(
            "Potassium. Work function two electron volts. Threshold "
            "wavelength? h c over phi. Six point two four times ten to the "
            "minus seven metres. Six hundred twenty four nanometres. "
            "Answer A."
        ),
        orientation=SHORT,
        beats_json=arc_short("packet", annotate="chain",
                             law="warn", shake="lobe",
                             punch="packet"),
        target_duration_sec=60,
    )

    # -------------------------------------------------- S9. Coulomb ratio
    add(
        video_id="short_coulomb",
        concept_type="GENERIC",
        header_title="Coulomb Ratio",
        tagline="Coulomb beats gravity by 10^39",
        question_text=("Ratio of electric to gravitational force between e "
                       "and p?"),
        option_a="10^10", option_b="10^20",
        option_c="2.3e39", option_d="10^50",
        correct_answer="Correct Answer: (C)",
        equations_json=[r"F_E/F_G=k e^2/(G m_e m_p)"],
        visual_data_json=[
            e_field("pair",
                    charges=[{"position": [-2.0, 0.0, 0.0], "charge": 1.0},
                             {"position": [2.0, 0.0, 0.0],
                              "charge": -1.0}],
                    xr=(-4.0, 4.0), yr=(-3.0, 3.0),
                    cols=9, rows=7),
            la_vectors("vec", (2.0, 0.0), (-1.0, 1.0),
                       center=(0.0, -3.5, 0.0), scale=0.8),
            numerical_chain("chain",
                            steps=[r"k e^2 = 2.30\times 10^{-28}",
                                   r"G m_e m_p = 1.0\times 10^{-67}",
                                   r"\text{ratio} = 2.3\times 10^{39}"],
                            pos=(4.0, 2.0, 0.0)),
            field_by_opacity("lines",
                             sources=[[-2.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
                             wavelength=0.5, omega=2.0, density=8,
                             width=6.0, height=4.0, color=ACCENT),
        ],
        audio_script=(
            "Ratio of electric to gravitational force between electron and "
            "proton. Plug in. Two point three times ten to the thirty "
            "nine. Answer C. And yet gravity runs the cosmos, because "
            "charges cancel and masses do not."
        ),
        orientation=SHORT,
        beats_json=arc_short("pair", annotate="chain",
                             law="lines", shake="vec",
                             punch="pair"),
        target_duration_sec=60,
    )

    # -------------------------------------------------- S10. Cyclotron
    add(
        video_id="short_cyclotron",
        concept_type="GENERIC",
        header_title="Cyclotron Period",
        tagline="The period does not depend on speed",
        question_text=("A proton at 5e6 m/s in a 0.5 T field. What is the "
                       "period?"),
        option_a="1e-7 s", option_b="6.6e-8 s",
        option_c="2.5e-7 s", option_d="1e-9 s",
        correct_answer="Correct Answer: (B)",
        equations_json=[r"T=2\pi m/(qB)"],
        visual_data_json=[
            m_field("field",
                    wires=[{"start": [-3.0, -2.0, 0.0],
                            "end": [3.0, 2.0, 0.0], "current": 0.5}],
                    xr=(-4.0, 4.0), yr=(-3.0, 3.0),
                    cols=11, rows=9),
            orbit("guide", radius=1.5, color=ACCENT),
            live_label("readout",
                       var_fn="2*pi*1.67e-27/(1.6e-19*0.5)",
                       fmt="T = {v:.2e} s",
                       pos=(0.0, -3.5, 0.0),
                       font_size=20),
            em_wave("emw", amp=0.5, freq=2.0, speed=3.0, length=4.0),
        ],
        audio_script=(
            "A proton in a magnetic field of half a tesla. Period is two "
            "pi m over q B. Plug in. Six point six times ten to the minus "
            "eight seconds. Answer B. Notice the speed does not appear. "
            "Every proton takes the same time."
        ),
        orientation=SHORT,
        beats_json=arc_short("field", annotate="readout",
                             law="guide", shake="emw",
                             punch="field"),
        target_duration_sec=60,
    )

    return rows


# ===========================================================================
# 5. Pre-flight check
# ===========================================================================

def preflight() -> None:
    """Verify every builder called by build_rows is defined in this module."""
    import inspect
    module = inspect.getmodule(preflight)
    defined = {
        name for name, value in vars(module).items()
        if callable(value) and not name.startswith("_")
    }
    builtins = {
        "print", "len", "range", "sum", "float", "int", "str", "list",
        "dict", "tuple", "set", "isinstance", "getattr", "setattr",
        "hasattr", "open", "enumerate", "min", "max", "abs", "sorted",
        "round", "zip", "map", "filter", "format", "repr",
    }
    required = [
        "beat", "arc_lecture", "arc_short",
        "calculus_graph", "derivative_tangent", "integral_area",
        "riemann_sum",
        "la_vectors", "la_dot", "la_cross", "la_det", "la_transform",
        "la_solve",
        "geo_polyline", "geo_polygon", "geo_circle", "geo_segment",
        "rotor",
        "venturi", "hydrostatic",
        "e_field", "m_field", "em_wave",
        "sim", "body",
        "wave_", "wave_pulse", "momentum", "pendulum", "projectile",
        "orbit", "gas", "heat_flow", "pv_tracker", "landscape",
        "potential_well", "induction_coil", "compass_grid",
        "interference", "two_beam", "bohr", "crystal", "rolling",
        "torsion", "pipe_gauge", "wave_packet", "accretion",
        "random_walk",
        "live_label", "numerical_chain", "equation_morph",
        "warning_box", "quiz_frame",
        "stream_field", "field_by_opacity", "energy_bar",
        "number_line", "damped_oscillator", "two_source",
        "beat_pattern", "harmonic_decomposition", "spectral_sum",
        "sliced_wave", "two_path_interference", "grid_warp",
        "taylor_expand", "exponential_atmosphere", "phase_portrait",
        "color_triangle", "polar_pattern",
        "text_", "dot_",
    ]
    missing = [name for name in required
               if name not in defined and name not in builtins]
    if missing:
        raise RuntimeError(
            f"generate_csv.py is missing definitions for: {missing}. "
            f"The file will fail at import time."
        )


# ===========================================================================
# 6. Writer and CLI
# ===========================================================================

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS,
                                quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


def summarise(rows: list[dict[str, Any]]) -> str:
    lectures = [r for r in rows if r["orientation"] == LECTURE]
    shorts = [r for r in rows if r["orientation"] == SHORT]
    return (
        f"Wrote {len(rows)} rows\n"
        f"  vertical   3-min lectures : {len(lectures)}\n"
        f"  horizontal 1-min shorts   : {len(shorts)}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="content_batch.csv",
                        help="output CSV path (default: content_batch.csv)")
    args = parser.parse_args(argv)

    preflight()
    rows = build_rows()
    out = Path(args.out)
    write_csv(out, rows)

    print(summarise(rows))
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
