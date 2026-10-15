#!/usr/bin/env python3
"""
generate_csv.py — Ohanian full-book generator, fully wired.

Produces content_batch.csv with 46 vertical 180-second lectures
(9:16, x∈[-4.5,4.5], y∈[-8,8]) and 17 horizontal 60-second shorts
(16:9, x∈[-8,8], y∈[-4.5,4.5]).

Orientation convention (CSV_AUTHORING.md):
    vertical   → lecture (180 s)
    horizontal → short   ( 60 s)

Engines exercised:
    calculus_engine        — calculus_graph, derivative_tangent,
                             integral_area, riemann_sum
    linear_algebra_engine  — vectors, dot, cross, determinant,
                             transform, solve
    geometry_engine        — segment, polyline, polygon, circle
    rotational_motion_eng  — solid_disk, hoop, rod_center, rod_end
    fluid_dynamics_engine  — venturi, hydrostatic
    electromagnetics_eng   — electric_field, magnetic_field,
                             electromagnetic_wave
    physics_simulation     — uniform_acceleration, linear_drag,
                             spring, central_gravity
    advanced_visuals       — live_label, numerical_chain, equation_morph,
                             warning_box, quiz_frame, stream_field,
                             field_by_opacity, energy_bar, number_line,
                             damped_oscillator, two_source, beat_pattern,
                             harmonic_decomposition, spectral_sum,
                             sliced_wave, two_path_interference,
                             grid_warp, taylor_expand,
                             exponential_atmosphere, phase_portrait,
                             color_triangle, polar_pattern
    visual_kit             — annotate, spotlight, kinetic_title,
                             term_bind, camera_shake, ambient,
                             cinematic_transition
    sound_design           — tick, whoosh, drone, chime

Beats use the schema_validator vocabulary:
    promise, hook, analogy, experiment, law, midpoint,
    emphasis, annotate, shake, punchline

Run:
    python3 generate_csv.py                    # content_batch.csv
    python3 generate_csv.py --out ohanian.csv  # custom path
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


# ===========================================================================
# 1. Schema and constants
# ===========================================================================

COLUMNS: tuple[str, ...] = (
    "video_id", "concept_type", "header_title", "tagline", "question_text",
    "option_a", "option_b", "option_c", "option_d", "correct_answer",
    "equations_json", "visual_data_json", "audio_script", "orientation",
    "beats_json", "target_duration_sec",
)

# Doc convention from CSV_AUTHORING.md — do not swap.
LECTURE = "vertical"     # 180 s, frame x∈[-4.5, 4.5], y∈[-8, 8]
SHORT   = "horizontal"   #  60 s, frame x∈[-8, 8],   y∈[-4.5, 4.5]

# Semantic palette — meaning attached, do not repaint casually.
PRIMARY = "#4CC9F0"   # subject
ACCENT  = "#F1C40F"   # contrast / second body
OK      = "#2ECC71"   # closure, positive
WARM    = "#E74C3C"   # warning, pathological
NEUTRAL = "#8A8F9C"   # axes, guides, gridlines


# ===========================================================================
# 2. Beat vocabulary (enriched)
# ===========================================================================

def beat(kind: str, focus: str, transition: str | None = None, *,
         annotate: dict | None = None,
         spotlight: dict | None = None,
         kinetic_title: dict | None = None,
         shake: bool = False,
         sound: dict | None = None) -> dict[str, Any]:
    """One beat. Extra keys are optional; renderer may ignore them."""
    b: dict[str, Any] = {"type": kind, "focus": focus}
    if transition:
        b["transition"] = transition
    if annotate:
        b["annotate"] = annotate
    if spotlight:
        b["spotlight"] = spotlight
    if kinetic_title:
        b["kinetic_title"] = kinetic_title
    if shake:
        b["shake"] = True
    if sound:
        b["sound"] = sound
    return b


def arc_lecture(focus: str, *, title: str | None = None,
                annotate_text: str | None = None,
                law_text: str | None = None,
                analogy: bool = False,
                experiment: bool = False,
                midpoint: bool = False,
                emphasis: bool = False) -> list[dict[str, Any]]:
    """Bare Feynman arc. Enriched later by enrich_lecture_beats()."""
    b = [beat("promise", focus,
              kinetic_title=kinetic_title("kt_open", title) if title else None,
              sound=drone("drone_open", duration=2.0)),
         beat("hook", focus,
              annotate=annotate("an_hook", annotate_text)
              if annotate_text else None,
              sound=whoosh("w_hook"))]
    if analogy:
        b.append(beat("analogy", focus, sound=tick("t_analogy")))
    if experiment:
        b.append(beat("experiment", focus, sound=tick("t_experiment")))
    b.append(beat("law", focus, transition="wipe",
                  annotate=annotate("an_law", law_text) if law_text else None,
                  sound=chime("c_law")))
    if midpoint:
        b.append(beat("midpoint", focus, sound=tick("t_mid")))
    if emphasis:
        b.append(beat("emphasis", focus, shake=True,
                      spotlight=spotlight("sp_emph", (0.0, 0.0, 0.0)),
                      sound=whoosh("w_emph")))
    b.append(beat("punchline", focus, sound=chime("c_close", pitch="C6")))
    return b


def arc_short(focus: str, *, title: str | None = None,
              annotate_text: str | None = None) -> list[dict[str, Any]]:
    return [
        beat("hook", focus,
             kinetic_title=kinetic_title("kt_open", title) if title else None,
             sound=whoosh("w_hook")),
        beat("annotate", focus,
             annotate=annotate("an_body", annotate_text)
             if annotate_text else None,
             sound=tick("t_body")),
        beat("law", focus, transition="wipe",
             sound=chime("c_law")),
        beat("shake", focus, shake=True, sound=whoosh("w_shake")),
        beat("punchline", focus, sound=chime("c_close", pitch="C6")),
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
                       xl=6.0, yl=3.0, ctr=(0.0, 0.0, 0.0)):
    return {"type": "derivative_tangent", "id": id_, "expression": expr,
            "x_range": list(xr), "y_range": list(yr),
            "x_length": xl, "y_length": yl, "center": list(ctr),
            "x0": x0, "delta": delta}


def integral_area(id_, expr, xr, yr, a, b, color=PRIMARY):
    return {"type": "integral_area", "id": id_, "expression": expr,
            "x_range": list(xr), "y_range": list(yr), "a": a, "b": b,
            "color": color}


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


def geo_polygon(id_, points, color=PRIMARY, opacity=0.20):
    return {"type": "geometry", "id": id_, "dimension": 2,
            "kind": "polygon", "points": [list(p) for p in points],
            "color": color, "fill_opacity": opacity}


def geo_circle(id_, position, radius, color=PRIMARY, opacity=0.12):
    return {"type": "geometry", "id": id_, "dimension": 2,
            "kind": "circle", "position": list(position),
            "radius": radius, "color": color, "fill_opacity": opacity}


def geo_segment(id_, points, color=PRIMARY, stroke=2.5):
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


def em_wave(id_, amp=1.0, freq=1.0, speed=2.0, length=5.0):
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


def falling(id_, mass, height, g=9.8, color=PRIMARY):
    return {"type": "falling_energy", "id": id_, "mass": mass,
            "height": height, "g": g, "color": color}


def projectile(id_, v0, angle, g=9.8, color=PRIMARY):
    return {"type": "projectile_motion", "id": id_, "v0": v0,
            "angle": angle, "g": g, "color": color}


def orbit(id_, radius, color=PRIMARY):
    return {"type": "orbit", "id": id_, "radius": radius, "color": color}


def gas(id_, count=80, box=(6.0, 3.0), color=PRIMARY):
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


potential_well = landscape  # alias


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
    return {"type": "two_beam_splitter", "id": id_, "beam_color": color}


def bohr(id_, color=PRIMARY):
    return {"type": "bohr_orbit_photon", "id": id_, "color": color}


def crystal(id_, color=PRIMARY):
    return {"type": "crystal_lattice", "id": id_, "color": color}


def rolling(id_, color=PRIMARY):
    return {"type": "rolling_wheel_cycloid", "id": id_, "color": color}


def torsion(id_, color=PRIMARY):
    return {"type": "torsion_rod", "id": id_, "color": color}


def pipe_gauge(id_, color=PRIMARY):
    return {"type": "pipe_with_gauge", "id": id_, "color": color}


def wave_packet(id_, color=PRIMARY):
    return {"type": "wave_packet_tunneling", "id": id_, "color": color}


def accretion(id_, pos=(0.0, 3.0, 0.0), color=PRIMARY):
    return {"type": "accretion_disk", "id": id_, "pos": list(pos),
            "color": color}


def random_walk(id_, color=PRIMARY):
    return {"type": "random_walk", "id": id_, "color": color}


# --- advanced visuals (from generate_csv-5.py) ----------------------------

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
            "options": list(options), "correct": correct, "pause": pause}


def stream_field(id_, charges, xr=(-4.0, 4.0), yr=(1.0, 5.0), color=OK):
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


# --- visual_kit (was promised by all three docstrings, actually missing) --

def annotate(id_, text, pos=(0.0, 3.5, 0.0), color=ACCENT, arrow=None):
    d = {"type": "annotate", "id": id_, "text": text,
         "pos": list(pos), "color": color}
    if arrow:
        d["arrow"] = list(arrow)
    return d


def spotlight(id_, target, radius=1.5, color=ACCENT):
    return {"type": "spotlight", "id": id_, "target": list(target),
            "radius": radius, "color": color}


def kinetic_title(id_, text, pos=(0.0, 4.5, 0.0), color=PRIMARY):
    return {"type": "kinetic_title", "id": id_, "text": text,
            "pos": list(pos), "color": color}


def term_bind(id_, term, target, color=ACCENT):
    return {"type": "term_bind", "id": id_, "term": term,
            "target": list(target), "color": color}


def camera_shake(id_, amplitude=0.15, duration=0.5):
    return {"type": "camera_shake", "id": id_,
            "amplitude": amplitude, "duration": duration}


def ambient(id_, color=PRIMARY, intensity=0.3):
    return {"type": "ambient", "id": id_, "color": color,
            "intensity": intensity}


def cinematic_transition(id_, kind="wipe", duration=0.6):
    return {"type": "cinematic_transition", "id": id_,
            "kind": kind, "duration": duration}


# --- sound_design (also missing everywhere) -------------------------------

def tick(id_, at=0.0):
    return {"type": "tick", "id": id_, "at": at}


def whoosh(id_, at=0.0, duration=0.4):
    return {"type": "whoosh", "id": id_, "at": at, "duration": duration}


def drone(id_, at=0.0, duration=4.0, pitch="low"):
    return {"type": "drone", "id": id_, "at": at,
            "duration": duration, "pitch": pitch}


def chime(id_, at=0.0, pitch="C5"):
    return {"type": "chime", "id": id_, "at": at, "pitch": pitch}


def text_(id_, txt, pos=(0.0, 3.8, 0.0), color=PRIMARY):
    return {"type": "text", "id": id_, "text": txt, "pos": list(pos),
            "color": color}


def dot_(id_, pos, color=ACCENT, label=None):
    d = {"type": "dot", "id": id_, "pos": list(pos), "color": color}
    if label:
        d["label"] = label
    return d


def num_line(id_, rng, markers, color=PRIMARY):
    """Legacy alias — delegates to number_line."""
    return number_line(id_, rng, markers, color=color)


# ===========================================================================
# 4. Chapter spec helpers
# ===========================================================================

def chapter(num, title, slug, header, tagline, question, eqs, vis, script,
            short=None):
    return dict(num=num, title=title, slug=slug, header=header,
                tagline=tagline, question=question, eqs=eqs, vis=vis,
                script=script, short=short)


def mk_short(vid, header, tagline, question, opts, correct, eqs, vis,
             script):
    a, b, c, d = opts
    return dict(video_id=vid, header=header, tagline=tagline,
                question=question, option_a=a, option_b=b, option_c=c,
                option_d=d, correct=correct, eqs=eqs, vis=vis,
                script=script)


# ===========================================================================
# 5. Chapters — full Ohanian book, enriched with advanced visuals
# ===========================================================================

CHAPTERS = [

# 1 ------------------------------------------------------------------------
chapter(1, "Measurement", "ohanian_ch01_measurement",
    "The Number That Lies", "Trailing zeros are promises",
    "Why is 1.5 not the same as 1.50?",
    [r"\text{precision} \Rightarrow \text{sig figs}"],
    [geo_segment("ruler", [(-3.0, 0.0), (3.0, 0.0)]),
     number_line("scale", (-0.5, 5.0), (1.5, 2.5, 3.5)),
     warning_box("warn", "The last digit is always a guess."),
     text_("note", "the last digit is always a guess")],
    "I am going to show you something strange. Three students measure "
    "the same table. Same ruler, same table, same everything. Student "
    "one says one point five meters. Student two says one point five "
    "zero. Student three says one point five zero zero. Which is "
    "right? All of them, and none of them. The digits are not "
    "decoration. They are a claim about precision. A calculator will "
    "happily report ten digits from two-digit inputs. The calculator "
    "is not lying. It is just doing arithmetic. Physics is different. "
    "Every digit is a promise. The last digit is always uncertain. "
    "The number of significant figures tells your reader how "
    "uncertain. Multiply or divide, keep the least. Add or subtract, "
    "keep the least decimal place. A ruler marked in millimeters "
    "cannot measure to a tenth of a millimeter. The tool sets the "
    "precision. The precision sets the digits. In engineering, this "
    "decides whether a bridge is safe. In medicine, whether a "
    "diagnosis is real. The digits are not decoration. They are a "
    "promise you are making to every reader.",
    short=mk_short("ohanian_ch01_sigfigs",
        "Count the Significant Figures", "Leading zeros never count",
        "How many significant figures in 0.00540 m?",
        ("2", "3", "4", "5"), "Correct Answer: (B)",
        [r"\text{leading zeros mark decimal place only}"],
        [number_line("line", (-0.5, 5.0), (0.0, 3.0)),
         numerical_chain("chain",
                         steps=[r"0.00540", r"\text{first nonzero: 5}",
                                r"\text{count: 5, 4, 0}", r"n = 3"],
                         pos=(0.0, -2.5, 0.0))],
        "Zero point zero zero five four zero meters. How many "
        "significant figures? Leading zeros never count. They mark the "
        "decimal place. The first nonzero digit is five. Everything "
        "from there counts. Five, four, and the trailing zero. Three. "
        "Answer B.")),

# 2 ------------------------------------------------------------------------
chapter(2, "Kinematics 1D", "ohanian_ch02_worldline",
    "The Speedometer's Secret",
    "Instantaneous speed is a limit, not a reading",
    "What does a speed dial actually measure?",
    [r"v=\lim_{\Delta t \to 0}\frac{\Delta x}{\Delta t}"],
    [derivative_tangent("curve", "x**2/2 + 0.5",
                        (-2.0, 2.0), (-1.0, 3.0), x0=1.0, delta=0.7),
     sim("falling",
         bodies=[body(1.0, (0.0, 4.0), (0.0, 0.0), label="ball")],
         forces=[{"type": "uniform_acceleration",
                  "acceleration": [0.0, -9.8]}],
         duration=0.9, playback=3.0),
     live_label("readout", var_fn="0.5*9.8*t*t", fmt="x = {v:.2f} m",
                pos=(0.0, -5.0, 0.0)),
     numerical_chain("chain",
                     steps=[r"F = ma", r"a = g", r"v = g t",
                            r"x = \tfrac{1}{2} g t^2"],
                     pos=(0.0, -7.5, 0.0))],
    "Here is something strange. Your speedometer says fifty. Over what? "
    "The last second? The last minute? Each window gives a different "
    "average. The dial is claiming something stronger. It says speed "
    "right now. But right now is zero duration. No time passes, no "
    "distance accumulates. So the dial is either lying or doing "
    "something subtler. Newton and Leibniz invented calculus to make "
    "it precise. Pick an interval. Compute the average. Shrink the "
    "interval. Compute again. Shrink again. If the averages settle "
    "toward a single number, that number is the instantaneous speed. "
    "On a position-versus-time graph, the average speed is the slope "
    "of a secant line. As the interval shrinks, the secant pivots. In "
    "the limit, it becomes the tangent. The instantaneous speed is "
    "the slope of that tangent. That is the derivative. Every dial "
    "you have ever read is a derivative in disguise.",
    short=mk_short("ohanian_ch02_avg_speed",
        "Average Speed Is Not the Average",
        "You cannot just average the two speeds",
        "A jogger runs 2 km at 10 km/h then 2 km at 6 km/h. Average speed?",
        ("7.5 km/h", "8.0 km/h", "8.5 km/h", "9.0 km/h"),
        "Correct Answer: (A)", [r"v_{avg} = d_{total}/t_{total}"],
        [number_line("line", (0.0, 4.0), (0.0, 2.0, 4.0)),
         numerical_chain("chain",
                         steps=[r"t_1 = 0.2\ \text{h}",
                                r"t_2 = 0.333\ \text{h}",
                                r"v = 4 / 0.533 = 7.5"],
                         pos=(0.0, -2.5, 0.0))],
        "Two kilometers at ten. Two at six. Average speed? Tempting "
        "answer, eight. Wrong. Total distance over total time. Time "
        "running, zero point two. Time walking, zero point three "
        "three. Four over zero point five three is seven point five. "
        "Answer A. Closer to the slow speed, because more time was "
        "spent there.")),

# 3 ------------------------------------------------------------------------
chapter(3, "Vectors", "ohanian_ch03_vectors",
    "Arrows That Do Not Lie", "Vector addition is triangle geometry",
    "Why can't you add vectors like ordinary numbers?",
    [r"\vec{R}=\vec{A}+\vec{B}"],
    [la_vectors("v_add", (2.0, 1.0), (-1.0, 2.0),
                center=(0.0, 1.5, 0.0), scale=0.9),
     la_dot("dot", (2.0, 1.0), (-1.0, 2.0), center=(0.0, -2.5, 0.0)),
     warning_box("warn", "Forces do not add like numbers.")],
    "I will show you why forces do not add like numbers. Two forces act "
    "on a block. Ten newtons east. Five newtons north. What is the "
    "total? Not fifteen. Never fifteen. Forces are vectors. They have "
    "magnitude and direction. You add them tip to tail, like arrows. "
    "Place the tail of the second at the tip of the first. Draw from "
    "the first tail to the second tip. That is the resultant. Its "
    "magnitude comes from the Pythagorean theorem. Its direction from "
    "trigonometry. This is not a mathematical trick. It reflects "
    "physics. Displace yourself one meter east, then one meter north. "
    "You are not two meters from where you started. You are one point "
    "four one meters away, on a diagonal. Velocity, acceleration, "
    "momentum, torque, electric field, magnetic field. Almost every "
    "directed physical quantity obeys the same rules.",
    short=mk_short("ohanian_ch03_resultant",
        "Resultant of Two Vectors", "Law of cosines in disguise",
        "A is 10 units west. B is 5 units at 70 deg N of E. Resultant?",
        ("9.5 units", "12 units", "15 units", "17 units"),
        "Correct Answer: (A)", [r"R^2 = A^2 + B^2 - 2AB\cos\theta"],
        [la_vectors("v", (-10.0, 0.0), (1.7, 4.7),
                    center=(0.0, 0.0, 0.0), scale=0.30),
         numerical_chain("chain",
                         steps=[r"R^2 = 100 + 25 - 100(0.342)",
                                r"R^2 = 90.8", r"R \approx 9.5"],
                         pos=(0.0, -3.0, 0.0))],
        "A is ten west. B is five at seventy degrees north of east. "
        "The angle between them, tip to tail, is one hundred ten "
        "degrees. R squared equals one hundred plus twenty five minus "
        "one hundred times zero point three four two. Which gives "
        "ninety. Root ninety is nine point five. Answer A.")),

# 4 ------------------------------------------------------------------------
chapter(4, "Kinematics 3D", "ohanian_ch04_projectile",
    "The Trick of Falling Sideways",
    "Gravity does not care how fast you move sideways",
    "Which ball hits first?",
    [r"x=v_{0x}t", r"y=-\tfrac{1}{2}gt^2"],
    [sim("drop_and_fire",
         bodies=[body(1.0, (-3.0, 4.0), (5.0, 0.0), label="fired",
                      color=PRIMARY),
                 body(1.0, (-3.0, 4.0), (0.0, 0.0), label="dropped",
                      color=ACCENT)],
         forces=[{"type": "uniform_acceleration",
                  "acceleration": [0.0, -9.8]}],
         duration=1.0, playback=3.0),
     projectile("trajectory", v0=10.0, angle=0.0),
     la_vectors("components", (5.0, 0.0), (0.0, -9.8),
                center=(0.0, -5.0, 0.0), scale=0.5)],
    "I am going to show you something almost everyone gets wrong. Two "
    "identical balls, one dropped, one fired horizontally. Which hits "
    "first? Almost everyone says the fired one takes longer. It has "
    "farther to travel. It does have farther to travel. But it lands "
    "at the same instant. Why? Horizontal and vertical motion do not "
    "talk. Gravity pulls down. It has no opinion about sideways "
    "speed. This is Newton's second law, split into components. F x "
    "equals zero, so a x equals zero. F y equals minus m g, so a y "
    "equals minus g. Two separate stories. The parabola is what you "
    "get when you stitch a straight line to a free fall. Every "
    "projectile problem collapses under this one insight."),

# 5 ------------------------------------------------------------------------
chapter(5, "Newton's Laws", "ohanian_ch05_free_body",
    "The Force You Invented", "Accelerations do not create forces",
    "Why do beginners add an arrow that isn't there?",
    [r"F_{net}=ma"],
    [sim("block_with_drag",
         bodies=[body(1.0, (-3.0, 0.0), (3.0, 0.0), label="m")],
         forces=[{"type": "linear_drag", "coefficient": 0.6}],
         duration=4.0, playback=4.0),
     warning_box("warn", "No extra arrow. Forces cause acceleration, "
                         "not the reverse.",
                 pos=(0.0, 3.5, 0.0)),
     la_vectors("fb", (2.0, 0.0), (0.0, -1.0),
                center=(0.0, -3.5, 0.0), scale=0.8)],
    "Here is the single most common mistake in mechanics. A block "
    "slides on a rough floor. You draw the free-body diagram. Weight. "
    "Normal. Friction. And then you add one more arrow pointing in "
    "the direction of motion. Because the block is moving, something "
    "must push it. That arrow does not exist. Newton's second law "
    "says accelerations come from forces. Not the other way. A block "
    "sliding at constant velocity has zero net force. Its motion is "
    "not a force. Motion is what happens when forces balance. When "
    "you build a free-body diagram, ask two questions. What is "
    "touching the object? Is there a long-range force? Gravity. Or a "
    "charge. Draw only those. Then set the vector sum equal to m a. "
    "If the block is accelerating, the diagram shows which force did "
    "it. If not, the arrows cancel. Forces cause acceleration. "
    "Accelerations do not cause forces."),

# 6 ------------------------------------------------------------------------
chapter(6, "Forces", "ohanian_ch06_spring",
    "The Spring That Pushes Back",
    "Hooke's law is a differential equation in disguise",
    "What happens when the force depends on position?",
    [r"F=-kx", r"x(t)=A\cos(\omega t+\phi)"],
    [sim("spring",
         bodies=[body(1.0, (0.0, 1.5), (0.0, 0.0), label="m")],
         forces=[{"type": "spring", "body": 0, "anchor": [0.0, 0.0],
                  "stiffness": 4.0, "rest_length": 1.0,
                  "damping": 0.08}],
         duration=8.0, playback=5.0),
     damped_oscillator("osc", anchor=(3.0, 1.5, 0.0),
                       rest_length=1.0, amplitude=0.6, omega=3.0,
                       gamma=0.1),
     equation_morph("eq",
                    steps=[r"F = -kx",
                           r"m \frac{d^2 x}{dt^2} = -kx",
                           r"\frac{d^2 x}{dt^2} + \omega^2 x = 0"],
                    pos=(0.0, -4.0, 0.0))],
    "I will show you the first differential equation every physicist "
    "solves. Push a spring. It pushes back. Pull it, it pulls back. "
    "The force is proportional to displacement, opposite in "
    "direction. Hooke's law. Simple. But what happens when the force "
    "depends on position? Newton's second law becomes a differential "
    "equation. F equals m a. Minus k x equals m d squared x over d t "
    "squared. Rearrange. d squared x over d t squared plus k over m "
    "times x equals zero. This is the harmonic oscillator equation. "
    "Its solutions are sines and cosines. The mass oscillates "
    "forever, back and forth, at a frequency set by k over m. This is "
    "one of the most important equations in physics, because almost "
    "every potential looks like a parabola near its minimum."),

# 7 ------------------------------------------------------------------------
chapter(7, "Work-Energy", "ohanian_ch07_work",
    "Push Harder as You Go", "Work is the area under the curve",
    "How do you add up a force that keeps changing?",
    [r"W=\int_a^b F\,dx", r"W_{net}=\Delta K"],
    [calculus_graph("force_curve", "2*x + 1",
                    (0.0, 3.0), (0.0, 8.0), xl=6.0, yl=3.0),
     riemann_sum("strips", "2*x + 1",
                 (0.0, 3.0), (0.0, 8.0), 0.0, 3.0, n=14,
                 sample="midpoint"),
     integral_area("area", "2*x + 1", (0.0, 3.0), (0.0, 8.0),
                   0.0, 3.0)],
    "I am going to show you where calculus comes from in physics. Push "
    "a crate across a rough floor. At first easy. As you go, the "
    "resistance grows. You cannot just multiply force by distance. "
    "The force keeps changing. Here is the trick. Break the journey "
    "into tiny steps. On each step the force is essentially constant. "
    "Work equals force times step length. A little rectangle under "
    "the force curve. Add the rectangles. Shrink the steps. The sum "
    "becomes an integral. The work done by a variable force is the "
    "area under the force-versus-position curve. That is all calculus "
    "is. Bookkeeping for things that change."),

# 8 ------------------------------------------------------------------------
chapter(8, "Conservation", "ohanian_ch08_landscape",
    "The Shortcut Through Space",
    "Energy lets you skip the trajectory",
    "Why can you solve some problems without tracking every moment?",
    [r"K+U=\text{constant}", r"U=-\int F\,dx"],
    [landscape("well", "0.5*x**2", (-3.0, 3.0), (0.0, 5.0)),
     sim("ball_in_well",
         bodies=[body(1.0, (2.0, 3.0), (0.0, 0.0), label="ball")],
         forces=[{"type": "spring", "body": 0, "anchor": [0.0, 0.0],
                  "stiffness": 4.0, "rest_length": 0.0,
                  "damping": 0.05}],
         duration=10.0, playback=5.0),
     energy_bar("ke", pos=(3.0, 0.0, 0.0), fill=0.5,
                label="K + U", width=2.0)],
    "I will show you how to cheat. Throw a ball up. It rises, slows, "
    "stops, falls back. You can solve this with Newton's laws, "
    "tracking velocity and position at every instant. Or you can take "
    "a shortcut. Define energy. For gravity, m g h. As the ball "
    "rises, kinetic drops, potential rises. The sum stays constant. "
    "You do not need the trajectory. You only need the endpoints. "
    "This works whenever the force is conservative. The potential "
    "curve tells you everything. Where it is steep, the force is "
    "strong. Where it has a minimum, the object oscillates."),

# 9 ------------------------------------------------------------------------
chapter(9, "Gravitation", "ohanian_ch09_orbit",
    "The Moon Is Falling", "It has been falling for four billion years",
    "Why does the Moon keep missing the Earth?",
    [r"F=\frac{GMm}{r^2}", r"v=\sqrt{\frac{GM}{r}}"],
    [sim("orbit_sim",
         bodies=[body(1.0, (-2.5, 0.0), (0.0, 2.0), label="Moon",
                      color=PRIMARY),
                 body(1.0, (0.0, 0.0), (0.0, 0.0), label="Earth",
                      color=ACCENT)],
         forces=[{"type": "central_gravity", "source": 1, "mu": 24.0}],
         duration=14.0, playback=6.0),
     orbit("guide", radius=2.5, color=ACCENT),
     numerical_chain("chain",
                     steps=[r"F_g = F_c",
                            r"\frac{GMm}{r^2} = \frac{mv^2}{r}",
                            r"v = \sqrt{GM/r}"],
                     pos=(0.0, -7.0, 0.0))],
    "Newton's apple is the famous fruit. But the apple is half the "
    "story. The real question was the Moon. Why does it go around the "
    "Earth instead of falling onto it? Because it is falling. It has "
    "been falling for four billion years. It just keeps missing. "
    "Imagine throwing a ball horizontally from a very tall tower. "
    "Throw gently, it lands nearby. Harder, farther. Throw hard "
    "enough, the Earth curves away beneath it as fast as it falls. "
    "The ball never lands. That is an orbit. The Moon does this. "
    "Gravity pulls inward, constantly. But it has the right sideways "
    "speed, so it curves instead of crashing. Set the gravitational "
    "force equal to the centripetal force. The orbital speed comes "
    "out to the square root of G M over r. It depends on the central "
    "mass and the radius. Not on the Moon's mass. This is why a "
    "pebble and a moon at the same radius orbit at the same speed.",
    short=mk_short("ohanian_ch09_escape",
        "How Fast to Leave Earth?", "Escape is only √2 times orbital",
        "What is the escape velocity from the Earth's surface?",
        ("7.9 km/s", "11.2 km/s", "15 km/s", "3.0 km/s"),
        "Correct Answer: (B)", [r"v_{esc}=\sqrt{2GM_E/R_E}"],
        [orbit("earth", 2.0),
         dot_("launch", (2.0, 0.0, 0.0), color=ACCENT),
         numerical_chain("chain",
                         steps=[r"v_{orb} = 7.9\ \text{km/s}",
                                r"v_{esc} = \sqrt{2}\, v_{orb}",
                                r"v_{esc} = 11.2\ \text{km/s}"],
                         pos=(0.0, -2.5, 0.0))],
        "What speed do you need to leave Earth and never come back? "
        "Set kinetic energy equal to gravitational binding energy. One "
        "half m v squared equals G M m over R. The m cancels. v equals "
        "root two G M over R. Plug in Earth's mass and radius. v is "
        "eleven point two kilometers per second. Answer B. That is "
        "orbital speed times root two. This is why the Moon has no "
        "atmosphere.")),

# 10 -----------------------------------------------------------------------
chapter(10, "Systems", "ohanian_ch10_center_of_mass",
    "The Point That Never Moves", "Every explosion has a still center",
    "Where is the center of a spinning, exploding object?",
    [r"F_{ext}=Ma_{CM}"],
    [momentum("collision", 1.0, 3.0, 4.0, 0.0),
     dot_("cm", (-0.5, 0.0, 0.0), color=ACCENT, label="CM"),
     la_vectors("cm_sum", (1.0, 0.0), (3.0, 0.0),
                center=(0.0, -3.0, 0.0), scale=0.6)],
    "I am going to show you a point that does not move. A firework "
    "explodes into a hundred pieces. Every piece takes its own path. "
    "Chaotic. But one point keeps moving as if nothing happened. The "
    "center of mass. It follows the same parabola the unexploded "
    "shell would have followed. It does not know the explosion "
    "occurred. This is the heart of Ohanian's chapter on systems of "
    "particles. Newton's second law applied to every atom is a "
    "nightmare. Applied once to the center of mass, it is simple. Net "
    "external force equals total mass times the acceleration of the "
    "center of mass. Internal forces cancel in pairs by Newton's "
    "third law. They never move the center of mass."),

# 11 -----------------------------------------------------------------------
chapter(11, "Collisions", "ohanian_ch11_impulse",
    "The Impulse Approximation", "Fast collisions hide the outside world",
    "Why is momentum conserved but not kinetic energy?",
    [r"m_1v_1+m_2v_2=m_1v_1'+m_2v_2'"],
    [momentum("collision", 2.0, 4.0, 5.0, -2.0),
     equation_morph("eq",
                    steps=[r"m_1 v_1 + m_2 v_2 = m_1 v_1' + m_2 v_2'",
                           r"K \neq K'", r"\Delta K \to \text{heat}"],
                    pos=(0.0, 4.0, 0.0))],
    "I am going to show you why the equations work. Two carts collide. "
    "Momentum is conserved. Kinetic energy is not. Before, they "
    "carried some kinetic energy. After, less. Where did it go? Heat, "
    "sound, deformation. Momentum is a vector, and Newton's third law "
    "guarantees equal and opposite impulses. Energy is a scalar. It "
    "changes form. But Ohanian adds a subtle point. The reason "
    "momentum is conserved is not that external forces are absent. It "
    "is that they are small compared to the collision force, and they "
    "act over an extremely short window. Their impulse is negligible. "
    "This is the impulse approximation.",
    short=mk_short("ohanian_ch11_ballistic",
        "The Ballistic Pendulum", "Conservation of momentum in one line",
        "A 20 g bullet at 300 m/s embeds in a 500 g block. Block speed?",
        ("7.5 m/s", "11.5 m/s", "15 m/s", "20 m/s"),
        "Correct Answer: (B)", [r"m_1v_1=(m_1+m_2)v'"],
        [momentum("collision", 0.02, 0.5, 300.0, 0.0),
         numerical_chain("chain",
                         steps=[r"p = (0.02)(300) = 6",
                                r"m' = 0.52",
                                r"v' = 6 / 0.52 = 11.5"],
                         pos=(0.0, -2.5, 0.0))],
        "A twenty gram bullet at three hundred meters per second hits a "
        "stationary five hundred gram block. Embeds. Momentum is "
        "conserved. Before, six kilogram meters per second. After, "
        "combined mass is zero point five two kilograms. Six over zero "
        "point five two is eleven point five. Answer B. Kinetic energy "
        "is not conserved. Most of it became heat.")),

# 12 -----------------------------------------------------------------------
chapter(12, "Rigid Kinematics", "ohanian_ch12_angular",
    "The Dance of Angles", "Every point on a rigid body shares omega",
    "Why does the rim of a wheel move faster than the hub?",
    [r"v=\omega R", r"a=\alpha R"],
    [rolling("cycloid"),
     rotor("wheel", "solid_disk", 1.0, 1.2, 2.0, 0.0,
           center=(0.0, -2.0, 0.0)),
     live_label("v_rim", var_fn="2.0 * 1.2", fmt="v = {v:.2f} m/s",
                pos=(3.0, 2.0, 0.0))],
    "I will show you why every point on a wheel has the same omega. A "
    "wheel spins. A point near the hub moves slowly. A point on the "
    "rim moves fast. Both complete one revolution in the same time. "
    "This is the key insight of rotational kinematics. Linear "
    "velocity depends on the distance from the axis. Angular velocity "
    "does not. Every point on a rigid body shares omega. Every point "
    "shares alpha. If you tried to describe every point separately, "
    "you would drown in detail. Instead, describe the body once. Then "
    "convert to linear variables whenever you need them."),

# 13 -----------------------------------------------------------------------
chapter(13, "Rigid Dynamics", "ohanian_ch13_torque",
    "Why the Disk Always Wins", "Mass distribution sets the race",
    "A hoop and a disk roll down the same ramp. Which wins?",
    [r"\tau=I\alpha", r"I=\sum m_i r_i^2"],
    [rotor("disk", "solid_disk", 2.0, 1.2, 2.0, 0.0,
           center=(0.0, 2.0, 0.0)),
     rotor("hoop", "hoop", 2.0, 1.2, 2.0, 0.0,
           center=(0.0, -2.0, 0.0), color=ACCENT),
     energy_bar("ke_bar", pos=(3.0, -3.0, 0.0), fill=0.7,
                label="K_total", width=2.0),
     equation_morph("eq",
                    steps=[r"I_{disk} = \tfrac{1}{2} M R^2",
                           r"I_{hoop} = M R^2",
                           r"I_{hoop} > I_{disk}"],
                    pos=(0.0, -6.0, 0.0), font_size=24)],
    "I am going to show you why the disk always wins. Same mass, same "
    "radius, same ramp. Release. The disk reaches the bottom first. "
    "Both lose the same potential energy. Both end with the same "
    "total kinetic energy. But kinetic energy has two flavours. "
    "Translational, one half m v squared. Rotational, one half I "
    "omega squared. For rolling without slipping, v equals omega R. "
    "So the rotational share depends on the moment of inertia. The "
    "hoop's mass sits at the rim. Its moment of inertia is m R "
    "squared. The disk's mass is spread out. Its moment is only one "
    "half m R squared. A bigger fraction of the hoop's energy goes "
    "into spinning. Less into forward motion. The hoop loses.",
    short=mk_short("ohanian_ch13_torque_disk",
        "Torque on a Solid Disk", "The moment of inertia sets alpha",
        "A 12 N·m torque acts on a 4 kg, 0.5 m solid disk. Find alpha.",
        ("3.0 rad/s²", "6.0 rad/s²", "12 rad/s²", "24 rad/s²"),
        "Correct Answer: (D)", [r"\tau = I\alpha,\ I = \tfrac{1}{2}MR^2"],
        [rotor("disk", "solid_disk", 4.0, 1.5, 0.0, 12.0,
               center=(0.0, 0.0, 0.0)),
         numerical_chain("chain",
                         steps=[r"I = \tfrac{1}{2}(4)(0.5)^2 = 0.5",
                                r"\alpha = \tau / I",
                                r"\alpha = 12 / 0.5 = 24"],
                         pos=(0.0, -3.0, 0.0))],
        "A solid disk of mass four kilograms and radius half a meter. "
        "Torque of twelve newton meters. Moment of inertia of a disk "
        "is one half m r squared, which is zero point five. Alpha "
        "equals torque over I. Twelve over zero point five. Twenty "
        "four. Answer D. A hoop would resist more.")),

# 14 -----------------------------------------------------------------------
chapter(14, "Statics", "ohanian_ch14_equilibrium",
    "The Stuck Drawer", "Torque decides equilibrium",
    "Why does a wide drawer stick when you pull one side?",
    [r"\sum F=0", r"\sum \tau=0"],
    [torsion("bar"),
     geo_polygon("drawer", [(-2.0, -1.0), (2.0, -1.0),
                             (2.0, 1.0), (-2.0, 1.0)],
                 color=PRIMARY, opacity=0.15),
     number_line("offset", (-2.5, 2.5), (0.0, 1.7))],
    "I will show you why a wide drawer sticks. Pull from the middle, "
    "it slides. Pull from one side, it jams. Why? Statics. When you "
    "pull from the middle, the two front corners push against the "
    "frame with equal force. Pull from one side, and a torque "
    "develops about the centerline. One corner digs in harder. If the "
    "offset is large enough, the corner digs so hard it jams. The "
    "threshold is set by the friction coefficient and the depth. "
    "Statics is not just for bridges. It is for kitchen cabinets."),

# 15 -----------------------------------------------------------------------
chapter(15, "Oscillations", "ohanian_ch15_pendulum",
    "The Clock That Ignores Amplitude",
    "A pendulum's period depends only on length",
    "Why does the swing rhythm stay the same at every size?",
    [r"T=2\pi\sqrt{L/g}"],
    [pendulum("swing", length=2.0, angle=18.0),
     sim("shm_spring",
         bodies=[body(1.0, (1.0, 2.0), (0.0, 0.0), label="m",
                      color=ACCENT)],
         forces=[{"type": "spring", "body": 0, "anchor": [0.0, 2.0],
                  "stiffness": 3.0, "rest_length": 1.0,
                  "damping": 0.0}],
         duration=6.0, playback=4.0),
     phase_portrait("phase", amplitude=1.5, gamma=0.0, omega=3.0)],
    "I am going to show you something that surprised Galileo. Watch a "
    "grandfather clock. The pendulum swings back and forth at the same "
    "tempo, hour after hour. As the clock runs down, the swing gets "
    "smaller. Yet the period does not change. A small swing and a "
    "large swing take the same time. Why? The restoring force comes "
    "from gravity pulling the bob back to the bottom. For small "
    "angles, that force is proportional to displacement. Double the "
    "displacement, double the force. That linearity makes the motion "
    "harmonic. It makes the period independent of amplitude. This is "
    "isochronism. Galileo noticed it watching a chandelier sway in a "
    "cathedral.",
    short=mk_short("ohanian_ch15_period",
        "Pendulum Period", "No mass, no amplitude",
        "A one meter pendulum swings. What is its period?",
        ("0.5 s", "1.0 s", "2.0 s", "4.0 s"),
        "Correct Answer: (C)", [r"T = 2\pi\sqrt{L/g}"],
        [pendulum("swing", length=1.0, angle=15.0),
         live_label("readout", var_fn="2*3.14159*(1/9.8)**0.5",
                    fmt="T = {v:.2f} s", pos=(0.0, -3.5, 0.0))],
        "A pendulum one meter long. Period equals two pi root L over g. "
        "Plug in one and nine point eight. Root of one over nine "
        "point eight is about zero point three two. Two pi times that "
        "is about two seconds. Answer C. Notice. No mass. No "
        "amplitude. That is why pendulums are clocks.")),

# 16 -----------------------------------------------------------------------
chapter(16, "Waves", "ohanian_ch16_medium",
    "A Wave Is Not the Medium",
    "The pattern travels while the particles stay put",
    "Does the string travel with the wave?",
    [r"v=\sqrt{F/\mu}", r"y(x,t)=A\cos(kx-\omega t)"],
    [wave_("wave", 1.0, 3.0, 1.0, (-4.0, 4.0)),
     wave_pulse("pulse", color=ACCENT),
     harmonic_decomposition("harmonics", length=6.0, n_terms=5),
     spectral_sum("spectrum",
                  components=[
                      {"amplitude": 1.0, "frequency": 1.0, "phase": 0.0,
                       "color": PRIMARY},
                      {"amplitude": 0.5, "frequency": 3.0, "phase": 0.0,
                       "color": ACCENT},
                      {"amplitude": 0.2, "frequency": 5.0, "phase": 0.0,
                       "color": OK}],
                  x_max=6.0)],
    "I am going to show you one of the most confusing ideas in physics. "
    "Pluck a guitar string. A wave travels from one end to the other. "
    "Now watch a single point on the string. It moves up and down. It "
    "does not travel with the wave. The wave is the pattern. The "
    "medium oscillates in place. When the wave arrives, the point "
    "rises, falls, rises again. When the wave leaves, the point is "
    "back where it started. Nothing has moved except the "
    "disturbance. The wave is the message. The medium is the "
    "messenger."),

# 17 -----------------------------------------------------------------------
chapter(17, "Sound", "ohanian_ch17_doppler",
    "The Whistle That Drops", "Moving sources compress their own waves",
    "Why does a train sound lower after it passes?",
    [r"f'=f_0\frac{v}{v\pm v_s}"],
    [wave_("whistle", 0.9, 2.0, 440.0, (-4.0, 4.0)),
     wave_("shifted", 0.6, 1.6, 550.0, (-4.0, 4.0), color=ACCENT),
     beat_pattern("beats", f1=460.0, f2=440.0, amplitude=0.7,
                  x_range=(0.0, 4.0))],
    "I am going to show you why a passing train drops in pitch. A "
    "whistle sounds at four hundred forty hertz. Approaching, you "
    "hear four sixty. Receding, three forty. Same whistle. Same speed "
    "of sound. The train is a moving source. Moving toward you, it "
    "launches each crest from a closer position. Crests compress. "
    "Shorter wavelength, higher frequency. Moving away, crests "
    "stretch. This is the Doppler shift. Not the sound changing. The "
    "geometry of the source motion."),

# 18 -----------------------------------------------------------------------
chapter(18, "Fluids", "ohanian_ch18_bernoulli",
    "Blow Across a Sheet of Paper",
    "Fast air pushes less. You would have guessed more.",
    "Why does the paper rise?",
    [r"p+\tfrac{1}{2}\rho v^2=\text{constant}"],
    [venturi("venturi", ih=1.6, th=0.8, iv=2.0, dens=1000.0,
             ip=200000.0, center=(0.0, 1.0, 0.0)),
     hydrostatic("tank", dens=1000.0, max_depth=3.0,
                 center=(0.0, -3.0, 0.0)),
     pipe_gauge("gauge", color=ACCENT),
     stream_field("streams",
                  charges=[{"pos": [-1.5, 1.0, 0.0], "charge": 1.0},
                           {"pos": [1.5, 1.0, 0.0], "charge": -1.0}],
                  xr=(-4.0, 4.0), yr=(-1.0, 3.0))],
    "I am going to show you something that contradicts intuition. Hold "
    "a sheet of paper by its edge. Blow across the top. The paper "
    "rises. You expected it to sink, because you are blowing on it. "
    "It rises. Why? Moving air has lower pressure than still air at "
    "the same height. Bernoulli's principle. The reason is energy. A "
    "fast fluid element has more kinetic energy than a slow one. If "
    "nothing pushes energy in, pressure must drop. Pressure plus half "
    "rho v squared plus rho g h is constant along a streamline. Where "
    "speed goes up, pressure goes down. Every atomizer, carburetor, "
    "curveball, and airplane wing leans on this single fact.",
    short=mk_short("ohanian_ch18_bernoulli_short",
        "Faster Water, Lower Pressure", "Continuity plus Bernoulli",
        "Water speeds up in a pipe. Does the pressure rise or fall?",
        ("2 m/s", "5 m/s", "10 m/s", "12 m/s"),
        "Correct Answer: (C)",
        [r"p_1 + \tfrac{1}{2}\rho v_1^2 = p_2 + \tfrac{1}{2}\rho v_2^2"],
        [venturi("v", ih=1.6, th=0.8, iv=2.0, dens=1000.0,
                 ip=200000.0, center=(0.0, 0.0, 0.0)),
         numerical_chain("chain",
                         steps=[r"p_1 + \tfrac{1}{2}\rho v_1^2 = "
                                r"p_2 + \tfrac{1}{2}\rho v_2^2",
                                r"2 \times 10^5 + 2000 = "
                                r"1.5 \times 10^5 + 500 v_2^2",
                                r"v_2 \approx 10.2\ \text{m/s}"],
                         pos=(0.0, -3.0, 0.0))],
        "Water in a horizontal pipe. Point one. Pressure two times ten "
        "to the fifth. Speed two. Point two. Pressure one point five "
        "times ten to the fifth. Speed? Bernoulli. Solve for v two. "
        "About ten point two. Answer C.")),

# 19 -----------------------------------------------------------------------
chapter(19, "Kinetic Theory", "ohanian_ch19_gas",
    "The Speed of Molecules", "Temperature is average kinetic energy",
    "What does it mean for a gas to be hot?",
    [r"\tfrac{3}{2}k_BT = \tfrac{1}{2}mv_{rms}^2"],
    [gas("gas", count=80, box=(5.0, 3.5)),
     sim("two_molecules",
         bodies=[body(1.0, (-1.0, 1.0), (0.5, 0.3), label="H2",
                      color=PRIMARY),
                 body(16.0, (1.5, -0.5), (-0.15, -0.1), label="O2",
                      color=ACCENT)],
         forces=[{"type": "linear_drag", "coefficient": 0.0}],
         duration=5.0, playback=4.0),
     exponential_atmosphere("atmo", num_particles=30, height=3.0,
                            scale_height=1.0)],
    "I am going to show you what temperature actually is. Not a number "
    "on a dial. Molecules. Billions of them, in a box, moving in every "
    "direction, bouncing off each other and the walls. Each has a "
    "mass and a speed. The average of one half m v squared is the "
    "kinetic energy. Multiply by two thirds and you get k B T. "
    "Temperature is a measure of average kinetic energy. Nothing "
    "more. Double the temperature, the average kinetic energy "
    "doubles. This is why hydrogen escapes from Earth's atmosphere "
    "and oxygen does not.",
    short=mk_short("ohanian_ch19_rms",
        "Hot Light Molecules", "rms speed scales as √T / √m",
        "H2 at 30 C has a certain rms speed. At what T does O2 match?",
        ("300 K", "750 K", "4800 K", "5500 K"),
        "Correct Answer: (C)", [r"v_{rms}=\sqrt{3RT/M}"],
        [gas("gas", count=60, box=(6.0, 3.5)),
         numerical_chain("chain",
                         steps=[r"T_H / m_H = T_O / m_O",
                                r"m_O / m_H = 16",
                                r"T_O = 16 \times 303 = 4850\ \text{K}"],
                         pos=(0.0, -2.5, 0.0))],
        "Hydrogen at thirty Celsius. At what temperature does oxygen "
        "match its rms speed? RMS speed goes as root T over m. Set "
        "them equal. T_H over m_H equals T_O over m_O. Hydrogen is "
        "two, oxygen is thirty two. Ratio sixteen. Oxygen needs "
        "sixteen times the temperature. Three hundred three times "
        "sixteen. About four thousand eight hundred. Answer C.")),

# 20 -----------------------------------------------------------------------
chapter(20, "Heat", "ohanian_ch20_latent",
    "The Missing Calorie", "Phase changes absorb energy without heating",
    "Why does boiling water stay at 100 C?",
    [r"Q=mc\Delta T", r"Q=mL_f"],
    [heat_flow("flow"),
     number_line("energy", (0.0, 100.0), (0.0, 20.0, 60.0, 100.0)),
     phase_portrait("phase", amplitude=1.0, gamma=0.0, omega=1.0)],
    "I am going to show you where the extra heat goes. A pot of water "
    "on the stove. At first, temperature rises. At one hundred "
    "Celsius, something strange. You keep adding heat. Temperature "
    "stops rising. Water boils. All the energy goes into breaking "
    "bonds between molecules, not into their kinetic energy. This is "
    "a phase change. The energy per kilogram is the latent heat of "
    "vaporization. When steam condenses, the same energy is released. "
    "This is why steam burns are worse than hot water burns."),

# 21 -----------------------------------------------------------------------
chapter(21, "Thermodynamics", "ohanian_ch21_entropy",
    "Why You Cannot Unstir Coffee", "Entropy counts arrangements",
    "Why does heat flow one way and never the other?",
    [r"S=k_B\ln W", r"\Delta S\geq 0"],
    [pv_tracker("cycle"),
     random_walk("walk", color=ACCENT),
     color_triangle("ct")],
    "I am going to show you why you cannot un-stir coffee. A drop of "
    "ink in water. Stir. It spreads. It stays spread. Now try to "
    "gather all the ink back into one corner. You cannot. Not because "
    "mechanics forbids it. Every collision between ink and water is "
    "reversible. But the number of ways to arrange the ink molecules "
    "in one corner is astronomically smaller than the number of ways "
    "to spread them out. The system evolves toward more arrangements. "
    "This is entropy. The second law says that in an isolated system, "
    "entropy never decreases. Not because reversal is forbidden. "
    "Because it is so improbable you would need longer than the age "
    "of the universe to see it."),

# 22 -----------------------------------------------------------------------
chapter(22, "Electric Force", "ohanian_ch22_coulomb",
    "The Battle of Two Forces", "Coulomb beats gravity by 10^39",
    "Why does electricity dominate atoms but not the cosmos?",
    [r"F=\frac{kq_1q_2}{r^2}"],
    [e_field("pair",
             charges=[{"position": [-2.0, 0.0, 0.0], "charge": 1.0},
                      {"position": [2.0, 0.0, 0.0], "charge": -1.0}]),
     polar_pattern("lobe", pattern="dipole", radius_max=2.0),
     text_("note", "inverse square, both forces")],
    "I am going to show you the greatest mismatch in physics. Electron "
    "and proton. Compare electric to gravitational. Both follow "
    "inverse square laws. The ratio is independent of distance. Plug "
    "in. Electric wins by two point three times ten to the thirty "
    "nine. That is two thousand billion billion billion billion. And "
    "yet gravity runs the universe. How? Because positive and "
    "negative charges cancel. On the scale of a planet, of a galaxy, "
    "net charge is essentially zero. Gravity has no such "
    "cancellation. Mass always attracts. Over astronomical "
    "distances, gravity is all that remains.",
    short=mk_short("ohanian_ch22_ratio",
        "Which Force Wins?", "Coulomb beats gravity by 10^39",
        "Ratio of electric to gravitational force between e and p?",
        ("10^10", "10^20", "2.3 x 10^39", "10^50"),
        "Correct Answer: (C)",
        [r"F_E/F_G = ke^2/(Gm_em_p)"],
        [e_field("pair",
                 charges=[{"position": [-2.0, 0.0, 0.0], "charge": 1.0},
                          {"position": [2.0, 0.0, 0.0], "charge": -1.0}],
                 xr=(-4.0, 4.0), yr=(-3.0, 3.0),
                 cols=9, rows=7),
         numerical_chain("chain",
                         steps=[r"k e^2 = 2.3 \times 10^{-28}",
                                r"G m_e m_p = 1.0 \times 10^{-67}",
                                r"\text{ratio} = 2.3 \times 10^{39}"],
                         pos=(0.0, -3.0, 0.0))],
        "Ratio of electric to gravitational force between an electron "
        "and a proton. Both inverse square. r cancels. k e squared "
        "over G m e m p. Plug in. Two point three times ten to the "
        "thirty nine. Answer C. And yet gravity runs the cosmos, "
        "because charges cancel and masses do not.")),

# 23 -----------------------------------------------------------------------
chapter(23, "Electric Field", "ohanian_ch23_field",
    "The Field Is the Messenger",
    "Action at a distance becomes local action",
    "How does one charge know another is nearby?",
    [r"E=\frac{F}{q}", r"E=\frac{kQ}{r^2}"],
    [e_field("dipole",
             charges=[{"position": [-1.5, 0.0, 0.0], "charge": 2.0},
                      {"position": [1.5, 0.0, 0.0], "charge": -2.0}],
             xr=(-4.0, 4.0), yr=(-3.5, 3.5),
             cols=11, rows=9),
     field_by_opacity("lines",
                      sources=[[-1.5, 0.0, 0.0], [1.5, 0.0, 0.0]],
                      wavelength=0.6, omega=1.5, density=10,
                      width=6.0, height=4.0),
     warning_box("warn",
                 "Field lines start on + and end on −. "
                 "They never cross.")],
    "I am going to show you how one charge knows another is nearby. It "
    "cannot see. It cannot shout. Yet bring two positive charges "
    "close and they repel, instantly. Newton hated this. He called it "
    "the greatest absurdity in physics. Faraday found a way out. "
    "Instead of saying one charge reaches across space and pulls on "
    "another, say that each charge creates something in the space "
    "around it. That something is the electric field. Every point in "
    "space has a field vector. A second charge placed there responds "
    "locally to the field at its own location. Action at a distance "
    "becomes two local events, connected by a messenger."),

# 24 -----------------------------------------------------------------------
chapter(24, "Gauss' Law", "ohanian_ch24_gauss",
    "Why You Are Safe Inside",
    "The field cannot penetrate a conductor",
    "Why is the field zero inside a metal box?",
    [r"\oint \vec{E}\cdot d\vec{A} = Q/\epsilon_0"],
    [e_field("uniform",
             charges=[{"position": [-3.0, 0.0, 0.0], "charge": 5.0},
                      {"position": [3.0, 0.0, 0.0], "charge": 5.0}],
             xr=(-4.0, 4.0), yr=(-3.5, 3.5),
             cols=11, rows=9),
     geo_circle("surface", (0.0, 0.0), 1.5, color=ACCENT, opacity=0.10),
     stream_field("streams",
                  charges=[{"pos": [-3.0, 0.0, 0.0], "charge": 5.0},
                           {"pos": [3.0, 0.0, 0.0], "charge": 5.0}],
                  xr=(-4.0, 4.0), yr=(-3.0, 3.0))],
    "I am going to show you why you are safe in a metal box. Sit "
    "inside. The box is in a strong electric field. What happens "
    "inside? Nothing. The field is zero. Here is why. Electrons in a "
    "metal are free to move. If there were a field inside, they would "
    "feel a force and move. But in a steady state nothing is "
    "happening. So they rearrange on the surface until they cancel "
    "the external field at every interior point. The field inside is "
    "zero. All charge ends up on the surface. This one result, "
    "falling straight out of Gauss's law, explains why a car protects "
    "you from lightning, why a Faraday cage shields electronics, and "
    "why a sharp point on a conductor has a stronger field than a "
    "smooth surface."),

# 25 -----------------------------------------------------------------------
chapter(25, "Potential", "ohanian_ch25_potential",
    "The Work to Bring a Charge Home",
    "Potential is energy per unit charge",
    "What does a volt actually measure?",
    [r"V=\frac{kQ}{r}", r"V=\frac{U}{q}"],
    [landscape("well", "1/x", (0.4, 3.5), (0.0, 4.0), color=PRIMARY),
     calculus_graph("gradient", "1/x", (0.4, 3.5), (0.0, 4.0),
                    xl=5.0, yl=2.5, ctr=(0.0, -3.0, 0.0))],
    "I am going to show you what a volt actually is. Not a force. Not "
    "a field. Energy per unit charge. The work you would do to bring "
    "a positive test charge from infinity to some point, divided by "
    "the charge. The field tells you the force at each point. The "
    "potential tells you the energy. The two are related. The field "
    "is the gradient of the potential. Steep slope, strong field. "
    "Flat region, weak field. This is why potential is so useful. It "
    "is a scalar. One number per point, not three. Conceptually, it "
    "maps the energy landscape."),

# 26 -----------------------------------------------------------------------
chapter(26, "Electric Energy", "ohanian_ch26_energy",
    "The Cost of Assembly",
    "Charges repel, so assembling them costs energy",
    "Where does the energy of a charged conductor go?",
    [r"U=\tfrac{1}{2}QV"],
    [e_field("sphere",
             charges=[{"position": [0.0, 0.0, 0.0], "charge": 1.0}],
             xr=(-4.0, 4.0), yr=(-3.5, 3.5),
             cols=11, rows=11),
     field_by_opacity("shell",
                      sources=[[0.0, 0.0, 0.0]],
                      wavelength=0.6, omega=1.5, density=12,
                      width=6.0, height=6.0)],
    "I am going to show you where the energy goes when you charge a "
    "sphere. You brought charges in from infinity, one by one. Each "
    "had to be pushed against the repulsion of the charges already "
    "there. Total work equals energy stored. One half Q V. Where is "
    "this energy? Two answers, both correct. You can say it is stored "
    "in the charge distribution. Or you can say it is stored in the "
    "electric field the charges produce. The energy density of an "
    "electric field is one half epsilon zero E squared. Integrate "
    "over all space. Same answer. This is the seed of field theory."),

# 27 -----------------------------------------------------------------------
chapter(27, "Capacitors", "ohanian_ch27_dielectric",
    "Slide Plastic Into a Capacitor",
    "Dielectrics weaken the field",
    "Why does a dielectric reduce the electric field?",
    [r"E=E_{free}/\kappa", r"C=\kappa C_0"],
    [e_field("plates",
             charges=[{"position": [-2.5, 0.0, 0.0], "charge": 3.0},
                      {"position": [2.5, 0.0, 0.0], "charge": -3.0}],
             xr=(-4.0, 4.0), yr=(-3.5, 3.5),
             cols=11, rows=11),
     polar_pattern("dipole_align", pattern="dipole", radius_max=1.5),
     warning_box("warn", "Bound surface charge opposes the free field.")],
    "I am going to show you how plastic can weaken an electric field. "
    "Charge a capacitor. Disconnect the battery. The plates hold their "
    "charge. Slide a slab of plastic between them. The field shrinks. "
    "Not by a little. By a factor of three for ordinary plastic. By "
    "thousands for certain ceramics. Where does the field go? It gets "
    "cancelled by the plastic itself. Every molecule inside is either "
    "a permanent dipole or becomes one when placed in the field. The "
    "dipoles align. They create bound surface charge on the slab. "
    "That bound charge produces a field opposing the original. Net "
    "field weaker."),

# 28 -----------------------------------------------------------------------
chapter(28, "Currents", "ohanian_ch28_drift",
    "The Slowest Fast Thing",
    "Electrons drift at millimetres per second",
    "Why does the light come on instantly?",
    [r"I=neAv_d", r"V=IR"],
    [sim("drift",
         bodies=[body(1.0, (-3.0, 0.0), (0.4, 0.0), label="e-",
                      color=PRIMARY)],
         forces=[{"type": "linear_drag", "coefficient": 0.8}],
         duration=6.0, playback=4.0),
     live_label("vd", var_fn="0.00014", fmt="v_d = {v:.2e} m/s",
                pos=(3.0, 1.5, 0.0))],
    "I am going to show you the slowest fast thing in physics. A copper "
    "wire carries current. Electrons flow. How fast? You would guess "
    "near the speed of light. Wrong. Drift velocity in a copper wire "
    "at ordinary currents is about zero point one millimetre per "
    "second. Slower than a snail. Yet when you flip the switch, the "
    "light comes on instantly. How? The electric field travels. The "
    "signal moves at nearly the speed of light, pushing all the "
    "electrons along at once. The electrons crawl. The field "
    "orchestrates them.",
    short=mk_short("ohanian_ch28_drift_short",
        "Drift Velocity in Copper", "Slow carriers, fast signal",
        "A 0.5 cm2 copper bar carries 98 A. Electron drift velocity?",
        ("1.4 x 10^-4 m/s", "1.4 mm/s", "1.4 m/s", "1400 m/s"),
        "Correct Answer: (A)", [r"I = neAv_d"],
        [number_line("speed", (-6.0, 0.0), (-3.85,)),
         numerical_chain("chain",
                         steps=[r"I = n e A v_d",
                                r"n = 8.5 \times 10^{28}",
                                r"v_d = 1.4 \times 10^{-4}\ \text{m/s}"],
                         pos=(0.0, -3.0, 0.0))],
        "Copper bar, half a square centimeter, ninety eight amperes. "
        "How fast do electrons drift? Current equals n e A v d. "
        "Rearrange. n for copper, eight point five times ten to the "
        "twenty eight per cubic meter. Plug in. v d is one point four "
        "times ten to the minus four meters per second. Answer A. A "
        "snail moves faster. Yet the light comes on instantly, because "
        "the field propagates at c.")),

# 29 -----------------------------------------------------------------------
chapter(29, "DC Circuits", "ohanian_ch29_kirchhoff",
    "Where the Electrons Go",
    "Charge and energy bookkeeping",
    "How do you solve a circuit with more than one loop?",
    [r"\sum I_{in}=\sum I_{out}", r"\sum V_{loop}=0"],
    [geo_polyline("loop", [(-3.0, -2.0), (3.0, -2.0),
                            (3.0, 2.0), (0.0, 2.0),
                            (0.0, -2.0), (-3.0, -2.0)],
                  color=PRIMARY, stroke=3.0),
     geo_polyline("branch", [(-3.0, -2.0), (-3.0, 2.0)],
                  color=ACCENT, stroke=2.0),
     la_solve("solve",
              matrix=[[2.0, -1.0], [-1.0, 3.0]],
              rhs=[5.0, 2.0],
              center=(0.0, -5.0, 0.0))],
    "I am going to show you how to solve any circuit. Multiple "
    "resistors, multiple batteries. What is the current in each "
    "branch? There is a systematic way. Kirchhoff's rules. Two "
    "statements. Charge is conserved. At every junction, current in "
    "equals current out. Energy is conserved. Around any closed loop, "
    "voltage gains minus drops equals zero. Two rules. That is all. "
    "Apply them systematically. Label unknown currents. Choose "
    "directions. One equation per junction. One per independent loop. "
    "Solve. If a current comes out negative, your guess was wrong. No "
    "harm. The magnitude is correct, the direction reversed."),

# 30 -----------------------------------------------------------------------
chapter(30, "Magnetic Force", "ohanian_ch30_relativity",
    "Magnetism Is Electricity in Disguise",
    "Special relativity explains magnetic force",
    "Why do parallel currents attract?",
    [r"F_m=\mu_0\epsilon_0 v^2 F_e", r"\mu_0\epsilon_0 c^2=1"],
    [m_field("wires",
             wires=[{"start": [-3.5, 1.5, 0.0],
                     "end": [3.5, 1.5, 0.0], "current": 5.0},
                    {"start": [-3.5, -1.5, 0.0],
                     "end": [3.5, -1.5, 0.0], "current": 5.0}],
             xr=(-4.0, 4.0), yr=(-3.5, 3.5),
             cols=11, rows=9),
     compass_grid("compass", color=ACCENT),
     induction_coil("coil", color=OK)],
    "I am going to show you that magnetism is not a separate force. Two "
    "wires carry current the same direction. They attract. But both "
    "contain moving electrons, and like charges repel. So why do the "
    "wires pull together? Take the rest frame of the electrons in one "
    "wire. From that frame, the other wire is not neutral. The "
    "positive ions are moving backward, and length contraction packs "
    "them closer. The electrons in the other wire are moving at a "
    "different speed, so their spacing changes by a different "
    "amount. Net effect. Charge imbalance. Electric field. "
    "Attraction. Magnetism is electricity viewed from a moving frame.",
    short=mk_short("ohanian_ch30_field_wire",
        "Field Around a Wire", "Ampere's law in one line",
        "What is B at 0.50 m from a long straight wire carrying 5 A?",
        ("1.0 x 10^-6 T", "2.0 x 10^-6 T", "5.0 x 10^-6 T",
         "1.0 x 10^-5 T"),
        "Correct Answer: (B)", [r"B = \mu_0 I / (2\pi r)"],
        [m_field("wire",
                 wires=[{"start": [-3.0, 0.0, 0.0],
                         "end": [3.0, 0.0, 0.0], "current": 5.0}],
                 xr=(-4.0, 4.0), yr=(-3.0, 3.0),
                 cols=11, rows=9),
         numerical_chain("chain",
                         steps=[r"B = \mu_0 I / (2\pi r)",
                                r"\mu_0 = 1.256 \times 10^{-6}",
                                r"B = 2.0 \times 10^{-6}\ \text{T}"],
                         pos=(0.0, -3.0, 0.0))],
        "Wire carries five amps. What is B half a meter away? B equals "
        "mu zero I over two pi r. mu zero is one point two five six "
        "times ten to the minus six. Times five. Over two pi times "
        "zero point five. That is two times ten to the minus six "
        "tesla. Answer B.")),

# 31 -----------------------------------------------------------------------
chapter(31, "Ampere's Law", "ohanian_ch31_ampere",
    "The Field Around a Wire", "Ampere is Gauss in a circle",
    "How do you compute a field without integrating?",
    [r"\oint \vec{B}\cdot d\vec{l} = \mu_0 I"],
    [m_field("wire",
             wires=[{"start": [-3.5, 0.0, 0.0],
                     "end": [3.5, 0.0, 0.0], "current": 8.0}],
             xr=(-4.0, 4.0), yr=(-3.5, 3.5),
             cols=11, rows=9),
     geo_circle("loop", (0.0, 0.0), 1.5, color=ACCENT),
     stream_field("streams",
                  charges=[{"pos": [0.0, 0.0, 0.0], "charge": 1.0}],
                  xr=(-3.0, 3.0), yr=(-3.0, 3.0))],
    "I am going to show you a shortcut that saves you an integral. "
    "Current through a wire. Magnetic field around it. You could use "
    "the Biot-Savart law. Tedious. Or Ampere's law. The line integral "
    "of B around a closed loop equals mu zero times the current "
    "enclosed. Pick a loop matching the symmetry. For a long straight "
    "wire, a circle. The field is constant on the circle and tangent. "
    "The line integral is B times two pi r. Set it equal to mu zero "
    "I. Solve. B equals mu zero I over two pi r."),

# 32 -----------------------------------------------------------------------
chapter(32, "Induction", "ohanian_ch32_lenz",
    "Nature Fights Every Change", "Lenz's law is energy conservation",
    "Why does an induced current oppose its cause?",
    [r"\mathcal{E} = -d\Phi_B/dt"],
    [induction_coil("coil"),
     m_field("moving",
             wires=[{"start": [-1.0, 0.0, 0.0],
                     "end": [1.0, 0.0, 0.0], "current": 3.0}],
             xr=(-4.0, 4.0), yr=(-3.0, 3.0),
             cols=11, rows=9, color=PRIMARY),
     warning_box("warn", "Oppose the change — or energy is not conserved.")],
    "I am going to show you that Lenz's law is not a rule to memorize. "
    "It is energy conservation in disguise. Move a magnet toward a "
    "coil. Current flows. Pull it away. Current the other way. In "
    "both cases the current opposes the change. Why? Suppose the "
    "opposite. Then pushing the magnet in would pull it faster, "
    "inducing more current, pulling harder. Runaway. Energy from "
    "nothing. Lenz says no. The universe resists change."),

# 33 -----------------------------------------------------------------------
chapter(33, "Magnetic Materials", "ohanian_ch33_domains",
    "The Domains Inside Iron",
    "Tiny aligned patches flip and grow",
    "Why does iron stick to a magnet?",
    [r"\vec{B}=\mu_0(\vec{H}+\vec{M})"],
    [compass_grid("grid", color=ACCENT),
     crystal("lattice", color=ACCENT),
     polar_pattern("domain", pattern="dipole", radius_max=1.0)],
    "I am going to show you why iron sticks and copper does not. Inside "
    "iron there are domains. Tiny regions where all the atomic "
    "magnetic moments are aligned. In the absence of an external "
    "field, they point in random directions. Net magnetization zero. "
    "Bring a magnet close. The domains that happen to align with the "
    "field grow. Their neighbors flip and join. Suddenly huge swaths "
    "of the iron are aligned. Iron becomes a magnet. Above the Curie "
    "temperature, thermal motion destroys the domains."),

# 34 -----------------------------------------------------------------------
chapter(34, "AC Circuits", "ohanian_ch34_resonance",
    "The Frequency That Selects",
    "Resonance picks one signal from a crowd",
    "Why does a radio tune to a single station?",
    [r"Z=\sqrt{R^2+(X_L-X_C)^2}", r"\omega_0=1/\sqrt{LC}"],
    [em_wave("wave", amp=1.0, freq=1.0, speed=2.0, length=5.0),
     spectral_sum("peak",
                  components=[
                      {"amplitude": 0.2, "frequency": 0.7, "phase": 0.0,
                       "color": NEUTRAL},
                      {"amplitude": 1.0, "frequency": 1.0, "phase": 0.0,
                       "color": PRIMARY},
                      {"amplitude": 0.2, "frequency": 1.4, "phase": 0.0,
                       "color": NEUTRAL}],
                  x_max=6.0),
     text_("note", "peak at resonance")],
    "I am going to show you how your radio picks one station out of "
    "hundreds. Resonance. Your radio contains an inductor and a "
    "capacitor in series. Together they form a circuit with a natural "
    "frequency. Change the capacitor. You tune the natural frequency. "
    "Signals at that frequency drive the circuit hard. Signals at "
    "other frequencies barely move it. The circuit selects.",
    short=mk_short("ohanian_ch34_lc",
        "The Natural Frequency", "LC circuit oscillates at w0 = 1/sqrt(LC)",
        "An LC circuit has L = 1 mH, C = 1 nF. What is f0?",
        ("1.6 kHz", "16 kHz", "160 kHz", "1.6 MHz"),
        "Correct Answer: (C)", [r"f_0 = 1/(2\pi\sqrt{LC})"],
        [em_wave("wave", amp=1.0, freq=2.0, speed=2.0, length=5.0),
         numerical_chain("chain",
                         steps=[r"LC = 10^{-12}",
                                r"\sqrt{LC} = 10^{-6}",
                                r"f_0 = 1 / (2\pi \times 10^{-6})",
                                r"f_0 \approx 160\ \text{kHz}"],
                         pos=(0.0, -3.0, 0.0))],
        "An LC circuit. L is one millihenry. C is one nanofarad. "
        "Natural frequency? f zero equals one over two pi root L C. "
        "L times C is ten to the minus twelve. Root is ten to the "
        "minus six. So f zero is one over two pi times ten to the "
        "minus six. That is about one hundred sixty kilohertz. "
        "Answer C.")),

# 35 -----------------------------------------------------------------------
chapter(35, "Maxwell", "ohanian_ch35_maxwell",
    "The Four Equations", "All of electromagnetism in four lines",
    "What did Maxwell add to make the theory complete?",
    [r"\oint \vec{E}\cdot d\vec{A} = Q/\epsilon_0",
     r"\oint \vec{B}\cdot d\vec{A} = 0",
     r"\oint \vec{E}\cdot d\vec{l} = -d\Phi_B/dt",
     r"\oint \vec{B}\cdot d\vec{l} = \mu_0 I + \mu_0\epsilon_0 d\Phi_E/dt"],
    [em_wave("wave", amp=1.0, freq=1.0, speed=2.0, length=5.0),
     equation_morph("eqs",
                    steps=[r"\nabla \cdot \vec{E} = \rho/\epsilon_0",
                           r"\nabla \cdot \vec{B} = 0",
                           r"\nabla \times \vec{E} = -\partial_t \vec{B}",
                           r"\nabla \times \vec{B} = \mu_0 \vec{J} "
                           r"+ \mu_0 \epsilon_0 \partial_t \vec{E}"],
                    pos=(0.0, -4.0, 0.0), font_size=20),
     quiz_frame("quiz",
                question="What does Maxwell's added term predict?",
                options=["Static fields",
                         "Electromagnetic waves",
                         "Magnetic monopoles",
                         "Gravity waves"],
                correct=1, pause=3.0)],
    "I am going to show you all of electricity and magnetism in four "
    "lines. Gauss's law. No magnetic monopoles. Faraday's law. "
    "Ampere's law with Maxwell's addition. Together they describe "
    "every electromagnetic phenomenon in the universe. Maxwell's "
    "contribution was the fourth term. Without it, the equations were "
    "inconsistent. With it, they predict waves of electric and "
    "magnetic fields, propagating at c equals one over the square "
    "root of mu zero epsilon zero. That number came out to three "
    "times ten to the eighth meters per second. The speed of light. "
    "Maxwell realized light is an electromagnetic wave."),

# 36 -----------------------------------------------------------------------
chapter(36, "Light and Radio Waves", "ohanian_ch36_pressure",
    "Light Pushes", "Photons carry momentum",
    "How does sunlight exert force?",
    [r"p=E/c", r"S=EB/\mu_0"],
    [em_wave("wave", amp=1.0, freq=1.0, speed=2.0, length=5.0),
     energy_bar("radiation", pos=(0.0, -3.0, 0.0), fill=0.8,
                label="S", width=4.0, color=ACCENT)],
    "I am going to show you that light pushes. Light carries energy. "
    "Does it carry momentum? Yes. Every photon has momentum equal to "
    "its energy over c. Shine a laser on a mirror. The mirror is "
    "pushed. Radiation pressure. Not a curiosity. A measurable force. "
    "Sunlight delivers about one thousand three hundred fifty watts "
    "per square meter at Earth's orbit. Pressure, four point five "
    "microPascals. Tiny. But the Earth intercepts a disk of radius "
    "six thousand four hundred kilometers. Total outward force, five "
    "hundred eighty million newtons."),

# 37 -----------------------------------------------------------------------
chapter(37, "Reflection and Refraction", "ohanian_ch37_snell",
    "The Bent Straw", "Light slows down in glass and bends",
    "Why does a straw look broken in a glass of water?",
    [r"n_1\sin\theta_1 = n_2\sin\theta_2"],
    [sliced_wave("refract", interface_origin=(0.0, 1.0, 0.0),
                 index=1.5, c=2.0, frequency=0.3, amplitude=1.0),
     geo_polyline("ray_in", [(-2.5, 2.5), (0.0, 0.0)]),
     geo_polyline("ray_out", [(0.0, 0.0), (1.8, -1.5)], color=ACCENT),
     geo_polyline("normal", [(0.0, -2.0), (0.0, 2.0)], color=NEUTRAL,
                  stroke=1.5)],
    "I am going to show you why a straw looks broken in a glass of "
    "water. Light slows down when it enters water. Or glass. Or any "
    "transparent medium. The speed of light in a medium is c over n. "
    "When light crosses a boundary at an angle, the change in speed "
    "bends the ray. Snell's law. Into a denser medium, the ray bends "
    "toward the normal. Out of one, away. Every lens, every camera, "
    "every telescope depends on this single fact."),

# 38 -----------------------------------------------------------------------
chapter(38, "Mirrors and Lenses", "ohanian_ch38_optics",
    "Why Sign Conventions Make You Cry",
    "Draw the diagram first",
    "Why do mirrors and lenses use opposite sign rules?",
    [r"1/s + 1/s' = 1/f"],
    [geo_polyline("axis", [(-4.0, 0.0), (4.0, 0.0)], color=NEUTRAL,
                  stroke=1.5),
     geo_polyline("ray_in", [(-3.0, 1.5), (0.0, 0.0)], color=ACCENT),
     geo_polyline("ray_out", [(0.0, 0.0), (3.0, 1.0)], color=OK),
     geo_polyline("ray_through", [(0.0, 0.0), (3.0, -1.5)],
                  color=PRIMARY),
     equation_morph("eq",
                    steps=[r"1/s + 1/s' = 1/f",
                           r"\text{mirror: } f > 0 \text{ if concave}",
                           r"\text{lens: } f > 0 \text{ if convex}"],
                    pos=(0.0, -3.0, 0.0), font_size=22)],
    "I am going to show you why students hate optics. Sign "
    "conventions. For mirrors, focal length is positive if concave. "
    "For lenses, positive if convex. Why? Because mirrors and lenses "
    "use the same equation to describe different geometry. The mirror "
    "equation is one over s plus one over s prime equals one over f. "
    "But do not memorize the table. Draw a ray diagram first. Trace "
    "the light. Where rays converge is a real image. Where they "
    "appear to come from is a virtual image. The signs follow the "
    "diagram."),

# 39 -----------------------------------------------------------------------
chapter(39, "Interference", "ohanian_ch39_film",
    "Why Soap Bubbles Shine",
    "Two reflections and a phase flip",
    "What makes the colours on a soap bubble?",
    [r"2d=m\lambda"],
    [interference("fringes"),
     two_beam("split"),
     two_path_interference("paths",
                           start=(-2.0, 0.0, 0.0),
                           end_a=(2.0, 0.5, 0.0),
                           end_b=(2.0, -0.5, 0.0))],
    "I am going to show you where the colours on a soap bubble come "
    "from. A thin film of water between two layers of air. Sunlight "
    "hits it. Some light reflects off the outer surface. Some passes "
    "through and reflects off the inner surface. The two reflected "
    "rays interfere. In phase, bright colour. Out of phase, that "
    "colour is missing. What sets the phase? Two things. The extra "
    "path the inner ray travels is twice the film thickness. And a "
    "phase flip happens when light reflects off a boundary where the "
    "index increases."),

# 40 -----------------------------------------------------------------------
chapter(40, "Diffraction", "ohanian_ch40_limit",
    "Why Stars Blur", "Diffraction limits every telescope",
    "Why is there a limit to how sharp a telescope can see?",
    [r"\theta=1.22\lambda/D"],
    [interference("fringes", color=ACCENT),
     two_beam("split"),
     geo_circle("aperture", (0.0, 0.0), 1.8, color=PRIMARY, opacity=0.08),
     two_source("sources",
                source_a=(-1.0, 0.5, 0.0),
                source_b=(1.0, -0.5, 0.0),
                wavelength=0.5, speed=1.5, max_radius=4.0)],
    "I am going to show you why every telescope has a limit. Point a "
    "telescope at a distant star. It should look like a bright dot. "
    "It does not. It looks like a small disk with faint rings around "
    "it. Diffraction. When light passes through a circular opening it "
    "spreads. The spread depends on wavelength and on the diameter of "
    "the opening. Bigger opening, tighter spread. Shorter wavelength, "
    "tighter spread. But it never reaches zero. For a twelve "
    "centimeter lens and visible light, the minimum resolvable angle "
    "is about one arcsecond."),

# 41 -----------------------------------------------------------------------
chapter(41, "Special Relativity", "ohanian_ch41_dilation",
    "The Proton That Shortcuts Spacetime",
    "Time dilates at high speed",
    "Why do fast clocks run slow?",
    [r"\Delta t' = \Delta t\sqrt{1-v^2/c^2}"],
    [accretion("galaxy"),
     orbit("guide", radius=3.0, color=ACCENT),
     grid_warp("warp", mass=1.5, mass_pos=(0.0, 3.0, 0.0),
               divisions=16),
     taylor_expand("series", "1/sqrt(1-x**2)", (-0.8, 0.8),
                   max_terms=5, term_time=0.7),
     text_("note", "gamma ~ 316")],
    "I am going to show you how a proton crosses the galaxy in under "
    "five hundred years. It travels at zero point nine nine nine nine "
    "nine c. The galaxy is one hundred thousand light years across. "
    "How much time on the proton's own clock? Not one hundred "
    "thousand years. Four hundred fifty. The Lorentz factor for that "
    "speed is three hundred sixteen. Proper time equals coordinate "
    "time divided by gamma. From the proton's point of view, the "
    "galaxy is contracted.",
    short=mk_short("ohanian_ch41_dilation_short",
        "A Proton Crosses the Galaxy",
        "Time dilation at high speed",
        "Proton at 0.99999c crosses a 10^5 ly galaxy. Proper time?",
        ("450 years", "100000 years", "1000 years", "2.2 years"),
        "Correct Answer: (A)",
        [r"\Delta t' = \Delta t\sqrt{1-v^2/c^2}"],
        [orbit("galaxy", 3.0),
         text_("note", "gamma ~ 316"),
         numerical_chain("chain",
                         steps=[r"\gamma \approx 316",
                                r"\Delta t' = \Delta t / \gamma",
                                r"\Delta t' = 10^5 / 316 \approx 450\ "
                                r"\text{yr}"],
                         pos=(0.0, -3.0, 0.0))],
        "A proton at zero point nine nine nine nine nine c crosses the "
        "Milky Way. One hundred thousand light years in the galaxy's "
        "frame. How much time on the proton's clock? Lorentz factor "
        "roughly three hundred sixteen. Proper time equals coordinate "
        "time divided by gamma. About four hundred fifty years. "
        "Answer A.")),

# 42 -----------------------------------------------------------------------
chapter(42, "Quanta of Light", "ohanian_ch42_photon",
    "The Threshold Wavelength", "Light comes in packets",
    "Why can red light not eject electrons from potassium?",
    [r"E=hf", r"K=hf-\phi"],
    [wave_packet("packet"),
     wave_("wave", 0.8, 2.0, 3.0, (-4.0, 4.0), color=ACCENT),
     warning_box("warn", "Brightness does not matter. Only frequency does.")],
    "I am going to show you why red light cannot eject electrons from "
    "potassium. Shine light on a metal surface. Electrons pop out. "
    "Classical physics says brighter light should give faster "
    "electrons. Wrong. Brighter light gives more electrons. Their "
    "speed stays the same. And if the frequency is too low, no "
    "electrons come out at all, no matter how bright. Einstein "
    "explained this in 1905. Light comes in packets. Photons.",
    short=mk_short("ohanian_ch42_threshold",
        "The Threshold Wavelength", "Below it, nothing",
        "Potassium work function 2.0 eV. Threshold wavelength?",
        ("624 nm", "400 nm", "250 nm", "900 nm"),
        "Correct Answer: (A)", [r"\lambda = hc/\phi"],
        [wave_pulse("packet"),
         numerical_chain("chain",
                         steps=[r"\lambda_0 = hc / \phi",
                                r"hc = 1240\ \text{eV·nm}",
                                r"\lambda_0 = 1240 / 2.0 = 620\ "
                                r"\text{nm}"],
                         pos=(0.0, -3.0, 0.0))],
        "Potassium has a work function of two electron volts. Longest "
        "wavelength that can eject an electron? At threshold, photon "
        "energy equals work function. h c over lambda equals phi. "
        "Solve. Six point two four times ten to the minus seven "
        "meters. Answer A, six hundred twenty four nanometres. Deep "
        "red.")),

# 43 -----------------------------------------------------------------------
chapter(43, "Atomic Structure", "ohanian_ch43_bohr",
    "The Bohr Ladder", "Energy levels are quantized",
    "Why do atoms emit only certain colours?",
    [r"E_n=-13.6/n^2\ \text{eV}"],
    [bohr("orbit"),
     number_line("ladder", (-15.0, 0.0), (-13.6, -3.4, -1.5, -0.85)),
     quiz_frame("quiz",
                question="Which quantum number sets hydrogen's energy?",
                options=["n", "l", "m", "s"],
                correct=0, pause=3.0)],
    "I am going to show you why atoms emit only certain colours. Heat "
    "a gas. It glows. Not with a rainbow. With sharp lines. Specific "
    "colours. Every element has its own fingerprint. Hydrogen emits "
    "red at six hundred fifty six nanometres, blue-green at four "
    "eighty six, violet at four thirty four. Where do these exact "
    "wavelengths come from? Bohr's answer. The electron can only "
    "orbit at certain radii. Each orbit has a specific energy."),

# 44 -----------------------------------------------------------------------
chapter(44, "Quantum Structure", "ohanian_ch44_exclusion",
    "The Rule That Builds Chemistry",
    "No two electrons share the same state",
    "Why do atoms fill their shells instead of collapsing?",
    [r"n,\ l,\ m,\ m_s\ \text{unique per electron}"],
    [crystal("lattice"),
     potential_well("well", "0.5*x**2", (-3.0, 3.0), (0.0, 5.0)),
     quiz_frame("quiz",
                question="How many quantum numbers per electron?",
                options=["1", "2", "3", "4"],
                correct=3, pause=3.0)],
    "I am going to show you why chemistry exists. Every electron in an "
    "atom has four quantum numbers. Principal, orbital, magnetic, "
    "spin. No two can have the same four. Pauli exclusion. This is "
    "why the periodic table exists. Without it, every electron would "
    "fall into the lowest energy state. All atoms would look like "
    "hydrogen. No chemical bonds. No life."),

# 45 -----------------------------------------------------------------------
chapter(45, "Nuclei", "ohanian_ch45_binding",
    "Where the Missing Mass Went",
    "Mass defect equals binding energy",
    "Why does a nucleus weigh less than its parts?",
    [r"E=mc^2", r"B.E.=(\sum m_{parts}-m_{nucleus})c^2"],
    [number_line("energy", (-30.0, 30.0), (-28.3, 0.0)),
     text_("note", "mass defect = B.E. / c^2"),
     equation_morph("eq",
                    steps=[r"E = mc^2",
                           r"\Delta m = \Delta E / c^2",
                           r"B.E. = (Z m_p + N m_n - m_{nuc}) c^2"],
                    pos=(0.0, -3.0, 0.0), font_size=20)],
    "I am going to show you where the missing mass went. Take a carbon "
    "nucleus. Six protons, six neutrons. Weigh the parts. Add them "
    "up. Now weigh the whole nucleus. It weighs less. Where did the "
    "mass go? It became energy. When the nucleus formed, the nucleons "
    "pulled together and released energy. That energy left as photons "
    "and neutrinos. By special relativity, energy has mass.",
    short=mk_short("ohanian_ch45_mass_defect",
        "Mass Defect of Helium-4", "Binding energy from missing mass",
        "A helium-4 nucleus has mass 4.0015 u. Binding energy?",
        ("8 MeV", "18 MeV", "28 MeV", "48 MeV"),
        "Correct Answer: (C)",
        [r"B.E. = (2m_p + 2m_n - m_{He})c^2"],
        [number_line("energy", (-30.0, 30.0), (0.0, -28.3)),
         numerical_chain("chain",
                         steps=[r"\Delta m = 0.0305\ \text{u}",
                                r"1\ \text{u} = 931.5\ \text{MeV}/c^2",
                                r"B.E. \approx 28\ \text{MeV}"],
                         pos=(0.0, -3.0, 0.0))],
        "Helium-4 nucleus. Two protons plus two neutrons would weigh "
        "four point zero three two u. The actual nucleus weighs four "
        "point zero zero one five u. Difference, zero point zero three "
        "zero five u. Times nine hundred thirty one point five MeV per "
        "u. About twenty eight MeV. Answer C.")),

# 46 -----------------------------------------------------------------------
chapter(46, "Elementary Particles", "ohanian_ch46_quarks",
    "What Matter Is Really Made Of",
    "Two quarks and one lepton is all you need",
    "What are protons and neutrons made of?",
    [r"p=(u,u,d),\ n=(u,d,d)"],
    [crystal("quark_lattice", color=PRIMARY),
     la_vectors("quark_sum", (2/3, 2/3), (-1/3, 0.0),
                center=(0.0, -2.0, 0.0), scale=1.5),
     numerical_chain("chain",
                     steps=[r"q_p = 2(+2/3) + (-1/3)",
                            r"q_p = 4/3 - 1/3 = +1"],
                     pos=(0.0, -5.0, 0.0))],
    "I am going to show you what matter is really made of. Atoms "
    "first. Electrons around a nucleus. Then the nucleus splits into "
    "protons and neutrons. Then the protons and neutrons split too. "
    "Into quarks. Up and down. Two up, one down makes a proton. "
    "Charge, plus two thirds plus two thirds minus one third. Plus "
    "one. Two down, one up makes a neutron. Charge, minus one third "
    "minus one third plus two thirds. Zero. That is it.",
    short=mk_short("ohanian_ch46_proton",
        "Charge of a Proton", "Two up, one down",
        "A proton is (u, u, d). What is its electric charge?",
        ("+1e", "0", "-1e", "-2/3 e"),
        "Correct Answer: (A)",
        [r"q_p = 2q_u + q_d"],
        [la_vectors("quarks", (2/3, 2/3), (-1/3, 0.0),
                    center=(0.0, 0.0, 0.0), scale=1.5),
         numerical_chain("chain",
                         steps=[r"q_u = +2/3,\ q_d = -1/3",
                                r"q_p = 2(2/3) - 1/3",
                                r"q_p = +1"],
                         pos=(0.0, -3.0, 0.0))],
        "A proton contains two up quarks and one down quark. Up quarks "
        "carry plus two thirds of the elementary charge. Down quarks "
        "carry minus one third. Two up quarks plus one down. Plus two "
        "thirds plus two thirds minus one third. Plus one. Answer A.")),
]


# ===========================================================================
# 6. Beat enrichment
# ===========================================================================

_BEAT_SOUNDS = {
    "promise":   lambda i: drone(f"drone_{i}", duration=2.0),
    "hook":      lambda i: whoosh(f"whoosh_{i}"),
    "analogy":   lambda i: tick(f"tick_{i}"),
    "experiment": lambda i: tick(f"tick_{i}"),
    "law":       lambda i: chime(f"chime_{i}", pitch="C5"),
    "midpoint":  lambda i: tick(f"tick_{i}"),
    "emphasis":  lambda i: whoosh(f"whoosh_{i}", duration=0.6),
    "annotate":  lambda i: tick(f"tick_{i}"),
    "shake":     lambda i: whoosh(f"whoosh_{i}", duration=0.5),
    "punchline": lambda i: chime(f"chime_{i}", pitch="C6"),
}


def _enrich_beats(beats: list[dict[str, Any]],
                  title: str | None = None,
                  annotate_text: str | None = None,
                  law_text: str | None = None) -> list[dict[str, Any]]:
    """Attach sound cues and visual cues to a bare beat arc."""
    out: list[dict[str, Any]] = []
    for i, b in enumerate(beats):
        kind = b["type"]
        b = dict(b)
        if "sound" not in b:
            maker = _BEAT_SOUNDS.get(kind)
            if maker:
                b["sound"] = maker(i)
        if kind == "promise" and title and "kinetic_title" not in b:
            b["kinetic_title"] = kinetic_title("kt_open", title)
        if kind == "hook" and annotate_text and "annotate" not in b:
            b["annotate"] = annotate("an_hook", annotate_text)
        if kind == "law" and law_text and "annotate" not in b:
            b["annotate"] = annotate("an_law", law_text)
        out.append(b)
    return out


# ===========================================================================
# 7. Row assembly
# ===========================================================================

def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def _add(**kw: Any) -> None:
        row: dict[str, Any] = {c: "" for c in COLUMNS}
        for key in ("equations_json", "visual_data_json", "beats_json"):
            if key in kw and isinstance(kw[key], (list, dict)):
                kw[key] = json.dumps(kw[key], ensure_ascii=False)
        row.update(kw)
        missing = [c for c in COLUMNS if c not in row]
        if missing:
            raise ValueError(f"row {kw.get('video_id')!r} missing {missing}")
        rows.append(row)

    for ch in CHAPTERS:
        primary = ch["vis"][0]["id"]
        law_text = ch["eqs"][0] if ch["eqs"] else None
        beats = _enrich_beats(
            arc_lecture(primary),
            title=ch["header"],
            annotate_text=ch["tagline"],
            law_text=law_text,
        )
        _add(
            video_id=ch["slug"],
            concept_type="GENERIC",
            header_title=ch["header"],
            tagline=ch["tagline"],
            question_text=ch["question"],
            equations_json=ch["eqs"],
            visual_data_json=ch["vis"],
            audio_script=ch["script"],
            orientation=LECTURE,
            beats_json=beats,
            target_duration_sec=180,
        )
        s = ch.get("short")
        if s:
            s_primary = s["vis"][0]["id"]
            s_law = s["eqs"][0] if s["eqs"] else None
            s_beats = _enrich_beats(
                arc_short(s_primary),
                title=s["header"],
                annotate_text=s["tagline"],
                law_text=s_law,
            )
            _add(
                video_id=s["video_id"],
                concept_type="PYQ",
                header_title=s["header"],
                tagline=s["tagline"],
                question_text=s["question"],
                option_a=s["option_a"],
                option_b=s["option_b"],
                option_c=s["option_c"],
                option_d=s["option_d"],
                correct_answer=s["correct"],
                equations_json=s["eqs"],
                visual_data_json=s["vis"],
                audio_script=s["script"],
                orientation=SHORT,
                beats_json=s_beats,
                target_duration_sec=60,
            )

    return rows


# ===========================================================================
# 8. Pre-flight — no dangling identifier
# ===========================================================================

def preflight() -> None:
    """Raise if any builder used by CHAPTERS is undefined."""
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
        "beat", "arc_lecture", "arc_short", "_enrich_beats",
        "calculus_graph", "derivative_tangent", "integral_area",
        "riemann_sum",
        "la_vectors", "la_dot", "la_cross", "la_det", "la_transform",
        "la_solve",
        "geo_polyline", "geo_polygon", "geo_circle", "geo_segment",
        "rotor", "venturi", "hydrostatic",
        "e_field", "m_field", "em_wave",
        "sim", "body",
        "wave_", "wave_pulse", "momentum", "pendulum", "falling",
        "projectile", "orbit", "gas", "heat_flow", "pv_tracker",
        "landscape", "potential_well", "induction_coil", "compass_grid",
        "interference", "two_beam", "bohr", "crystal", "rolling",
        "torsion", "pipe_gauge", "wave_packet", "accretion",
        "random_walk",
        "live_label", "numerical_chain", "equation_morph",
        "warning_box", "quiz_frame", "stream_field", "field_by_opacity",
        "energy_bar", "number_line", "damped_oscillator", "two_source",
        "beat_pattern", "harmonic_decomposition", "spectral_sum",
        "sliced_wave", "two_path_interference", "grid_warp",
        "taylor_expand", "exponential_atmosphere", "phase_portrait",
        "color_triangle", "polar_pattern",
        "annotate", "spotlight", "kinetic_title", "term_bind",
        "camera_shake", "ambient", "cinematic_transition",
        "tick", "whoosh", "drone", "chime",
        "text_", "dot_", "num_line",
    ]
    missing = [name for name in required
               if name not in defined and name not in builtins]
    if missing:
        raise RuntimeError(
            f"generate_csv.py is missing definitions for: {missing}. "
            f"The file will fail at import time."
        )


# ===========================================================================
# 9. Writer and CLI
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
