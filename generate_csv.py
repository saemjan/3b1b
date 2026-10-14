#!/usr/bin/env python3
"""
Generate content_batch.csv:
  - 10 horizontal 3-minute concept lectures (target_duration_sec=180)
  - 10 vertical 1-minute PYQ shorts           (target_duration_sec=60)

Frame bounds:
  horizontal: x in [-8, 8],   y in [-4.5, 4.5]
  vertical:   x in [-4.5, 4.5], y in [-8, 8]
"""
import csv
import json

COLUMNS = [
    "video_id", "concept_type", "header_title", "tagline", "question_text",
    "option_a", "option_b", "option_c", "option_d", "correct_answer",
    "equations_json", "visual_data_json", "audio_script", "orientation",
    "beats_json", "target_duration_sec",
]

rows = []

def add(**kw):
    base = {c: "" for c in COLUMNS}
    base.update(kw)
    for key in ("equations_json", "visual_data_json", "beats_json"):
        if isinstance(base.get(key), (list, dict)):
            base[key] = json.dumps(base[key], ensure_ascii=False)
    rows.append(base)


# =====================================================================
# SECTION A — 10 HORIZONTAL 3-MINUTE CONCEPT LECTURES
# orientation="horizontal", target_duration_sec=180, concept_type=GENERIC
# Frame: x in [-8, 8], y in [-4.5, 4.5]
# =====================================================================

# A1. Newton's Second Law
add(
    video_id="lecture_newton_second_law",
    concept_type="GENERIC",
    header_title="Force Changes Motion",
    tagline="The net force sets the acceleration",
    question_text="How does net force determine acceleration?",
    equations_json=[
        r"F_{net}=ma",
        r"a=\frac{F_{net}}{m}",
        r"F_x=ma_x,\ F_y=ma_y,\ F_z=ma_z",
    ],
    visual_data_json=[
        {"type": "falling_energy", "id": "fall",
         "mass": 2.0, "height": 8.0, "g": 9.8, "color": "#4CC9F0"},
        {"type": "geometry", "id": "force_arrow", "dimension": 2,
         "kind": "polyline", "points": [[-6.0, 3.0], [-4.0, 3.0]],
         "color": "#F1C40F"},
    ],
    audio_script=(
        "Newton's second law is the central equation of mechanics. It says that "
        "the net force on an object equals its mass times its acceleration. In "
        "symbols, F equals m a. This single equation explains why a heavy truck "
        "accelerates more slowly than a small car under the same engine force, "
        "and why a rocket needs enormous thrust to lift off the ground. The law "
        "has three ingredients. First, force is a vector, with both magnitude "
        "and direction. Second, mass measures inertia, the resistance to changes "
        "in motion. Third, acceleration is the rate at which velocity changes. "
        "When you push a shopping cart, your push is the force. The cart's mass "
        "resists the push. The result is an acceleration that is larger when "
        "the push is stronger, and smaller when the cart is heavier. Notice "
        "that the law works in all three dimensions. We can write it component "
        "by component: F x equals m a x, F y equals m a y, and F z equals m a z. "
        "Each direction is independent. This is why projectile motion separates "
        "so cleanly into horizontal motion at constant velocity and vertical "
        "motion under constant acceleration. A ball thrown across a room moves "
        "forward at a steady speed while falling faster and faster. The two "
        "motions do not interfere, because forces in one direction do not affect "
        "motion in a perpendicular direction. Newton's second law also tells us "
        "what happens when the net force is zero. Then the acceleration is zero, "
        "and the object either stays at rest or moves in a straight line at "
        "constant speed. This is Newton's first law, and we see that it is "
        "really a special case of the second law. The second law is a cause and "
        "effect statement: forces cause accelerations. It is not velocity that "
        "requires a force to maintain, but changes in velocity. An object in "
        "motion needs no force to keep moving; it needs a force only to speed "
        "up, slow down, or change direction. In the visual, we see a ball "
        "falling under gravity. The only force is its weight, m g, directed "
        "down. So the acceleration is g, directed down, independent of the "
        "mass. A heavy ball and a light ball fall together when air resistance "
        "is negligible. This was Galileo's great insight, and it follows "
        "directly from Newton's second law when we set the force equal to the "
        "weight. The second law is the bridge between force and motion."
    ),
    orientation="horizontal",
    beats_json=[
        {"type": "hook", "focus": "fall"},
        {"type": "law", "focus": "force_arrow", "transition": "wipe"},
        {"type": "punchline", "focus": "fall"},
    ],
    target_duration_sec=180,
)

# A2. Gravitation and Orbits
add(
    video_id="lecture_gravity_orbit",
    concept_type="GENERIC",
    header_title="Gravity Guides an Orbit",
    tagline="Falling forever around a planet",
    question_text="Why does a satellite keep falling without reaching Earth?",
    equations_json=[
        r"F=\frac{GMm}{r^2}",
        r"v=\sqrt{\frac{GM}{r}}",
        r"T^2=\frac{4\pi^2 r^3}{GM}",
        r"v_{esc}=\sqrt{\frac{2GM}{R}}",
    ],
    visual_data_json=[
        {"type": "orbit", "id": "orbit", "radius": 5.0,
         "mass": 1.0, "color": "#4CC9F0"},
        {"type": "vector", "id": "gravity_vec",
         "start": [5.0, 0.0, 0.0], "end": [3.5, 0.0, 0.0],
         "color": "#F1C40F"},
    ],
    audio_script=(
        "Gravity is the force that holds the planets in their orbits around the "
        "Sun, and it is also the force that pulls an apple from a tree. "
        "Newton's great insight was that these are the same force, governed by "
        "a single law. The gravitational force between two masses is "
        "proportional to the product of the masses, and inversely proportional "
        "to the square of the distance between them. In symbols, F equals G M m "
        "over r squared. The constant G is the same everywhere in the universe. "
        "For a planet in a circular orbit around the Sun, the gravitational "
        "force provides the centripetal acceleration. Setting the gravitational "
        "force equal to m v squared over r gives us the orbital speed, v equals "
        "the square root of G M over r. This tells us that the orbital speed "
        "depends only on the mass of the central body and the radius of the "
        "orbit, not on the mass of the orbiting body. If we square this and "
        "substitute the orbital period T equals two pi r over v, we obtain "
        "Kepler's third law: T squared is proportional to r cubed. This is a "
        "remarkably simple result that describes the motion of every planet, "
        "moon, and satellite in the solar system. The orbit visual shows a "
        "satellite in a circular path around a central mass. The gravitational "
        "force always points toward the center, so the satellite is "
        "continuously falling toward the central body. But because it also has "
        "a tangential velocity, it never actually reaches it. It keeps falling "
        "around the curve. If the tangential speed is too small, the satellite "
        "falls inward and crashes. If it is too large, the satellite escapes "
        "along a parabolic or hyperbolic path. The speed required to escape is "
        "the escape velocity, v escape equals the square root of two G M over "
        "R. This is exactly the square root of two times the circular orbital "
        "speed at the same radius. So a satellite launched at the circular "
        "speed needs only a factor of root two more speed to escape entirely. "
        "Gravity is the architect of the solar system and the universe beyond."
    ),
    orientation="horizontal",
    beats_json=[
        {"type": "hook", "focus": "orbit"},
        {"type": "law", "focus": "gravity_vec", "transition": "wipe"},
        {"type": "punchline", "focus": "orbit"},
    ],
    target_duration_sec=180,
)

# A3. Momentum and Collisions
add(
    video_id="lecture_momentum_collision",
    concept_type="GENERIC",
    header_title="Momentum Is Exchanged",
    tagline="In an isolated collision, total momentum is conserved",
    question_text="What happens to two carts during an isolated collision?",
    equations_json=[
        r"p=mv",
        r"m_1v_1+m_2v_2=m_1v_1'+m_2v_2'",
        r"K=\frac{1}{2}mv^2",
    ],
    visual_data_json=[
        {"type": "momentum_exchange", "id": "collision",
         "mass1": 2.0, "mass2": 3.0, "v1": 5.0, "v2": -2.0,
         "color": "#4CC9F0"},
        {"type": "vector", "id": "p_before",
         "start": [-6.0, 2.5, 0.0], "end": [-3.0, 2.5, 0.0],
         "color": "#F1C40F"},
        {"type": "vector", "id": "p_after",
         "start": [3.0, -2.5, 0.0], "end": [6.0, -2.5, 0.0],
         "color": "#F1C40F"},
    ],
    audio_script=(
        "Momentum is the product of mass and velocity. It is a vector, and it "
        "points in the same direction as the velocity. The total momentum of "
        "an isolated system, one that experiences no net external force, is "
        "conserved. This is one of the most powerful conservation laws in "
        "physics. Consider two carts on a frictionless track. Cart one has "
        "mass m one and velocity v one. Cart two has mass m two and velocity "
        "v two. They collide, and after the collision their velocities are v "
        "one prime and v two prime. The law of conservation of momentum says "
        "that the total momentum before the collision equals the total momentum "
        "after the collision. In symbols, m one v one plus m two v two equals m "
        "one v one prime plus m two v two prime. Notice that momentum is a "
        "vector equation. It applies separately in each direction. In a one "
        "dimensional collision, it reduces to a single scalar equation. The "
        "collision visual shows two carts approaching each other. The yellow "
        "arrows represent the momentum vectors before the collision. After the "
        "collision, the carts may have different velocities, but the total "
        "momentum is the same. In an elastic collision, kinetic energy is also "
        "conserved. In an inelastic collision, some kinetic energy is converted "
        "into other forms, such as heat or deformation. But in every case, "
        "momentum is conserved as long as no net external force acts on the "
        "system. Momentum conservation is a consequence of Newton's third law. "
        "During the collision, the force that cart one exerts on cart two is "
        "equal and opposite to the force that cart two exerts on cart one. "
        "These equal and opposite forces act for the same time, so the impulses "
        "they deliver are equal and opposite. The change in momentum of cart "
        "one is the negative of the change in momentum of cart two. The total "
        "momentum is unchanged. This is why momentum conservation is so "
        "robust. It does not depend on the details of the force between the "
        "carts during the collision."
    ),
    orientation="horizontal",
    beats_json=[
        {"type": "hook", "focus": "collision"},
        {"type": "law", "focus": "p_before", "transition": "wipe"},
        {"type": "punchline", "focus": "p_after"},
    ],
    target_duration_sec=180,
)

# A4. Simple Harmonic Motion
add(
    video_id="lecture_shm_pendulum",
    concept_type="GENERIC",
    header_title="Oscillations Measure Time",
    tagline="Period depends on length and gravity, not on mass",
    question_text="How does pendulum length set its period and frequency?",
    equations_json=[
        r"T=2\pi\sqrt{\frac{L}{g}}",
        r"f=\frac{1}{T}",
        r"\omega=2\pi f",
        r"x(t)=A\cos(\omega t+\delta)",
    ],
    visual_data_json=[
        {"type": "pendulum", "id": "pendulum",
         "length": 2.0, "gravity": 9.8, "angle": 20.0,
         "color": "#4CC9F0"},
        {"type": "calculus_graph", "id": "shm_curve",
         "expression": "cos(2*pi*x/3)",
         "x_range": [0.0, 6.0], "y_range": [-1.5, 1.5],
         "x_length": 5.0, "y_length": 2.0,
         "center": [0.0, -3.0, 0.0]},
    ],
    audio_script=(
        "Simple harmonic motion is the back and forth motion of an object under "
        "a restoring force proportional to its displacement. A pendulum is the "
        "classic example. When the bob is displaced from equilibrium and "
        "released, it swings back and forth. For small angles, the restoring "
        "force is proportional to the displacement, and the motion is simple "
        "harmonic. The period of a simple pendulum, the time for one complete "
        "cycle, is given by T equals two pi times the square root of L over g. "
        "Here L is the length of the pendulum and g is the acceleration due to "
        "gravity. Notice that the period does not depend on the mass of the "
        "bob. It depends only on the length and on g. This is a remarkable "
        "fact. A heavy bob and a light bob on strings of the same length swing "
        "with the same period. The frequency is the inverse of the period, f "
        "equals one over T. The angular frequency is omega equals two pi f. "
        "The position of the bob as a function of time is described by a cosine "
        "function, x of t equals A cosine omega t plus delta. Here A is the "
        "amplitude, the maximum displacement from equilibrium, and delta is the "
        "phase constant, which depends on the initial conditions. The graph "
        "shows the cosine curve. Notice that the motion repeats every period T. "
        "The period is independent of the amplitude for small angles, a "
        "property called isochronism. Galileo discovered this property by "
        "timing the swings of a chandelier. It is the basis of pendulum "
        "clocks. If you shorten the pendulum, the period decreases. If you "
        "lengthen it, the period increases. A pendulum of length one meter has "
        "a period of about two seconds. This is why grandfather clocks use "
        "pendulums of about one meter."
    ),
    orientation="horizontal",
    beats_json=[
        {"type": "hook", "focus": "pendulum"},
        {"type": "law", "focus": "shm_curve", "transition": "wipe"},
        {"type": "punchline", "focus": "pendulum"},
    ],
    target_duration_sec=180,
)

# A5. Wave Properties
add(
    video_id="lecture_wave_properties",
    concept_type="GENERIC",
    header_title="Waves Carry a Pattern",
    tagline="Speed equals frequency times wavelength",
    question_text="How are wave speed, frequency, and wavelength related?",
    equations_json=[
        r"v=\lambda f",
        r"v=\frac{\lambda}{T}",
        r"f=\frac{1}{T}",
        r"y(x,t)=A\cos(kx-\omega t)",
    ],
    visual_data_json=[
        {"type": "wave", "id": "wave",
         "amplitude": 1.5, "wavelength": 4.0, "frequency": 1.0,
         "color": "#4CC9F0"},
        {"type": "geometry", "id": "lambda_marker", "dimension": 2,
         "kind": "polyline", "points": [[-2.0, 3.5], [2.0, 3.5]],
         "color": "#F1C40F"},
    ],
    audio_script=(
        "A wave is a disturbance that travels through space, carrying energy "
        "and momentum without transporting matter. The key parameters of a "
        "periodic wave are its wavelength, frequency, and speed. The "
        "wavelength, lambda, is the distance between successive crests. The "
        "frequency, f, is the number of crests that pass a given point per "
        "second. The period, T, is the time for one complete wave to pass, so "
        "f equals one over T. The speed of the wave, v, is the distance the "
        "wave travels per unit time. These three quantities are related by the "
        "fundamental wave equation: v equals lambda times f. This equation is "
        "simple but powerful. It says that if the frequency is fixed by the "
        "source, then the wavelength must adjust so that the product equals the "
        "wave speed. Since the wave speed is determined by the medium, a "
        "change in frequency causes a change in wavelength. The wave visual "
        "shows a sinusoidal wave traveling to the right. The amplitude is the "
        "maximum displacement from equilibrium. The wavelength is marked by "
        "the yellow bar. The wave carries energy from left to right. The "
        "particles of the medium, however, oscillate up and down about their "
        "equilibrium positions. They do not travel with the wave. For a wave "
        "on a string, the speed is determined by the tension F and the mass per "
        "unit length mu: v equals the square root of F over mu. A tighter "
        "string or a lighter string produces a faster wave. For sound waves in "
        "air, the speed depends on the temperature. At room temperature, it is "
        "about 343 meters per second. For light waves in vacuum, the speed is "
        "the same for all frequencies: about three times ten to the eighth "
        "meters per second. The wave equation is one of the most important "
        "equations in physics."
    ),
    orientation="horizontal",
    beats_json=[
        {"type": "hook", "focus": "wave"},
        {"type": "law", "focus": "lambda_marker", "transition": "wipe"},
        {"type": "punchline", "focus": "wave"},
    ],
    target_duration_sec=180,
)

# A6. Fluid Dynamics and Bernoulli
add(
    video_id="lecture_fluid_bernoulli",
    concept_type="GENERIC",
    header_title="Fluids Conserve Energy",
    tagline="Faster flow means lower pressure",
    question_text="How does Bernoulli's equation relate pressure, speed, and height?",
    equations_json=[
        r"p+\frac{1}{2}\rho v^2+\rho g h=\text{constant}",
        r"A_1v_1=A_2v_2",
        r"p_1+\frac{1}{2}\rho v_1^2=p_2+\frac{1}{2}\rho v_2^2",
    ],
    visual_data_json=[
        {"type": "fluid_dynamics", "id": "venturi",
         "operation": "venturi", "color": "#4CC9F0"},
        {"type": "geometry", "id": "flow_arrow", "dimension": 2,
         "kind": "polyline", "points": [[-6.5, 0.0], [-4.5, 0.0]],
         "color": "#F1C40F"},
    ],
    audio_script=(
        "Bernoulli's equation is the statement of energy conservation for a "
        "flowing fluid. It says that the sum of the pressure, the kinetic "
        "energy density, and the gravitational potential energy density is "
        "constant along a streamline. In symbols, p plus one half rho v "
        "squared plus rho g h equals a constant. Here p is the pressure, rho "
        "is the density, v is the flow speed, and h is the height. This "
        "equation tells us that where the fluid flows faster, the pressure is "
        "lower. This is often counterintuitive, because we expect faster flow "
        "to mean higher pressure. But energy conservation demands the "
        "opposite. Consider a fluid flowing through a horizontal pipe with a "
        "constriction. The continuity equation, A one v one equals A two v "
        "two, tells us that the fluid must speed up as it passes through the "
        "narrower section. According to Bernoulli's equation, the pressure "
        "must decrease in the narrower section to keep the sum constant. The "
        "venturi visual shows this effect. The streamlines are closer together "
        "in the constriction, indicating faster flow. The pressure is lower "
        "there, which is why the fluid is drawn upward in the vertical tubes. "
        "Bernoulli's equation explains many everyday phenomena. It explains "
        "why a curveball curves. It explains why a shower curtain is pulled "
        "inward when you turn on the water. It explains why an airplane wing "
        "generates lift. The air flows faster over the curved top of the wing, "
        "so the pressure is lower there, and the higher pressure underneath "
        "pushes the wing upward. Bernoulli's equation also explains how a "
        "carburetor works, how a perfume atomizer works, and how a chimney "
        "draws smoke upward. Keep in mind that Bernoulli's equation applies "
        "only to steady, incompressible, nonviscous flow along a streamline."
    ),
    orientation="horizontal",
    beats_json=[
        {"type": "hook", "focus": "venturi"},
        {"type": "law", "focus": "flow_arrow", "transition": "wipe"},
        {"type": "punchline", "focus": "venturi"},
    ],
    target_duration_sec=180,
)

# A7. Electric Field
add(
    video_id="lecture_electric_field",
    concept_type="GENERIC",
    header_title="Charges Create Fields",
    tagline="The electric field is force per unit charge",
    question_text="How does a point charge produce an electric field?",
    equations_json=[
        r"E=\frac{F}{q}",
        r"E=\frac{1}{4\pi\epsilon_0}\frac{Q}{r^2}",
        r"F=qE",
    ],
    visual_data_json=[
        {"type": "electric_field", "id": "field", "q": 1.0,
         "position": [0.0, 0.0], "color": "#4CC9F0"},
        {"type": "vector", "id": "E_vec",
         "start": [4.0, 0.0, 0.0], "end": [6.0, 0.0, 0.0],
         "color": "#F1C40F"},
    ],
    audio_script=(
        "The electric field is a way of describing the influence that a charge "
        "exerts on the space around it. Instead of saying that a charge Q "
        "exerts a force directly on another charge q at a distance, we say that "
        "the charge Q creates an electric field in the space around it, and "
        "this field exerts a force on the charge q. The electric field is "
        "defined as the electric force per unit charge. In symbols, E equals F "
        "over q. The direction of the electric field is the direction of the "
        "force that a positive test charge would experience. The magnitude of "
        "the electric field produced by a point charge Q at a distance r is "
        "given by Coulomb's law divided by q: E equals one over four pi epsilon "
        "zero times Q over r squared. The constant epsilon zero is the "
        "permittivity of free space. The electric field of a positive charge "
        "points radially outward, and the field of a negative charge points "
        "radially inward. The electric field is a vector field. It has a "
        "magnitude and a direction at every point in space. The force on a "
        "charge q placed in an electric field E is simply q times E. If q is "
        "positive, the force is in the same direction as the field. If q is "
        "negative, the force is opposite to the field. The electric field "
        "visual shows the field lines emerging from a positive point charge. "
        "The lines are closer together near the charge, where the field is "
        "stronger, and farther apart far away, where the field is weaker. The "
        "field follows an inverse square law. If you double the distance from "
        "the charge, the field strength drops by a factor of four. The electric "
        "field concept is essential for understanding everything from atomic "
        "structure to electrical circuits to electromagnetic waves."
    ),
    orientation="horizontal",
    beats_json=[
        {"type": "hook", "focus": "field"},
        {"type": "law", "focus": "E_vec", "transition": "wipe"},
        {"type": "punchline", "focus": "field"},
    ],
    target_duration_sec=180,
)

# A8. Work-Energy Theorem
add(
    video_id="lecture_work_energy",
    concept_type="GENERIC",
    header_title="Work Changes Kinetic Energy",
    tagline="The net work equals the change in kinetic energy",
    question_text="How is work done by a force related to kinetic energy?",
    equations_json=[
        r"W=\int_a^b F\,dx",
        r"W_{net}=\Delta K=\tfrac{1}{2}mv_f^2-\tfrac{1}{2}mv_i^2",
        r"K=\tfrac{1}{2}mv^2",
    ],
    visual_data_json=[
        {"type": "calculus_graph", "id": "force_curve",
         "expression": "2*x+1",
         "x_range": [0.0, 3.0], "y_range": [0.0, 8.0],
         "x_length": 5.0, "y_length": 3.0,
         "center": [0.0, 0.0, 0.0]},
        {"type": "integral_area", "id": "work_area",
         "expression": "2*x+1", "x_range": [1.0, 3.0],
         "color": "#4CC9F0"},
    ],
    audio_script=(
        "The work energy theorem is a bridge between force and energy. It says "
        "that the net work done on an object equals the change in its kinetic "
        "energy. Work is defined as the integral of force over displacement. "
        "For a constant force, W equals F d cosine theta, where theta is the "
        "angle between the force and the displacement. For a variable force, W "
        "equals the integral of F d x. The work is the area under the force "
        "versus position curve. The kinetic energy of an object is one half m v "
        "squared. The work energy theorem says that if you do positive work on "
        "an object, its kinetic energy increases. If you do negative work, its "
        "kinetic energy decreases. The visual shows a force that increases with "
        "position. The shaded area under the curve is the work done by the "
        "force. The work energy theorem is a consequence of Newton's second "
        "law. If we start with F equals m a and integrate both sides with "
        "respect to position, we obtain the work energy theorem. This is a "
        "powerful result because it allows us to calculate changes in speed "
        "without knowing the details of the motion. We only need to know the "
        "initial and final speeds and the work done by the net force. The work "
        "energy theorem applies to all forces, conservative and "
        "nonconservative. For conservative forces, we can also define potential "
        "energy, and the sum of kinetic and potential energy is conserved. For "
        "nonconservative forces, such as friction, the work done is negative, "
        "and mechanical energy is dissipated as heat. The work energy theorem "
        "is one of the most useful tools in mechanics. It is used to analyze "
        "everything from the motion of a car to the motion of an electron in an "
        "electric field."
    ),
    orientation="horizontal",
    beats_json=[
        {"type": "hook", "focus": "force_curve"},
        {"type": "law", "focus": "work_area", "transition": "wipe"},
        {"type": "punchline", "focus": "force_curve"},
    ],
    target_duration_sec=180,
)

# A9. Projectile Motion
add(
    video_id="lecture_projectile_motion",
    concept_type="GENERIC",
    header_title="Projectiles Curve",
    tagline="Horizontal and vertical motions are independent",
    question_text="How do horizontal motion and gravity combine in a projectile path?",
    equations_json=[
        r"x=v_{0x}t",
        r"y=v_{0y}t-\tfrac{1}{2}gt^2",
        r"v_y=v_{0y}-gt",
        r"R=\frac{v_0^2\sin 2\theta}{g}",
    ],
    visual_data_json=[
        {"type": "projectile_motion", "id": "path",
         "v0": 10.0, "angle": 35.0, "g": 9.8,
         "color": "#4CC9F0"},
        {"type": "vector", "id": "launch_vel",
         "start": [-6.0, -3.0, 0.0], "end": [-4.0, -1.0, 0.0],
         "color": "#F1C40F"},
    ],
    audio_script=(
        "Projectile motion is the motion of an object launched into the air and "
        "moving under the influence of gravity alone. The key insight is that "
        "horizontal and vertical motions are independent. Gravity acts only in "
        "the vertical direction. It does not affect the horizontal motion. So "
        "the horizontal velocity remains constant, and the horizontal position "
        "is x equals v zero x t. The vertical motion is uniformly accelerated, "
        "with acceleration g downward. The vertical position is y equals v "
        "zero y t minus one half g t squared. The vertical velocity is v y "
        "equals v zero y minus g t. The combination of constant horizontal "
        "velocity and constant vertical acceleration produces a parabolic "
        "path. The projectile visual shows the trajectory of a launched object. "
        "The horizontal motion is uniform. The vertical motion is accelerated. "
        "The velocity vector at any point is tangent to the path. The "
        "horizontal component of the velocity is constant. The vertical "
        "component changes. At the highest point of the trajectory, the "
        "vertical component of the velocity is zero. The projectile then "
        "begins to descend. The range of a projectile on level ground is R "
        "equals v zero squared sine two theta over g. The maximum range occurs "
        "for a launch angle of 45 degrees. The maximum height is h equals v "
        "zero squared sine squared theta over two g. The time of flight is t "
        "equals two v zero sine theta over g. These formulas assume no air "
        "resistance. In reality, air resistance reduces the range and changes "
        "the shape of the trajectory. But for many everyday projectiles, such "
        "as a baseball or a golf ball, the parabolic approximation is "
        "reasonably accurate."
    ),
    orientation="horizontal",
    beats_json=[
        {"type": "hook", "focus": "path"},
        {"type": "law", "focus": "launch_vel", "transition": "wipe"},
        {"type": "punchline", "focus": "path"},
    ],
    target_duration_sec=180,
)

# A10. Rotational Motion
add(
    video_id="lecture_rotational_motion",
    concept_type="GENERIC",
    header_title="Rotation Has Inertia",
    tagline="Moment of inertia determines resistance to angular acceleration",
    question_text="How does moment of inertia affect rotational motion?",
    equations_json=[
        r"\tau=I\alpha",
        r"I=\sum m_i r_i^2",
        r"K=\tfrac{1}{2}I\omega^2",
        r"L=I\omega",
    ],
    visual_data_json=[
        {"type": "rotational_motion", "id": "rotation",
         "shape": "solid_disk", "mass": 2.0, "radius": 2.5,
         "angular_velocity": 2.0, "torque": 0.0,
         "color": "#4CC9F0"},
        {"type": "geometry", "id": "torque_arrow", "dimension": 2,
         "kind": "polyline", "points": [[2.5, 0.0], [4.0, 0.0]],
         "color": "#F1C40F"},
    ],
    audio_script=(
        "Rotational motion is the motion of an object spinning about an axis. "
        "The rotational analogue of force is torque. The rotational analogue "
        "of mass is moment of inertia. The rotational analogue of Newton's "
        "second law is tau equals I alpha, where tau is the torque, I is the "
        "moment of inertia, and alpha is the angular acceleration. The moment "
        "of inertia depends not only on the mass of the object but also on how "
        "that mass is distributed relative to the axis of rotation. For a "
        "collection of point masses, I equals the sum of m i r i squared. The "
        "farther the mass is from the axis, the larger the moment of inertia. "
        "This is why a hoop has a larger moment of inertia than a disk of the "
        "same mass and radius. All the mass of the hoop is at the rim, while "
        "the mass of the disk is distributed throughout. The rotational "
        "kinetic energy is K equals one half I omega squared. The angular "
        "momentum is L equals I omega. Angular momentum is conserved when the "
        "net external torque is zero. The rotation visual shows a spinning "
        "object. The torque arrow represents the twisting force that causes "
        "angular acceleration. If the moment of inertia is large, a large "
        "torque is needed to produce a given angular acceleration. This is why "
        "a figure skater spins faster when she pulls her arms in. By reducing "
        "her moment of inertia, she reduces the resistance to rotation, and "
        "since angular momentum is conserved, her angular velocity increases. "
        "The same principle explains why a diver tucks to complete more "
        "somersaults, and why a cat can land on its feet. Rotational motion is "
        "everywhere in nature, from the spinning of galaxies to the rotation of "
        "electrons in atoms."
    ),
    orientation="horizontal",
    beats_json=[
        {"type": "hook", "focus": "rotation"},
        {"type": "law", "focus": "torque_arrow", "transition": "wipe"},
        {"type": "punchline", "focus": "rotation"},
    ],
    target_duration_sec=180,
)


# =====================================================================
# SECTION B — 10 VERTICAL 1-MINUTE PYQ SHORTS
# orientation="vertical", target_duration_sec=60, concept_type=PYQ
# Frame: x in [-4.5, 4.5], y in [-8, 8]
# =====================================================================

# B1. Newton's Second Law — falling acceleration
add(
    video_id="short_newton_fall",
    concept_type="PYQ",
    header_title="Find the Acceleration",
    tagline="Apply F = ma to a falling object",
    question_text=("A 5 kg object is released from rest and falls freely near "
                   "Earth's surface. What is its acceleration?"),
    option_a="9.8 m/s^2",
    option_b="5.0 m/s^2",
    option_c="49 m/s^2",
    option_d="0 m/s^2",
    correct_answer="A",
    equations_json=[
        r"F_{net}=ma",
        r"a=\frac{F_{net}}{m}",
        r"a=g=9.8\ \text{m/s}^2",
    ],
    visual_data_json=[
        {"type": "falling_energy", "id": "fall",
         "mass": 5.0, "height": 6.0, "g": 9.8,
         "color": "#4CC9F0"},
    ],
    audio_script=(
        "A five kilogram object is released from rest and falls freely near "
        "the Earth's surface. What is its acceleration? The only force acting "
        "on the object is gravity, so the net force is its weight, m g. "
        "Newton's second law tells us that the acceleration is the net force "
        "divided by the mass. The mass cancels, and we are left with g, which "
        "is approximately nine point eight meters per second squared. The "
        "correct answer is A. Notice that the mass did not matter. Any object "
        "in free fall near the Earth's surface accelerates at the same rate, "
        "regardless of its mass."
    ),
    orientation="vertical",
    beats_json=[
        {"type": "hook", "focus": "fall"},
        {"type": "example", "focus": "fall", "transition": "wipe"},
        {"type": "punchline", "focus": "fall"},
    ],
    target_duration_sec=60,
)

# B2. Orbit — Kepler's Third Law
add(
    video_id="short_orbit_period",
    concept_type="PYQ",
    header_title="Find the Orbital Period",
    tagline="Apply Kepler's third law",
    question_text=("A satellite orbits Earth at radius r. If the orbital "
                   "radius were doubled, by what factor would the period "
                   "change?"),
    option_a=r"\sqrt{2}",
    option_b="2",
    option_c=r"2\sqrt{2}",
    option_d="4",
    correct_answer="C",
    equations_json=[
        r"T^2=\frac{4\pi^2 r^3}{GM}",
        r"\frac{T_2}{T_1}=\left(\frac{r_2}{r_1}\right)^{3/2}",
    ],
    visual_data_json=[
        {"type": "orbit", "id": "orbit1", "radius": 2.0,
         "mass": 1.0, "color": "#4CC9F0"},
        {"type": "orbit", "id": "orbit2", "radius": 4.0,
         "mass": 1.0, "color": "#F1C40F"},
    ],
    audio_script=(
        "Kepler's third law tells us that the square of the orbital period is "
        "proportional to the cube of the orbital radius. So the period is "
        "proportional to r to the three halves power. If the radius doubles, "
        "the period changes by a factor of two to the three halves, which is "
        "two times the square root of two. The correct answer is C, two root "
        "two. This is approximately two point eight three."
    ),
    orientation="vertical",
    beats_json=[
        {"type": "hook", "focus": "orbit1"},
        {"type": "example", "focus": "orbit2", "transition": "wipe"},
        {"type": "punchline", "focus": "orbit2"},
    ],
    target_duration_sec=60,
)

# B3. Collision — Inelastic
add(
    video_id="short_collision",
    concept_type="PYQ",
    header_title="Find the Final Velocity",
    tagline="Use momentum conservation",
    question_text=("A 2 kg cart moving at 3 m/s collides with a stationary "
                   "4 kg cart. They stick together. What is their common "
                   "velocity?"),
    option_a="1 m/s",
    option_b="1.5 m/s",
    option_c="2 m/s",
    option_d="3 m/s",
    correct_answer="A",
    equations_json=[
        r"m_1v_1+m_2v_2=(m_1+m_2)v'",
        r"v'=\frac{m_1v_1}{m_1+m_2}",
    ],
    visual_data_json=[
        {"type": "momentum_exchange", "id": "collision",
         "mass1": 2.0, "mass2": 4.0, "v1": 3.0, "v2": 0.0,
         "color": "#4CC9F0"},
    ],
    audio_script=(
        "A two kilogram cart moving at three meters per second collides with "
        "a stationary four kilogram cart. They stick together. What is their "
        "common velocity? Since the carts stick together, this is a perfectly "
        "inelastic collision. Momentum is conserved. The initial momentum is "
        "two kilograms times three meters per second, which is six kilogram "
        "meters per second. After the collision, the total mass is six "
        "kilograms. The common velocity is the initial momentum divided by "
        "the total mass, which is six divided by six, or one meter per "
        "second. The correct answer is A. Notice that kinetic energy is not "
        "conserved. The initial kinetic energy is nine joules, and the final "
        "kinetic energy is three joules."
    ),
    orientation="vertical",
    beats_json=[
        {"type": "hook", "focus": "collision"},
        {"type": "example", "focus": "collision", "transition": "wipe"},
        {"type": "punchline", "focus": "collision"},
    ],
    target_duration_sec=60,
)

# B4. Pendulum Period
add(
    video_id="short_pendulum_period",
    concept_type="PYQ",
    header_title="Find the Pendulum Period",
    tagline=r"Apply $T = 2\pi\sqrt{L/g}$",
    question_text=("A pendulum has a length of 1.0 m. What is its period? "
                   "(g = 9.8 m/s^2)"),
    option_a="0.5 s",
    option_b="1.0 s",
    option_c="2.0 s",
    option_d="4.0 s",
    correct_answer="C",
    equations_json=[
        r"T=2\pi\sqrt{\frac{L}{g}}",
        r"T=2\pi\sqrt{\frac{1.0}{9.8}}\approx 2.0\ \text{s}",
    ],
    visual_data_json=[
        {"type": "pendulum", "id": "pendulum", "length": 1.0,
         "gravity": 9.8, "angle": 15.0, "color": "#4CC9F0"},
    ],
    audio_script=(
        "A pendulum has a length of one point zero meters. What is its "
        "period? The period of a simple pendulum is given by T equals two pi "
        "times the square root of L over g. Plugging in L equals one point "
        "zero meters and g equals nine point eight meters per second squared, "
        "we get T equals two pi times the square root of one over nine point "
        "eight. The square root of one over nine point eight is approximately "
        "zero point three two. Two pi times zero point three two is "
        "approximately two point zero seconds. The correct answer is C. "
        "Notice that the period does not depend on the mass of the bob, or on "
        "the amplitude, as long as the amplitude is small."
    ),
    orientation="vertical",
    beats_json=[
        {"type": "hook", "focus": "pendulum"},
        {"type": "example", "focus": "pendulum", "transition": "wipe"},
        {"type": "punchline", "focus": "pendulum"},
    ],
    target_duration_sec=60,
)

# B5. Wave Speed
add(
    video_id="short_wave_speed",
    concept_type="PYQ",
    header_title="Find the Wave Speed",
    tagline=r"Apply $v = \lambda f$",
    question_text=("A wave has a wavelength of 2.0 m and a frequency of "
                   "5.0 Hz. What is its speed?"),
    option_a="0.4 m/s",
    option_b="2.5 m/s",
    option_c="7.0 m/s",
    option_d="10 m/s",
    correct_answer="D",
    equations_json=[
        r"v=\lambda f",
        r"v=2.0\ \text{m}\times 5.0\ \text{Hz}=10\ \text{m/s}",
    ],
    visual_data_json=[
        {"type": "wave", "id": "wave",
         "amplitude": 1.0, "wavelength": 2.0, "frequency": 5.0,
         "color": "#4CC9F0"},
    ],
    audio_script=(
        "A wave has a wavelength of two point zero meters and a frequency of "
        "five point zero hertz. What is its speed? The wave equation tells us "
        "that the speed is the product of the wavelength and the frequency. "
        "So v equals two point zero meters times five point zero hertz, which "
        "is ten meters per second. The correct answer is D, ten meters per "
        "second. This relationship, v equals lambda f, is one of the most "
        "fundamental in wave physics. It applies to all waves, including "
        "sound waves, water waves, and light waves."
    ),
    orientation="vertical",
    beats_json=[
        {"type": "hook", "focus": "wave"},
        {"type": "example", "focus": "wave", "transition": "wipe"},
        {"type": "punchline", "focus": "wave"},
    ],
    target_duration_sec=60,
)

# B6. Bernoulli — Flow Speed
add(
    video_id="short_bernoulli",
    concept_type="PYQ",
    header_title="Find the Flow Speed",
    tagline="Apply Bernoulli's equation",
    question_text=("Water flows through a horizontal pipe. At point 1, "
                   "pressure is 2.0 x 10^5 Pa and speed is 2.0 m/s. At "
                   "point 2, pressure is 1.5 x 10^5 Pa. What is the speed at "
                   "point 2? (rho = 1000 kg/m^3)"),
    option_a="2.0 m/s",
    option_b="5.0 m/s",
    option_c="10 m/s",
    option_d="12 m/s",
    correct_answer="C",
    equations_json=[
        r"p_1+\tfrac{1}{2}\rho v_1^2=p_2+\tfrac{1}{2}\rho v_2^2",
        r"v_2=\sqrt{v_1^2+\frac{2(p_1-p_2)}{\rho}}",
        r"v_2=\sqrt{4+100}\approx 10.2\ \text{m/s}",
    ],
    visual_data_json=[
        {"type": "fluid_dynamics", "id": "venturi",
         "operation": "venturi", "color": "#4CC9F0"},
    ],
    audio_script=(
        "Water flows through a horizontal pipe. At point one, pressure is "
        "two point zero times ten to the fifth pascals, and speed is two "
        "point zero meters per second. At point two, pressure is one point "
        "five times ten to the fifth pascals. What is the speed at point "
        "two? Bernoulli's equation tells us that the sum of pressure and "
        "kinetic energy density is constant along a horizontal streamline. "
        "Solving for v two gives v two equals the square root of v one "
        "squared plus two times the pressure difference over rho. The "
        "pressure difference is zero point five times ten to the fifth "
        "pascals. Plugging in the numbers gives approximately ten point two "
        "meters per second. The closest answer is C, ten meters per second. "
        "The speed increases as the pressure decreases."
    ),
    orientation="vertical",
    beats_json=[
        {"type": "hook", "focus": "venturi"},
        {"type": "example", "focus": "venturi", "transition": "wipe"},
        {"type": "punchline", "focus": "venturi"},
    ],
    target_duration_sec=60,
)

# B7. Electric Field
add(
    video_id="short_electric_field",
    concept_type="PYQ",
    header_title="Find the Electric Field",
    tagline=r"Apply $E = kQ/r^2$",
    question_text=("What is the electric field at a distance of 0.50 m from "
                   "a point charge of +2.0 x 10^-6 C?"),
    option_a="1.8 x 10^4 N/C",
    option_b="3.6 x 10^4 N/C",
    option_c="7.2 x 10^4 N/C",
    option_d="1.4 x 10^5 N/C",
    correct_answer="C",
    equations_json=[
        r"E=\frac{kQ}{r^2}",
        r"E=\frac{(9.0\times 10^9)(2.0\times 10^{-6})}{(0.50)^2}=7.2\times 10^4\ \text{N/C}",
    ],
    visual_data_json=[
        {"type": "electric_field", "id": "field", "q": 1.0,
         "position": [0.0, 0.0], "color": "#4CC9F0"},
    ],
    audio_script=(
        "What is the electric field at a distance of zero point five zero "
        "meters from a point charge of plus two point zero times ten to the "
        "minus sixth coulombs? The electric field of a point charge is given "
        "by E equals k Q over r squared. Here k is the Coulomb constant, "
        "nine point zero times ten to the ninth. Q is two point zero times "
        "ten to the minus sixth coulombs. r is zero point five zero meters. "
        "Plugging in, we get seven point two times ten to the fourth newtons "
        "per coulomb. The correct answer is C. The field points radially "
        "outward from the positive charge."
    ),
    orientation="vertical",
    beats_json=[
        {"type": "hook", "focus": "field"},
        {"type": "example", "focus": "field", "transition": "wipe"},
        {"type": "punchline", "focus": "field"},
    ],
    target_duration_sec=60,
)

# B8. Work Integral
add(
    video_id="short_work_integral",
    concept_type="PYQ",
    header_title="Find the Work Done",
    tagline=r"Apply $W = \int F\,dx$",
    question_text=("A force F(x) = 3x^2 N acts on an object from x = 0 to "
                   "x = 2.0 m. How much work is done?"),
    option_a="4.0 J",
    option_b="8.0 J",
    option_c="12 J",
    option_d="24 J",
    correct_answer="B",
    equations_json=[
        r"W=\int_0^{2.0} 3x^2\,dx",
        r"W=\left[x^3\right]_0^{2.0}=8.0\ \text{J}",
    ],
    visual_data_json=[
        {"type": "calculus_graph", "id": "force_curve",
         "expression": "3*x^2",
         "x_range": [0.0, 2.0], "y_range": [0.0, 12.0],
         "x_length": 4.0, "y_length": 4.0,
         "center": [0.0, 0.0, 0.0]},
        {"type": "integral_area", "id": "work_area",
         "expression": "3*x^2", "x_range": [0.0, 2.0],
         "color": "#4CC9F0"},
    ],
    audio_script=(
        "A force F of x equals three x squared newtons acts on an object "
        "from x equals zero to x equals two point zero meters. How much work "
        "is done? The work done by a variable force is the integral of the "
        "force with respect to position. So W equals the integral from zero "
        "to two of three x squared d x. The antiderivative of three x squared "
        "is x cubed. Evaluating from zero to two, we get eight minus zero, "
        "which is eight. The correct answer is B, eight point zero joules. "
        "Graphically, the work is the area under the force versus position "
        "curve."
    ),
    orientation="vertical",
    beats_json=[
        {"type": "hook", "focus": "force_curve"},
        {"type": "example", "focus": "work_area", "transition": "wipe"},
        {"type": "punchline", "focus": "force_curve"},
    ],
    target_duration_sec=60,
)

# B9. Projectile Range
add(
    video_id="short_projectile_range",
    concept_type="PYQ",
    header_title="Find the Range",
    tagline=r"Apply $R = v_0^2\sin 2\theta / g$",
    question_text=("A ball is launched at 20 m/s at an angle of 30 degrees. "
                   "What is its range on level ground? (g = 9.8 m/s^2)"),
    option_a="17 m",
    option_b="35 m",
    option_c="40 m",
    option_d="70 m",
    correct_answer="B",
    equations_json=[
        r"R=\frac{v_0^2\sin 2\theta}{g}",
        r"R=\frac{(20)^2\sin 60^\circ}{9.8}\approx 35\ \text{m}",
    ],
    visual_data_json=[
        {"type": "projectile_motion", "id": "path",
         "v0": 20.0, "angle": 30.0, "g": 9.8,
         "color": "#4CC9F0"},
    ],
    audio_script=(
        "A ball is launched at twenty meters per second at an angle of "
        "thirty degrees. What is its range on level ground? The range of a "
        "projectile on level ground is given by R equals v zero squared sine "
        "two theta over g. Here v zero is twenty meters per second, theta is "
        "thirty degrees, and g is nine point eight meters per second squared. "
        "Sine of sixty degrees is approximately zero point eight six six. "
        "Plugging in, we get four hundred times zero point eight six six "
        "divided by nine point eight, which is approximately thirty five "
        "point three meters. The correct answer is B, thirty five meters. "
        "For a given launch speed, the maximum range occurs at forty five "
        "degrees."
    ),
    orientation="vertical",
    beats_json=[
        {"type": "hook", "focus": "path"},
        {"type": "example", "focus": "path", "transition": "wipe"},
        {"type": "punchline", "focus": "path"},
    ],
    target_duration_sec=60,
)

# B10. Angular Acceleration
add(
    video_id="short_angular_acceleration",
    concept_type="PYQ",
    header_title="Find the Angular Acceleration",
    tagline=r"Apply $\tau = I\alpha$",
    question_text=("A torque of 12 N.m is applied to a solid disk of mass "
                   "4.0 kg and radius 0.50 m. What is the angular "
                   "acceleration?"),
    option_a="3.0 rad/s^2",
    option_b="6.0 rad/s^2",
    option_c="12 rad/s^2",
    option_d="24 rad/s^2",
    correct_answer="D",
    equations_json=[
        r"\tau=I\alpha",
        r"I=\tfrac{1}{2}MR^2",
        r"\alpha=\tau/I=12/0.50=24\ \text{rad/s}^2",
    ],
    visual_data_json=[
        {"type": "rotational_motion", "id": "rotation",
         "shape": "solid_disk", "mass": 4.0, "radius": 1.5,
         "angular_velocity": 0.0, "torque": 12.0,
         "color": "#4CC9F0"},
        {"type": "geometry", "id": "torque_arrow", "dimension": 2,
         "kind": "polyline", "points": [[1.5, 0.0], [3.0, 0.0]],
         "color": "#F1C40F"},
    ],
    audio_script=(
        "A torque of twelve newton meters is applied to a solid disk of mass "
        "four point zero kilograms and radius zero point five zero meters. "
        "What is the angular acceleration? The moment of inertia of a solid "
        "disk about its central axis is I equals one half M R squared. "
        "Plugging in M equals four and R equals zero point five, we get I "
        "equals zero point five kilogram meter squared. The angular "
        "acceleration is the torque divided by the moment of inertia. So "
        "alpha equals twelve divided by zero point five, which is twenty four "
        "radians per second squared. The correct answer is D. A hoop of the "
        "same mass and radius would have a larger moment of inertia and "
        "therefore a smaller angular acceleration."
    ),
    orientation="vertical",
    beats_json=[
        {"type": "hook", "focus": "rotation"},
        {"type": "example", "focus": "torque_arrow", "transition": "wipe"},
        {"type": "punchline", "focus": "rotation"},
    ],
    target_duration_sec=60,
)


# =====================================================================
# Write CSV
# =====================================================================

if __name__ == "__main__":
    out = "content_batch.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out}")
    print(f"  Horizontal 3-min lectures: {sum(1 for r in rows if r['orientation']=='horizontal')}")
    print(f"  Vertical 1-min shorts:     {sum(1 for r in rows if r['orientation']=='vertical')}")
