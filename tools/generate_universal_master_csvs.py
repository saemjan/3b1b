#!/usr/bin/env python3
"""
generate_universal_master_csvs.py

Rewrites master CSV files for the saemjan/3b1b pipeline.

Creates:
  content/master_horizontal.csv
  content/master_vertical.csv
  content_batch.csv

Design goals:
  - Feynman-correct conceptual framing.
  - 3Blue1Brown-style visual/beats structure.
  - Wide physics coverage.
  - Safe CSV generation with nested JSON.
  - Schema-compatible output.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

FIELDNAMES = [
    "video_id",
    "concept_type",
    "header_title",
    "tagline",
    "question_text",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct_answer",
    "equations_json",
    "visual_data_json",
    "audio_script",
    "orientation",
    "beats_json",
    "target_duration_sec",
]

BRIDGE = (
    "The animation asks three questions: What system is being studied? "
    "What quantity is being tracked? What rule keeps the accounting consistent? "
    "When these questions are answered, a pretty picture becomes a physical argument. "
    "The equation is then not a decoration; it is the compressed statement of the pattern."
)

FEYNMAN_OUTRO = (
    "The Feynman method is not to memorize formulas. "
    "First say what the system is and what objects belong to it. "
    "Then name the assumptions and decide which effects are small enough to ignore. "
    "Next choose the bookkeeping quantity: energy, momentum, charge, probability amplitude, entropy, or phase. "
    "Follow that quantity through every stage and ask where it is stored, how it is transferred, and what remains constant. "
    "Connect the picture to an equation, check the units, and test a limiting case. "
    "The animation is a model, not a literal photograph. "
    "It exaggerates the important relationships so that the eye can see what the mathematics says. "
    "If a prediction fails, inspect the boundary, the assumptions, or the bookkeeping. "
    "That is how visual beauty becomes reliable physics."
)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text))


def compose_script(base_script: str, min_words: int = 205) -> str:
    script = base_script.strip()

    if word_count(script) < min_words:
        script = f"{script} {BRIDGE}"

    if word_count(script) < min_words:
        script = f"{script} {FEYNMAN_OUTRO}"

    while word_count(script) < min_words:
        script = f"{script} {FEYNMAN_OUTRO}"

    return script


def make_beats(orientation: str) -> str:
    if orientation == "vertical":
        beats = [
            {"type": "hook", "focus": "model"},
            {"type": "promise", "focus": "math", "transition": "push"},
            {"type": "experiment", "focus": "model", "transition": "wipe"},
            {"type": "law", "focus": "math", "transition": "zoom_blur"},
            {"type": "emphasis", "focus": "model", "transition": "push"},
            {"type": "punchline", "focus": "caption", "transition": "wipe"},
        ]
    else:
        beats = [
            {"type": "hook", "focus": "model"},
            {"type": "promise", "focus": "math", "transition": "push"},
            {"type": "experiment", "focus": "model", "transition": "wipe"},
            {"type": "law", "focus": "math", "transition": "zoom_blur"},
            {"type": "midpoint", "focus": "model", "transition": "push"},
            {"type": "experiment", "focus": "model", "transition": "wipe"},
            {"type": "emphasis", "focus": "math", "transition": "zoom_blur"},
            {"type": "punchline", "focus": "caption", "transition": "push"},
            {"type": "cta", "focus": "caption", "transition": "wipe"},
        ]

    return json.dumps(beats, ensure_ascii=False)


def build_model_params(orientation: str, primitive: str, spec: dict) -> dict:
    params = dict(spec.get("model_params", {}))

    if primitive == "particle_gas":
        if orientation == "vertical":
            params.setdefault("container_dims", [3.4, 3.2])
        else:
            params.setdefault("container_dims", [6.8, 3.0])
        params.setdefault("num_particles", 18)
        params.setdefault("speed", 1.0)

    if primitive in {"falling_energy", "energy_bar"}:
        params.setdefault("orientation", orientation)

    if primitive == "falling_energy":
        params.setdefault("period", 7.0)
        params.setdefault("energy_change", 98.1)

    if primitive == "energy_bar":
        params.setdefault("period", 6.0)

    if primitive == "two_path_interference":
        params.setdefault("slits", 2)

    if primitive == "quiz_frame":
        params.setdefault("question", spec.get("question_text", ""))

    return params


def make_visual_data(orientation: str, spec: dict) -> str:
    primitive = spec["primitive"]

    if orientation == "vertical":
        title_pos = [0.0, 6.8, 0.0]
        model_pos = [0.0, 1.0, 0.0]
        math_pos = [0.0, -2.8, 0.0]
        caption_pos = [0.0, -6.7, 0.0]
        title_size = 34
        math_size = 26
        caption_size = 24
    else:
        title_pos = [0.0, 3.8, 0.0]
        model_pos = [0.0, 0.4, 0.0]
        math_pos = [0.0, -1.8, 0.0]
        caption_pos = [0.0, -3.6, 0.0]
        title_size = 32
        math_size = 24
        caption_size = 22

    model_params = build_model_params(orientation, primitive, spec)

    model_element = {
        "type": primitive,
        "id": "model",
        "pos": model_pos,
        "color": spec.get("color", "#4CC9F0"),
    }
    model_element.update(model_params)

    elements = [
        {
            "type": "text",
            "id": "title",
            "text": spec["header_title"],
            "pos": title_pos,
            "color": "#F2F3F5",
            "font_size": title_size,
        },
        model_element,
        {
            "type": "text",
            "id": "math",
            "text": spec["math_text"],
            "pos": math_pos,
            "color": "#8AC926",
            "font_size": math_size,
        },
        {
            "type": "text",
            "id": "caption",
            "text": spec["caption"],
            "pos": caption_pos,
            "color": "#F1C40F",
            "font_size": caption_size,
        },
    ]

    return json.dumps(elements, ensure_ascii=False)


def build_row(orientation: str, spec: dict) -> dict:
    duration = 180 if orientation == "horizontal" else 60

    return {
        "video_id": spec["id"],
        "concept_type": spec["concept_type"],
        "header_title": spec["header_title"],
        "tagline": spec["tagline"],
        "question_text": spec["question_text"],
        "option_a": spec["option_a"],
        "option_b": spec["option_b"],
        "option_c": spec["option_c"],
        "option_d": spec["option_d"],
        "correct_answer": spec["correct_answer"],
        "equations_json": json.dumps(spec["equations"], ensure_ascii=False),
        "visual_data_json": make_visual_data(orientation, spec),
        "audio_script": compose_script(spec["script"]),
        "orientation": orientation,
        "beats_json": make_beats(orientation),
        "target_duration_sec": duration,
    }


HORIZONTAL_SPECS = [
    {
        "id": "hz_mech_least_action",
        "concept_type": "MECHANICS",
        "header_title": "The Principle of Least Action",
        "tagline": "Nature chooses stationary paths",
        "question_text": "Why does a mechanical path get selected?",
        "option_a": "The object looks ahead",
        "option_b": "The action is stationary",
        "option_c": "Force is minimized",
        "option_d": "Speed is maximized",
        "correct_answer": "B",
        "equations": [
            r"S = \int_{t_1}^{t_2} (T - V) dt",
            r"\delta S = 0",
        ],
        "primitive": "calculus_graph",
        "math_text": "Action: S = integral of (T - V) dt",
        "caption": "the physical path makes action stationary",
        "color": "#4CC9F0",
        "script": (
            "A thrown ball traces a parabola, but the deeper rule is not that the ball looks ahead. "
            "Nature compares possible histories using a quantity called the action, the time integral of kinetic energy minus potential energy. "
            "The actual path is the one for which small variations do not change the action to first order. "
            "This is the principle of least action. It turns motion into geometry: among all imaginable paths, "
            "the physical path makes the action stationary. The same idea organizes optics, mechanics, fields, and quantum phases."
        ),
    },
    {
        "id": "hz_mech_energy_bookkeeping",
        "concept_type": "MECHANICS",
        "header_title": "Energy Is Bookkeeping",
        "tagline": "Follow the stores, not the words",
        "question_text": "What is the central habit in energy problems?",
        "option_a": "Memorize formulas",
        "option_b": "Define system and track energy stores",
        "option_c": "Ignore the surroundings",
        "option_d": "Assume energy disappears",
        "correct_answer": "B",
        "equations": [
            r"U_g = mgh",
            r"K = \frac{1}{2}mv^2",
            r"\Delta K + \Delta U = 0",
        ],
        "primitive": "falling_energy",
        "math_text": "Potential falls as kinetic rises",
        "caption": "energy is transferred, not destroyed",
        "color": "#F1C40F",
        "script": (
            "Energy is not a substance; it is a bookkeeping rule. When an object falls, gravitational potential energy decreases "
            "while kinetic energy increases. If we choose the system carefully and include every relevant interaction, "
            "the total account balances. The animation shows one store becoming another. The lesson is not the formula m g h by itself. "
            "The lesson is to define the system, identify the energy stores, track transfers, and check the balance. "
            "When the balance seems wrong, some hidden store such as heat, sound, or deformation was omitted."
        ),
    },
    {
        "id": "hz_rot_angular_momentum",
        "concept_type": "MECHANICS",
        "header_title": "Angular Momentum and Precession",
        "tagline": "Torque changes direction",
        "question_text": "Why does a spinning top precess?",
        "option_a": "Gravity vanishes",
        "option_b": "Torque changes angular momentum direction",
        "option_c": "Friction reverses gravity",
        "option_d": "The top becomes massless",
        "correct_answer": "B",
        "equations": [
            r"\vec{\tau} = \frac{d\vec{L}}{dt}",
            r"\vec{L} = I\vec{\omega}",
        ],
        "primitive": "rotational_motion",
        "math_text": "Torque changes the direction of L",
        "caption": "precession is vector bookkeeping",
        "color": "#F72585",
        "script": (
            "A spinning top does not simply resist falling. Its angular momentum is a vector, and gravity produces a torque "
            "that changes the direction of that vector. The result is precession: the axis moves sideways instead of dropping immediately. "
            "The same vector rule explains bicycle wheels, gyroscopes, and planetary orientation. "
            "The visual goal is to make torque perpendicular to angular momentum visible. "
            "Once the vector relationship is seen, the surprising stability is no longer magic. "
            "It is conservation and direction acting together."
        ),
    },
    {
        "id": "hz_em_gauss_law",
        "concept_type": "ELECTROMAGNETISM",
        "header_title": "Gauss's Law as Symmetry",
        "tagline": "Count field lines through surfaces",
        "question_text": "What does electric flux through a closed surface measure?",
        "option_a": "Magnetic charge",
        "option_b": "Enclosed electric charge",
        "option_c": "The surface area only",
        "option_d": "The wire resistance",
        "correct_answer": "B",
        "equations": [
            r"\Phi_E = \oint \vec{E}\cdot d\vec{A}",
            r"\Phi_E = \frac{Q_{\rm in}}{\epsilon_0}",
        ],
        "primitive": "electric_field",
        "math_text": "Flux through a closed surface measures charge inside",
        "caption": "symmetry turns flux into algebra",
        "color": "#3A86FF",
        "script": (
            "Gauss's law says that electric flux through a closed surface measures the charge inside. "
            "The power of the law comes from symmetry. If the field is radial, uniform over a spherical surface, "
            "or planar over a flat symmetry, the flux integral becomes a simple product. "
            "Then the field can be found without brute-force integration. "
            "The animation should show field lines crossing a closed surface and the count depending only on enclosed charge. "
            "The law is bookkeeping for electric field lines."
        ),
    },
    {
        "id": "hz_em_faraday_lenz",
        "concept_type": "ELECTROMAGNETISM",
        "header_title": "Faraday and Lenz",
        "tagline": "The minus sign protects energy",
        "question_text": "Why is there a minus sign in Faraday's law?",
        "option_a": "Convention only",
        "option_b": "Induced current opposes the change",
        "option_c": "Magnetic fields are negative",
        "option_d": "It corrects measurement error",
        "correct_answer": "B",
        "equations": [
            r"\mathcal{E} = -\frac{d\Phi_B}{dt}",
            r"\nabla \times \vec{E} = -\frac{\partial \vec{B}}{\partial t}",
        ],
        "primitive": "vector_field",
        "math_text": "Changing flux induces an opposing response",
        "caption": "Lenz's law is conservation of energy",
        "color": "#4361EE",
        "script": (
            "Faraday's law says a changing magnetic flux induces an electromotive force. "
            "The minus sign is Lenz's law: the induced current opposes the change that created it. "
            "This is not a decorative sign convention; it is conservation of energy. "
            "If the induced current helped the change, a magnet and coil could amplify themselves into a perpetual-motion machine. "
            "The animation shows a changing flux, an induced field, and the opposition. "
            "The equation becomes a causal story: change, response, constraint."
        ),
    },
    {
        "id": "hz_wave_double_slit",
        "concept_type": "QUANTUM",
        "header_title": "Double Slit Amplitudes",
        "tagline": "Add arrows, not probabilities",
        "question_text": "What interferes in the double-slit experiment?",
        "option_a": "Classical forces",
        "option_b": "Probability amplitudes",
        "option_c": "Air pressure",
        "option_d": "Gravitational waves",
        "correct_answer": "B",
        "equations": [
            r"P = |\psi_1 + \psi_2|^2",
            r"\psi = e^{i(kx - \omega t)}",
        ],
        "primitive": "two_path_interference",
        "math_text": "Probability = squared length of total amplitude",
        "caption": "arrows add tip to tail",
        "color": "#7209B7",
        "script": (
            "The double-slit experiment is the central mystery of quantum mechanics. "
            "An electron is described by a probability amplitude, often drawn as a rotating arrow. "
            "Each path contributes an arrow, and the arrows are added tip to tail. "
            "The probability is the square of the length of the final arrow. "
            "Where arrows reinforce, detection is likely; where they cancel, darkness appears. "
            "The lesson is not that the electron is a tiny billiard ball. "
            "It is that quantum probabilities are amplitudes, not ordinary probabilities."
        ),
    },
    {
        "id": "hz_wave_doppler",
        "concept_type": "WAVES",
        "header_title": "Doppler Geometry",
        "tagline": "Motion changes crest spacing",
        "question_text": "Why does frequency shift when source and observer move?",
        "option_a": "Wave speed becomes infinite",
        "option_b": "Crest spacing changes in the observer frame",
        "option_c": "The medium disappears",
        "option_d": "Frequency is not physical",
        "correct_answer": "B",
        "equations": [
            r"f' = f \frac{v \pm v_o}{v \mp v_s}",
        ],
        "primitive": "wave_pulse",
        "math_text": "Moving source compresses or stretches wavelength",
        "caption": "frequency shift is geometry in time",
        "color": "#06D6A0",
        "script": (
            "The Doppler effect is not a trick of the detector alone; it follows from wave crests and relative motion. "
            "If a source moves toward an observer, crests are emitted closer together in the observer's frame, so frequency rises. "
            "If the source recedes, crest spacing increases and frequency falls. "
            "The animation makes this geometric: wave pulses, moving source, compressed wavelength in front, stretched wavelength behind. "
            "The equation then becomes a bookkeeping of distances and times between successive crests."
        ),
    },
    {
        "id": "hz_thermo_entropy",
        "concept_type": "THERMODYNAMICS",
        "header_title": "Entropy Is Counting",
        "tagline": "Microstates decide the arrow of time",
        "question_text": "What does entropy count?",
        "option_a": "Heat particles",
        "option_b": "Microstates compatible with a macrostate",
        "option_c": "Atomic colors",
        "option_d": "Absolute stillness",
        "correct_answer": "B",
        "equations": [
            r"S = k_B \ln \Omega",
        ],
        "primitive": "particle_gas",
        "math_text": "Entropy grows because probable arrangements dominate",
        "caption": "statistics creates the arrow of time",
        "color": "#8AC926",
        "script": (
            "Entropy is often stated as disorder, but the sharper idea is counting. "
            "A macrostate is what we can observe: pressure, temperature, volume. "
            "A microstate is one detailed arrangement of all the particles. "
            "Entropy measures how many microstates correspond to the same macrostate. "
            "Ink spreads because mixed arrangements vastly outnumber separated ones. "
            "The Second Law is therefore not a mysterious push; it is overwhelming statistics. "
            "The animation should show particles exploring many arrangements and the system moving toward the larger collection of possibilities."
        ),
    },
    {
        "id": "hz_quantum_uncertainty",
        "concept_type": "QUANTUM",
        "header_title": "Uncertainty Is Fourier Geometry",
        "tagline": "Narrow pulse, wide spectrum",
        "question_text": "Why does localization spread momentum?",
        "option_a": "Measurement clumsiness only",
        "option_b": "A narrow wave packet needs many wavelengths",
        "option_c": "Momentum is imaginary",
        "option_d": "Particles stop moving",
        "correct_answer": "B",
        "equations": [
            r"\Delta x \Delta p \geq \frac{\hbar}{2}",
        ],
        "primitive": "harmonic_decomposition",
        "math_text": "Localized wave needs many momentum components",
        "caption": "uncertainty is built into waves",
        "color": "#FF006E",
        "script": (
            "The uncertainty principle is not only about clumsy measurement. It is a mathematical property of waves. "
            "A sharply localized wave packet requires many wavelengths, and in quantum mechanics wavelength is related to momentum. "
            "Therefore a narrow position distribution implies a broad momentum distribution. "
            "The animation uses Fourier decomposition: squeeze the pulse in space, and its spectrum spreads. "
            "The inequality Delta x Delta p >= hbar/2 becomes a statement about how waves are built, "
            "not about experimental imperfections alone."
        ),
    },
    {
        "id": "hz_problem_projectile_energy",
        "concept_type": "PROBLEM",
        "header_title": "Projectile Energy Problem",
        "tagline": "Use conservation before algebra",
        "question_text": "What is the cleanest way to find final speed after a fall?",
        "option_a": "Memorize trajectory formulas",
        "option_b": "Use energy conservation",
        "option_c": "Ignore gravity",
        "option_d": "Assume mass cancels only for rockets",
        "correct_answer": "B",
        "equations": [
            r"mgh = \frac{1}{2}mv^2",
            r"v = \sqrt{2gh}",
        ],
        "primitive": "projectile_motion",
        "math_text": "Potential energy lost becomes kinetic energy gained",
        "caption": "conservation replaces complicated tracking",
        "color": "#FB5607",
        "script": (
            "A projectile problem becomes simpler when we separate directions and use energy carefully. "
            "Horizontally, velocity remains constant if air resistance is ignored. "
            "Vertically, gravity changes the vertical speed and exchanges potential energy for kinetic energy. "
            "The problem asks us to define the system, choose the reference height, and track the energy balance. "
            "The final speed can be found from the drop height without knowing every detail of the path. "
            "This is the Feynman approach: use conservation to replace complicated motion with reliable bookkeeping."
        ),
    },
]


VERTICAL_SPECS = [
    {
        "id": "vz_mech_projectile",
        "concept_type": "MECHANICS",
        "header_title": "Projectile Motion",
        "tagline": "Two simple stories at once",
        "question_text": "Why is projectile motion parabolic?",
        "option_a": "Gravity bends space",
        "option_b": "Horizontal motion is uniform while vertical motion accelerates",
        "option_c": "Air pushes the object",
        "option_d": "The object chooses a curve",
        "correct_answer": "B",
        "equations": [
            r"x = v_x t",
            r"y = v_{0y}t - \frac{1}{2}gt^2",
        ],
        "primitive": "projectile_motion",
        "math_text": "x uniform, y accelerated",
        "caption": "independent directions combine into a parabola",
        "color": "#4CC9F0",
        "script": (
            "A projectile keeps moving sideways because nothing horizontal pushes it, while gravity changes only the vertical motion. "
            "The path is a parabola because one direction is uniform and the other has constant acceleration. "
            "The visual separates the two components and then combines them. "
            "The key insight is independence of perpendicular motions. "
            "Once seen, projectile motion is not a pile of formulas; it is two simple stories happening at once."
        ),
    },
    {
        "id": "vz_rot_gyro",
        "concept_type": "MECHANICS",
        "header_title": "Why Tops Precess",
        "tagline": "Angular momentum is a vector",
        "question_text": "Why does a spinning top not simply fall?",
        "option_a": "Gravity is cancelled",
        "option_b": "Torque changes the direction of angular momentum",
        "option_c": "The top becomes lighter",
        "option_d": "Air holds it up",
        "correct_answer": "B",
        "equations": [
            r"\vec{\tau} = \frac{d\vec{L}}{dt}",
        ],
        "primitive": "rotational_motion",
        "math_text": "Torque redirects L",
        "caption": "precession is vector motion",
        "color": "#F72585",
        "script": (
            "A spinning top does not fall straight down because gravity creates torque, and torque changes the direction of angular momentum. "
            "The axis therefore precesses instead of simply tipping. "
            "The vector picture makes the surprise understandable. "
            "The angular momentum vector is dragged sideways by the torque. "
            "This is the same geometry behind gyroscopes and stable bicycles. "
            "The lesson is vector direction, not mysterious anti-gravity."
        ),
    },
    {
        "id": "vz_energy_bars",
        "concept_type": "MECHANICS",
        "header_title": "Energy Bars",
        "tagline": "Make conservation visible",
        "question_text": "What do energy bars teach?",
        "option_a": "Energy disappears",
        "option_b": "Energy stores exchange while total stays balanced",
        "option_c": "Only kinetic energy matters",
        "option_d": "Potential energy is imaginary",
        "correct_answer": "B",
        "equations": [
            r"\Delta K + \Delta U = 0",
        ],
        "primitive": "energy_bar",
        "math_text": "One store falls, another rises",
        "caption": "define the system first",
        "color": "#F1C40F",
        "script": (
            "Energy bars make conservation visible. As an object falls, one bar shrinks while another grows. "
            "The total remains fixed if no energy escapes the chosen system. "
            "If friction or air resistance matters, a third bar for thermal energy must appear. "
            "The visual teaches the habit of defining the system before applying formulas. "
            "Conservation becomes an account you can check, not an equation you memorize."
        ),
    },
    {
        "id": "vz_em_electric_field",
        "concept_type": "ELECTROMAGNETISM",
        "header_title": "Electric Field Lines",
        "tagline": "A map of force per charge",
        "question_text": "What do electric field lines represent?",
        "option_a": "Physical strings",
        "option_b": "Direction of force on a positive test charge",
        "option_c": "Magnetic poles",
        "option_d": "Gravitational contours",
        "correct_answer": "B",
        "equations": [
            r"\vec{E} = \frac{\vec{F}}{q}",
        ],
        "primitive": "electric_field",
        "math_text": "E = force per unit charge",
        "caption": "field patterns reveal symmetry",
        "color": "#3A86FF",
        "script": (
            "Electric field lines show the direction a positive test charge would be pushed. "
            "Near a positive source, lines point outward; near a negative source, they point inward. "
            "The density of lines suggests field strength. "
            "The field is not a physical string; it is a map of force per charge. "
            "The visual makes symmetry visible. Once the pattern is seen, Gauss's law becomes counting lines through surfaces."
        ),
    },
    {
        "id": "vz_em_magnetic_loops",
        "concept_type": "ELECTROMAGNETISM",
        "header_title": "Magnetic Loops",
        "tagline": "No magnetic monopoles",
        "question_text": "Why do magnetic field lines form closed loops?",
        "option_a": "They are circular magnets",
        "option_b": "The divergence of B is zero",
        "option_c": "Air bends them",
        "option_d": "Electric fields push them",
        "correct_answer": "B",
        "equations": [
            r"\nabla \cdot \vec{B} = 0",
        ],
        "primitive": "magnetic_field",
        "math_text": "div B = 0",
        "caption": "field lines have no beginning or end",
        "color": "#4361EE",
        "script": (
            "Magnetic field lines form closed loops because no isolated magnetic monopole has been observed. "
            "If you cut a magnet, you do not isolate a north pole; you make two smaller dipoles. "
            "The visual shows loops leaving one side and returning to the other. "
            "Mathematically, the divergence of B is zero. "
            "The lesson is that magnetism has a geometry different from electrostatics."
        ),
    },
    {
        "id": "vz_wave_packet",
        "concept_type": "WAVES",
        "header_title": "Wave Packets",
        "tagline": "Envelope versus ripples",
        "question_text": "What moves with the particle in a wave packet?",
        "option_a": "The phase ripples only",
        "option_b": "The envelope or group",
        "option_c": "The medium",
        "option_d": "Nothing moves",
        "correct_answer": "B",
        "equations": [
            r"v_g = \frac{d\omega}{dk}",
        ],
        "primitive": "wave_pulse",
        "math_text": "group velocity carries the packet",
        "caption": "separate envelope from ripples",
        "color": "#06D6A0",
        "script": (
            "A quantum particle is often represented by a wave packet. "
            "The packet's overall envelope moves with the group velocity, while the ripples inside move with the phase velocity. "
            "The envelope carries the particle's probability and energy. "
            "The visual separates these two motions. "
            "This distinction explains why a wave can have internal ripples without the particle itself moving faster than allowed."
        ),
    },
    {
        "id": "vz_double_slit_arrows",
        "concept_type": "QUANTUM",
        "header_title": "Quantum Arrows",
        "tagline": "Interference is vector addition",
        "question_text": "What should be added in quantum interference?",
        "option_a": "Probabilities directly",
        "option_b": "Probability amplitudes",
        "option_c": "Forces",
        "option_d": "Masses",
        "correct_answer": "B",
        "equations": [
            r"P = |\psi_1 + \psi_2|^2",
        ],
        "primitive": "two_path_interference",
        "math_text": "add amplitudes, then square",
        "caption": "canceling arrows make dark bands",
        "color": "#7209B7",
        "script": (
            "In the double-slit experiment, add arrows, not probabilities. "
            "Each path contributes a complex amplitude, represented by a rotating arrow. "
            "The arrows are placed tip to tail, and the final length squared gives probability. "
            "Cancellation produces dark bands. "
            "The visual makes quantum interference a geometric addition. "
            "The mystery becomes clear without pretending the electron is a classical pebble."
        ),
    },
    {
        "id": "vz_thermo_gas_pressure",
        "concept_type": "THERMODYNAMICS",
        "header_title": "Gas Pressure",
        "tagline": "Many tiny collisions",
        "question_text": "What causes gas pressure?",
        "option_a": "A static fluid force",
        "option_b": "Molecular collisions with walls",
        "option_c": "Gravity only",
        "option_d": "Chemical color",
        "correct_answer": "B",
        "equations": [
            r"PV = Nk_B T",
        ],
        "primitive": "particle_gas",
        "math_text": "pressure = average momentum transfer",
        "caption": "microscopic motion becomes macroscopic force",
        "color": "#8AC926",
        "script": (
            "Gas pressure comes from countless molecular collisions with a container wall. "
            "Each collision transfers momentum, and the average of many collisions produces a smooth force. "
            "Temperature measures the average molecular kinetic energy. "
            "The visual shows random motion and links microscopic impacts to macroscopic pressure. "
            "The ideal gas law then becomes statistical bookkeeping, not magic."
        ),
    },
    {
        "id": "vz_quantum_tunneling",
        "concept_type": "QUANTUM",
        "header_title": "Quantum Tunneling",
        "tagline": "Waves leak through barriers",
        "question_text": "Why can a quantum particle cross a classically forbidden barrier?",
        "option_a": "It breaks the barrier",
        "option_b": "Its wavefunction decays but leaks through",
        "option_c": "It becomes heavier",
        "option_d": "Classical physics allows it",
        "correct_answer": "B",
        "equations": [
            r"\psi \sim e^{-\kappa x}",
        ],
        "primitive": "wave_pulse",
        "math_text": "exponential decay can leak through",
        "caption": "tunneling is wave leakage",
        "color": "#FF006E",
        "script": (
            "Quantum tunneling happens because a particle is described by a wavefunction. "
            "At a barrier, the wave does not stop instantly; it decays exponentially. "
            "If the barrier is thin enough, some amplitude leaks through. "
            "The particle can appear on the far side even when classical energy is insufficient. "
            "The visual shows exponential decay and leakage. "
            "This is how alpha decay and many modern devices work."
        ),
    },
    {
        "id": "vz_problem_energy_mcq",
        "concept_type": "PROBLEM",
        "header_title": "Energy MCQ",
        "tagline": "Choose the balance",
        "question_text": "If losses are ignored, what equals kinetic energy gained?",
        "option_a": "Potential energy lost",
        "option_b": "Mass lost",
        "option_c": "Time lost",
        "option_d": "Force gained",
        "correct_answer": "A",
        "equations": [
            r"mgh = \frac{1}{2}mv^2",
        ],
        "primitive": "quiz_frame",
        "math_text": "potential lost = kinetic gained",
        "caption": "use the energy account",
        "color": "#FB5607",
        "script": (
            "A quick energy problem asks: what system, what initial store, what final store? "
            "If losses are ignored, potential energy lost equals kinetic energy gained. "
            "The correct choice follows from the balance, not from guessing force formulas. "
            "The visual uses energy bars and a numerical chain. "
            "The habit is always the same: define the system, track the stores, check units, and confirm the limiting behavior."
        ),
    },
]


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=FIELDNAMES,
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()

        for row in rows:
            clean_row = {key: row.get(key, "") for key in FIELDNAMES}
            writer.writerow(clean_row)


def main() -> None:
    horizontal_rows = [build_row("horizontal", spec) for spec in HORIZONTAL_SPECS]
    vertical_rows = [build_row("vertical", spec) for spec in VERTICAL_SPECS]

    horizontal_path = CONTENT_DIR / "master_horizontal.csv"
    vertical_path = CONTENT_DIR / "master_vertical.csv"
    combined_path = ROOT / "content_batch.csv"

    write_csv(horizontal_path, horizontal_rows)
    write_csv(vertical_path, vertical_rows)
    write_csv(combined_path, horizontal_rows + vertical_rows)

    print("Generated:")
    print(horizontal_path)
    print(vertical_path)
    print(combined_path)

    print()
    print("Validate horizontal:")
    print("SAEM_ORIENTATION=horizontal python schema_validator.py content/master_horizontal.csv")
    print()
    print("Validate vertical:")
    print("SAEM_ORIENTATION=vertical python schema_validator.py content/master_vertical.csv")


if __name__ == "__main__":
    main()
