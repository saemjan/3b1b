#!/usr/bin/env python3
"""
generate_csv.py — Feynman-voiced, 3b1b-styled batch generator.

Design contract
---------------
* Horizontal rows  →  3-minute GENERIC lectures  (target_duration_sec=180)
* Vertical rows    →  1-minute PYQ shorts        (target_duration_sec=60)

Style rules enforced by hand, not by code:
  1. Every script opens on a concrete image (shopping cart, pier, skater,
     sheet of paper) and ends on a punchline that reframes the whole idea.
  2. Every row carries ONE primary visual that advances the argument,
     plus at most one annotation that names the surprise.
  3. Colours are semantic — the audience learns the code within a topic:
        PRIMARY  →  the subject of the story
        ACCENT   →  the contrast, marker, or second body
        WARM     →  reserved for warnings / pathological cases
  4. Beats are build → tension → resolution, not a slide deck:
        hook       →  open on the image
        emphasis   →  point at the counterintuitive bit
        law        →  the equation, arriving as consequence
        punchline  →  the reframe

Run:
    python3 generate_csv.py                 # writes content_batch.csv
    python3 generate_csv.py --out foo.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 1. Schema
# ---------------------------------------------------------------------------

COLUMNS: tuple[str, ...] = (
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
)

ORIENTATION_LECTURE = "horizontal"   # 180 s, bounds x∈[-8,8], y∈[-4.5,4.5]
ORIENTATION_SHORT   = "vertical"     #  60 s, bounds x∈[-4.5,4.5], y∈[-8,8]

# Semantic palette — do not add new colours without a matching meaning.
PRIMARY = "#4CC9F0"     # subject of the story
ACCENT  = "#F1C40F"     # contrast, marker, second body
WARM    = "#E74C3C"     # reserved for failure modes (unused in this batch)

# Beat vocabulary (see schema_validator.py for the authoritative set).
HOOK      = "hook"
LAW       = "law"
EMPHASIS  = "emphasis"
PUNCHLINE = "punchline"


# ---------------------------------------------------------------------------
# 2. Primitive helpers
# ---------------------------------------------------------------------------

def beat(kind: str, focus: str, *, transition: str | None = None) -> dict[str, Any]:
    """One story beat. `focus` must match a visual object's `id`."""
    b: dict[str, Any] = {"type": kind, "focus": focus}
    if transition:
        b["transition"] = transition
    return b


def vec(id_: str, start: tuple[float, float, float],
        end: tuple[float, float, float], *, color: str = ACCENT) -> dict[str, Any]:
    return {
        "type": "vector", "id": id_,
        "start": list(start), "end": list(end), "color": color,
    }


def label(id_: str, text: str,
          pos: tuple[float, float, float] = (0.0, 3.8, 0.0)) -> dict[str, Any]:
    return {"type": "text", "id": id_, "text": text, "pos": list(pos)}


def orbit(id_: str, radius: float, *, color: str = PRIMARY) -> dict[str, Any]:
    return {"type": "orbit", "id": id_, "radius": radius, "color": color}


def wave(id_: str, *, amplitude: float, wavelength: float, frequency: float,
         x_range: tuple[float, float], color: str = PRIMARY) -> dict[str, Any]:
    return {
        "type": "wave", "id": id_,
        "amplitude": amplitude, "wavelength": wavelength, "frequency": frequency,
        "x_range": list(x_range), "color": color,
    }


def pendulum(id_: str, *, length: float, gravity: float, angle: float,
             color: str = PRIMARY) -> dict[str, Any]:
    return {
        "type": "pendulum", "id": id_,
        "length": length, "gravity": gravity, "angle": angle, "color": color,
    }


def collision(id_: str, *, m1: float, m2: float, v1: float, v2: float,
              color: str = PRIMARY) -> dict[str, Any]:
    return {
        "type": "momentum_exchange", "id": id_,
        "mass1": m1, "mass2": m2, "v1": v1, "v2": v2, "color": color,
    }


def calc_graph(id_: str, *, expression: str, x_range, y_range,
               x_length: float, y_length: float, center) -> dict[str, Any]:
    return {
        "type": "calculus_graph", "id": id_,
        "expression": expression,
        "x_range": list(x_range), "y_range": list(y_range),
        "x_length": x_length, "y_length": y_length, "center": list(center),
    }


def integral(id_: str, *, expression: str, x_range, y_range, a: float, b: float,
             color: str = PRIMARY) -> dict[str, Any]:
    return {
        "type": "integral_area", "id": id_,
        "expression": expression,
        "x_range": list(x_range), "y_range": list(y_range),
        "a": a, "b": b, "color": color,
    }


def e_field(id_: str, *, charge: float, x_range, y_range, columns: int, rows: int) -> dict[str, Any]:
    return {
        "type": "electric_field", "id": id_,
        "charges": [{"position": [0.0, 0.0, 0.0], "charge": charge}],
        "x_range": list(x_range), "y_range": list(y_range),
        "columns": columns, "rows": rows,
    }


def venturi(id_: str, *, inlet_height: float, throat_height: float,
            inlet_velocity: float, density: float, inlet_pressure: float,
            particle_count: int = 14, color: str = PRIMARY) -> dict[str, Any]:
    return {
        "type": "fluid_dynamics", "id": id_, "operation": "venturi",
        "inlet_height": inlet_height, "throat_height": throat_height,
        "inlet_velocity": inlet_velocity, "density": density,
        "inlet_pressure": inlet_pressure, "particle_count": particle_count,
        "color": color,
    }


def projectile(id_: str, *, v0: float, angle: float, g: float,
               color: str = PRIMARY) -> dict[str, Any]:
    return {"type": "projectile_motion", "id": id_, "v0": v0, "angle": angle,
            "g": g, "color": color}


def rotor(id_: str, *, shape: str, mass: float, radius: float,
          angular_velocity: float, torque: float, color: str = PRIMARY) -> dict[str, Any]:
    return {
        "type": "rotational_motion", "id": id_, "shape": shape,
        "mass": mass, "radius": radius,
        "angular_velocity": angular_velocity, "torque": torque, "color": color,
    }


# ---------------------------------------------------------------------------
# 3. Row builder
# ---------------------------------------------------------------------------

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
            raise ValueError(f"row {kw.get('video_id')!r} missing: {missing}")
        rows.append(row)

    # =====================================================================
    # A. HORIZONTAL 3-MINUTE CONCEPT LECTURES
    # =====================================================================

    add(
        video_id="lecture_newton_second_law",
        concept_type="GENERIC",
        header_title="Why Heavy Things Don't Fall Faster",
        tagline="Force and inertia cancel in free fall",
        question_text="Why do a heavy ball and a light ball land together?",
        equations_json=[
            r"F_{net}=ma",
            r"a=\frac{F_{net}}{m}",
        ],
        visual_data_json=[
            {"type": "falling_energy", "id": "fall", "mass": 5.0,
             "height": 7.0, "g": 9.8, "color": PRIMARY},
            label("mass_note", "a = g, whatever the mass"),
        ],
        audio_script=(
            "Push an empty shopping cart. It rolls away easily. Now load it with "
            "bricks and push with the same effort. It crawls. Nothing about your "
            "push changed. The cart's mass changed, and with it the cart's "
            "response to your push. This is Newton's second law: net force "
            "equals mass times acceleration. Rearrange it. Acceleration equals "
            "force divided by mass. The acceleration is what you see. The force "
            "is what you do. The mass is what the object resists with. Now the "
            "strange part. Drop a heavy ball and a light ball from the same "
            "height. Which lands first? Aristotle said the heavy one. Almost "
            "everyone's intuition agrees. But they land together. Why? The heavy "
            "ball feels a bigger gravitational pull: twice the mass, twice the "
            "weight. But twice the mass also means twice the inertia, twice the "
            "resistance to being moved. The two effects cancel exactly. The "
            "acceleration comes out the same. Galileo's famous experiment was "
            "shocking not because objects fall, but because the thing that "
            "should have made the heavy one fall faster is exactly the thing "
            "that makes it harder to move at all. Force and inertia are two "
            "sides of one coin. This is why, when the only force is gravity, "
            "mass drops out of the equation entirely. In a vacuum, a hammer and "
            "a feather fall side by side. On Earth the feather loses because air "
            "pushes back on it, and that push depends on shape, not on mass. "
            "Strip the air away, and the difference disappears. The second law "
            "works in every direction, independently. Write it once for x, once "
            "for y, once for z. This is why a thrown ball keeps moving sideways "
            "at the same speed while it falls. The horizontal motion does not "
            "know the vertical motion exists. They do not interfere. That single "
            "fact is the entire logic of projectile motion."
        ),
        orientation=ORIENTATION_LECTURE,
        beats_json=[
            beat(HOOK, "fall"),
            beat(EMPHASIS, "mass_note", transition="wipe"),
            beat(PUNCHLINE, "fall"),
        ],
        target_duration_sec=180,
    )

    add(
        video_id="lecture_gravity_orbit",
        concept_type="GENERIC",
        header_title="The Moon Is Falling",
        tagline="It has been falling for four billion years",
        question_text="Why does the Moon keep missing the Earth?",
        equations_json=[
            r"F=\frac{GMm}{r^2}",
            r"v=\sqrt{\frac{GM}{r}}",
        ],
        visual_data_json=[
            orbit("orbit", 4.0, color=PRIMARY),
            {"type": "dot", "id": "earth", "pos": [0.0, 0.0, 0.0],
             "color": ACCENT, "label": "Earth"},
        ],
        audio_script=(
            "Newton's apple is the most famous fruit in physics. But the apple "
            "is only half the story. Newton's real question was about the Moon. "
            "Why does the Moon go around the Earth instead of falling onto it? "
            "Here is the answer he found. The Moon is falling. It has been "
            "falling for four and a half billion years. It just keeps missing. "
            "Imagine throwing a ball horizontally from a very tall tower. Throw "
            "it gently, and it lands a little way off. Throw it harder, and it "
            "lands farther. Throw it hard enough, and something strange happens. "
            "The Earth curves away beneath it as fast as the ball falls toward "
            "it. The ball is falling the whole time, but the ground is also "
            "dropping away. It never lands. That is an orbit. The Moon is doing "
            "exactly this. Gravity pulls it toward Earth, constantly, without "
            "pause. But the Moon has just the right sideways speed, so instead "
            "of crashing, it curves around. And there is a beautiful "
            "relationship hiding in this. Set the gravitational force equal to "
            "the centripetal force needed to keep the Moon on its circle. The "
            "orbital speed comes out to v equals the square root of G M over r. "
            "It depends only on the central mass and the radius. Not on the "
            "Moon's mass. Not on what the Moon is made of. A tiny satellite and "
            "a giant moon at the same radius orbit at the same speed. Kepler "
            "noticed this from the data long before Newton explained it: the "
            "square of the period is proportional to the cube of the radius. In "
            "Newton's hands, that becomes a statement about gravity itself. An "
            "inverse-square law that reaches across the solar system. Everything "
            "in space is a balance between falling, and moving sideways fast "
            "enough to keep missing."
        ),
        orientation=ORIENTATION_LECTURE,
        beats_json=[
            beat(HOOK, "orbit"),
            beat(EMPHASIS, "earth", transition="wipe"),
            beat(PUNCHLINE, "orbit"),
        ],
        target_duration_sec=180,
    )

    add(
        video_id="lecture_momentum_collision",
        concept_type="GENERIC",
        header_title="The Universe Keeps Books",
        tagline="Two skaters push off and never meet again",
        question_text="Where does the motion come from when two skaters push apart?",
        equations_json=[
            r"p=mv",
            r"m_1v_1+m_2v_2=m_1v_1'+m_2v_2'",
        ],
        visual_data_json=[
            collision("collision", m1=2.0, m2=4.0, v1=0.0, v2=0.0, color=PRIMARY),
            label("zero", "total p = 0 before and after"),
        ],
        audio_script=(
            "Two ice skaters stand at rest, facing each other, hands touching. "
            "They push. Immediately they move apart, one gliding backward, the "
            "other gliding backward the other way. But wait. They started at "
            "rest. Total momentum was zero. They end in motion, in opposite "
            "directions. Total momentum is still zero, because momentum is a "
            "vector and the two arrows cancel. Nothing about this is obvious. "
            "Where did the motion come from? It came from the push. But here is "
            "the deep fact underneath: for every action there is an equal and "
            "opposite reaction. Skater A pushes on skater B. Skater B pushes "
            "back on skater A with the same force. Same force, same time, "
            "opposite directions. Newton's third law. Multiply force by time and "
            "you get impulse, which equals change in momentum. The two impulses "
            "are equal and opposite. So the two momentum changes are equal and "
            "opposite. The total is unchanged. Always. This is why momentum "
            "conservation is not a theorem about ice or about skaters. It is a "
            "statement that the universe keeps books. No matter how complicated "
            "the collision, no matter how many pieces fly off, the vector sum of "
            "all momenta before equals the vector sum after. Kinetic energy is "
            "not so lucky. In a perfectly elastic collision it survives. In an "
            "inelastic one it leaks into heat and deformation. But momentum "
            "never leaks. It is the most reliable accounting in physics."
        ),
        orientation=ORIENTATION_LECTURE,
        beats_json=[
            beat(HOOK, "collision"),
            beat(EMPHASIS, "zero", transition="wipe"),
            beat(PUNCHLINE, "collision"),
        ],
        target_duration_sec=180,
    )

    add(
        video_id="lecture_shm_pendulum",
        concept_type="GENERIC",
        header_title="The Clock That Ignores Amplitude",
        tagline="A pendulum's period depends only on its length",
        question_text="Why does a pendulum keep the same rhythm at every swing size?",
        equations_json=[r"T=2\pi\sqrt{\frac{L}{g}}"],
        visual_data_json=[
            pendulum("pendulum", length=2.0, gravity=9.8, angle=18.0, color=PRIMARY),
            label("period", "T depends only on L"),
        ],
        audio_script=(
            "Watch a grandfather clock. The pendulum swings, back and forth, back "
            "and forth, at the same tempo, hour after hour. Here is what is "
            "strange. As the clock runs down, the swing gets smaller. The bob "
            "travels a shorter arc. Yet the period does not change. A small "
            "swing and a large swing take exactly the same time. Why? Look at "
            "the forces. The restoring force on the bob comes from gravity "
            "pulling it back toward the bottom. For small angles, that force is "
            "proportional to the displacement. Double the displacement, double "
            "the force. That linearity is what makes the motion simple harmonic, "
            "and what makes the period independent of how far the bob swings. It "
            "is called isochronism, and Galileo noticed it while watching a "
            "chandelier sway in a cathedral. He timed it against his own pulse. "
            "The period depends only on the length of the pendulum and on g. Not "
            "on the mass of the bob. Not on the amplitude, as long as the angle "
            "stays small. Shorten the string, and the clock runs fast. Move the "
            "clock to the Moon, where g is smaller, and it runs slow. This is "
            "why pendulum clocks must be adjusted for latitude: the Earth is not "
            "perfectly round, so g varies slightly from place to place. A "
            "pendulum one meter long has a period of about two seconds. Cut it "
            "to a quarter of a meter, and the period halves to one second. "
            "Everything about the motion scales, but the rhythm stays pure."
        ),
        orientation=ORIENTATION_LECTURE,
        beats_json=[
            beat(HOOK, "pendulum"),
            beat(EMPHASIS, "period", transition="wipe"),
            beat(PUNCHLINE, "pendulum"),
        ],
        target_duration_sec=180,
    )

    add(
        video_id="lecture_wave_properties",
        concept_type="GENERIC",
        header_title="Counting Crests at a Pier",
        tagline="The wave equation is just bookkeeping",
        question_text="What actually makes v = λf true?",
        equations_json=[r"v=\lambda f"],
        visual_data_json=[
            wave("wave", amplitude=1.2, wavelength=3.0, frequency=1.0,
                 x_range=(-6.0, 6.0), color=PRIMARY),
            label("note", "count crests, measure spacing"),
        ],
        audio_script=(
            "Imagine you are standing on a pier, counting the crests that slap "
            "against a post. You count five crests in one second. So the "
            "frequency is five hertz. Now you notice the spacing between crests. "
            "Each crest is two meters behind the one in front. So the wavelength "
            "is two meters. In that one second, how far has the wave train "
            "moved? You counted five crests, each two meters apart. So the "
            "leading edge must have traveled ten meters. The speed is ten meters "
            "per second. That is the entire content of v equals lambda times f. "
            "It is not a law someone handed down from on high. It is "
            "bookkeeping. You counted crests, you measured spacing, you "
            "multiplied. The equation is what your counting already implied. Now "
            "the surprising consequence. The frequency is set by the source. If "
            "a boat bobs up and down twice a second, it launches two crests per "
            "second, forever. The speed is set by the medium. On deep water, "
            "waves travel fast; on shallow water, they slow down. So when a wave "
            "train moves from deep water into shallow water, the frequency "
            "cannot change, but the speed does. That means the wavelength must "
            "stretch or shrink to keep the product true. Move to deeper water, "
            "and crests spread apart. The wave has no choice. The universe "
            "enforces the accounting."
        ),
        orientation=ORIENTATION_LECTURE,
        beats_json=[
            beat(HOOK, "wave"),
            beat(EMPHASIS, "note", transition="wipe"),
            beat(PUNCHLINE, "wave"),
        ],
        target_duration_sec=180,
    )

    add(
        video_id="lecture_fluid_bernoulli",
        concept_type="GENERIC",
        header_title="Blow Across a Sheet of Paper",
        tagline="It rises. You would have guessed it would sink.",
        question_text="Why does fast-moving air push less?",
        equations_json=[r"p+\frac{1}{2}\rho v^2=\text{constant}"],
        visual_data_json=[
            venturi("venturi", inlet_height=1.8, throat_height=0.9,
                    inlet_velocity=2.0, density=1000, inlet_pressure=200000,
                    color=PRIMARY),
            label("note", "faster flow, lower pressure"),
        ],
        audio_script=(
            "Hold a sheet of paper by its edge and blow across the top. The "
            "paper lifts. Most people expect it to be pushed down, because you "
            "are blowing on it. It rises instead. Here is why. Moving air has "
            "lower pressure than still air at the same height. This is "
            "Bernoulli's principle, and it is one of the most counterintuitive "
            "facts in everyday physics. The reason is energy. A fluid element "
            "moving fast has more kinetic energy than one moving slowly. If "
            "nothing else is pushing energy into the fluid, then the pressure, "
            "which is a form of energy density, must drop to compensate. "
            "Pressure plus half rho v squared plus rho g h equals a constant "
            "along a streamline. Where the speed goes up, the pressure must go "
            "down. Watch this in a venturi tube. The pipe narrows, and by "
            "continuity the fluid must speed up to get through the tight "
            "section. But as the fluid speeds up, its pressure drops. You can "
            "see the pressure drop directly if you stick a vertical tube into "
            "the narrow section: the fluid rises less than it does in the wide "
            "section. Every atomizer, every carburetor, every chimney, every "
            "curveball, and every airplane wing leans on this same fact. The air "
            "on the curved top of a wing moves faster than the air underneath, "
            "so the pressure up there is lower, and the wing is pushed upward. "
            "Not because the wing is being sucked up, but because the ordinary "
            "pressure underneath has no counterweight above. Fast air, low "
            "pressure. Slow air, high pressure. It is that simple and that "
            "strange."
        ),
        orientation=ORIENTATION_LECTURE,
        beats_json=[
            beat(HOOK, "venturi"),
            beat(EMPHASIS, "note", transition="wipe"),
            beat(PUNCHLINE, "venturi"),
        ],
        target_duration_sec=180,
    )

    add(
        video_id="lecture_electric_field",
        concept_type="GENERIC",
        header_title="The Field Is the Messenger",
        tagline="How a charge knows another charge is nearby",
        question_text="How does one charge feel another without touching it?",
        equations_json=[
            r"E=\frac{F}{q}",
            r"E=\frac{kQ}{r^2}",
        ],
        visual_data_json=[
            e_field("field", charge=2e-6,
                    x_range=(-6.0, 6.0), y_range=(-3.5, 3.5),
                    columns=13, rows=9),
        ],
        audio_script=(
            "How does one charge know another charge is nearby? It cannot see. "
            "It cannot shout. Yet if you bring two positive charges close "
            "together, they repel, instantly, with no visible connection "
            "between them. Newton called this action at a distance, and he "
            "hated it. He thought it was the greatest absurdity in physics. "
            "Faraday found a way out. Instead of saying that one charge "
            "reaches across space and pulls on another, say that each charge "
            "creates something in the space around it. That something is the "
            "electric field. Picture a small positive test charge you can "
            "carry around. At every point in space, the field tells you what "
            "force that test charge would feel. Near a positive charge, the "
            "field arrows point outward, like porcupine quills. Farther away, "
            "they thin out. Double the distance, and each arrow gets four "
            "times weaker, because the field falls off as one over r squared. "
            "Now place a second charge in this field. It does not need to know "
            "that the first charge exists. It only feels the field at its own "
            "location, and responds locally. The first charge creates the "
            "field. The field travels. The second charge responds. Action at a "
            "distance becomes two local events, connected by a messenger. This "
            "is one of the great conceptual shifts in physics, and it is why "
            "the field concept survived from Faraday to Maxwell to Einstein. A "
            "charge never reaches across space. It only changes the space right "
            "around it."
        ),
        orientation=ORIENTATION_LECTURE,
        beats_json=[
            beat(HOOK, "field"),
            beat(LAW, "field", transition="wipe"),
            beat(PUNCHLINE, "field"),
        ],
        target_duration_sec=180,
    )

    add(
        video_id="lecture_work_energy",
        concept_type="GENERIC",
        header_title="Push Harder as You Go",
        tagline="Work is the area under the force curve",
        question_text="How do you add up a force that keeps changing?",
        equations_json=[
            r"W=\int_a^b F\,dx",
            r"W_{net}=\Delta K",
        ],
        visual_data_json=[
            calc_graph("force_curve", expression="2*x+1",
                       x_range=(0.0, 3.0), y_range=(0.0, 8.0),
                       x_length=5.0, y_length=3.0,
                       center=(0.0, 0.0, 0.0)),
            integral("work_area", expression="2*x+1",
                     x_range=(1.0, 3.0), y_range=(0.0, 8.0), a=1.0, b=3.0,
                     color=PRIMARY),
        ],
        audio_script=(
            "Imagine pushing a crate across a rough warehouse floor. At first, "
            "easy. As you go, the resistance grows, and you have to push "
            "harder. When you finally reach the far wall, you are tired. Where "
            "did your energy go? Into the crate, in the form of kinetic energy, "
            "and into friction, in the form of heat. But how much went into the "
            "crate? You cannot just multiply force by distance, because the "
            "force kept changing. Here is the trick. Break the whole journey "
            "into tiny steps, each so short that the force is essentially "
            "constant across it. On each tiny step, the work is force times "
            "step length: a little rectangle under the force curve. Add up all "
            "the rectangles, and you get the total work. Take the limit as the "
            "steps shrink to zero, and the sum becomes an integral. The work "
            "done by a variable force is the area under the force-versus-"
            "position curve. That is all calculus is: it is bookkeeping for "
            "things that change. And once you have the total work, the work-"
            "energy theorem tells you what it did. The net work on the object "
            "equals the change in its kinetic energy. Push with more net work "
            "than friction removes, and the object speeds up. Push with less, "
            "and it slows down. This is not a new law. It is Newton's second "
            "law, integrated over position, dressed up in energy language. But "
            "the phrasing is powerful, because energy bookkeeping ignores the "
            "messy details of the trajectory. You only need the beginning and "
            "the end."
        ),
        orientation=ORIENTATION_LECTURE,
        beats_json=[
            beat(HOOK, "force_curve"),
            beat(EMPHASIS, "work_area", transition="wipe"),
            beat(PUNCHLINE, "force_curve"),
        ],
        target_duration_sec=180,
    )

    add(
        video_id="lecture_projectile_motion",
        concept_type="GENERIC",
        header_title="Drop and Shoot Land Together",
        tagline="Horizontal motion does not help you fall",
        question_text="Which hits the ground first, a dropped ball or a fired one?",
        equations_json=[
            r"x=v_{0x}t",
            r"y=-\tfrac{1}{2}gt^2",
        ],
        visual_data_json=[
            projectile("path", v0=8.0, angle=0.0, g=9.8, color=PRIMARY),
            {"type": "falling_energy", "id": "drop", "mass": 1.0,
             "height": 3.0, "g": 9.8, "color": ACCENT},
        ],
        audio_script=(
            "Stand on a table with two identical balls. Hold one in each hand. "
            "Drop the left one straight down. At the same instant, fire the "
            "right one horizontally, as fast as you can. Which hits the floor "
            "first? Almost everyone says the fired one will take longer, "
            "because it has farther to travel. It does have farther to travel. "
            "But it does not take longer. Both hit the floor at the same "
            "instant. The reason is that horizontal motion and vertical motion "
            "do not talk to each other. Gravity pulls down. It has no opinion "
            "about horizontal speed. A ball moving at five meters per second "
            "sideways falls at exactly the same rate as one moving at fifty. "
            "The vertical fall is identical. It is as if the horizontal motion "
            "did not exist. This is Newton's second law, split into components. "
            "F x equals zero, so a x equals zero, so v x is constant. F y "
            "equals minus m g, so a y equals minus g, so the ball accelerates "
            "downward at exactly the same rate as a dropped ball. The two "
            "motions combine into a curve, but they are two separate stories. "
            "Once you see this, projectile problems become easy. Write the "
            "horizontal motion as a straight line. Write the vertical motion "
            "as free fall. Then stitch them together by eliminating time. You "
            "get the parabolic path, the range formula, the maximum height, "
            "all of it. And you get the punchline for free: horizontal motion "
            "never helps you fall faster. It only carries you farther while "
            "you do."
        ),
        orientation=ORIENTATION_LECTURE,
        beats_json=[
            beat(HOOK, "drop"),
            beat(EMPHASIS, "path", transition="wipe"),
            beat(PUNCHLINE, "drop"),
        ],
        target_duration_sec=180,
    )

    add(
        video_id="lecture_rotational_motion",
        concept_type="GENERIC",
        header_title="The Skater Who Sped Up Without Pushing",
        tagline="Angular momentum is conserved",
        question_text="Why does a skater spin faster when she pulls her arms in?",
        equations_json=[
            r"L=I\omega",
            r"I=\sum m_i r_i^2",
        ],
        visual_data_json=[
            rotor("rotation", shape="solid_disk", mass=2.0, radius=2.5,
                  angular_velocity=2.0, torque=0.0, color=PRIMARY),
            label("note", "smaller I, larger omega"),
        ],
        audio_script=(
            "A figure skater glides across the ice, arms stretched wide, "
            "spinning slowly. She pulls her arms in to her chest. She spins "
            "faster. She did not push against anything. She did not do any "
            "obvious work. Where did the extra spin come from? The answer is "
            "that she never gained any spin at all. She always had it. What "
            "changed was how it was distributed. Angular momentum, L, is the "
            "rotational analogue of linear momentum. It equals the moment of "
            "inertia I times the angular velocity omega. The moment of inertia "
            "depends on how far the mass is from the axis of rotation. Arms "
            "out, the mass is far, so I is large. Arms in, the mass is close, "
            "so I is small. If no external torque acts on her, L is conserved. "
            "So if I drops, omega must rise to keep the product the same. That "
            "is the entire trick. It is the same physics that makes a diver "
            "tuck to complete more somersaults, and that makes a cat right "
            "itself in midair. There is something deeply satisfying about "
            "this, because it does not require any new forces. It is just "
            "angular bookkeeping. The skater does do work when she pulls her "
            "arms in, because she is moving mass against the centrifugal "
            "tendency, and that work goes into rotational kinetic energy. She "
            "spins faster and with more energy than before, but the total "
            "angular momentum is exactly what it was. Nature insists on the "
            "balance. She just rearranged the terms."
        ),
        orientation=ORIENTATION_LECTURE,
        beats_json=[
            beat(HOOK, "rotation"),
            beat(EMPHASIS, "note", transition="wipe"),
            beat(PUNCHLINE, "rotation"),
        ],
        target_duration_sec=180,
    )

    # =====================================================================
    # B. VERTICAL 1-MINUTE PYQ SHORTS
    # =====================================================================

    add(
        video_id="short_newton_fall",
        concept_type="PYQ",
        header_title="Free Fall Doesn't Care About Mass",
        tagline="Both balls hit the ground together",
        question_text="A 5 kg ball is dropped. What is its acceleration?",
        option_a="9.8 m/s^2",
        option_b="5.0 m/s^2",
        option_c="49 m/s^2",
        option_d="0 m/s^2",
        correct_answer="Correct Answer: (A)",
        equations_json=[r"a=\frac{F_{net}}{m}=\frac{mg}{m}=g"],
        visual_data_json=[
            {"type": "falling_energy", "id": "fall", "mass": 5.0,
             "height": 6.0, "g": 9.8, "color": PRIMARY},
        ],
        audio_script=(
            "Drop a bowling ball and a tennis ball from the same height. Most "
            "people bet on the bowling ball. Here is the surprise. The only "
            "force on each is gravity, which equals m g. So the net force "
            "divided by the mass is m g over m, which is g. The mass cancels. "
            "The acceleration is nine point eight meters per second squared, "
            "whatever the ball weighs. Answer A."
        ),
        orientation=ORIENTATION_SHORT,
        beats_json=[
            beat(HOOK, "fall"),
            beat(LAW, "fall", transition="wipe"),
            beat(PUNCHLINE, "fall"),
        ],
        target_duration_sec=60,
    )

    add(
        video_id="short_orbit_period",
        concept_type="PYQ",
        header_title="Double the Radius and Wait Longer",
        tagline="Kepler's third law in one minute",
        question_text="If the orbital radius doubles, by what factor does the period change?",
        option_a=r"\sqrt{2}",
        option_b="2",
        option_c=r"2\sqrt{2}",
        option_d="4",
        correct_answer="Correct Answer: (C)",
        equations_json=[r"T^2\propto r^3"],
        visual_data_json=[
            orbit("orbit1", 1.5, color=PRIMARY),
            orbit("orbit2", 3.5, color=ACCENT),
        ],
        audio_script=(
            "Double the radius of an orbit. You might guess the period doubles. "
            "Kepler's third law says no. The square of the period grows as the "
            "cube of the radius, so T scales as r to the three halves. Double "
            "r, and T multiplies by two to the three halves, which is two root "
            "two, about two point eight. The outer orbit is not just longer to "
            "travel, it is also slower. Both effects compound. Answer C."
        ),
        orientation=ORIENTATION_SHORT,
        beats_json=[
            beat(HOOK, "orbit1"),
            beat(LAW, "orbit2", transition="wipe"),
            beat(PUNCHLINE, "orbit2"),
        ],
        target_duration_sec=60,
    )

    add(
        video_id="short_collision",
        concept_type="PYQ",
        header_title="When Carts Stick and Move Together",
        tagline="A 2 kg cart hits a 4 kg cart. They stick.",
        question_text="A 2 kg cart at 3 m/s hits a stationary 4 kg cart. They stick. Final speed?",
        option_a="1 m/s",
        option_b="1.5 m/s",
        option_c="2 m/s",
        option_d="3 m/s",
        correct_answer="Correct Answer: (A)",
        equations_json=[r"m_1v_1=(m_1+m_2)v'"],
        visual_data_json=[
            collision("collision", m1=2.0, m2=4.0, v1=3.0, v2=0.0, color=PRIMARY),
        ],
        audio_script=(
            "A two kilogram cart moving at three meters per second hits a "
            "stationary four kilogram cart. They stick together. Momentum is "
            "conserved. Before: two times three equals six kilogram meters per "
            "second. After, the combined mass is six kilograms. So the final "
            "speed is six divided by six, one meter per second. Kinetic energy "
            "is not conserved; most of it went into deformation. Answer A."
        ),
        orientation=ORIENTATION_SHORT,
        beats_json=[
            beat(HOOK, "collision"),
            beat(LAW, "collision", transition="wipe"),
            beat(PUNCHLINE, "collision"),
        ],
        target_duration_sec=60,
    )

    add(
        video_id="short_pendulum_period",
        concept_type="PYQ",
        header_title="Why Pendulums Keep Time",
        tagline="The period ignores mass and amplitude",
        question_text="A one meter pendulum swings. What is its period? (g=9.8)",
        option_a="0.5 s",
        option_b="1.0 s",
        option_c="2.0 s",
        option_d="4.0 s",
        correct_answer="Correct Answer: (C)",
        equations_json=[r"T=2\pi\sqrt{L/g}"],
        visual_data_json=[
            pendulum("pendulum", length=1.0, gravity=9.8, angle=15.0, color=PRIMARY),
        ],
        audio_script=(
            "A pendulum one meter long. What is its period? The formula is T "
            "equals two pi times the square root of L over g. Plug in L equals "
            "one, g equals nine point eight. The square root of one over nine "
            "point eight is about zero point three two. Two pi times that is "
            "about two seconds. Notice: no mass, no amplitude. That is why "
            "pendulums are clocks. Answer C."
        ),
        orientation=ORIENTATION_SHORT,
        beats_json=[
            beat(HOOK, "pendulum"),
            beat(LAW, "pendulum", transition="wipe"),
            beat(PUNCHLINE, "pendulum"),
        ],
        target_duration_sec=60,
    )

    add(
        video_id="short_wave_speed",
        concept_type="PYQ",
        header_title="Count Crests to Find the Speed",
        tagline="Five crests per second, two meters apart",
        question_text="A wave has wavelength 2 m and frequency 5 Hz. Speed?",
        option_a="0.4 m/s",
        option_b="2.5 m/s",
        option_c="7 m/s",
        option_d="10 m/s",
        correct_answer="Correct Answer: (D)",
        equations_json=[r"v=\lambda f"],
        visual_data_json=[
            wave("wave", amplitude=1.0, wavelength=2.0, frequency=5.0,
                 x_range=(-4.0, 4.0), color=PRIMARY),
        ],
        audio_script=(
            "Stand at a pier and count crests. Five hit per second. Each crest "
            "is two meters behind the one in front. In one second, five waves "
            "times two meters each means ten meters of wave train swept past. "
            "So the speed is ten meters per second. That is the whole of v "
            "equals lambda f. Answer D."
        ),
        orientation=ORIENTATION_SHORT,
        beats_json=[
            beat(HOOK, "wave"),
            beat(LAW, "wave", transition="wipe"),
            beat(PUNCHLINE, "wave"),
        ],
        target_duration_sec=60,
    )

    add(
        video_id="short_bernoulli",
        concept_type="PYQ",
        header_title="Faster Water, Lower Pressure",
        tagline="Blow across paper and it rises",
        question_text="Water in a horizontal pipe speeds up. Does the pressure rise or fall?",
        option_a="2 m/s",
        option_b="5 m/s",
        option_c="10 m/s",
        option_d="12 m/s",
        correct_answer="Correct Answer: (C)",
        equations_json=[r"p_1+\tfrac{1}{2}\rho v_1^2=p_2+\tfrac{1}{2}\rho v_2^2"],
        visual_data_json=[
            venturi("venturi", inlet_height=1.8, throat_height=0.9,
                    inlet_velocity=2.0, density=1000, inlet_pressure=200000,
                    color=PRIMARY),
        ],
        audio_script=(
            "Water flows through a horizontal pipe. At point one, pressure is "
            "two times ten to the fifth, and speed is two. At point two, "
            "pressure is one point five times ten to the fifth. What is the "
            "speed there? Bernoulli says the sum of pressure and kinetic "
            "energy density is constant. Solve for v two. The result is about "
            "ten point two meters per second, so the closest answer is C. "
            "Faster flow, lower pressure. Answer C."
        ),
        orientation=ORIENTATION_SHORT,
        beats_json=[
            beat(HOOK, "venturi"),
            beat(LAW, "venturi", transition="wipe"),
            beat(PUNCHLINE, "venturi"),
        ],
        target_duration_sec=60,
    )

    add(
        video_id="short_electric_field",
        concept_type="PYQ",
        header_title="The Field Falls as One Over r Squared",
        tagline="Double the distance, quarter the field",
        question_text="Find E at 0.50 m from a +2.0 microcoulomb charge",
        option_a="1.8e4 N/C",
        option_b="3.6e4 N/C",
        option_c="7.2e4 N/C",
        option_d="1.4e5 N/C",
        correct_answer="Correct Answer: (C)",
        equations_json=[r"E=\frac{kQ}{r^2}"],
        visual_data_json=[
            e_field("field", charge=2e-6,
                    x_range=(-4.0, 4.0), y_range=(-6.0, 6.0),
                    columns=11, rows=13),
        ],
        audio_script=(
            "A point charge of plus two microcoulombs. Find the electric field "
            "at half a meter. E equals k Q over r squared. k is nine times ten "
            "to the ninth, Q is two times ten to the minus sixth, r squared is "
            "zero point two five. Multiply and divide, and you get seven point "
            "two times ten to the fourth newtons per coulomb. Answer C. Double "
            "the distance, and the field drops by a factor of four."
        ),
        orientation=ORIENTATION_SHORT,
        beats_json=[
            beat(HOOK, "field"),
            beat(LAW, "field", transition="wipe"),
            beat(PUNCHLINE, "field"),
        ],
        target_duration_sec=60,
    )

    add(
        video_id="short_work_integral",
        concept_type="PYQ",
        header_title="Add Up the Area Under the Curve",
        tagline="Work is integral of force",
        question_text="A force 3x^2 N acts from 0 to 2 m. How much work?",
        option_a="4 J",
        option_b="8 J",
        option_c="12 J",
        option_d="24 J",
        correct_answer="Correct Answer: (B)",
        equations_json=[r"W=\int_0^2 3x^2\,dx=8\ \text{J}"],
        visual_data_json=[
            calc_graph("force_curve", expression="3*x^2",
                       x_range=(0.0, 2.0), y_range=(0.0, 12.0),
                       x_length=4.0, y_length=4.0,
                       center=(0.0, 0.0, 0.0)),
            integral("work_area", expression="3*x^2",
                     x_range=(0.0, 2.0), y_range=(0.0, 12.0), a=0.0, b=2.0,
                     color=PRIMARY),
        ],
        audio_script=(
            "A force that grows as three x squared acts from zero to two "
            "meters. You cannot just multiply force by distance, because the "
            "force keeps changing. Integrate instead. The antiderivative of "
            "three x squared is x cubed. Evaluate at two, subtract the value "
            "at zero. You get eight joules. The work is the shaded area under "
            "the curve. Answer B."
        ),
        orientation=ORIENTATION_SHORT,
        beats_json=[
            beat(HOOK, "force_curve"),
            beat(LAW, "work_area", transition="wipe"),
            beat(PUNCHLINE, "force_curve"),
        ],
        target_duration_sec=60,
    )

    add(
        video_id="short_projectile_range",
        concept_type="PYQ",
        header_title="30 and 60 Give the Same Range",
        tagline="sin 2θ is symmetric around 45",
        question_text="A ball launches at 20 m/s at 30 degrees. Range? (g=9.8)",
        option_a="17 m",
        option_b="35 m",
        option_c="40 m",
        option_d="70 m",
        correct_answer="Correct Answer: (B)",
        equations_json=[r"R=\frac{v_0^2\sin 2\theta}{g}"],
        visual_data_json=[
            projectile("path", v0=20.0, angle=30.0, g=9.8, color=PRIMARY),
        ],
        audio_script=(
            "Fire a ball at twenty meters per second, thirty degrees above "
            "horizontal. Range equals v zero squared sine two theta over g. "
            "Sine of sixty degrees is about zero point eight six six. Twenty "
            "squared is four hundred. Divide by nine point eight, and you get "
            "about thirty five meters. Answer B. Fire at sixty degrees and you "
            "get the same range, because sine of two theta is the same for "
            "thirty and sixty."
        ),
        orientation=ORIENTATION_SHORT,
        beats_json=[
            beat(HOOK, "path"),
            beat(LAW, "path", transition="wipe"),
            beat(PUNCHLINE, "path"),
        ],
        target_duration_sec=60,
    )

    add(
        video_id="short_angular_acceleration",
        concept_type="PYQ",
        header_title="Why a Disk Beats a Hoop",
        tagline="Torque of 12 N·m on a solid disk",
        question_text="A 12 N·m torque acts on a 4 kg, 0.5 m disk. Find alpha",
        option_a="3.0",
        option_b="6.0",
        option_c="12",
        option_d="24",
        correct_answer="Correct Answer: (D)",
        equations_json=[r"\tau=I\alpha,\quad I=\tfrac{1}{2}MR^2"],
        visual_data_json=[
            rotor("rotation", shape="solid_disk", mass=4.0, radius=1.5,
                  angular_velocity=0.0, torque=12.0, color=PRIMARY),
        ],
        audio_script=(
            "A solid disk of mass four kilograms and radius half a meter. A "
            "torque of twelve newton meters. Moment of inertia of a disk is "
            "one half m r squared, which is zero point five. Angular "
            "acceleration is torque over I, twelve over zero point five, "
            "twenty four radians per second squared. Answer D. A hoop with "
            "the same mass would resist more, because all its mass sits "
            "farther from the axis."
        ),
        orientation=ORIENTATION_SHORT,
        beats_json=[
            beat(HOOK, "rotation"),
            beat(LAW, "rotation", transition="wipe"),
            beat(PUNCHLINE, "rotation"),
        ],
        target_duration_sec=60,
    )

    return rows


# ---------------------------------------------------------------------------
# 4. Entry point
# ---------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


def summarise(rows: list[dict[str, Any]]) -> str:
    lectures = [r for r in rows if r["orientation"] == ORIENTATION_LECTURE]
    shorts   = [r for r in rows if r["orientation"] == ORIENTATION_SHORT]
    total    = len(rows)
    return (
        f"Wrote {total} rows\n"
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
