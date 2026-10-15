#!/usr/bin/env python3
"""
generate_csv.py — Engine-driven batch with synced narration.

Rule for every row:
  * one primary engine primitive, driven by real numbers
  * one short text annotation at most
  * narration names what the engine is computing, in order
  * no OpenGL-only primitives, no off-frame coordinates
  * wave frequencies in the visible range (0.1 to 3.0), not physics Hz

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


COLUMNS: tuple[str, ...] = (
    "video_id", "concept_type", "header_title", "tagline", "question_text",
    "option_a", "option_b", "option_c", "option_d", "correct_answer",
    "equations_json", "visual_data_json", "audio_script", "orientation",
    "beats_json", "target_duration_sec",
)

LECTURE = "vertical"
SHORT   = "horizontal"

PRIMARY = "#4CC9F0"
ACCENT  = "#F1C40F"
OK      = "#2ECC71"
NEUTRAL = "#8A8F9C"


# ---------------------------------------------------------------------------
# Beats
# ---------------------------------------------------------------------------

def b(kind: str, focus: str, transition: str | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {"type": kind, "focus": focus}
    if transition:
        d["transition"] = transition
    return d


def arc_lecture(focus: str, *,
                analogy: str | None = None,
                experiment: str | None = None,
                law: str | None = None,
                midpoint: str | None = None) -> list[dict[str, Any]]:
    out = [b("promise", focus), b("hook", focus)]
    if analogy:
        out.append(b("analogy", analogy))
    if experiment:
        out.append(b("experiment", experiment))
    out.append(b("law", law or focus, transition="wipe"))
    if midpoint:
        out.append(b("midpoint", midpoint))
    out.append(b("punchline", focus))
    return out


def arc_short(focus: str, *,
              law: str | None = None) -> list[dict[str, Any]]:
    return [
        b("hook", focus),
        b("law", law or focus, transition="wipe"),
        b("punchline", focus),
    ]


# ---------------------------------------------------------------------------
# Engine primitive builders
# ---------------------------------------------------------------------------

def falling(id_, mass, height, g=9.8, orientation="vertical",
            energy_change=0.0, color=PRIMARY):
    return {"type": "falling_energy", "id": id_,
            "mass": mass, "height": height, "g": g,
            "orientation": orientation,
            "energy_change": energy_change,
            "period": 7.0, "color": color}


def wave_vis(id_, amp, wavelength, visual_freq, xr, color=PRIMARY):
    """Visible-range frequency. Not the physics frequency in Hz."""
    return {"type": "wave", "id": id_, "amplitude": amp,
            "wavelength": wavelength, "frequency": visual_freq,
            "x_range": list(xr), "color": color}


def pendulum(id_, length, gravity=9.8, angle=20.0, color=PRIMARY):
    return {"type": "pendulum", "id": id_, "length": length,
            "gravity": gravity, "angle": angle, "color": color}


def orbit(id_, radius, color=PRIMARY):
    return {"type": "orbit", "id": id_, "radius": radius, "color": color}


def momentum(id_, m1, m2, v1, v2, color=PRIMARY):
    return {"type": "momentum_exchange", "id": id_,
            "mass1": m1, "mass2": m2, "v1": v1, "v2": v2, "color": color}


def rotor(id_, shape, mass, radius, omega, torque=0.0,
          center=(0.0, 0.0, 0.0), color=PRIMARY):
    return {"type": "rotational_motion", "id": id_, "shape": shape,
            "mass": mass, "radius": radius, "angular_velocity": omega,
            "torque": torque, "center": list(center), "color": color}


def gas(id_, count=120, box=(6.0, 3.5), color=PRIMARY):
    return {"type": "particle_gas", "id": id_, "count": count,
            "box_size": list(box), "color": color}


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


def venturi(id_, ih=1.6, th=0.8, iv=2.0, dens=1000.0, ip=200000.0,
            center=(0.0, 0.0, 0.0), color=PRIMARY):
    return {"type": "fluid_dynamics", "id": id_, "operation": "venturi",
            "inlet_height": ih, "throat_height": th,
            "inlet_velocity": iv, "density": dens,
            "inlet_pressure": ip, "center": list(center), "color": color}


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


def graph(id_, expr, xr, yr, xl=6.0, yl=3.0, ctr=(0.0, 0.0, 0.0),
          color=PRIMARY):
    return {"type": "calculus_graph", "id": id_, "expression": expr,
            "x_range": list(xr), "y_range": list(yr),
            "x_length": xl, "y_length": yl, "center": list(ctr),
            "color": color}


def tangent(id_, expr, xr, yr, x0, delta,
            xl=6.0, yl=3.0, ctr=(0.0, 0.0, 0.0)):
    return {"type": "derivative_tangent", "id": id_, "expression": expr,
            "x_range": list(xr), "y_range": list(yr),
            "x_length": xl, "y_length": yl, "center": list(ctr),
            "x0": x0, "delta": delta}


def riemann(id_, expr, xr, yr, a, bb, n=12, sample="midpoint",
            color=ACCENT):
    return {"type": "riemann_sum", "id": id_, "expression": expr,
            "x_range": list(xr), "y_range": list(yr), "a": a, "b": bb,
            "rectangles": n, "sample": sample, "area_color": color}


def coil(id_, color=ACCENT):
    return {"type": "induction_coil", "id": id_, "color": color}


def compass(id_, color=ACCENT):
    return {"type": "compass_grid", "id": id_, "color": color}


def interference(id_, num_bright=6, color=PRIMARY, pos=(0.0, 0.0, 0.0)):
    return {"type": "interference_pattern", "id": id_,
            "num_bright": num_bright, "bright_color": color,
            "pos": list(pos)}


def bohr(id_, color=PRIMARY):
    return {"type": "bohr_orbit_photon", "id": id_, "color": color}


def crystal(id_, color=PRIMARY):
    return {"type": "crystal_lattice", "id": id_, "color": color}


def rolling(id_, color=PRIMARY):
    return {"type": "rolling_wheel_cycloid", "id": id_, "color": color}


def random_walk(id_, color=OK):
    return {"type": "random_walk", "id": id_, "color": color}


def two_source(id_, a, bb, wl=0.6, speed=1.5, mr=5.0, rings=5):
    return {"type": "two_source_waves", "id": id_,
            "source_a": list(a), "source_b": list(bb),
            "num_rings": rings, "wavelength": wl,
            "speed": speed, "max_radius": mr}


def text_(id_, txt, pos=(0.0, 5.5, 0.0), color=PRIMARY):
    return {"type": "text", "id": id_, "text": txt, "pos": list(pos),
            "color": color}


def dot_(id_, pos, color=ACCENT, label=None):
    d = {"type": "dot", "id": id_, "pos": list(pos), "color": color}
    if label:
        d["label"] = label
    return d


def num_line(id_, rng, markers, length=6.0, color=PRIMARY):
    return {"type": "number_line", "id": id_, "range": list(rng),
            "markers": list(markers), "length": length, "color": color}


def energy_bar(id_, pos, fill, label="E", width=5.0, color=OK):
    return {"type": "energy_bar", "id": id_, "pos": list(pos),
            "width": width, "fill": fill, "label": label, "color": color}


def equation_morph(id_, steps, pos=(0.0, 0.0, 0.0), font_size=26,
                   color=PRIMARY):
    return {"type": "equation_morph", "id": id_, "steps": list(steps),
            "pos": list(pos), "font_size": font_size, "color": color}


def numerical_chain(id_, steps, pos=(0.0, 0.0, 0.0), font_size=24,
                    color=PRIMARY):
    return {"type": "numerical_chain", "id": id_, "steps": list(steps),
            "pos": list(pos), "font_size": font_size, "color": color}


def warning_box(id_, txt, pos=(0.0, 0.0, 0.0)):
    return {"type": "warning_box", "id": id_, "text": txt,
            "pos": list(pos)}


# ---------------------------------------------------------------------------
# Row assembly
# ---------------------------------------------------------------------------

def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(**kw: Any) -> None:
        row: dict[str, Any] = {c: "" for c in COLUMNS}
        for key in ("equations_json", "visual_data_json", "beats_json"):
            if key in kw and isinstance(kw[key], (list, dict)):
                kw[key] = json.dumps(kw[key], ensure_ascii=False)
        row.update(kw)
        rows.append(row)

    # =====================================================================
    # VERTICAL LECTURES (180 s)
    # =====================================================================

    # L1 — Kinematics. Primary: derivative_tangent. Real numbers.
    add(
        video_id="lecture_kinematics_1d",
        concept_type="GENERIC",
        header_title="The Speedometer's Secret",
        tagline="Speed at an instant is a limit of averages",
        question_text="What does a speed dial actually measure?",
        equations_json=[
            r"v=\lim_{\Delta t\to 0}\frac{\Delta x}{\Delta t}",
        ],
        visual_data_json=[
            tangent("curve", "x**2/2",
                    (-2.0, 3.0), (-0.5, 4.5),
                    x0=1.5, delta=0.7,
                    xl=6.0, yl=4.0,
                    ctr=(0.0, 2.0, 0.0)),
        ],
        audio_script=(
            "I am going to show you what a speedometer is really measuring. "
            "On screen, a single curve. It is the worldline of a falling "
            "object. The horizontal axis is time. The vertical axis is "
            "position. The curve bends upward because the object keeps "
            "getting faster. Now look at the yellow line. It is a secant. "
            "It passes through two points on the curve. The slope of that "
            "secant is the average speed over the time interval between "
            "those points. I am going to shrink the interval. Watch the "
            "two points come closer together. The secant rotates. Every "
            "time I shrink the interval, the secant pivots, and its slope "
            "changes. It is approaching something. I keep shrinking. The "
            "interval is now a fraction of a second. The secant has become "
            "the green line, the tangent. The tangent touches the curve "
            "at one point only. Its slope is the instantaneous speed at "
            "that point. That is the whole idea of the derivative. The "
            "slope of the tangent is the limit of the slopes of the "
            "secants as the interval shrinks to zero. The speedometer on "
            "your car is not measuring a distance. It is computing this "
            "limit, thousands of times per second. The mathematics is "
            "inside every dial."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture("curve"),
        target_duration_sec=180,
    )

    # L2 — Two-body gravity. Real RK4 integration.
    add(
        video_id="lecture_orbit",
        concept_type="GENERIC",
        header_title="The Moon Is Falling",
        tagline="It has been falling for four billion years",
        question_text="Why does the Moon keep missing the Earth?",
        equations_json=[
            r"F=\frac{GMm}{r^2}",
            r"v=\sqrt{\frac{GM}{r}}",
        ],
        visual_data_json=[
            sim("orbit_sim",
                bodies=[
                    body(1.0, (-2.5, 0.0), (0.0, 2.2),
                         label="Moon", color=PRIMARY),
                    body(1000.0, (0.0, 0.0), (0.0, 0.0),
                         label="Earth", color=ACCENT),
                ],
                forces=[{"type": "central_gravity",
                         "source": 1, "mu": 15.0}],
                duration=20.0, playback=8.0),
        ],
        audio_script=(
            "I am going to show you the question Newton answered. Why does "
            "the Moon go around the Earth instead of falling onto it. "
            "Because it is falling. It has been falling for four billion "
            "years. It just keeps missing. On screen, two bodies. The "
            "small blue point is the Moon. The big yellow point is the "
            "Earth. The engine on screen is integrating Newton's law of "
            "gravity for every time step. At every instant, it computes "
            "the force between the two bodies. The force is proportional "
            "to the product of their masses. It is inversely proportional "
            "to the square of the distance between them. Then it applies "
            "Newton's second law. Force equals mass times acceleration. "
            "It updates the position and the velocity of the Moon. Then "
            "it takes another step. That is all. Every position on the "
            "orbit you see is the result of that calculation, repeated "
            "thousands of times. The Moon has a sideways velocity. It "
            "also feels a pull toward the Earth. Those two effects "
            "combine. The Moon falls toward the Earth, but it also moves "
            "sideways. By the time it has fallen the distance the Earth "
            "has curved away beneath it, it is somewhere else. It keeps "
            "missing. This is what an orbit is. Not a balance. Not a "
            "stillness. A continuous fall that never lands."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture("orbit_sim"),
        target_duration_sec=180,
    )

    # L3 — Pendulum. Two lengths, real oscillator.
    add(
        video_id="lecture_pendulum",
        concept_type="GENERIC",
        header_title="The Clock That Ignores Amplitude",
        tagline="The period depends only on length",
        question_text="Why does the rhythm stay the same at every swing size?",
        equations_json=[r"T=2\pi\sqrt{L/g}"],
        visual_data_json=[
            pendulum("swing", length=2.0, gravity=9.8, angle=25.0,
                     color=PRIMARY),
        ],
        audio_script=(
            "I am going to show you something that puzzled Galileo. On "
            "screen, a pendulum. It swings left. It swings right. Left "
            "again. Right again. The same rhythm, hour after hour. Here "
            "is the strange part. As the swing gets smaller, the period "
            "does not change. A small swing and a large swing take "
            "exactly the same time. This is called isochronism. Galileo "
            "noticed it as a young man watching a chandelier sway in the "
            "cathedral at Pisa. He timed it against his own pulse, "
            "because that was the only clock he had. The reason is the "
            "shape of the restoring force. Gravity pulls the bob back "
            "toward the bottom of its arc. For small angles, that force "
            "is proportional to the displacement. Double the "
            "displacement, double the force. That linearity is what "
            "makes the motion simple harmonic. It is also what makes "
            "the period independent of the amplitude. The formula is T "
            "equals two pi times the square root of L over g. Only the "
            "length and the value of g appear. Not the mass of the bob. "
            "Not the amplitude of the swing. Shorten the string, and "
            "the period decreases. Move the pendulum to the Moon, "
            "where g is smaller, and the period increases. A one metre "
            "pendulum has a period of about two seconds. That is why "
            "grandfather clocks use a pendulum roughly a metre long."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture("swing"),
        target_duration_sec=180,
    )

    # L4 — Momentum conservation. Real two-body collision.
    add(
        video_id="lecture_momentum",
        concept_type="GENERIC",
        header_title="The Universe Keeps Books",
        tagline="Total momentum is unchanged in every collision",
        question_text="Where does the momentum go in a collision?",
        equations_json=[
            r"p=mv",
            r"m_1v_1+m_2v_2=m_1v_1'+m_2v_2'",
        ],
        visual_data_json=[
            momentum("collision", 2.0, 4.0, 4.0, -2.0, color=PRIMARY),
        ],
        audio_script=(
            "I am going to show you a conservation law that surprises "
            "almost everyone. Two carts moving toward each other. The "
            "green cart has mass two kilograms. It moves at four metres "
            "per second to the right. The yellow cart has mass four "
            "kilograms. It moves at two metres per second to the left. "
            "Watch what happens when they meet. Both velocities change. "
            "The arrows on screen show the momentum. Before the "
            "collision, the green cart has momentum eight kilogram "
            "metres per second to the right. The yellow cart has minus "
            "eight, because it moves the other way. Total momentum is "
            "zero. After the collision, the velocities have changed. The "
            "green cart is now moving at some new speed. The yellow cart "
            "is now moving at some other new speed. But if you add the "
            "two momenta together, the total is still zero. Momentum is "
            "conserved. This is not a coincidence. It is Newton's third "
            "law. When the carts touch, the green cart pushes on the "
            "yellow. The yellow pushes back on the green with an equal "
            "and opposite force. The forces act for the same amount of "
            "time. So the impulses are equal and opposite. Impulse "
            "equals change in momentum. The green cart loses exactly the "
            "momentum that the yellow cart gains. The total is "
            "unchanged. This is true for every collision in the "
            "universe. Two cars, two atoms, two galaxies. Momentum never "
            "leaks."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture("collision"),
        target_duration_sec=180,
    )

    # L5 — Electric field of a dipole. Real Coulomb superposition.
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
                    charges=[{"position": [-1.5, 0.0, 0.0],
                              "charge": 2.0},
                             {"position": [1.5, 0.0, 0.0],
                              "charge": -2.0}],
                    xr=(-4.0, 4.0), yr=(-3.5, 3.5),
                    cols=11, rows=9),
        ],
        audio_script=(
            "I am going to show you how one charge knows another is "
            "nearby. It cannot see. It cannot shout. Yet bring two "
            "opposite charges together, and they attract. Faraday gave "
            "us a way to think about this. Each charge creates something "
            "in the space around it. That something is the electric "
            "field. On screen, a pair of charges. The red one on the "
            "left is positive. The blue one on the right is negative. "
            "Every arrow you see is the actual electric field vector at "
            "that point. The engine computed it from Coulomb's law. For "
            "each grid point, it sums the contribution from both "
            "charges. The positive charge pushes a test charge away. "
            "The negative charge pulls it in. The arrow you see is the "
            "vector sum. Near a charge, the arrows are long. Farther "
            "away, they get shorter. The field falls off as one over r "
            "squared. Double the distance, quarter the field. Now look "
            "at the pattern. The arrows emerge from the positive "
            "charge. They curve around. They end on the negative "
            "charge. Field lines never cross. They never start or stop "
            "in empty space. They begin on positive charge and end on "
            "negative. This is the shape of the electric field of every "
            "dipole in the universe. Every water molecule. Every "
            "antenna. Every atom."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture("dipole"),
        target_duration_sec=180,
    )

    # L6 — Magnetic field of two parallel wires. Real Biot-Savart.
    add(
        video_id="lecture_magnetic_field",
        concept_type="GENERIC",
        header_title="Magnetism Is Electricity in Disguise",
        tagline="Two wires one field",
        question_text="Why do parallel currents attract?",
        equations_json=[r"B=\mu_0 I/2\pi r"],
        visual_data_json=[
            m_field("wires",
                    wires=[{"start": [-3.5, 1.5, 0.0],
                            "end": [3.5, 1.5, 0.0],
                            "current": 5.0},
                           {"start": [-3.5, -1.5, 0.0],
                            "end": [3.5, -1.5, 0.0],
                            "current": 5.0}],
                    xr=(-4.0, 4.0), yr=(-3.5, 3.5),
                    cols=11, rows=9),
        ],
        audio_script=(
            "I am going to show you a magnetic field you can compute "
            "from first principles. On screen, two long straight wires. "
            "Each carries five amperes of current, in the same "
            "direction. Every arrow you see is the actual magnetic "
            "field vector at that point. The engine computed it by "
            "integrating the Biot-Savart law along both wires. Around "
            "each wire, the field curls in circles. Between the wires, "
            "the field from the top wire points downward. The field "
            "from the bottom wire points upward. They oppose. The "
            "arrows between the wires are short. Outside the pair, "
            "above the top and below the bottom, the fields point the "
            "same way. They add. The arrows there are long. Now here is "
            "the deeper story. Both wires carry moving electrons. Like "
            "charges should repel. So why do the wires attract. Take "
            "the rest frame of the electrons in one of the wires. In "
            "that frame, the other wire is not neutral. Length "
            "contraction packs the positive ions closer together. The "
            "wire has a net positive charge. That charge produces an "
            "electric field. The other wire feels that field. What we "
            "call magnetism in the lab frame, an observer riding on the "
            "electrons calls electricity."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture("wires"),
        target_duration_sec=180,
    )

    # L7 — Ideal gas and entropy. Real particle motion.
    add(
        video_id="lecture_entropy",
        concept_type="GENERIC",
        header_title="Why You Cannot Unstir Coffee",
        tagline="Entropy counts arrangements",
        question_text="Why does heat flow one way and never the other?",
        equations_json=[r"\Delta S\geq 0"],
        visual_data_json=[
            gas("gas", count=150, box=(6.0, 3.5), color=PRIMARY),
        ],
        audio_script=(
            "I am going to show you why you cannot un-stir coffee. On "
            "screen, a box of gas. Every particle you see is moving at "
            "a random speed, in a random direction. When two particles "
            "meet, their velocities change. The physics of each "
            "collision is reversible. If you ran the movie backward, "
            "every collision would still obey Newton's laws. So why "
            "does the gas never spontaneously gather in one corner. "
            "Watch the distribution. The particles are moving from left "
            "to right, from top to bottom, in every direction. Some of "
            "them are near the left wall. Some are near the right. The "
            "distribution is uniform. Now imagine the opposite. Imagine "
            "all the particles in the left half of the box. The number "
            "of ways to arrange them that way is astronomically small. "
            "The number of ways to spread them out is astronomically "
            "large. The system evolves toward the more numerous "
            "arrangements. Not because it is forced to. Because it is "
            "overwhelmingly more likely. This is entropy. The second "
            "law of thermodynamics says that in an isolated system, "
            "entropy never decreases. Not because the reverse is "
            "forbidden. Because the reverse is so improbable you would "
            "need to wait longer than the age of the universe to see "
            "it."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture("gas"),
        target_duration_sec=180,
    )

    # L8 — Wave on a string. Visible frequency.
    add(
        video_id="lecture_wave",
        concept_type="GENERIC",
        header_title="A Wave Is Not the Medium",
        tagline="The pattern travels while the particles stay put",
        question_text="Does the string travel with the wave?",
        equations_json=[r"v=\lambda f"],
        visual_data_json=[
            wave_vis("wave", amp=1.5, wavelength=2.5, visual_freq=0.8,
                     xr=(-4.0, 4.0), color=PRIMARY),
        ],
        audio_script=(
            "I am going to show you one of the most confusing ideas in "
            "physics. On screen, a wave travelling along a string. Watch "
            "a single point on the string. Mark it in your mind. The "
            "wave arrives. The point moves up. Then it moves down. Then "
            "it moves up again. The point never moves along the string. "
            "It only bobs in place. The wave travels. The medium does "
            "not. This is the central insight of wave physics. The wave "
            "is a pattern. The pattern moves. The particles of the "
            "medium oscillate about their equilibrium positions. They "
            "never travel with the wave. Watch the animation again. The "
            "shape you see at one instant. A moment later, the shape "
            "has shifted. But every point on the string has only moved "
            "up or down. The speed of the wave is the distance the "
            "pattern travels per second. The wavelength is the "
            "distance between two crests. The frequency is the number "
            "of crests that pass a fixed point per second. These three "
            "quantities are related by one simple equation. v equals "
            "lambda times f. Speed equals wavelength times frequency."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture("wave"),
        target_duration_sec=180,
    )

    # L9 — Fluid flow. Real continuity + Bernoulli.
    add(
        video_id="lecture_fluids",
        concept_type="GENERIC",
        header_title="Fast Air Pushes Less",
        tagline="You would have guessed more. You would be wrong.",
        question_text="Why does a sheet of paper rise when you blow across it?",
        equations_json=[
            r"p+\tfrac{1}{2}\rho v^2=\text{constant}",
            r"A_1v_1=A_2v_2",
        ],
        visual_data_json=[
            venturi("venturi", ih=1.8, th=0.9, iv=2.0,
                    dens=1000.0, ip=200000.0,
                    center=(0.0, 0.0, 0.0), color=PRIMARY),
        ],
        audio_script=(
            "I am going to show you something that contradicts "
            "intuition. Hold a sheet of paper by its edge. Blow across "
            "the top. The paper rises. You expected it to sink, because "
            "you are blowing on it. It rises instead. On screen, a pipe "
            "with a narrow throat. Water flows from left to right. The "
            "particles you see are real. Each one is advanced by the "
            "local velocity of the fluid at its position. At the "
            "narrow throat, the pipe cross section has shrunk. "
            "Continuity forces the fluid to speed up. Watch the "
            "particles accelerate through the throat. Now look at the "
            "pressure gauges. The gauge at the wide section is taller "
            "than the gauge at the throat. Higher pressure at the wide "
            "section. Lower pressure at the throat. Fast fluid, low "
            "pressure. This is Bernoulli's principle. Where the speed "
            "goes up, the pressure goes down. The reason is energy. A "
            "fast fluid element has more kinetic energy than a slow "
            "one. If nothing pushes energy in from outside, the "
            "pressure, which is a form of energy density, must drop. "
            "Every atomizer, every carburetor, every curveball, every "
            "airplane wing relies on this same fact."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture("venturi"),
        target_duration_sec=180,
    )

    # L10 — Projectile with drag. Real RK4 with linear drag.
    add(
        video_id="lecture_projectile_drag",
        concept_type="GENERIC",
        header_title="Two Projectiles One with Air",
        tagline="The trajectory without drag is not the real one",
        question_text="How much does air resistance change a projectile?",
        equations_json=[
            r"m\ddot{x}=-b\dot{x}",
            r"m\ddot{y}=-mg-b\dot{y}",
        ],
        visual_data_json=[
            sim("pair",
                bodies=[
                    body(1.0, (-3.0, 3.0), (5.0, 7.0),
                         label="vacuum", color=PRIMARY),
                    body(1.0, (-3.0, 3.0), (5.0, 7.0),
                         label="drag", color=ACCENT),
                ],
                forces=[
                    {"type": "uniform_acceleration",
                     "acceleration": [0.0, -9.8]},
                    {"type": "linear_drag",
                     "bodies": [1], "coefficient": 0.6},
                ],
                duration=2.0, playback=6.0),
        ],
        audio_script=(
            "I am going to show you how air resistance changes a "
            "trajectory. On screen, two identical objects. Same mass. "
            "Same launch position. Same launch velocity. The blue "
            "trajectory has no air resistance. The yellow trajectory "
            "has linear drag. The engine integrates the equations of "
            "motion for both at every time step. Watch what happens. At "
            "the start, the two paths are almost identical. Then they "
            "diverge. The yellow object peaks earlier. It reaches a "
            "lower peak. By the time it descends, it is well behind "
            "the blue. It lands sooner and travels less distance. This "
            "is drag. Every real projectile experiences it. The drag "
            "force depends on speed. The faster the object, the more "
            "air it pushes aside. The force points opposite the "
            "velocity. For slow objects, drag is proportional to speed. "
            "For fast objects, it grows as the square of the speed. The "
            "trajectory is no longer a parabola. Every golf ball, every "
            "baseball, every cannonball follows this shape. In the "
            "vacuum of a physics textbook, the parabola is exact. In "
            "the real world, drag always wins."
        ),
        orientation=LECTURE,
        beats_json=arc_lecture("pair"),
        target_duration_sec=180,
    )

    # =====================================================================
    # HORIZONTAL SHORTS (60 s)
    # =====================================================================

    # S1 — Pendulum period. Real oscillator.
    add(
        video_id="short_pendulum",
        concept_type="GENERIC",
        header_title="Why Pendulums Keep Time",
        tagline="The period ignores mass and amplitude",
        question_text="A one metre pendulum swings. What is its period?",
        option_a="0.5 s", option_b="1.0 s",
        option_c="2.0 s", option_d="4.0 s",
        correct_answer="Correct Answer: (C)",
        equations_json=[r"T=2\pi\sqrt{L/g}"],
        visual_data_json=[
            pendulum("swing", length=1.0, gravity=9.8, angle=15.0,
                     color=PRIMARY),
        ],
        audio_script=(
            "A pendulum one metre long. What is its period. The formula "
            "is T equals two pi times the square root of L over g. Plug "
            "in L equals one, g equals nine point eight. The square "
            "root of one over nine point eight is about zero point "
            "three two. Two pi times that is about two seconds. Notice "
            "that the period does not depend on the mass of the bob. It "
            "does not depend on the amplitude either. That is why "
            "pendulums were clocks for three centuries. Answer C."
        ),
        orientation=SHORT,
        beats_json=arc_short("swing"),
        target_duration_sec=60,
    )

    # S2 — Projectile range. Real trajectory.
    add(
        video_id="short_projectile",
        concept_type="GENERIC",
        header_title="Projectile Range",
        tagline="30 and 60 give the same range",
        question_text="A ball launches at 20 m/s at 30 degrees. What is its range?",
        option_a="17 m", option_b="35 m",
        option_c="40 m", option_d="70 m",
        correct_answer="Correct Answer: (B)",
        equations_json=[r"R=\frac{v_0^2\sin 2\theta}{g}"],
        visual_data_json=[
            sim("ball",
                bodies=[body(1.0, (-6.0, 0.5), (17.3, 10.0),
                             label="ball", color=PRIMARY)],
                forces=[{"type": "uniform_acceleration",
                         "acceleration": [0.0, -9.8]}],
                duration=2.1, playback=6.0),
        ],
        audio_script=(
            "A ball launched at twenty metres per second, thirty "
            "degrees above horizontal. Watch the trajectory on screen. "
            "The engine integrated Newton's second law at every time "
            "step. The horizontal velocity stays constant. The vertical "
            "velocity is pulled down by gravity. The result is a "
            "parabola. To find the range, use R equals v zero squared "
            "sine two theta over g. v zero squared is four hundred. "
            "Sine of sixty degrees is about zero point eight six six. "
            "Divide by nine point eight. About thirty five metres. "
            "Answer B. If you fired at sixty degrees instead of thirty, "
            "you would get the same range. Sine of two theta is "
            "symmetric about forty five degrees."
        ),
        orientation=SHORT,
        beats_json=arc_short("ball"),
        target_duration_sec=60,
    )

    # S3 — Two carts. Real collision integration.
    add(
        video_id="short_collision",
        concept_type="GENERIC",
        header_title="The Ballistic Pendulum",
        tagline="Momentum is conserved. Energy is not.",
        question_text="A 20 g bullet at 300 m/s embeds in a 500 g block. What is the block speed?",
        option_a="7.5 m/s", option_b="11.5 m/s",
        option_c="15 m/s", option_d="20 m/s",
        correct_answer="Correct Answer: (B)",
        equations_json=[r"m_1v_1=(m_1+m_2)v'"],
        visual_data_json=[
            momentum("collision", 0.02, 0.5, 300.0, 0.0, color=PRIMARY),
        ],
        audio_script=(
            "A twenty gram bullet at three hundred metres per second "
            "hits a stationary five hundred gram block. The bullet "
            "embeds. Before the collision, only the bullet is moving. "
            "Its momentum is zero point zero two times three hundred, "
            "which is six kilogram metres per second. After the "
            "collision, the bullet and block move together. Their "
            "combined mass is zero point five two kilograms. Momentum "
            "is conserved, so the final speed is six divided by zero "
            "point five two, which is eleven point five metres per "
            "second. Answer B. Notice that kinetic energy is not "
            "conserved. Before, nine hundred joules. After, only about "
            "thirty four. The rest went into deforming the block and "
            "heating it."
        ),
        orientation=SHORT,
        beats_json=arc_short("collision"),
        target_duration_sec=60,
    )

    # S4 — Rotating disk. Real moment of inertia.
    add(
        video_id="short_torque",
        concept_type="GENERIC",
        header_title="Torque on a Solid Disk",
        tagline="The moment of inertia sets the response",
        question_text="A 12 newton metre torque acts on a 4 kg, 0.5 m disk. What is the angular acceleration?",
        option_a="3 rad/s^2", option_b="6 rad/s^2",
        option_c="12 rad/s^2", option_d="24 rad/s^2",
        correct_answer="Correct Answer: (D)",
        equations_json=[
            r"\tau=I\alpha",
            r"I=\tfrac{1}{2}MR^2",
        ],
        visual_data_json=[
            rotor("disk", "solid_disk", 4.0, 1.0, 0.0, 12.0,
                  center=(0.0, 0.0, 0.0), color=PRIMARY),
        ],
        audio_script=(
            "A solid disk. Mass four kilograms. Radius half a metre. A "
            "torque of twelve newton metres is applied. What is the "
            "angular acceleration. The moment of inertia of a solid "
            "disk is one half m r squared. Plug in. One half times four "
            "times zero point two five. That is zero point five "
            "kilogram metre squared. The angular acceleration is torque "
            "divided by moment of inertia. Twelve divided by zero point "
            "five. That is twenty four radians per second squared. "
            "Answer D. A hoop of the same mass and radius would have a "
            "moment of inertia of m r squared, which is twice as large. "
            "Its angular acceleration would be half."
        ),
        orientation=SHORT,
        beats_json=arc_short("disk"),
        target_duration_sec=60,
    )

    # S5 — Wave. Visible frequency.
    add(
        video_id="short_wave",
        concept_type="GENERIC",
        header_title="Count Crests at the Pier",
        tagline="Speed equals wavelength times frequency",
        question_text="A wave has wavelength 2 m and frequency 5 Hz. What is its speed?",
        option_a="0.4 m/s", option_b="2.5 m/s",
        option_c="7 m/s", option_d="10 m/s",
        correct_answer="Correct Answer: (D)",
        equations_json=[r"v=\lambda f"],
        visual_data_json=[
            wave_vis("wave", amp=1.0, wavelength=2.0, visual_freq=1.5,
                     xr=(-4.0, 4.0), color=PRIMARY),
        ],
        audio_script=(
            "Stand at a pier and count the crests. Five crests pass "
            "every second. Each crest is two metres behind the one in "
            "front. In one second, five waves times two metres each "
            "equals ten metres of wave train. So the speed is ten "
            "metres per second. That is the whole of v equals lambda f. "
            "Speed equals wavelength times frequency. It applies to "
            "sound, to light, to water, to every wave in physics. "
            "Answer D."
        ),
        orientation=SHORT,
        beats_json=arc_short("wave"),
        target_duration_sec=60,
    )

    # S6 — Particle gas. Real random motion.
    add(
        video_id="short_rms",
        concept_type="GENERIC",
        header_title="Hot Light Molecules",
        tagline="Same temperature, lighter is faster",
        question_text="At the same temperature, do lighter or heavier molecules move faster?",
        option_a="lighter", option_b="heavier",
        option_c="same speed", option_d="depends on pressure",
        correct_answer="Correct Answer: (A)",
        equations_json=[r"v_{rms}=\sqrt{3RT/M}"],
        visual_data_json=[
            gas("gas", count=120, box=(6.0, 3.5), color=PRIMARY),
        ],
        audio_script=(
            "Watch the gas particles on screen. Every particle is "
            "moving at a random speed. The temperature of the gas is "
            "the average kinetic energy of the particles. At the same "
            "temperature, every gas has the same average kinetic "
            "energy. Kinetic energy is one half m v squared. So if one "
            "gas is lighter than the other, its particles must move "
            "faster. The formula is v rms equals the square root of "
            "three R T over M. R is the gas constant. T is the "
            "temperature. M is the molar mass. Hydrogen has molar mass "
            "two. Oxygen has molar mass thirty two. Hydrogen is "
            "sixteen times lighter. Its rms speed is four times larger. "
            "Answer A. This is why hydrogen escapes from the Earth's "
            "atmosphere and oxygen stays."
        ),
        orientation=SHORT,
        beats_json=arc_short("gas"),
        target_duration_sec=60,
    )

    # S7 — Coulomb force. Real field.
    add(
        video_id="short_coulomb",
        concept_type="GENERIC",
        header_title="Which Force Wins",
        tagline="Coulomb beats gravity by 10^39",
        question_text="Ratio of electric to gravitational force between an electron and a proton?",
        option_a="10^10", option_b="10^20",
        option_c="2.3e39", option_d="10^50",
        correct_answer="Correct Answer: (C)",
        equations_json=[r"\frac{F_E}{F_G}=\frac{ke^2}{Gm_em_p}"],
        visual_data_json=[
            e_field("pair",
                    charges=[{"position": [-2.0, 0.0, 0.0],
                              "charge": 1.0},
                             {"position": [2.0, 0.0, 0.0],
                              "charge": -1.0}],
                    xr=(-4.0, 4.0), yr=(-3.0, 3.0),
                    cols=9, rows=7),
        ],
        audio_script=(
            "Take an electron and a proton. Compare the electric force "
            "to the gravitational force. Both follow inverse square "
            "laws. The ratio is independent of distance. On screen, the "
            "field between two opposite charges. The electric field "
            "pulls them together. The gravitational field also pulls "
            "them together. But the electric force is much stronger. "
            "k e squared over r squared. Gravitational force is G m e m "
            "p over r squared. Divide. The r squared cancels. Plug in. "
            "Two point three times ten to the thirty nine. That is two "
            "thousand billion billion billion billion. Answer C. And "
            "yet gravity runs the universe. Because positive and "
            "negative charges cancel on large scales. Mass never "
            "cancels. Mass always adds."
        ),
        orientation=SHORT,
        beats_json=arc_short("pair"),
        target_duration_sec=60,
    )

    # S8 — Riemann. Real numerical integration.
    add(
        video_id="short_riemann",
        concept_type="GENERIC",
        header_title="Area Under the Curve",
        tagline="How an integral is computed",
        question_text="What is the area under the curve f(x) = 0.5x^2 + 1 from x=0 to x=2?",
        option_a="2.0", option_b="3.0",
        option_c="3.33", option_d="4.5",
        correct_answer="Correct Answer: (C)",
        equations_json=[r"\int_0^2\left(\tfrac{x^2}{2}+1\right)dx=\tfrac{10}{3}"],
        visual_data_json=[
            riemann("strips", "0.5*x**2+1",
                    (0.0, 2.0), (0.0, 3.0), 0.0, 2.0,
                    n=12, sample="midpoint",
                    color=ACCENT),
        ],
        audio_script=(
            "We want the area under the curve f of x equals zero point "
            "five x squared plus one from x equals zero to x equals "
            "two. On screen, twelve rectangles. Each rectangle is "
            "sampled at its midpoint. The engine on screen evaluates "
            "the function at every midpoint, multiplies by the width, "
            "and adds the results. The sum is an approximation. With "
            "twelve rectangles, the answer is very close to the exact "
            "value. The exact value is the integral from zero to two of "
            "x squared over two plus one, which equals ten over three, "
            "or three point three three. Answer C."
        ),
        orientation=SHORT,
        beats_json=arc_short("strips"),
        target_duration_sec=60,
    )

    # S9 — Bohr atom. Real energy levels.
    add(
        video_id="short_bohr",
        concept_type="GENERIC",
        header_title="The Bohr Ladder",
        tagline="Energy levels are quantized",
        question_text="Why do atoms emit only certain colours?",
        option_a="because of gravity", option_b="because of quantized energy",
        option_c="because of temperature", option_d="because of pressure",
        correct_answer="Correct Answer: (B)",
        equations_json=[r"E_n=-13.6/n^2\text{ eV}"],
        visual_data_json=[
            bohr("atom", color=PRIMARY),
        ],
        audio_script=(
            "Watch the atom on screen. The electron orbits the nucleus. "
            "In Bohr's model, only certain orbits are allowed. The "
            "innermost orbit has energy minus thirteen point six "
            "electron volts. The next has minus three point four. The "
            "third has minus one point five. Now watch what happens "
            "when the electron drops from the second orbit to the "
            "first. It emits a photon. The photon carries exactly the "
            "energy difference. Ten point two electron volts. That "
            "corresponds to one specific wavelength of ultraviolet "
            "light. When the electron jumps from the third orbit to the "
            "second, the energy difference is smaller. The photon has a "
            "longer wavelength. Visible red light. Different jumps, "
            "different colours. Answer B."
        ),
        orientation=SHORT,
        beats_json=arc_short("atom"),
        target_duration_sec=60,
    )

    # S10 — Interference. Real two-source pattern.
    add(
        video_id="short_interference",
        concept_type="GENERIC",
        header_title="Two Sources One Pattern",
        tagline="Superposition creates fringes",
        question_text="What kind of pattern does a two-slit experiment produce?",
        option_a="single band", option_b="alternating bright and dark bands",
        option_c="two bands", option_d="no pattern",
        correct_answer="Correct Answer: (B)",
        equations_json=[r"d\sin\theta=m\lambda"],
        visual_data_json=[
            two_source("sources",
                       a=(-2.0, 0.8, 0.0), bb=(-2.0, -0.8, 0.0),
                       wl=0.6, speed=1.5, mr=5.0, rings=6),
        ],
        audio_script=(
            "Two slits. Two sources. On screen, each source sends out "
            "a circular wave. The waves overlap. Where a crest from one "
            "source meets a crest from the other, the amplitudes add. "
            "Bright. Where a crest meets a trough, they cancel. Dark. "
            "The result is a pattern of alternating bright and dark "
            "bands on the screen. This is the double-slit interference "
            "pattern. It was first demonstrated by Thomas Young in "
            "eighteen hundred and one. It was the experiment that "
            "settled the wave nature of light. Answer B. Every bright "
            "band corresponds to a path difference that is an integer "
            "multiple of the wavelength."
        ),
        orientation=SHORT,
        beats_json=arc_short("sources"),
        target_duration_sec=60,
    )

    return rows


# ---------------------------------------------------------------------------
# Writer and CLI
# ---------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS,
                                quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="content_batch.csv")
    args = parser.parse_args(argv)

    rows = build_rows()
    write_csv(Path(args.out), rows)
    lectures = sum(1 for r in rows if r["orientation"] == LECTURE)
    shorts = sum(1 for r in rows if r["orientation"] == SHORT)
    print(f"Wrote {len(rows)} rows "
          f"({lectures} vertical lectures, {shorts} horizontal shorts)")
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
