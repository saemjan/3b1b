#!/usr/bin/env python3
"""
generate_csv.py — Ohanian full-book generator wired to every engine.

Engines used (one per chapter, matched to the chapter's physics):
    calculus_engine        — calculus_graph, derivative_tangent,
                             integral_area, riemann_sum
    linear_algebra_engine  — vectors, dot, cross, determinant,
                             matrix_vector, transform, solve
    geometry_engine        — 1D/2D/3D polyline, polygon, circle,
                             sphere, cube, cylinder
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

Beats use the full schema_validator vocabulary:
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

LECTURE = "horizontal"   # 180 s, frame x ∈ [-8, 8],   y ∈ [-4.5, 4.5]
SHORT   = "vertical"     #  60 s, frame x ∈ [-4.5, 4.5], y ∈ [-8, 8]

PRIMARY = "#4CC9F0"
ACCENT  = "#F1C40F"
OK      = "#2ECC71"
WARM    = "#E74C3C"

# ===========================================================================
# 2. Beat vocabulary
# ===========================================================================

def beat(kind: str, focus: str, transition: str | None = None) -> dict[str, Any]:
    b: dict[str, Any] = {"type": kind, "focus": focus}
    if transition:
        b["transition"] = transition
    return b

def arc_lecture(focus: str, *,
                analogy: bool = False,
                experiment: bool = False,
                midpoint: bool = False) -> list[dict[str, Any]]:
    """Feynman arc: promise → hook → [analogy] → [experiment] → law → [midpoint] → punchline."""
    beats: list[dict[str, Any]] = [beat("promise", focus), beat("hook", focus)]
    if analogy:
        beats.append(beat("analogy", focus))
    if experiment:
        beats.append(beat("experiment", focus))
    beats.append(beat("law", focus, transition="wipe"))
    if midpoint:
        beats.append(beat("midpoint", focus))
    beats.append(beat("punchline", focus))
    return beats

def arc_short(focus: str) -> list[dict[str, Any]]:
    """Tight arc for a 60 s short."""
    return [
        beat("hook", focus),
        beat("annotate", focus),
        beat("law", focus, transition="wipe"),
        beat("shake", focus),
        beat("punchline", focus),
    ]

# ===========================================================================
# 3. Engine primitive builders
# ===========================================================================

# --- calculus_engine -----------------------------------------------------

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

def la_det(id_, matrix, center=(0.0, 0.0, 0.0)):
    return {"type": "linear_algebra", "id": id_, "operation": "determinant",
            "matrix": [list(r) for r in matrix], "center": list(center)}

def la_transform(id_, matrix, vector, center=(0.0, 0.0, 0.0)):
    return {"type": "linear_algebra", "id": id_,
            "operation": "matrix_vector",
            "matrix": [list(r) for r in matrix], "vector": list(vector),
            "center": list(center)}

def la_solve(id_, matrix, rhs, center=(0.0, 0.0, 0.0)):
    return {"type": "linear_algebra", "id": id_, "operation": "solve",
            "matrix": [list(r) for r in matrix], "rhs": list(rhs),
            "center": list(center)}

# --- geometry_engine ------------------------------------------------------

def geo_polyline(id_, points, color=PRIMARY, stroke=2.5):
    return {"type": "geometry", "id": id_, "dimension": 2,
            "kind": "polyline", "points": [list(p) for p in points],
            "color": color, "stroke_width": stroke}

def geo_polygon(id_, points, color=PRIMARY, opacity=0.22):
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

def venturi(id_, ih=1.8, th=0.9, iv=2.0, dens=1000.0, ip=200000.0,
            color=PRIMARY):
    return {"type": "fluid_dynamics", "id": id_, "operation": "venturi",
            "inlet_height": ih, "throat_height": th,
            "inlet_velocity": iv, "density": dens,
            "inlet_pressure": ip, "color": color}

def hydrostatic(id_, dens=1000.0, max_depth=4.0,
                center=(0.0, 0.0, 0.0)):
    return {"type": "fluid_dynamics", "id": id_, "operation": "hydrostatic",
            "density": dens, "max_depth": max_depth, "center": list(center)}

# --- electromagnetics_engine ----------------------------------------------

def e_field(id_, charges, xr=(-6.0, 6.0), yr=(-3.5, 3.5),
            cols=13, rows=9, color=PRIMARY):
    return {"type": "electric_field", "id": id_, "charges": charges,
            "x_range": list(xr), "y_range": list(yr),
            "columns": cols, "rows": rows, "color": color}

def m_field(id_, wires, xr=(-6.0, 6.0), yr=(-3.5, 3.5),
            cols=13, rows=9, color=ACCENT):
    return {"type": "magnetic_field", "id": id_, "wires": wires,
            "x_range": list(xr), "y_range": list(yr),
            "columns": cols, "rows": rows, "color": color}

def em_wave(id_, amp=1.0, freq=1.0, speed=2.0, length=7.0):
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

# --- direct primitives used where engines don't fit -----------------------

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

def induction_coil(id_, color=ACCENT):
    return {"type": "induction_coil", "id": id_, "color": color}

def compass_grid(id_, color=ACCENT):
    return {"type": "compass_grid", "id": id_, "color": color}

def interference(id_, color=PRIMARY):
    return {"type": "interference_pattern", "id": id_, "color": color}

def two_beam(id_, color=PRIMARY):
    return {"type": "two_beam_splitter", "id": id_, "color": color}

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

def accretion(id_, color=PRIMARY):
    return {"type": "accretion_disk", "id": id_, "color": color}

def random_walk(id_, color=PRIMARY):
    return {"type": "random_walk", "id": id_, "color": color}

def dot_(id_, pos, color=PRIMARY, label=None):
    d = {"type": "dot", "id": id_, "pos": list(pos), "color": color}
    if label:
        d["label"] = label
    return d

def text_(id_, txt, pos=(0.0, 3.8, 0.0)):
    return {"type": "text", "id": id_, "text": txt, "pos": list(pos)}

def num_line(id_, rng, markers, color=PRIMARY):
    return {"type": "number_line", "id": id_, "range": list(rng),
            "markers": list(markers), "color": color}


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
# 5. Chapters — every engine in the repo, matched to the physics
# ===========================================================================

CHAPTERS = [

# 1 ------------------------------------------------------------------------
chapter(1, "Measurement", "ohanian_ch01_measurement",
    "The Number That Lies", "Trailing zeros are promises",
    "Why is 1.5 not the same as 1.50?",
    [r"\text{precision} \Rightarrow \text{sig figs}"],
    [geo_segment("ruler", [(-3.0, 0.0), (3.0, 0.0)]),
     num_line("scale", (-0.5, 5.0), (1.5, 1.50, 1.500)),
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
        [num_line("line", (-0.5, 5.0), (0.0, 3.0))],
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
         duration=0.9, playback=3.0)],
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
    "you have ever read is a derivative in disguise. The worldline "
    "tells you where something has been. Its tangent tells you where "
    "it is going, right now, in the only sense physics can define "
    "right now.",
    short=mk_short("ohanian_ch02_avg_speed",
        "Average Speed Is Not the Average",
        "You cannot just average the two speeds",
        "A jogger runs 2 km at 10 km/h then 2 km at 6 km/h. Average speed?",
        ("7.5 km/h", "8.0 km/h", "8.5 km/h", "9.0 km/h"),
        "Correct Answer: (A)", [r"v_{avg} = d_{total}/t_{total}"],
        [num_line("line", (0.0, 4.0), (0.0, 2.0, 4.0))],
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
    [la_vectors("v_add", (2.0, 1.0), (-1.0, 2.0)),
     la_dot("dot", (2.0, 1.0), (-1.0, 2.0), center=(0.0, -2.5, 0.0))],
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
    "directed physical quantity obeys the same rules. Learn the "
    "geometric picture once and you never go wrong.",
    short=mk_short("ohanian_ch03_resultant",
        "Resultant of Two Vectors", "Law of cosines in disguise",
        "A is 10 units west. B is 5 units at 70 deg N of E. Resultant?",
        ("9.5 units", "12 units", "15 units", "17 units"),
        "Correct Answer: (A)", [r"R^2 = A^2 + B^2 - 2AB\cos\theta"],
        [la_vectors("v", (-10.0, 0.0), (1.7, 4.7), scale=0.35)],
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
         duration=1.0, playback=3.0)],
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
    "projectile problem collapses under this one insight. Split the "
    "axes. Solve each. Stitch by eliminating time."),

# 5 ------------------------------------------------------------------------
chapter(5, "Newton's Laws", "ohanian_ch05_free_body",
    "The Force You Invented", "Accelerations do not create forces",
    "Why do beginners add an arrow that isn't there?",
    [r"F_{net}=ma"],
    [sim("block_with_drag",
         bodies=[body(1.0, (-3.0, 0.0), (3.0, 0.0), label="m")],
         forces=[{"type": "linear_drag", "coefficient": 0.6}],
         duration=4.0, playback=4.0),
     text_("warning", "no extra arrow", pos=(0.0, 3.5, 0.0))],
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
     text_("note", "F = -kx  ⇔  m d²x/dt² = -kx")],
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
    "every potential looks like a parabola near its minimum. A "
    "pendulum. A molecule. A plucked string. A building in an "
    "earthquake. Zoom in close enough and the force is linear, the "
    "motion is harmonic. The spring is the template."),

# 7 ------------------------------------------------------------------------
chapter(7, "Work-Energy", "ohanian_ch07_work",
    "Push Harder as You Go", "Work is the area under the curve",
    "How do you add up a force that keeps changing?",
    [r"W=\int_a^b F\,dx", r"W_{net}=\Delta K"],
    [calculus_graph("force_curve", "2*x + 1",
                    (0.0, 3.0), (0.0, 8.0)),
     riemann_sum("strips", "2*x + 1",
                 (0.0, 3.0), (0.0, 8.0), 0.0, 3.0, n=14,
                 sample="midpoint")],
    "I am going to show you where calculus comes from in physics. Push "
    "a crate across a rough floor. At first easy. As you go, the "
    "resistance grows. You cannot just multiply force by distance. "
    "The force keeps changing. Here is the trick. Break the journey "
    "into tiny steps. On each step the force is essentially constant. "
    "Work equals force times step length. A little rectangle under "
    "the force curve. Add the rectangles. Shrink the steps. The sum "
    "becomes an integral. The work done by a variable force is the "
    "area under the force-versus-position curve. That is all calculus "
    "is. Bookkeeping for things that change. Once you have the total "
    "work, the work-energy theorem tells you what it did. Net work "
    "equals change in kinetic energy. Push with more work than "
    "friction removes, the crate speeds up. Push with less, it slows "
    "down. This is not a new law. It is Newton's second law, "
    "integrated over position."),

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
         duration=10.0, playback=5.0)],
    "I will show you how to cheat. Throw a ball up. It rises, slows, "
    "stops, falls back. You can solve this with Newton's laws, "
    "tracking velocity and position at every instant. Or you can take "
    "a shortcut. Define energy. For gravity, m g h. As the ball "
    "rises, kinetic drops, potential rises. The sum stays constant. "
    "You do not need the trajectory. You only need the endpoints. "
    "This works whenever the force is conservative. Gravity is "
    "conservative. Friction is not. The potential curve tells you "
    "everything. Where it is steep, the force is strong. Where it has "
    "a minimum, the object oscillates. Where it has a maximum, the "
    "motion is unstable. This is why physicists love energy. It "
    "bypasses the details, gives global answers. You trade local "
    "information for a global invariant."),

# 9 ------------------------------------------------------------------------
chapter(9, "Gravitation", "ohanian_ch09_orbit",
    "The Moon Is Falling", "It has been falling for four billion years",
    "Why does the Moon keep missing the Earth?",
    [r"F=\frac{GMm}{r^2}", r"v=\sqrt{\frac{GM}{r}}"],
    [sim("orbit_sim",
         bodies=[body(1.0, (3.0, 0.0), (0.0, 2.6), label="Moon")],
         forces=[{"type": "central_gravity", "source": 0, "mu": 24.0}],
         duration=14.0, playback=6.0),
     orbit("guide", radius=3.0, color=ACCENT)],
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
    "mass and the radius. Not on the Moon's mass. A pebble and a moon "
    "at the same radius orbit at the same speed. Kepler knew this "
    "from data long before Newton explained it. In Newton's hands, "
    "Kepler's rules became a law of nature.",
    short=mk_short("ohanian_ch09_escape",
        "How Fast to Leave Earth?", "Escape is only √2 times orbital",
        "What is the escape velocity from the Earth's surface?",
        ("7.9 km/s", "11.2 km/s", "15 km/s", "3.0 km/s"),
        "Correct Answer: (B)", [r"v_{esc}=\sqrt{2GM_E/R_E}"],
        [orbit("earth", 2.0),
         dot_("launch", (2.0, 0.0, 0.0), color=ACCENT)],
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
     dot_("cm", (-0.5, 0.0, 0.0), color=ACCENT, label="CM")],
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
    "third law. They never move the center of mass. This is why a "
    "bullet and a rifle recoil together. Why a rocket accelerates. "
    "Why two skaters who push off end up with the same center of mass "
    "they started with. A billion particles, and the center of mass "
    "still behaves like a single particle."),

# 11 -----------------------------------------------------------------------
chapter(11, "Collisions", "ohanian_ch11_impulse",
    "The Impulse Approximation", "Fast collisions hide the outside world",
    "Why is momentum conserved but not kinetic energy?",
    [r"m_1v_1+m_2v_2=m_1v_1'+m_2v_2'"],
    [momentum("collision", 2.0, 4.0, 5.0, -2.0),
     text_("note", "KE becomes heat", pos=(0.0, 3.5, 0.0))],
    "I am going to show you why the equations work. Two carts collide. "
    "Momentum is conserved. Kinetic energy is not. Before, they "
    "carried some kinetic energy. After, less. Where did it go? Heat, "
    "sound, deformation. Momentum is a vector, and Newton's third law "
    "guarantees equal and opposite impulses. Energy is a scalar. It "
    "changes form. This is why momentum conservation is robust. But "
    "Ohanian adds a subtle point. The reason momentum is conserved is "
    "not that external forces are absent. It is that they are small "
    "compared to the collision force, and they act over an extremely "
    "short window. Their impulse is negligible. This is the impulse "
    "approximation. Friction, gravity, air resistance all push on the "
    "carts. During the millisecond of contact they deliver almost "
    "nothing. Momentum is frozen. After, friction bleeds motion away. "
    "But the collision is already over. Fast events hide the world.",
    short=mk_short("ohanian_ch11_ballistic",
        "The Ballistic Pendulum", "Conservation of momentum in one line",
        "A 20 g bullet at 300 m/s embeds in a 500 g block. Block speed?",
        ("7.5 m/s", "11.5 m/s", "15 m/s", "20 m/s"),
        "Correct Answer: (B)", [r"m_1v_1=(m_1+m_2)v'"],
        [momentum("collision", 0.02, 0.5, 300.0, 0.0)],
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
           center=(0.0, 0.0, 0.0))],
    "I will show you why every point on a wheel has the same omega. A "
    "wheel spins. A point near the hub moves slowly. A point on the "
    "rim moves fast. Both complete one revolution in the same time. "
    "This is the key insight of rotational kinematics. Linear "
    "velocity depends on the distance from the axis. Angular velocity "
    "does not. Every point on a rigid body shares omega. Every point "
    "shares alpha. If you tried to describe every point separately, "
    "you would drown in detail. Instead, describe the body once. Then "
    "convert to linear variables whenever you need them. v equals "
    "omega R. A single multiplication. Same trick as vectors. Find "
    "the right variables, and the problem collapses. Angular "
    "kinematics is linear kinematics in a different hat. And the "
    "rolling wheel traces a cycloid, one of the most beautiful curves "
    "in physics."),

# 13 -----------------------------------------------------------------------
chapter(13, "Rigid Dynamics", "ohanian_ch13_torque",
    "Why the Disk Always Wins", "Mass distribution sets the race",
    "A hoop and a disk roll down the same ramp. Which wins?",
    [r"\tau=I\alpha", r"I=\sum m_i r_i^2"],
    [rotor("disk", "solid_disk", 2.0, 1.5, 2.0, 0.0,
           center=(-3.0, 0.0, 0.0)),
     rotor("hoop", "hoop", 2.0, 1.5, 2.0, 0.0,
           center=(3.0, 0.0, 0.0), color=ACCENT),
     text_("note", "same mass, different I", pos=(0.0, 3.8, 0.0))],
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
    "into spinning. Less into forward motion. The hoop loses. Same "
    "physics explains why a solid sphere beats a hollow one. It is "
    "not the mass that matters. It is where the mass lives.",
    short=mk_short("ohanian_ch13_torque_disk",
        "Torque on a Solid Disk", "The moment of inertia sets alpha",
        "A 12 N·m torque acts on a 4 kg, 0.5 m solid disk. Find alpha.",
        ("3.0 rad/s²", "6.0 rad/s²", "12 rad/s²", "24 rad/s²"),
        "Correct Answer: (D)", [r"\tau = I\alpha,\ I = \tfrac{1}{2}MR^2"],
        [rotor("disk", "solid_disk", 4.0, 1.5, 0.0, 12.0)],
        "A solid disk of mass four kilograms and radius half a meter. "
        "Torque of twelve newton meters. Moment of inertia of a disk "
        "is one half m r squared, which is zero point five. Alpha "
        "equals torque over I. Twelve over zero point five. Twenty "
        "four. Answer D. A hoop would resist more, because its mass "
        "sits farther from the axis.")),

# 14 -----------------------------------------------------------------------
chapter(14, "Statics", "ohanian_ch14_equilibrium",
    "The Stuck Drawer", "Torque decides equilibrium",
    "Why does a wide drawer stick when you pull one side?",
    [r"\sum F=0", r"\sum \tau=0"],
    [torsion("bar"),
     geo_polygon("drawer", [(-2.0, -1.0), (2.0, -1.0),
                             (2.0, 1.0), (-2.0, 1.0)],
                 color=PRIMARY, opacity=0.15),
     num_line("offset", (-2.5, 2.5), (0.0, 1.7))],
    "I will show you why a wide drawer sticks. Pull from the middle, "
    "it slides. Pull from one side, it jams. Why? Statics. When you "
    "pull from the middle, the two front corners push against the "
    "frame with equal force. Pull from one side, and a torque "
    "develops about the centerline. One corner digs in harder. If the "
    "offset is large enough, the corner digs so hard it jams. The "
    "threshold is set by the friction coefficient and the depth. For "
    "a forty centimeter drawer with friction coefficient zero point "
    "six, the maximum safe offset is about seventeen centimeters. "
    "Beyond that, jam. This is why wide drawers have handles near the "
    "center. And why a stuck drawer sometimes opens when you pull "
    "from the middle. Statics is not just for bridges. It is for "
    "kitchen cabinets."),

# 15 -----------------------------------------------------------------------
chapter(15, "Oscillations", "ohanian_ch15_pendulum",
    "The Clock That Ignores Amplitude",
    "A pendulum's period depends only on length",
    "Why does the swing rhythm stay the same at every size?",
    [r"T=2\pi\sqrt{L/g}"],
    [pendulum("swing", length=2.0, angle=18.0),
     sim("shm_spring",
         bodies=[body(1.0, (1.0, 0.0), (0.0, 0.0), label="m",
                      color=ACCENT)],
         forces=[{"type": "spring", "body": 0, "anchor": [0.0, 0.0],
                  "stiffness": 3.0, "rest_length": 1.0,
                  "damping": 0.0}],
         duration=6.0, playback=4.0)],
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
    "cathedral. He timed it against his own pulse. The period depends "
    "only on length and on g. Not on mass. Not on amplitude. Shorten "
    "the string, the clock runs fast. Move to the Moon, it runs "
    "slow. This is why pendulum clocks are adjusted for latitude.",
    short=mk_short("ohanian_ch15_period",
        "Pendulum Period", "No mass, no amplitude",
        "A one meter pendulum swings. What is its period?",
        ("0.5 s", "1.0 s", "2.0 s", "4.0 s"),
        "Correct Answer: (C)", [r"T = 2\pi\sqrt{L/g}"],
        [pendulum("swing", length=1.0, angle=15.0)],
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
    [wave_("wave", 1.2, 3.0, 1.0, (-6.0, 6.0)),
     wave_pulse("pulse", color=ACCENT)],
    "I am going to show you one of the most confusing ideas in physics. "
    "Pluck a guitar string. A wave travels from one end to the other. "
    "Now watch a single point on the string. It moves up and down. It "
    "does not travel with the wave. The wave is the pattern. The "
    "medium oscillates in place. When the wave arrives, the point "
    "rises, falls, rises again. When the wave leaves, the point is "
    "back where it started. Nothing has moved except the "
    "disturbance. The wave is the message. The medium is the "
    "messenger. On a string, the wave speed is root tension over "
    "linear density. Tighten the string, wave speeds up. Make it "
    "heavier, wave slows down. This is why thick bass strings play "
    "low notes. Slower wave, longer wavelength, lower pitch. And it "
    "is why the same note on a violin and a cello sounds different. "
    "Same wave. Different medium."),

# 17 -----------------------------------------------------------------------
chapter(17, "Sound", "ohanian_ch17_doppler",
    "The Whistle That Drops", "Moving sources compress their own waves",
    "Why does a train sound lower after it passes?",
    [r"f'=f_0\frac{v}{v\pm v_s}"],
    [wave_("whistle", 1.0, 2.0, 440.0, (-4.0, 4.0)),
     wave_("shifted", 0.7, 1.6, 550.0, (-4.0, 4.0), color=ACCENT)],
    "I am going to show you why a passing train drops in pitch. A "
    "whistle sounds at four hundred forty hertz. Approaching, you "
    "hear four sixty. Receding, three forty. Same whistle. Same speed "
    "of sound. The train is a moving source. Moving toward you, it "
    "launches each crest from a closer position. Crests compress. "
    "Shorter wavelength, higher frequency. Moving away, crests "
    "stretch. Longer wavelength, lower frequency. This is the Doppler "
    "shift. Not the sound changing. The geometry of the source "
    "motion. The same thing happens with light. A star moving away "
    "has its light stretched toward red. This is how astronomers "
    "measure motion without touching the star. Every ambulance, every "
    "police radar, every weather radar uses the same physics."),

# 18 -----------------------------------------------------------------------
chapter(18, "Fluids", "ohanian_ch18_bernoulli",
    "Blow Across a Sheet of Paper",
    "Fast air pushes less. You would have guessed more.",
    "Why does the paper rise?",
    [r"p+\tfrac{1}{2}\rho v^2=\text{constant}"],
    [venturi("venturi", ih=1.8, th=0.9, iv=2.0, dens=1000.0,
             ip=200000.0),
     hydrostatic("tank", dens=1000.0, max_depth=3.5,
                 center=(4.0, 0.0, 0.0))],
    "I am going to show you something that contradicts intuition. Hold "
    "a sheet of paper by its edge. Blow across the top. The paper "
    "rises. You expected it to sink, because you are blowing on it. "
    "It rises. Why? Moving air has lower pressure than still air at "
    "the same height. Bernoulli's principle. The reason is energy. A "
    "fast fluid element has more kinetic energy than a slow one. If "
    "nothing pushes energy in, pressure must drop. Pressure plus half "
    "rho v squared plus rho g h is constant along a streamline. Where "
    "speed goes up, pressure goes down. Watch it in a venturi. The "
    "pipe narrows. Continuity forces the fluid to speed up. Pressure "
    "drops. See it directly with a vertical tube. Every atomizer, "
    "carburetor, curveball, and airplane wing leans on this single "
    "fact. Fast air, low pressure.",
    short=mk_short("ohanian_ch18_bernoulli_short",
        "Faster Water, Lower Pressure", "Continuity plus Bernoulli",
        "Water speeds up in a pipe. Does the pressure rise or fall?",
        ("2 m/s", "5 m/s", "10 m/s", "12 m/s"),
        "Correct Answer: (C)",
        [r"p_1 + \tfrac{1}{2}\rho v_1^2 = p_2 + \tfrac{1}{2}\rho v_2^2"],
        [venturi("v", ih=1.8, th=0.9, iv=2.0, dens=1000.0,
                 ip=200000.0)],
        "Water in a horizontal pipe. Point one. Pressure two times ten "
        "to the fifth. Speed two. Point two. Pressure one point five "
        "times ten to the fifth. Speed? Bernoulli. Solve for v two. "
        "About ten point two. Answer C.")),

# 19 -----------------------------------------------------------------------
chapter(19, "Kinetic Theory", "ohanian_ch19_gas",
    "The Speed of Molecules", "Temperature is average kinetic energy",
    "What does it mean for a gas to be hot?",
    [r"\tfrac{3}{2}k_BT = \tfrac{1}{2}mv_{rms}^2"],
    [gas("gas", count=90, box=(6.0, 3.0)),
     sim("two_molecules",
         bodies=[body(1.0, (-1.0, 1.0), (0.5, 0.3), label="H₂",
                      color=PRIMARY),
                 body(16.0, (1.5, -0.5), (-0.15, -0.1), label="O₂",
                      color=ACCENT)],
         forces=[{"type": "linear_drag", "coefficient": 0.0}],
         duration=5.0, playback=4.0)],
    "I am going to show you what temperature actually is. Not a number "
    "on a dial. Molecules. Billions of them, in a box, moving in every "
    "direction, bouncing off each other and the walls. Each has a "
    "mass and a speed. The average of one half m v squared is the "
    "kinetic energy. Multiply by two thirds and you get k B T. "
    "Temperature is a measure of average kinetic energy. Nothing "
    "more. Double the temperature, the average kinetic energy "
    "doubles. Not the speed. So the rms speed goes up by root two. "
    "This is why hydrogen escapes from Earth's atmosphere and oxygen "
    "does not. Lighter molecules move faster at the same temperature. "
    "Some reach escape speed. Over a billion years, the atmosphere "
    "becomes what we have. The ideal gas law is not fundamental. It "
    "is a statistical consequence of molecules bouncing in a box.",
    short=mk_short("ohanian_ch19_rms",
        "Hot Light Molecules", "rms speed scales as √T / √m",
        "H₂ at 30 C has a certain rms speed. At what T does O₂ match?",
        ("300 K", "750 K", "4800 K", "5500 K"),
        "Correct Answer: (C)", [r"v_{rms}=\sqrt{3RT/M}"],
        [gas("gas", count=60, box=(5.0, 3.0))],
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
     num_line("energy", (0.0, 100.0), (0.0, 20.0, 60.0, 100.0))],
    "I am going to show you where the extra heat goes. A pot of water "
    "on the stove. At first, temperature rises. At one hundred "
    "Celsius, something strange. You keep adding heat. Temperature "
    "stops rising. Water boils. All the energy goes into breaking "
    "bonds between molecules, not into their kinetic energy. This is "
    "a phase change. The energy per kilogram is the latent heat of "
    "vaporization. Five hundred forty kilocalories per kilogram. When "
    "steam condenses, the same energy is released. This is why steam "
    "burns are worse than hot water burns. The steam has extra energy "
    "stored in its phase. Ice melting works in reverse. Eighty "
    "kilocalories per kilogram to melt ice at zero. Temperature does "
    "not change. The phase does. And that phase change holds or "
    "releases enormous energy silently, at fixed temperature."),

# 21 -----------------------------------------------------------------------
chapter(21, "Thermodynamics", "ohanian_ch21_entropy",
    "Why You Cannot Unstir Coffee", "Entropy counts arrangements",
    "Why does heat flow one way and never the other?",
    [r"S=k_B\ln W", r"\Delta S\geq 0"],
    [pv_tracker("cycle"),
     random_walk("walk", color=ACCENT)],
    "I am going to show you why you cannot un-stir coffee. A drop of "
    "ink in water. Stir. It spreads. It stays spread. Now try to "
    "gather all the ink back into one corner. You cannot. Not because "
    "mechanics forbids it. Every collision between ink and water is "
    "reversible. Run the movie backward and every collision still "
    "obeys Newton's laws. But the number of ways to arrange the ink "
    "molecules in one corner is astronomically smaller than the "
    "number of ways to spread them out. The system evolves toward "
    "more arrangements. Not because it is forced to. Because it is "
    "overwhelmingly likely. This is entropy. The second law says that "
    "in an isolated system, entropy never decreases. Not because "
    "reversal is forbidden. Because it is so improbable you would "
    "need longer than the age of the universe to see it. The universe "
    "is not marching toward disorder. It is marching toward the most "
    "numerous arrangements. Almost all of them look disordered."),

# 22 -----------------------------------------------------------------------
chapter(22, "Electric Force", "ohanian_ch22_coulomb",
    "The Battle of Two Forces", "Coulomb beats gravity by 10^39",
    "Why does electricity dominate atoms but not the cosmos?",
    [r"F=\frac{kq_1q_2}{r^2}"],
    [e_field("pair",
             charges=[{"position": [-2.0, 0.0, 0.0], "charge": 1.0},
                      {"position": [2.0, 0.0, 0.0], "charge": -1.0}],
             xr=(-4.0, 4.0), yr=(-3.5, 3.5), cols=11, rows=9),
     text_("note", "inverse square, both forces")],
    "I am going to show you the greatest mismatch in physics. Electron "
    "and proton. Compare electric to gravitational. Both follow "
    "inverse square laws. The ratio is independent of distance. Plug "
    "in. Electric wins by two point three times ten to the thirty "
    "nine. That is two thousand billion billion billion billion. And "
    "yet gravity runs the universe. How? Because positive and "
    "negative charges cancel. On the scale of a planet, of a galaxy, "
    "net charge is essentially zero. Electric forces between "
    "neighboring atoms are colossal, but they cancel at any distance "
    "larger than an atom. Gravity has no such cancellation. Mass "
    "always attracts. Over astronomical distances, gravity is all "
    "that remains. The strong force wins the atom. Coulomb wins "
    "everything smaller than a dust grain. Masses only attract.",
    short=mk_short("ohanian_ch22_ratio",
        "Which Force Wins?", "Coulomb beats gravity by 10^39",
        "Ratio of electric to gravitational force between e and p?",
        ("10^10", "10^20", "2.3 × 10^39", "10^50"),
        "Correct Answer: (C)",
        [r"F_E/F_G = ke^2/(Gm_em_p)"],
        [e_field("pair",
                 charges=[{"position": [-1.0, 0.0, 0.0], "charge": 1.0},
                          {"position": [1.0, 0.0, 0.0], "charge": -1.0}],
                 xr=(-3.0, 3.0), yr=(-2.5, 2.5), cols=9, rows=7)],
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
             xr=(-6.0, 6.0), yr=(-3.5, 3.5), cols=15, rows=11)],
    "I am going to show you how one charge knows another is nearby. It "
    "cannot see. It cannot shout. Yet bring two positive charges "
    "close and they repel, instantly. Newton hated this. He called it "
    "the greatest absurdity in physics. Faraday found a way out. "
    "Instead of saying one charge reaches across space and pulls on "
    "another, say that each charge creates something in the space "
    "around it. That something is the electric field. Every point in "
    "space has a field vector. A second charge placed there responds "
    "locally to the field at its own location. The first creates the "
    "field. The field travels. The second responds. Action at a "
    "distance becomes two local events, connected by a messenger. The "
    "field falls off as one over r squared. Double the distance, "
    "quarter the field. Draw the field lines. They start on positive "
    "charges, end on negative. This concept survived from Faraday to "
    "Maxwell to Einstein."),

# 24 -----------------------------------------------------------------------
chapter(24, "Gauss' Law", "ohanian_ch24_gauss",
    "Why You Are Safe Inside",
    "The field cannot penetrate a conductor",
    "Why is the field zero inside a metal box?",
    [r"\oint \vec{E}\cdot d\vec{A} = Q/\epsilon_0"],
    [e_field("uniform",
             charges=[{"position": [-4.0, 0.0, 0.0], "charge": 5.0},
                      {"position": [4.0, 0.0, 0.0], "charge": 5.0}],
             xr=(-6.0, 6.0), yr=(-3.5, 3.5), cols=15, rows=11)],
    "I am going to show you why you are safe in a metal box. Sit "
    "inside. The box is in a strong electric field. What happens "
    "inside? Nothing. The field is zero. Here is why. Electrons in a "
    "metal are free to move. If there were a field inside, they would "
    "feel a force and move. But in a steady state nothing is "
    "happening. So they rearrange on the surface until they cancel "
    "the external field at every interior point. The field inside is "
    "zero. All charge ends up on the surface. This one result, "
    "falling straight out of Gauss's law, explains a lot. Why a car "
    "protects you from lightning. Why a Faraday cage shields "
    "electronics. Why a sharp point on a conductor has a stronger "
    "field than a smooth surface. The charge crowds at the tip. This "
    "is why lightning rods work."),

# 25 -----------------------------------------------------------------------
chapter(25, "Potential", "ohanian_ch25_potential",
    "The Work to Bring a Charge Home",
    "Potential is energy per unit charge",
    "What does a volt actually measure?",
    [r"V=\frac{kQ}{r}", r"V=\frac{U}{q}"],
    [landscape("well", "k/x", (0.4, 4.0), (-3.0, 0.5), color=PRIMARY)],
    "I am going to show you what a volt actually is. Not a force. Not "
    "a field. Energy per unit charge. The work you would do to bring "
    "a positive test charge from infinity to some point, divided by "
    "the charge. The field tells you the force at each point. The "
    "potential tells you the energy. The two are related. The field "
    "is the gradient of the potential. Steep slope, strong field. "
    "Flat region, weak field. This is why potential is so useful. It "
    "is a scalar. One number per point, not three. Conceptually, it "
    "maps the energy landscape. A charge rolls downhill like a ball. "
    "The potential is the height. Around a positive charge, high and "
    "falls off as one over r. Around a negative charge, low. Between "
    "two charges, valleys and hills. Every battery label you have "
    "ever read is a statement about this landscape."),

# 26 -----------------------------------------------------------------------
chapter(26, "Electric Energy", "ohanian_ch26_energy",
    "The Cost of Assembly",
    "Charges repel, so assembling them costs energy",
    "Where does the energy of a charged conductor go?",
    [r"U=\tfrac{1}{2}QV"],
    [e_field("sphere",
             charges=[{"position": [0.0, 0.0, 0.0], "charge": 1.0}],
             xr=(-3.5, 3.5), yr=(-3.5, 3.5), cols=11, rows=11)],
    "I am going to show you where the energy goes when you charge a "
    "sphere. You brought charges in from infinity, one by one. Each "
    "had to be pushed against the repulsion of the charges already "
    "there. Total work equals energy stored. One half Q V. Half the "
    "charge times the potential. Same formula for any conductor. "
    "Where is this energy? Two answers, both correct. You can say it "
    "is stored in the charge distribution. Or you can say it is "
    "stored in the electric field the charges produce. The energy "
    "density of an electric field is one half epsilon zero E squared. "
    "Integrate over all space. Same answer. This is the seed of field "
    "theory. Energy is not attached to particles. It is attached to "
    "the space between them."),

# 27 -----------------------------------------------------------------------
chapter(27, "Capacitors", "ohanian_ch27_dielectric",
    "Slide Plastic Into a Capacitor",
    "Dielectrics weaken the field",
    "Why does a dielectric reduce the electric field?",
    [r"E=E_{free}/\kappa", r"C=\kappa C_0"],
    [e_field("plates",
             charges=[{"position": [-3.0, 0.0, 0.0], "charge": 3.0},
                      {"position": [3.0, 0.0, 0.0], "charge": -3.0}],
             xr=(-6.0, 6.0), yr=(-3.5, 3.5), cols=15, rows=11)],
    "I am going to show you how plastic can weaken an electric field. "
    "Charge a capacitor. Disconnect the battery. The plates hold their "
    "charge. Slide a slab of plastic between them. The field shrinks. "
    "Not by a little. By a factor of three for ordinary plastic. By "
    "thousands for certain ceramics. Where does the field go? It gets "
    "cancelled by the plastic itself. Every molecule inside is either "
    "a permanent dipole or becomes one when placed in the field. The "
    "dipoles align. Their positive ends point one way, negative the "
    "other. They create bound surface charge on the slab. That bound "
    "charge produces a field opposing the original. Net field weaker. "
    "Ohanian calls the ratio the dielectric constant, kappa. The "
    "capacitance rises by the same factor. This is why real "
    "capacitors have dielectrics inside. To multiply capacitance for "
    "free."),

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
     text_("note", "slow carriers, fast signal")],
    "I am going to show you the slowest fast thing in physics. A copper "
    "wire carries current. Electrons flow. How fast? You would guess "
    "near the speed of light. Wrong. Drift velocity in a copper wire "
    "at ordinary currents is about zero point one millimetre per "
    "second. Slower than a snail. Yet when you flip the switch, the "
    "light comes on instantly. How? The electric field travels. The "
    "signal moves at nearly the speed of light, pushing all the "
    "electrons along at once. The electrons crawl. The field "
    "orchestrates them. Current equals n e A v d. Number density of "
    "carriers, charge, cross section, drift velocity. For copper, n "
    "is enormous. That is why you do not need fast electrons to get a "
    "big current. You need many of them, each slow, together a flood.",
    short=mk_short("ohanian_ch28_drift_short",
        "Drift Velocity in Copper", "Slow carriers, fast signal",
        "A 0.5 cm² copper bar carries 98 A. Electron drift velocity?",
        ("1.4 × 10⁻⁴ m/s", "1.4 mm/s", "1.4 m/s", "1400 m/s"),
        "Correct Answer: (A)", [r"I = neAv_d"],
        [num_line("speed", (-6.0, 0.0), (-3.85,))],
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
    [geo_polyline("loop", [(-4.0, -1.5), (4.0, -1.5),
                            (4.0, 1.5), (0.0, 1.5),
                            (0.0, -1.5), (-4.0, -1.5)],
                  color=PRIMARY, stroke=3.0),
     geo_polyline("branch", [(-4.0, -1.5), (-4.0, 1.5)],
                  color=ACCENT, stroke=2.0)],
    "I am going to show you how to solve any circuit. Multiple "
    "resistors, multiple batteries. What is the current in each "
    "branch? There is a systematic way. Kirchhoff's rules. Two "
    "statements. Charge is conserved. At every junction, current in "
    "equals current out. Energy is conserved. Around any closed loop, "
    "voltage gains minus drops equals zero. Two rules. That is all. "
    "Apply them systematically. Label unknown currents. Choose "
    "directions. One equation per junction. One per independent loop. "
    "Solve. If a current comes out negative, your guess was wrong. No "
    "harm. The magnitude is correct, the direction reversed. This is "
    "the same conservation logic you used in mechanics. The circuit "
    "is a bookkeeping system. Kirchhoff just tells you where to keep "
    "the books."),

# 30 -----------------------------------------------------------------------
chapter(30, "Magnetic Force", "ohanian_ch30_relativity",
    "Magnetism Is Electricity in Disguise",
    "Special relativity explains magnetic force",
    "Why do parallel currents attract?",
    [r"F_m=\mu_0\epsilon_0 v^2 F_e", r"\mu_0\epsilon_0 c^2=1"],
    [m_field("wires",
             wires=[{"start": [-4.0, 1.5, 0.0],
                     "end": [4.0, 1.5, 0.0], "current": 5.0},
                    {"start": [-4.0, -1.5, 0.0],
                     "end": [4.0, -1.5, 0.0], "current": 5.0}],
             xr=(-5.0, 5.0), yr=(-3.5, 3.5), cols=15, rows=11)],
    "I am going to show you that magnetism is not a separate force. Two "
    "wires carry current the same direction. They attract. But both "
    "contain moving electrons, and like charges repel. So why do the "
    "wires pull together? Take the rest frame of the electrons in one "
    "wire. From that frame, the other wire is not neutral. The "
    "positive ions are moving backward, and length contraction packs "
    "them closer. The electrons in the other wire are moving at a "
    "different speed, so their spacing changes by a different "
    "amount. Net effect. Charge imbalance. Electric field. "
    "Attraction. What we call magnetism in the lab frame, an observer "
    "riding the electrons calls electricity. Same force, different "
    "accounting. The magnetic force is the electric force multiplied "
    "by v squared over c squared. Magnetism is electricity viewed "
    "from a moving frame. That is why the speed of light appears in "
    "Maxwell's equations.",
    short=mk_short("ohanian_ch30_field_wire",
        "Field Around a Wire", "Ampère's law in one line",
        "What is B at 0.50 m from a long straight wire carrying 5 A?",
        ("1.0 × 10⁻⁶ T", "2.0 × 10⁻⁶ T", "5.0 × 10⁻⁶ T", "1.0 × 10⁻⁵ T"),
        "Correct Answer: (B)", [r"B = \mu_0 I / (2\pi r)"],
        [m_field("wire",
                 wires=[{"start": [-3.0, 0.0, 0.0],
                         "end": [3.0, 0.0, 0.0], "current": 5.0}],
                 xr=(-4.0, 4.0), yr=(-3.5, 3.5), cols=13, rows=11)],
        "Wire carries five amps. What is B half a meter away? B equals "
        "mu zero I over two pi r. mu zero is one point two five six "
        "times ten to the minus six. Times five. Over two pi times "
        "zero point five. That is two times ten to the minus six "
        "tesla. Answer B.")),

# 31 -----------------------------------------------------------------------
chapter(31, "Ampère", "ohanian_ch31_ampere",
    "The Field Around a Wire", "Ampère is Gauss in a circle",
    "How do you compute a field without integrating?",
    [r"\oint \vec{B}\cdot d\vec{l} = \mu_0 I"],
    [m_field("wire",
             wires=[{"start": [-5.0, 0.0, 0.0],
                     "end": [5.0, 0.0, 0.0], "current": 8.0}],
             xr=(-6.0, 6.0), yr=(-3.5, 3.5), cols=17, rows=11),
     geo_circle("loop", (0.0, 0.0), 1.5, color=ACCENT)],
    "I am going to show you a shortcut that saves you an integral. "
    "Current through a wire. Magnetic field around it. You could use "
    "the Biot-Savart law. Tedious. Or Ampère's law. The line integral "
    "of B around a closed loop equals mu zero times the current "
    "enclosed. Pick a loop matching the symmetry. For a long straight "
    "wire, a circle. The field is constant on the circle and tangent. "
    "The line integral is B times two pi r. Set it equal to mu zero "
    "I. Solve. B equals mu zero I over two pi r. Ampère's law is the "
    "magnetic twin of Gauss's law. Gauss uses closed surfaces and "
    "enclosed charge. Ampère uses closed loops and enclosed current. "
    "Both exploit symmetry. Both turn a hard integral into a one-line "
    "answer."),

# 32 -----------------------------------------------------------------------
chapter(32, "Induction", "ohanian_ch32_lenz",
    "Nature Fights Every Change", "Lenz's law is energy conservation",
    "Why does an induced current oppose its cause?",
    [r"\mathcal{E} = -d\Phi_B/dt"],
    [induction_coil("coil"),
     m_field("moving",
             wires=[{"start": [-1.0, 0.0, 0.0],
                     "end": [1.0, 0.0, 0.0], "current": 3.0}],
             xr=(-4.0, 4.0), yr=(-3.0, 3.0), cols=11, rows=9,
             color=PRIMARY)],
    "I am going to show you that Lenz's law is not a rule to memorize. "
    "It is energy conservation in disguise. Move a magnet toward a "
    "coil. Current flows. Pull it away. Current the other way. In "
    "both cases the current opposes the change. Push in, the induced "
    "current pushes back. Pull out, it pulls in. Why? Suppose the "
    "opposite. Suppose the current ran the other way. Then pushing "
    "the magnet in would pull it faster, inducing more current, "
    "pulling harder. Runaway. Energy from nothing. Lenz says no. The "
    "universe resists change. Move a metal plate through a field. "
    "Eddy currents resist the motion. Magnetic braking. High-speed "
    "trains. Roller coasters. Move a superconductor through a field. "
    "Currents become perfect. The material floats. Lenz's law is "
    "energy conservation wearing a magnetic disguise."),

# 33 -----------------------------------------------------------------------
chapter(33, "Magnetic Materials", "ohanian_ch33_domains",
    "The Domains Inside Iron",
    "Tiny aligned patches flip and grow",
    "Why does iron stick to a magnet?",
    [r"\vec{B}=\mu_0(\vec{H}+\vec{M})"],
    [compass_grid("grid"),
     crystal("lattice", color=ACCENT)],
    "I am going to show you why iron sticks and copper does not. Inside "
    "iron there are domains. Tiny regions where all the atomic "
    "magnetic moments are aligned. In the absence of an external "
    "field, they point in random directions. Net magnetization zero. "
    "Iron looks non-magnetic. Bring a magnet close. The domains that "
    "happen to align with the field grow. Their neighbors flip and "
    "join. Suddenly huge swaths of the iron are aligned. Iron becomes "
    "a magnet. The force of attraction is enormous. This is "
    "ferromagnetism. Above the Curie temperature, thermal motion "
    "destroys the domains. Iron becomes paramagnetic. Cool it, the "
    "domains reform. Every hard drive uses this physics. Write head "
    "flips domains on a magnetic disk. Read head detects them. A "
    "trillion bits stored in the alignment of tiny magnets."),

# 34 -----------------------------------------------------------------------
chapter(34, "AC Circuits", "ohanian_ch34_resonance",
    "The Frequency That Selects",
    "Resonance picks one signal from a crowd",
    "Why does a radio tune to a single station?",
    [r"Z=\sqrt{R^2+(X_L-X_C)^2}", r"\omega_0=1/\sqrt{LC}"],
    [em_wave("wave", amp=1.0, freq=1.0, speed=2.0, length=7.0),
     text_("note", "peak at resonance")],
    "I am going to show you how your radio picks one station out of "
    "hundreds. Resonance. Your radio contains an inductor and a "
    "capacitor in series. Together they form a circuit with a natural "
    "frequency. Change the capacitor. You tune the natural frequency. "
    "Signals at that frequency drive the circuit hard. Signals at "
    "other frequencies barely move it. The circuit selects. This is "
    "why old tuners had a dial. You were changing the resonance "
    "frequency. The sharpness of the selection is measured by Q. "
    "High Q means a very sharp peak. One station. Low Q means a broad "
    "peak. Several stations leak through. Every TV, every cell phone, "
    "every Wi-Fi router uses the same trick. Resonance is how the "
    "modern world picks one signal out of the electromagnetic noise.",
    short=mk_short("ohanian_ch34_lc",
        "The Natural Frequency", "LC circuit oscillates at ω₀ = 1/√LC",
        "An LC circuit has L = 1 mH, C = 1 nF. What is f₀?",
        ("1.6 kHz", "16 kHz", "160 kHz", "1.6 MHz"),
        "Correct Answer: (C)", [r"f_0 = 1/(2\pi\sqrt{LC})"],
        [em_wave("wave", amp=1.0, freq=2.0, speed=2.0, length=6.0)],
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
    [em_wave("wave", amp=1.0, freq=1.0, speed=2.0, length=8.0)],
    "I am going to show you all of electricity and magnetism in four "
    "lines. Gauss's law. No magnetic monopoles. Faraday's law. "
    "Ampère's law with Maxwell's addition. Together they describe "
    "every electromagnetic phenomenon in the universe. The first says "
    "electric field lines start on charges. The second says magnetic "
    "field lines never start or end. The third says a changing "
    "magnetic field creates an electric field. The fourth says a "
    "changing electric field creates a magnetic field. Maxwell's "
    "contribution was that fourth term. Without it, the equations "
    "were inconsistent. With it, they predict waves of electric and "
    "magnetic fields, propagating at c equals one over the square "
    "root of mu zero epsilon zero. That number came out to three "
    "times ten to the eighth meters per second. The speed of light. "
    "Maxwell realized light is an electromagnetic wave. He unified "
    "optics and electromagnetism in a single stroke."),

# 36 -----------------------------------------------------------------------
chapter(36, "Light and Radio Waves", "ohanian_ch36_pressure",
    "Light Pushes", "Photons carry momentum",
    "How does sunlight exert force?",
    [r"p=E/c", r"S=EB/\mu_0"],
    [em_wave("wave", amp=1.0, freq=1.0, speed=2.0, length=7.0)],
    "I am going to show you that light pushes. Light carries energy. "
    "Does it carry momentum? Yes. Every photon has momentum equal to "
    "its energy over c. Shine a laser on a mirror. The mirror is "
    "pushed. Radiation pressure. Not a curiosity. A measurable force. "
    "Sunlight delivers about one thousand three hundred fifty watts "
    "per square meter at Earth's orbit. Pressure, four point five "
    "microPascals. Tiny. But the Earth intercepts a disk of radius "
    "six thousand four hundred kilometers. Total outward force, five "
    "hundred eighty million newtons. Small compared to the Sun's "
    "gravity. Earth stays in orbit. But for a solar sail, the "
    "pressure is enough. A large thin reflective sheet can be "
    "accelerated by sunlight with no fuel. Engineers plan probes to "
    "the outer solar system that never need propellant. Comet tails "
    "always point away from the Sun for this reason."),

# 37 -----------------------------------------------------------------------
chapter(37, "Reflection and Refraction", "ohanian_ch37_snell",
    "The Bent Straw", "Light slows down in glass and bends",
    "Why does a straw look broken in a glass of water?",
    [r"n_1\sin\theta_1 = n_2\sin\theta_2"],
    [geo_polyline("ray_in", [(-3.0, 2.0), (0.0, 0.0)]),
     geo_polyline("ray_out", [(0.0, 0.0), (2.0, -1.0)], color=ACCENT),
     geo_polyline("normal", [(0.0, -1.5), (0.0, 1.5)], color="#8A8F9C",
                  stroke=1.5)],
    "I am going to show you why a straw looks broken in a glass of "
    "water. Light slows down when it enters water. Or glass. Or any "
    "transparent medium. The speed of light in a medium is c over n. "
    "Water, one point three three. Glass, one point five. Diamond, "
    "two point four. When light crosses a boundary at an angle, the "
    "change in speed bends the ray. Snell's law. n one sine theta one "
    "equals n two sine theta two. Into a denser medium, the ray bends "
    "toward the normal. Out of one, away. This is why eyeglasses "
    "correct vision. Why a swimming pool looks shallower than it is. "
    "Why a prism splits white light into a rainbow. The index "
    "depends slightly on wavelength. Blue bends more than red. "
    "Dispersion. Every lens, every camera, every telescope depends on "
    "this single fact."),

# 38 -----------------------------------------------------------------------
chapter(38, "Mirrors and Lenses", "ohanian_ch38_optics",
    "Why Sign Conventions Make You Cry",
    "Draw the diagram first",
    "Why do mirrors and lenses use opposite sign rules?",
    [r"1/s + 1/s' = 1/f"],
    [geo_polyline("axis", [(-6.0, 0.0), (6.0, 0.0)]),
     geo_polyline("ray_in", [(-4.0, 1.5), (0.0, 0.0)], color=ACCENT),
     geo_polyline("ray_out", [(0.0, 0.0), (4.0, 1.0)], color=OK),
     geo_polyline("ray_through", [(0.0, 0.0), (4.0, -1.5)],
                  color=PRIMARY)],
    "I am going to show you why students hate optics. Sign "
    "conventions. For mirrors, focal length is positive if concave. "
    "For lenses, positive if convex. Object and image distances "
    "follow different rules. Why? Because mirrors and lenses use the "
    "same equation to describe different geometry. The mirror "
    "equation is one over s plus one over s prime equals one over f. "
    "For a lens, s prime is on the opposite side for a real image. "
    "The math is the same. The picture is flipped. The convention "
    "handles this with signs. But do not memorize the table. Draw a "
    "ray diagram first. Trace the light. Where rays converge is a "
    "real image. Where they appear to come from is a virtual image. "
    "The signs follow the diagram. Students who memorize make "
    "errors. Students who draw do not. The picture is the physics."),

# 39 -----------------------------------------------------------------------
chapter(39, "Interference", "ohanian_ch39_film",
    "Why Soap Bubbles Shine",
    "Two reflections and a phase flip",
    "What makes the colours on a soap bubble?",
    [r"2d=m\lambda"],
    [interference("fringes"),
     two_beam("split")],
    "I am going to show you where the colours on a soap bubble come "
    "from. A thin film of water between two layers of air. Sunlight "
    "hits it. Some light reflects off the outer surface. Some passes "
    "through and reflects off the inner surface. The two reflected "
    "rays interfere. In phase, bright colour. Out of phase, that "
    "colour is missing. What sets the phase? Two things. The extra "
    "path the inner ray travels is twice the film thickness. And a "
    "phase flip happens when light reflects off a boundary where the "
    "index increases. For a bubble in air, the outer reflection "
    "flips. The inner one does not. So the interference condition is "
    "not the naive formula. Constructive interference needs a "
    "different condition than for an oil slick on water. This is why "
    "bubbles show colours that shift as you watch them. The film "
    "thins under gravity. The path difference changes. The colour "
    "changes."),

# 40 -----------------------------------------------------------------------
chapter(40, "Diffraction", "ohanian_ch40_limit",
    "Why Stars Blur", "Diffraction limits every telescope",
    "Why is there a limit to how sharp a telescope can see?",
    [r"\theta=1.22\lambda/D"],
    [interference("fringes", color=ACCENT),
     two_beam("split"),
     geo_circle("aperture", (0.0, 0.0), 1.8, color=PRIMARY, opacity=0.08)],
    "I am going to show you why every telescope has a limit. Point a "
    "telescope at a distant star. It should look like a bright dot. "
    "It does not. It looks like a small disk with faint rings around "
    "it. Diffraction. When light passes through a circular opening it "
    "spreads. The spread depends on wavelength and on the diameter of "
    "the opening. Bigger opening, tighter spread. Shorter wavelength, "
    "tighter spread. But it never reaches zero. For a twelve "
    "centimeter lens and visible light, the minimum resolvable angle "
    "is about one arcsecond. That is why Palomar has a five meter "
    "mirror. That is why Hubble has a two and a half meter mirror. "
    "Size buys resolution. This is also why radio telescopes must be "
    "enormous. Rayleigh put a number on it. Sin theta equals one "
    "point two two lambda over D. That number rules every telescope "
    "ever built."),

# 41 -----------------------------------------------------------------------
chapter(41, "Special Relativity", "ohanian_ch41_dilation",
    "The Proton That Shortcuts Spacetime",
    "Time dilates at high speed",
    "Why do fast clocks run slow?",
    [r"\Delta t' = \Delta t\sqrt{1-v^2/c^2}"],
    [accretion("galaxy"),
     orbit("guide", radius=3.5, color=ACCENT),
     text_("note", "gamma ~ 316")],
    "I am going to show you how a proton crosses the galaxy in under "
    "five hundred years. It travels at zero point nine nine nine nine "
    "nine c. The galaxy is one hundred thousand light years across. "
    "How much time on the proton's own clock? Not one hundred "
    "thousand years. Four hundred fifty. The Lorentz factor for that "
    "speed is three hundred sixteen. Proper time equals coordinate "
    "time divided by gamma. From the proton's point of view, the "
    "galaxy is contracted. Not one hundred thousand light years "
    "across. Three hundred twenty. It never breaks the speed of "
    "light. It just takes a shortcut through spacetime. Every GPS "
    "satellite corrects for this. Every particle accelerator designs "
    "around it. Every cosmic ray muon reaches the ground because of "
    "it. The universe has as many clocks as there are moving "
    "observers.",
    short=mk_short("ohanian_ch41_dilation_short",
        "A Proton Crosses the Galaxy",
        "Time dilation at high speed",
        "Proton at 0.99999c crosses a 10⁵ ly galaxy. Proper time?",
        ("450 years", "10⁵ years", "1000 years", "2.2 years"),
        "Correct Answer: (A)",
        [r"\Delta t' = \Delta t\sqrt{1-v^2/c^2}"],
        [orbit("galaxy", 3.0),
         text_("note", "gamma ~ 316")],
        "A proton at zero point nine nine nine nine nine c crosses the "
        "Milky Way. One hundred thousand light years in the galaxy's "
        "frame. How much time on the proton's clock? Lorentz factor "
        "roughly three hundred sixteen. Proper time equals coordinate "
        "time divided by gamma. About four hundred fifty years. "
        "Answer A. From the proton's view, the galaxy is contracted to "
        "three hundred twenty light years.")),

# 42 -----------------------------------------------------------------------
chapter(42, "Quanta of Light", "ohanian_ch42_photon",
    "The Threshold Wavelength", "Light comes in packets",
    "Why can red light not eject electrons from potassium?",
    [r"E=hf", r"K=hf-\phi"],
    [wave_packet("packet"),
     wave_("wave", 1.0, 2.0, 3.0, (-4.0, 4.0), color=ACCENT)],
    "I am going to show you why red light cannot eject electrons from "
    "potassium. Shine light on a metal surface. Electrons pop out. "
    "Classical physics says brighter light should give faster "
    "electrons. Wrong. Brighter light gives more electrons. Their "
    "speed stays the same. And if the frequency is too low, no "
    "electrons come out at all, no matter how bright. Einstein "
    "explained this in 1905. Light comes in packets. Photons. Each "
    "has energy h f. One photon ejects one electron. The photon's "
    "energy pays the work function of the metal, phi. The rest "
    "becomes the electron's kinetic energy. If h f is less than phi, "
    "no electron escapes. No matter how many photons you throw at the "
    "surface. Brightness is not the question. Frequency is. This "
    "discovery started quantum mechanics.",
    short=mk_short("ohanian_ch42_threshold",
        "The Threshold Wavelength", "Below it, nothing",
        "Potassium work function 2.0 eV. Threshold wavelength?",
        ("624 nm", "400 nm", "250 nm", "900 nm"),
        "Correct Answer: (A)", [r"\lambda = hc/\phi"],
        [wave_pulse("packet")],
        "Potassium has a work function of two electron volts. Longest "
        "wavelength that can eject an electron? At threshold, photon "
        "energy equals work function. h c over lambda equals phi. "
        "Solve. Six point two four times ten to the minus seven "
        "meters. Answer A, six hundred twenty four nanometres. Deep "
        "red. Longer wavelengths cannot eject electrons no matter how "
        "bright. Only frequency matters.")),

# 43 -----------------------------------------------------------------------
chapter(43, "Atomic Structure", "ohanian_ch43_bohr",
    "The Bohr Ladder", "Energy levels are quantized",
    "Why do atoms emit only certain colours?",
    [r"E_n=-13.6/n^2\ \text{eV}"],
    [bohr("orbit"),
     num_line("ladder", (-15.0, 0.0), (-13.6, -3.4, -1.5, -0.85))],
    "I am going to show you why atoms emit only certain colours. Heat "
    "a gas. It glows. Not with a rainbow. With sharp lines. Specific "
    "colours. Every element has its own fingerprint. Hydrogen emits "
    "red at six hundred fifty six nanometres, blue-green at four "
    "eighty six, violet at four thirty four. Where do these exact "
    "wavelengths come from? Bohr's answer. The electron can only "
    "orbit at certain radii. Each orbit has a specific energy. "
    "Transitions emit or absorb a photon with energy equal to the "
    "difference. The nth orbit energy is minus thirteen point six "
    "over n squared electron volts. Ground state, minus thirteen "
    "point six. First excited, minus three point four. The difference "
    "is ten point two. That is a photon of wavelength one twenty one "
    "nanometres. Ultraviolet. The Bohr model is wrong in detail. "
    "Electrons do not orbit like planets. But it gets the energies "
    "right. It opens the door to quantum mechanics."),

# 44 -----------------------------------------------------------------------
chapter(44, "Quantum Structure", "ohanian_ch44_exclusion",
    "The Rule That Builds Chemistry",
    "No two electrons share the same state",
    "Why do atoms fill their shells instead of collapsing?",
    [r"n,\ l,\ m,\ m_s\ \text{unique per electron}"],
    [crystal("lattice"),
     potential_well("well", "0.5*x**2", (-3.0, 3.0), (0.0, 5.0))
    "I am going to show you why chemistry exists. Every electron in an "
    "atom has four quantum numbers. Principal, orbital, magnetic, "
    "spin. No two can have the same four. Pauli exclusion. This is "
    "why the periodic table exists. Without it, every electron would "
    "fall into the lowest energy state. All atoms would look like "
    "hydrogen. No chemical bonds. No life. With it, electrons fill "
    "shells one at a time. Two in the first. Eight in the second. "
    "Eighteen in the third. Outermost electrons determine chemistry. "
    "Sodium has one lonely outer electron, gives it away easily. "
    "Chlorine has seven, needs one. Table salt. Oxygen needs two. "
    "Carbon has four. Every reaction in biology is a rearrangement of "
    "outermost electrons under the rule that no two can share the "
    "same state."),

# 45 -----------------------------------------------------------------------
chapter(45, "Nuclei", "ohanian_ch45_binding",
    "Where the Missing Mass Went",
    "Mass defect equals binding energy",
    "Why does a nucleus weigh less than its parts?",
    [r"E=mc^2", r"B.E.=(\sum m_{parts}-m_{nucleus})c^2"],
    [num_line("energy", (-3.0, 3.0), (-2.5, 0.0)),
     text_("note", "mass defect = B.E. / c²")],
    "I am going to show you where the missing mass went. Take a carbon "
    "nucleus. Six protons, six neutrons. Weigh the parts. Add them "
    "up. Now weigh the whole nucleus. It weighs less. Where did the "
    "mass go? It became energy. When the nucleus formed, the nucleons "
    "pulled together and released energy. That energy left as photons "
    "and neutrinos. By special relativity, energy has mass. The "
    "energy released had a mass equivalent. It carried that mass "
    "away. The nucleus that remains weighs less. The difference is "
    "the mass defect. For most nuclei, about eight MeV per nucleon. "
    "One percent of the rest-mass energy. It sounds small. It is the "
    "entire basis of nuclear power. Four hydrogens fuse into one "
    "helium. Helium weighs less. Difference powers the Sun. Uranium "
    "splits. Fragments weigh less. Difference powers a reactor. "
    "Every time you liberate energy, some mass disappears.",
    short=mk_short("ohanian_ch45_mass_defect",
        "Mass Defect of Helium-4", "Binding energy from missing mass",
        "A helium-4 nucleus has mass 4.0015 u. Binding energy?",
        ("8 MeV", "18 MeV", "28 MeV", "48 MeV"),
        "Correct Answer: (C)",
        [r"B.E. = (2m_p + 2m_n - m_{He})c^2"],
        [num_line("energy", (-30.0, 30.0), (0.0, -28.3))],
        "Helium-4 nucleus. Two protons plus two neutrons would weigh "
        "four point zero three two u. The actual nucleus weighs four "
        "point zero zero one five u. Difference, zero point zero three "
        "zero five u. Times nine hundred thirty one point five MeV per "
        "u. About twenty eight MeV. Answer C. That is seven MeV per "
        "nucleon. Helium is unusually tightly bound, which is why it "
        "is the endpoint of fusion in stars.")),

# 46 -----------------------------------------------------------------------
chapter(46, "Elementary Particles", "ohanian_ch46_quarks",
    "What Matter Is Really Made Of",
    "Two quarks and one lepton is all you need",
    "What are protons and neutrons made of?",
    [r"p=(u,u,d),\ n=(u,d,d)"],
    [crystal("quark_lattice", color=PRIMARY),
     la_vectors("quark_sum", (2/3, 2/3), (-1/3, 0.0),
                center=(0.0, -2.0, 0.0), scale=1.5)],
    "I am going to show you what matter is really made of. Atoms "
    "first. Electrons around a nucleus. Then the nucleus splits into "
    "protons and neutrons. Then the protons and neutrons split too. "
    "Into quarks. Up and down. Two up, one down makes a proton. "
    "Charge, plus two thirds plus two thirds minus one third. Plus "
    "one. Two down, one up makes a neutron. Charge, minus one third "
    "minus one third plus two thirds. Zero. That is it. Everything "
    "around you is made of two kinds of quark and one kind of lepton. "
    "The electron. Four more quarks exist. Strange, charmed, bottom, "
    "top. Four more leptons. Muon, tau, and their neutrinos. Six "
    "quarks, six leptons, four forces. That is the standard model. "
    "Quarks never appear alone. They confine in twos and threes. Try "
    "to pull them apart and the energy becomes new quark pairs. You "
    "can never isolate one.",
    short=mk_short("ohanian_ch46_proton",
        "Charge of a Proton", "Two up, one down",
        "A proton is (u, u, d). What is its electric charge?",
        ("+1e", "0", "−1e", "−2/3 e"),
        "Correct Answer: (A)",
        [r"q_p = 2q_u + q_d"],
        [la_vectors("quarks", (2/3, 2/3), (-1/3, 0.0), scale=1.5)],
        "A proton contains two up quarks and one down quark. Up quarks "
        "carry plus two thirds of the elementary charge. Down quarks "
        "carry minus one third. Two up quarks plus one down. Plus two "
        "thirds plus two thirds minus one third. Plus one. Answer A. "
        "Every proton in the universe is that same arithmetic.")),
]


# ===========================================================================
# 6. Row assembly
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
            beats_json=arc_lecture(primary),
            target_duration_sec=180,
        )
        s = ch.get("short")
        if s:
            s_primary = s["vis"][0]["id"]
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
                beats_json=arc_short(s_primary),
                target_duration_sec=60,
            )

    return rows


# ===========================================================================
# 7. Writer and CLI
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
        f"  horizontal 3-min lectures : {len(lectures)}\n"
        f"  vertical   1-min shorts   : {len(shorts)}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="content_batch.csv",
                        help="output CSV path (default: content_batch.csv)")
    args = parser.parse_args(argv)

    rows = build_rows()
    out = Path(args.out)
    write_csv(out, rows)

    print(summarise(rows))
    print(f"→ {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
