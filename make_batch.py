import csv
import json

HEADERS = [
    "video_id", "concept_type", "header_title", "tagline", 
    "question_text", "option_a", "option_b", "option_c", "option_d", "correct_answer", 
    "equations_json", "visual_data_json", "audio_script", "orientation", "target_duration_sec"
]

ROWS = [
    # --- VOLUME 1: CONCEPT (Vertical) ---
    {
        "video_id": "feynman_v1_concept_energy",
        "concept_type": "GENERIC",
        "header_title": "Conservation of Energy",
        "tagline": "Feynman Vol 1, Ch 4: The ultimate bookkeeping of nature.",
        "equations_json": json.dumps(["E = mgh + \\frac{1}{2}mv^2"]),
        "visual_data_json": json.dumps([
            {"type": "energy_bar", "id": "pe", "fraction": 1.0, "pos": [-2, 0, 0]}, 
            {"type": "energy_bar", "id": "ke", "fraction": 0.0, "pos": [2, 0, 0]}
        ]),
        "audio_script": "Feynman called it the ultimate bookkeeping of nature. Imagine a mass held high above the ground. It possesses potential energy. As it falls, this stored energy converts flawlessly into kinetic energy. The sum remains perfectly constant. No energy is lost; it merely changes its disguise.",
        "orientation": "vertical",
        "target_duration_sec": 30
    },
    # --- VOLUME 2: CONCEPT (Vertical) ---
    {
        "video_id": "feynman_v2_concept_emwave",
        "concept_type": "GENERIC",
        "header_title": "Light is a Wave",
        "tagline": "Feynman Vol 2, Ch 20: The dance of electric and magnetic fields.",
        "equations_json": json.dumps(["\\nabla \\times \\mathbf{E} = -\\frac{\\partial \\mathbf{B}}{\\partial t}"]),
        "visual_data_json": json.dumps([
            {"type": "electromagnetic_wave", "id": "wave1", "amplitude": 1, "frequency": 1, "speed": 2, "length": 7}
        ]),
        "audio_script": "What is light? Feynman showed it is a self-sustaining dance between electric and magnetic fields. A changing electric field creates a magnetic field, and a changing magnetic field creates an electric field. They leapfrog through the vacuum of space, carrying energy across the universe at the ultimate speed limit.",
        "orientation": "vertical",
        "target_duration_sec": 35
    },
    # --- VOLUME 3: CONCEPT (Vertical) ---
    {
        "video_id": "feynman_v3_concept_twoslit",
        "concept_type": "GENERIC",
        "header_title": "The Two-Slit Mystery",
        "tagline": "Feynman Vol 3, Ch 1: The heart of quantum mechanics.",
        "equations_json": json.dumps(["P = |\\psi_1 + \\psi_2|^2"]),
        "visual_data_json": json.dumps([
            {"type": "two_path_interference", "id": "inter1"}
        ]),
        "audio_script": "Feynman called the two-slit experiment the heart of quantum mechanics. When a particle can take two paths to a screen, it doesn't choose one. It takes both. The probability amplitudes add together like waves, creating a pattern of bright and dark fringes. It is a mystery no classical mind can fully picture, yet it is the fundamental truth of nature.",
        "orientation": "vertical",
        "target_duration_sec": 35
    },
    # --- VOLUME 1: APPLICATION (Horizontal) ---
    {
        "video_id": "feynman_v1_app_ratchet",
        "concept_type": "GENERIC",
        "header_title": "The Brownian Ratchet",
        "tagline": "Feynman Vol 1, Ch 46: Why microscopic machines fail.",
        "equations_json": json.dumps(["\\Delta S \\ge 0", "k_B T \\ln 2"]),
        "visual_data_json": json.dumps([
            {"type": "text", "id": "t1", "text": "T_1 = T_2 \\implies \\text{No work}", "pos": [0, 2, 0]}, 
            {"type": "particle_gas", "id": "gas1", "count": 20, "pos": [-3, -1, 0]}
        ]),
        "audio_script": "Can we build a microscopic machine that extracts work from the random thermal jiggling of atoms? Feynman analyzed the Brownian Ratchet, a tiny gear with a pawl. Intuition says the random bumps should turn it in one direction, generating free energy. But Feynman proved that if the pawl is at the same temperature as the gas, it too will jiggle, slipping backwards exactly as often as it is pushed forwards. The Second Law of Thermodynamics survives, even at the atomic scale.",
        "orientation": "horizontal",
        "target_duration_sec": 60
    },
    # --- VOLUME 2: APPLICATION (Horizontal) ---
    {
        "video_id": "feynman_v2_app_betatron",
        "concept_type": "GENERIC",
        "header_title": "The Betatron Accelerator",
        "tagline": "Feynman Vol 2, Ch 17: Trapping electrons in a magnetic vortex.",
        "equations_json": json.dumps(["\\oint \\mathbf{E} \\cdot d\\mathbf{l} = -\\frac{d\\Phi_B}{dt}", "F = qvB"]),
        "visual_data_json": json.dumps([
            {"type": "circle", "id": "ring", "radius": 2.5, "color": "GREY"}, 
            {"type": "orbit", "id": "electron", "width": 5, "height": 5}
        ]),
        "audio_script": "How do we accelerate electrons to near the speed of light without hitting them with physical paddles? Enter the Betatron. By increasing a magnetic field through a circular loop, Faraday's Law guarantees a swirling electric field is induced along the path. This invisible electric field accelerates the electrons. Simultaneously, the magnetic field itself bends their trajectory into a perfect circle. It is a masterpiece of applied electromagnetism, turning pure calculus into a high-energy particle beam.",
        "orientation": "horizontal",
        "target_duration_sec": 60
    },
    # --- VOLUME 3: APPLICATION (Horizontal) ---
    {
        "video_id": "feynman_v3_app_maser",
        "concept_type": "GENERIC",
        "header_title": "The Ammonia Maser",
        "tagline": "Feynman Vol 3, Ch 8: The first quantum amplifier.",
        "equations_json": json.dumps(["E = E_0 \\pm A", "h \\nu = 2A"]),
        "visual_data_json": json.dumps([
            {"type": "energy_landscape", "id": "well", "pos": [0, 0, 0]}, 
            {"type": "live_label", "id": "freq", "prefix": "\\nu", "unit": "GHz", "to": 24.0, "pos": [3, 2, 0]}
        ]),
        "audio_script": "Before the laser, there was the Maser. Feynman used the ammonia molecule to explain it. The nitrogen atom can tunnel through the plane of the hydrogen atoms, creating two quantum states separated by a tiny energy gap. When ammonia molecules in the higher state enter a resonant cavity, they are stimulated to drop to the lower state, releasing their energy as perfectly synchronized microwave photons. This quantum leap from theory to engineering gave us the most precise clocks in human history.",
        "orientation": "horizontal",
        "target_duration_sec": 65
    }
]

# Fill empty columns
for r in ROWS:
    for h in HEADERS:
        if h not in r:
            r[h] = ""

with open("feynman_6_video_batch.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=HEADERS)
    writer.writeheader()
    writer.writerows(ROWS)

print("Successfully generated feynman_6_video_batch.csv")
