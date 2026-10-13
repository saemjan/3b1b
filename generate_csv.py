#!/usr/bin/env python3
"""
generate_csv.py — Day 5 batch.

Feynman Lectures Vol. II, Chapters 9-10:
  Ch 9 — Electricity in the Atmosphere
  Ch 10 — Dielectrics

10 rows: 8 GENERIC + 2 PYQ, horizontal long-form.

Run:  python3 generate_csv.py
"""
import csv
import json

HEADER = [
    "video_id", "concept_type", "header_title", "tagline",
    "question_text", "option_a", "option_b", "option_c", "option_d",
    "correct_answer", "equations_json", "visual_data_json",
    "audio_script", "orientation",
]


def row(video_id, concept_type, header_title, tagline,
        question_text="", options=("", "", "", ""), correct="",
        equations=None, visuals=None, audio="",
        orientation="horizontal"):
    opts = list(options) + [""] * (4 - len(options))
    return {
        "video_id":          video_id,
        "concept_type":      concept_type,
        "header_title":      header_title,
        "tagline":           tagline,
        "question_text":     question_text,
        "option_a":          opts[0],
        "option_b":          opts[1],
        "option_c":          opts[2],
        "option_d":          opts[3],
        "correct_answer":    correct,
        "equations_json":    json.dumps(equations or []),
        "visual_data_json":  json.dumps(visuals or []),
        "audio_script":      audio,
        "orientation":       orientation,
    }


ROWS = []

# ============================================================ 01
ROWS.append(row(
    video_id="feynman_v2_day5_01_atmospheric_gradient",
    concept_type="GENERIC",
    header_title="The 100-Volt Sky",
    tagline="Why your head is 200 volts above your feet",
    equations=[
        r"E_{\text{atm}} \approx 100\ \text{V/m (downward)}",
        r"\phi_{\text{top}} - \phi_{\text{ground}} \approx 4 \times 10^5\ \text{V}",
    ],
    visuals=[
        {"type": "line", "start": [-4.0, -2.0, 0], "end": [4.0, -2.0, 0],
         "color": "#3498DB", "stroke_width": 3},
        {"type": "field", "direction": "DOWN", "rows": 5, "opacity": 0.35,
         "color": "#F1C40F"},
        {"type": "vector", "start": [0.0, 0.5, 0], "end": [0.0, -0.8, 0],
         "color": "#E74C3C", "label": "E"},
        {"type": "text", "text": "100 V/m", "pos": [-2.5, 1.5, 0],
         "color": "#F1C40F", "font_size": 20},
        {"type": "text", "text": "0 V", "pos": [2.5, -2.3, 0],
         "color": "#8A8F9C", "font_size": 18},
    ],
    audio=(
        "On an ordinary day, outdoors, over flat desert country, the "
        "electric potential increases as we go upward from the surface of "
        "the earth by about one hundred volts per meter. So there is a "
        "vertical electric field in the air. The sign of the field "
        "corresponds to a negative charge on the earth's surface. This "
        "means that outdoors the potential at the height of your nose is "
        "two hundred volts higher than the potential at your feet. Now "
        "you might ask: why don't we get a shock? Why don't we just put "
        "a pair of electrodes one meter apart and light up a bulb with "
        "this potential? The answer is that your body is a fairly good "
        "conductor. If you are standing on the ground, you and the "
        "ground together form one equipotential surface. The field lines "
        "bend around you. So the potential difference between your head "
        "and your feet is essentially zero. If you were a perfect "
        "insulator, you would feel this field. But you are not. There is "
        "another interesting consequence. The total potential difference "
        "from the surface of the earth to the top of the atmosphere is "
        "about four hundred thousand volts. That is the voltage of a "
        "small Van de Graaff generator. Where does it come from? That is "
        "one of the most fascinating questions in atmospheric physics, "
        "and the answer involves thunderstorms, cosmic rays, and the "
        "entire planet working as a giant electrical machine."
    ),
))

# ============================================================ 02
ROWS.append(row(
    video_id="feynman_v2_day5_02_cosmic_rays",
    concept_type="GENERIC",
    header_title="Where Do Air Ions Come From?",
    tagline="The surprising discovery of cosmic rays",
    equations=[
        r"\text{Ionization} \uparrow \text{ with altitude}",
        r"E_{\text{cosmic}} \sim 10^9\ \text{eV}",
    ],
    visuals=[
        {"type": "exponential_atmosphere", "num_particles": 40,
         "height": 5.0, "scale_height": 1.5, "color": "#F1C40F"},
        {"type": "radiating_wave", "pos": [-4.0, 3.5, 0],
         "num_rings": 3, "wavelength": 0.5,
         "color": "#E74C3C"},
        {"type": "text", "text": "cosmic ray", "pos": [-3.0, 4.5, 0],
         "color": "#E74C3C", "font_size": 20},
    ],
    audio=(
        "The conductivity of the air comes from ions. Here and there among "
        "the air molecules there is an ion, a molecule of oxygen that has "
        "gained or lost an electron. But where do these ions come from? "
        "The first guess, made in the early nineteen hundreds, was that "
        "they came from radioactive materials in the earth. The earth has "
        "traces of radium, uranium, potassium, and these all emit "
        "radiation that could ionize the air. If that theory were correct, "
        "then if we went up to high altitude we should find less "
        "ionization, because the radioactivity is all in the ground. So in "
        "nineteen twelve, Victor Hess carried an ionization detector up "
        "in a balloon. He expected to see the ionization fall with "
        "altitude. What he found was exactly the opposite. The ionization "
        "per unit volume increased as he went up. This was the most "
        "dramatic finding in the entire history of atmospheric "
        "electricity. It was so dramatic, in fact, that it required a "
        "branching off of an entirely new subject. The ionization was "
        "coming from outside the earth. Hess had discovered cosmic rays, "
        "for which he would later receive the Nobel Prize. These are "
        "charged particles, mostly protons and atomic nuclei, that arrive "
        "at the earth with enormous energies. They come from the sun, "
        "from supernovae, from active galaxies. When they hit the upper "
        "atmosphere, they shatter air molecules into ions. These ions are "
        "what give the atmosphere its conductivity. It is a beautiful "
        "example of how a small anomaly, if taken seriously, can open up "
        "an entirely new window on the universe."
    ),
))

# ============================================================ 03
ROWS.append(row(
    video_id="feynman_v2_day5_03_thunderstorm_cells",
    concept_type="GENERIC",
    header_title="Anatomy of a Thunderstorm",
    tagline="Why warm, wet air rises to the sky",
    equations=[
        r"\text{Adiabatic cooling: } T \uparrow \text{ height} \rightarrow T \downarrow",
        r"\text{Moist air cools slower (latent heat)}",
        r"\text{Thunderstorm cell} \approx 10\ \text{km tall}",
    ],
    visuals=[
        {"type": "particle_gas", "container_dims": [5.0, 4.5],
         "num_particles": 25, "color": "#F1C40F"},
        {"type": "vector", "start": [0.0, -1.8, 0], "end": [0.0, 1.8, 0],
         "color": "#E74C3C", "label": "updraft"},
        {"type": "text", "text": "warm + moist", "pos": [-3.5, -2.0, 0],
         "color": "#F1C40F", "font_size": 20},
        {"type": "text", "text": "cold + dry", "pos": [-3.5, 2.0, 0],
         "color": "#3498DB", "font_size": 20},
    ],
    audio=(
        "A thunderstorm is not one big cloud. It is made up of many "
        "smaller cells, each fairly independent. Let me describe one cell. "
        "The basic mechanism is simple: warm, moist air rises. As it "
        "rises, it expands. Expansion is adiabatic, so it cools. Now, if "
        "the air contains water vapor, the cooling is different. As the "
        "vapor condenses into droplets, it releases heat, so the air does "
        "not cool as fast. It stays warmer than its surroundings, which "
        "means it is lighter, which means it keeps rising. This is called "
        "convective instability, and it is what drives a thunderstorm "
        "cell. The rising air entrains more air from the sides. The water "
        "vapor condenses into tiny droplets, and above a certain altitude "
        "the droplets freeze into ice crystals. This buildup of ice is "
        "very important, because it is where the electrical effects come "
        "from. As the ice particles grow, they become heavy enough to "
        "fall. Now we have an updraft that is still going up, and a "
        "downdraft that is starting to come down. The whole thing becomes "
        "a churning storm. It can extend from a few hundred meters above "
        "the ground up to ten or fifteen thousand meters, and the updraft "
        "can be going at sixty miles an hour. That is the anatomy of a "
        "thunderstorm cell. In the next part, we will see how it "
        "generates a hundred million volts between its top and its "
        "bottom."
    ),
))

# ============================================================ 04
ROWS.append(row(
    video_id="feynman_v2_day5_04_charge_separation",
    concept_type="GENERIC",
    header_title="How a Cloud Builds 100 Million Volts",
    tagline="The mystery of charge separation",
    equations=[
        r"V_{\text{cloud-ground}} \sim 10^8\ \text{V}",
        r"Q_{\text{stroke}} \sim 20\ \text{C}",
        r"\text{Wilson: induced dipole on falling drop}",
    ],
    visuals=[
        {"type": "charge", "pos": [0.0, 2.5, 0], "color": "#FF4B4B",
         "radius": 0.18, "label": "+"},
        {"type": "charge", "pos": [0.0, -2.5, 0], "color": "#3498DB",
         "radius": 0.18, "label": "-"},
        {"type": "line", "start": [-3.5, 0.5, 0], "end": [3.5, 0.5, 0],
         "color": "#8A8F9C", "dashed": True},
        {"type": "text", "text": "10^8 V", "pos": [2.0, 0.5, 0],
         "color": "#F1C40F", "font_size": 22},
    ],
    audio=(
        "The charge at the bottom of a thundercloud is large enough to "
        "produce potential differences of twenty, thirty, even a hundred "
        "million volts between the cloud and the earth. That is far bigger "
        "than the four hundred thousand volts we found from the sky to the "
        "ground in a clear atmosphere. Where does all this charge come "
        "from? The mechanism is still not fully understood, but we have a "
        "good theory. In nineteen twenty-nine, C. T. R. Wilson proposed "
        "the following. The earth's fair weather field points downward, "
        "from positive sky to negative ground. A falling water or ice "
        "droplet in that field develops an induced dipole moment: the "
        "bottom becomes positive, the top negative. Now the air contains "
        "slow-moving large ions. Positive ions are repelled by the "
        "positive bottom of the drop and pushed away. Negative ions are "
        "attracted and captured. So the drop acquires a net negative "
        "charge as it falls, while leaving positive ions behind. Since the "
        "drops fall and the positive ions get carried up by the updraft, "
        "the cloud separates charge: negative at the bottom, positive at "
        "the top. This is Wilson's theory, and it explains the sign "
        "correctly. It also explains why thunderstorms pump negative "
        "charge down to the earth, keeping the earth charged even though "
        "fair weather is always discharging it. But the total charge "
        "involved is enormous, and there are still mysteries about how "
        "the mechanism sustains itself. Thunderstorm electrification "
        "remains one of the great unsolved problems in atmospheric "
        "physics."
    ),
))

# ============================================================ 05
ROWS.append(row(
    video_id="feynman_v2_day5_05_lightning",
    concept_type="GENERIC",
    header_title="How Lightning Actually Works",
    tagline="Step leaders, return strokes, and the thunderclap",
    equations=[
        r"\text{Leader speed} \sim c/6 \approx 5 \times 10^7\ \text{m/s}",
        r"\text{Return stroke current} \sim 10^4\ \text{A}",
        r"Q_{\text{transfer}} \approx 20\ \text{C}",
    ],
    visuals=[
        {"type": "line", "start": [0.0, 3.0, 0], "end": [0.0, 1.0, 0],
         "color": "#3498DB", "stroke_width": 3},
        {"type": "line", "start": [0.0, 1.0, 0], "end": [0.3, 0.0, 0],
         "color": "#3498DB", "stroke_width": 3},
        {"type": "line", "start": [0.3, 0.0, 0], "end": [0.0, -1.5, 0],
         "color": "#F1C40F", "stroke_width": 3},
        {"type": "line", "start": [0.0, -1.5, 0], "end": [0.3, -3.0, 0],
         "color": "#F1C40F", "stroke_width": 3},
        {"type": "text", "text": "step leader", "pos": [-2.5, 2.0, 0],
         "color": "#3498DB", "font_size": 20},
        {"type": "text", "text": "return stroke", "pos": [2.5, -2.0, 0],
         "color": "#F1C40F", "font_size": 20},
    ],
    audio=(
        "The first photographs of lightning were taken with a camera that "
        "was moved back and forth while the shutter was open. They showed "
        "something surprising: a lightning stroke is not one single "
        "discharge. It is a series of them, along the same path. Later, a "
        "camera with two lenses on a rapidly rotating disc, called a Boys "
        "camera, made the timing clear. Here is what happens. It all "
        "starts with a step leader. The bottom of the cloud is strongly "
        "negative. Electrons accelerate downward, ionizing the air as they "
        "go. But they do not go smoothly. The leader moves in steps of "
        "about fifty meters, pausing for about fifty microseconds between "
        "each step. It moves at roughly a sixth of the speed of light. The "
        "leader leaves behind a column of ionized air, a conducting "
        "channel from the cloud down toward the ground. When the leader "
        "finally touches the ground, the negative charge at the bottom of "
        "the cloud can finally escape. Electrons dump out of the cloud, "
        "rushing down the conducting channel. This is the return stroke, "
        "which is what we actually see as the bright flash of lightning. "
        "The current in the return stroke can be ten thousand amperes, "
        "and it carries down about twenty coulombs of charge. A few "
        "hundredths of a second later, if the cloud has more charge "
        "available, another leader comes down along the same ionized "
        "path, and there is another return stroke. So lightning strikes "
        "the same path many times in rapid succession, and that flickering "
        "is what we see."
    ),
))

# ============================================================ 06
ROWS.append(row(
    video_id="feynman_v2_day5_06_dielectric_constant",
    concept_type="GENERIC",
    header_title="What Faraday Discovered in Insulators",
    tagline="Why a capacitor holds more charge with glass between its plates",
    equations=[
        r"C = \frac{\epsilon_0 A}{d} \;\rightarrow\; C = \frac{\kappa \epsilon_0 A}{d}",
        r"\kappa = \text{dielectric constant}",
    ],
    visuals=[
        {"type": "line", "start": [-3.5, 1.5, 0], "end": [3.5, 1.5, 0],
         "color": "#FF4B4B", "stroke_width": 4},
        {"type": "line", "start": [-3.5, -1.5, 0], "end": [3.5, -1.5, 0],
         "color": "#3498DB", "stroke_width": 4},
        {"type": "shape", "kind": "rectangle", "pos": [0, 0, 0],
         "dims": [6.5, 2.5], "color": "#F1C40F", "fill_opacity": 0.15},
        {"type": "text", "text": "dielectric", "pos": [0, 0, 0],
         "color": "#F1C40F", "font_size": 22},
        {"type": "text", "text": "C = \\kappa \\epsilon_0 A / d",
         "pos": [0, -3.0, 0], "color": "#2ECC71", "font_size": 22},
    ],
    audio=(
        "In the eighteen thirties, Faraday did a simple experiment. He "
        "took a parallel-plate capacitor, charged it up, and measured the "
        "voltage. Then he slid a slab of glass between the plates. He "
        "found that the voltage went down. Since the charge on the plates "
        "was fixed, a lower voltage meant a higher capacitance. So the "
        "glass had increased the capacitance by some factor. That factor "
        "is called the dielectric constant, and it depends only on the "
        "material. For vacuum, it is exactly one. For air, it is about one "
        "point zero zero zero six. For glass, it is about five. For water, "
        "it is eighty. Now the surprising thing is that an insulator, "
        "which is by definition a material that does not conduct, has such "
        "a strong effect on the field. How can that be? The answer is "
        "polarization. In an insulator, the electrons are bound to "
        "individual atoms. But they can still shift a tiny bit within the "
        "atom. So when you apply an electric field, the positive nucleus "
        "gets pulled one way and the negative electrons the other way. The "
        "atoms become little dipoles, all aligned with the field. This "
        "collective alignment creates an internal electric field that "
        "opposes the applied field. So the net field inside the dielectric "
        "is weaker than it would be in vacuum. The capacitor voltages drop, "
        "and the capacitance rises. That is Faraday's observation "
        "explained. It is the beginning of our understanding of how matter "
        "responds to electric fields."
    ),
))

# ============================================================ 07
ROWS.append(row(
    video_id="feynman_v2_day5_07_polarization_charges",
    concept_type="GENERIC",
    header_title="Bound Charges in a Dielectric",
    tagline="Where polarization charges come from",
    equations=[
        r"\sigma_{\text{pol}} = P",
        r"\rho_{\text{pol}} = -\nabla \cdot \mathbf{P}",
        r"E = \frac{\sigma_{\text{free}} - P}{\epsilon_0}",
    ],
    visuals=[
        {"type": "shape", "kind": "rectangle", "pos": [0, 0, 0],
         "dims": [5.5, 2.5], "color": "#F1C40F", "fill_opacity": 0.15},
        {"type": "charge", "pos": [-2.9, 0.5, 0], "color": "#FF4B4B",
         "radius": 0.12},
        {"type": "charge", "pos": [2.9, 0.5, 0], "color": "#3498DB",
         "radius": 0.12},
        {"type": "vector", "start": [0.0, 0.0, 0], "end": [0.0, 1.0, 0],
         "color": "#2ECC71", "label": "P"},
        {"type": "text", "text": "\\sigma_{pol} = P",
         "pos": [0, -2.2, 0], "color": "#2ECC71", "font_size": 22},
    ],
    audio=(
        "When a dielectric slab is placed in a uniform electric field, all "
        "the little atomic dipoles align with the field. Inside the "
        "material, adjacent dipoles cancel each other out: the positive "
        "end of one meets the negative end of the next. So there is no net "
        "charge in the interior. But at the surfaces, something different "
        "happens. On one face, all the dipoles stick out their negative "
        "ends. On the other face, all the dipoles stick out their positive "
        "ends. So the surfaces acquire a sheet of bound charge. This is "
        "not free charge like the charge on a conductor. It is stuck to "
        "the atoms. But it still contributes to the electric field. We "
        "call it the polarization charge, and we write it as sigma pol. It "
        "turns out that the surface density of polarization charge is "
        "exactly equal to the magnitude of the polarization vector P. The "
        "polarization P is the dipole moment per unit volume. Now, "
        "combining this polarization charge with the free charge on the "
        "capacitor plates, we get the net field inside the dielectric. It "
        "is E equals sigma free minus P, all divided by epsilon zero. Since "
        "P points in the same direction as the field, it reduces the field. "
        "This is why the field inside a dielectric is smaller than the "
        "field in vacuum. The polarization charges are the microscopic "
        "explanation of Faraday's observation."
    ),
))

# ============================================================ 08
ROWS.append(row(
    video_id="feynman_v2_day5_08_d_field",
    concept_type="GENERIC",
    header_title="The D Field and Gauss's Law",
    tagline="Why we invent a new vector to simplify dielectric problems",
    equations=[
        r"\mathbf{D} = \epsilon_0 \mathbf{E} + \mathbf{P}",
        r"\nabla \cdot \mathbf{D} = \rho_{\text{free}}",
        r"\mathbf{D} = \kappa \epsilon_0 \mathbf{E}",
    ],
    visuals=[
        {"type": "shape", "kind": "rectangle", "pos": [0, 0, 0],
         "dims": [5.5, 2.5], "color": "#F1C40F", "fill_opacity": 0.15},
        {"type": "text", "text": "D = \\epsilon_0 E + P",
         "pos": [0, 1.5, 0], "color": "#F1C40F", "font_size": 22},
        {"type": "text", "text": "\\nabla \\cdot D = \\rho_{free}",
         "pos": [0, -1.5, 0], "color": "#2ECC71", "font_size": 22},
        {"type": "field", "direction": "RIGHT", "rows": 3, "opacity": 0.30,
         "color": "#3498DB"},
    ],
    audio=(
        "The problem with dielectrics is that we usually do not know where "
        "the polarization charges are. They depend on the field, which "
        "depends on the charges, which depend on the field. It is a "
        "self-consistent problem. To make life simpler, we introduce a "
        "new vector field, D, defined as D equals epsilon zero E plus P. "
        "The great advantage of D is that its divergence depends only on "
        "the free charges, the ones we put on the capacitor plates. All "
        "the messy polarization charge is hidden inside D. So Gauss's law "
        "in dielectrics takes a beautifully simple form: the divergence of "
        "D equals the free charge density. To solve a problem in a "
        "dielectric, we then need one more piece of information: the "
        "relation between D and E. For most materials, this relation is "
        "linear: D equals kappa epsilon zero times E, where kappa is the "
        "dielectric constant. This is a very useful approximation, but it "
        "is only an approximation. It breaks down at high fields, it "
        "breaks down for ferroelectric materials like barium titanate, and "
        "it breaks down when the frequency of the applied field becomes "
        "comparable to atomic transition frequencies. So we should always "
        "treat it as a model, not a fundamental law. The fundamental laws "
        "are Maxwell's equations, and they are always true. The relation "
        "between D and E is a property of matter. It is a very useful "
        "property, but it is not fundamental. That distinction is "
        "important."
    ),
))

# ============================================================ 09 PYQ
ROWS.append(row(
    video_id="feynman_v2_day5_pyq_01_dielectric_cap",
    concept_type="PYQ",
    header_title="Capacitor with a Dielectric",
    tagline="PYQ - plug in and compute",
    question_text=(
        "A parallel-plate capacitor has plate area 0.01 m^2 and plate "
        "separation 2 mm. A dielectric slab of kappa = 5 fills the space "
        "between the plates. What is the capacitance? "
        "Use epsilon_0 = 8.85e-12 F/m."
    ),
    options=["(A) 44 pF", "(B) 88 pF", "(C) 221 pF", "(D) 442 pF"],
    correct="Correct Answer: (C) 221 pF",
    equations=[
        r"C = \frac{\kappa \epsilon_0 A}{d}",
        r"C = \frac{5 \times 8.85 \times 10^{-12} \times 0.01}{2 \times 10^{-3}}",
        r"C = 2.21 \times 10^{-10}\ \text{F} = 221\ \text{pF}",
    ],
    visuals=[
        {"type": "line", "start": [-3.5, 1.5, 0], "end": [3.5, 1.5, 0],
         "color": "#FF4B4B", "stroke_width": 4},
        {"type": "line", "start": [-3.5, -1.5, 0], "end": [3.5, -1.5, 0],
         "color": "#3498DB", "stroke_width": 4},
        {"type": "shape", "kind": "rectangle", "pos": [0, 0, 0],
         "dims": [6.5, 2.5], "color": "#F1C40F", "fill_opacity": 0.15},
        {"type": "text", "text": "\\kappa = 5", "pos": [0, 0, 0],
         "color": "#F1C40F", "font_size": 22},
        {"type": "text", "text": "C = 221 pF", "pos": [0, -3.0, 0],
         "color": "#2ECC71", "font_size": 22},
    ],
    audio=(
        "A parallel-plate capacitor has plate area zero point zero one "
        "meters squared and plate separation two millimeters. A dielectric "
        "slab with dielectric constant kappa equals five fills the space "
        "between the plates. What is the capacitance? Use epsilon zero "
        "equals eight point eight five times ten to the minus twelve. The "
        "formula is C equals kappa epsilon zero A over d. Substituting: "
        "kappa is five, epsilon zero is eight point eight five times ten "
        "to the minus twelve, area is zero point zero one, and separation "
        "is two times ten to the minus three. Multiplying: five times "
        "eight point eight five times ten to the minus twelve equals four "
        "point four two five times ten to the minus eleven. Times zero "
        "point zero one equals four point four two five times ten to the "
        "minus thirteen. Divided by two times ten to the minus three gives "
        "two point two one times ten to the minus ten farads. That is two "
        "hundred and twenty one picofarads. Option C. Notice how the "
        "dielectric boosted the capacitance by a factor of five. Without "
        "the dielectric, the capacitance would have been forty four "
        "picofarads. With the dielectric, it is five times larger. This is "
        "one of the key practical reasons we use dielectrics: to make "
        "compact, high-capacitance capacitors for electronics. Radio, "
        "audio equipment, computers—they all depend on this factor of "
        "kappa."
    ),
))

# ============================================================ 10 PYQ
ROWS.append(row(
    video_id="feynman_v2_day5_pyq_02_field_dielectric",
    concept_type="PYQ",
    header_title="Field Inside a Dielectric",
    tagline="PYQ - reducing the field by kappa",
    question_text=(
        "A parallel-plate capacitor is charged to a surface charge density "
        "of 2.0 x 10^-6 C/m^2. A dielectric with kappa = 4 is inserted. "
        "What is the electric field inside the dielectric? "
        "Use epsilon_0 = 8.85e-12 F/m."
    ),
    options=["(A) 2.26 x 10^5 N/C", "(B) 5.65 x 10^4 N/C",
             "(C) 1.13 x 10^5 N/C", "(D) 4.52 x 10^5 N/C"],
    correct="Correct Answer: (B) 5.65 x 10^4 N/C",
    equations=[
        r"E_0 = \frac{\sigma_{\text{free}}}{\epsilon_0} = \frac{2.0 \times 10^{-6}}{8.85 \times 10^{-12}} = 2.26 \times 10^5\ \text{N/C}",
        r"E = \frac{E_0}{\kappa} = \frac{2.26 \times 10^5}{4} = 5.65 \times 10^4\ \text{N/C}",
    ],
    visuals=[
        {"type": "line", "start": [-3.5, 1.5, 0], "end": [3.5, 1.5, 0],
         "color": "#FF4B4B", "stroke_width": 4},
        {"type": "line", "start": [-3.5, -1.5, 0], "end": [3.5, -1.5, 0],
         "color": "#3498DB", "stroke_width": 4},
        {"type": "shape", "kind": "rectangle", "pos": [0, 0, 0],
         "dims": [6.5, 2.5], "color": "#F1C40F", "fill_opacity": 0.15},
        {"type": "field", "direction": "DOWN", "rows": 3, "opacity": 0.25},
        {"type": "text", "text": "E = 5.65 \\times 10^4 N/C",
         "pos": [0, -3.0, 0], "color": "#2ECC71", "font_size": 22},
    ],
    audio=(
        "A parallel-plate capacitor is charged to a surface charge density "
        "of two times ten to the minus six coulombs per meter squared. A "
        "dielectric with kappa equals four is inserted between the plates. "
        "What is the electric field inside the dielectric? First we "
        "compute the field without the dielectric. E zero equals sigma "
        "free over epsilon zero. Sigma free is two times ten to the minus "
        "six. Epsilon zero is eight point eight five times ten to the "
        "minus twelve. Dividing gives two point two six times ten to the "
        "fifth newtons per coulomb. Now, when we insert the dielectric, "
        "the field reduces by the factor kappa. So E equals E zero over "
        "kappa equals two point two six times ten to the fifth, divided by "
        "four, which equals five point six five times ten to the fourth "
        "newtons per coulomb. Option B. Let me emphasize what just "
        "happened. We did not add or remove any free charge. The charge on "
        "the plates is still two times ten to the minus six per square "
        "meter. But the field inside the dielectric is four times smaller. "
        "This is because the polarization of the dielectric creates bound "
        "charges that partially cancel the field from the free charges. "
        "The net effect is a reduction by the factor kappa. This is why a "
        "dielectric can be used to store more charge for a given voltage. "
        "It reduces the field, so you can push more charge onto the plates "
        "before the voltage gets too high. This is the fundamental reason "
        "we fill capacitors with dielectrics in the first place."
    ),
))


def main():
    with open("content_batch.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER,
                           quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in ROWS:
            w.writerow(r)
    print(f"Wrote content_batch.csv with {len(ROWS)} rows, "
          f"{len(HEADER)} columns each.")
    print("Day 5: Ch 9-10 of Feynman Vol II (10 rows, horizontal).")


if __name__ == "__main__":
    main()
