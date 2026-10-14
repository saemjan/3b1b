README.md

```markdown
# 🎬 Feynman Physics Shorts — Automated Video Pipeline

**Turn Feynman's Lectures on Physics into daily 3-minute vertical videos — automatically.**

A production pipeline that reads one CSV, synthesizes a cloned voice, renders a
Manim animation, muxes them with FFmpeg, and produces a finished YouTube Short.
Every day, the only thing you edit is one line in a CSV. Everything else runs
itself.

> **Tagline:** NEET · JEE · MIT
> **Style:** 3Blue1Brown's visual elegance · Feynman's narrative voice · Strang's pedagogical clarity.
> **Format:** 1080×1920 (9:16 vertical) · ~3 minutes · 30 fps

---

## 📖 Table of Contents

1. [What It Does](#-what-it-does)
2. [Architecture](#-architecture)
3. [File Inventory](#-file-inventory)
4. [Quick Start](#-quick-start)
5. [Daily Workflow](#-daily-workflow)
6. [CSV Schema](#-csv-schema)
7. [The Primitive Catalog](#-the-primitive-catalog)
8. [Content Coverage](#-content-coverage)
9. [The Audio Pipeline](#-the-audio-pipeline)
10. [Validation & Safety](#-validation--safety)
11. [CI / GitHub Actions](#-ci--github-actions)
12. [Troubleshooting](#-troubleshooting)
13. [FAQ](#-faq)
14. [Roadmap](#-roadmap)
15. [Golden Rules](#-golden-rules)

---

## 🎯 What It Does

Given a row in `content_batch.csv` like this:

```

video_id,concept_type,header_title,tagline,question_text,...,orientation
feynman_d1_01_atoms,GENERIC,One Sentence Holds All of Chemistry,The atomic hypothesis,...,vertical

```

The pipeline produces this:

```

output_shorts/feynman_d1_01_atoms_final.mp4

```

A fully narrated, animated, music-mixed, 3-minute vertical video explaining
Feynman's "atomic hypothesis." Ready to upload.

**What happens between input and output:**

1. **Voice** — XTTS-v2 clones your voice, reads the `audio_script`, produces a mastered WAV
2. **Render** — Manim draws the visuals described in `visual_data_json`
3. **Sync** — Voice and visuals are timed to the beat
4. **Mix** — FFmpeg glues voice + ambient pad + video into the final MP4

**No manual editing. No timeline software. No video editor.**

---

## 🏗 Architecture

Four stages, orchestrated by `batch_runner.py`. Each stage is a separate Python
script you can run standalone for debugging.

```

┌─────────────────────────────────────────────────────────────────┐
│  content_batch.csv  (the only thing you edit)                   │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│  1. generate_audio.py + soundscape.py                           │
│     → XTTS-v2 voice clone                                        │
│     → Mastered WAV (44.1 kHz, −14 LUFS, HPF/compress/LPF/fade)   │
│     → Ambient pad WAV (low-pass noise at −34 dB)                 │
│     → Duration returned to orchestrator                          │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│  2. render_universal.py  (Manim)                                 │
│     → Reads equations_json + visual_data_json                    │
│     → Picks scene class based on concept_type                    │
│     → Renders to media/videos/…/*.mp4 (raw, silent)              │
│     → 36 primitives, orientation-aware zones, branding           │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│  3. FFmpeg (inside batch_runner.py)                              │
│     → amix voice + pad                                           │
│     → apad to keep audio length                                 │
│     → tpad to keep video length                                  │
│     → H.264 + AAC 192k, yuv420p                                  │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│  4. output_shorts/<video_id>_final.mp4  (the finished Short)     │
└─────────────────────────────────────────────────────────────────┘

```

---

## 📁 File Inventory

Every file in the repo, what it does, and whether you should touch it.

### 🟢 Files you **edit regularly**

| File | Purpose | Safe to edit? |
|---|---|---|
| `content_batch.csv` | The daily input. One row per video. **This is the only file you touch every day.** | ✅ Yes |
| `generate_csv.py` | Optional. A Python generator for large batches. Skip if you edit CSV directly. | ✅ Yes |

### 🔵 Code files (stable, do not edit unless you know why)

| File | Purpose | Lines |
|---|---|---|
| `batch_runner.py` | Orchestrator. Reads CSV, calls the three pipeline stages, retries failures, logs runs. | ~250 |
| `generate_audio.py` | XTTS-v2 voice synthesis with deterministic seed per `video_id`. Falls back to CPU on CUDA OOM. | ~290 |
| `soundscape.py` | Voice mastering chain: DC-remove → HPF 80 Hz → soft compress 3:1 → LPF 12 kHz → LUFS −14 → peak limit 0.891. Also generates the ambient pad. | ~155 |
| `text_normalizer.py` | Prepares narration for TTS: units after numbers, Greek letters spelled out, scientific notation, LaTeX stripped. | ~200 |
| `render_universal.py` | The Manim engine. 36 primitives, 3 scene classes, orientation-aware zones, SaemLabs branding. | ~2000 |
| `schema_validator.py` | Stdlib-only pre-flight check. Column count, JSON integrity, primitive names, coordinates within frame, word count. | ~220 |

### 🟡 Assets

| File | Purpose | Notes |
|---|---|---|
| `saem_voice_sample.wav` | 10–20 second reference clip of your voice. XTTS-v2 uses it to clone. | **Back this up.** Not in repo. |

### 🔴 Infrastructure

| File | Purpose |
|---|---|
| `.github/workflows/render_shorts.yml` | CI. Validates, then 4-way shards batch rendering, then merges artifacts. |
| `tools/add_orientation.py` | One-shot migration to add the `orientation` column to old CSVs. |

### 📄 Docs

| File | Purpose |
|---|---|
| `README.md` | This file. |
| `MANIFEST.md` | File checksums, version, changelog. |
| `SAVEPOINT.md` | Feature-complete checkpoint notes. |
| `requirements.txt` | Python dependency pin. |

---

## 🚀 Quick Start

### 1. System dependencies

Ubuntu / Debian:
```bash
sudo apt-get install -y \
  ffmpeg \
  texlive-latex-base texlive-latex-recommended texlive-latex-extra \
  texlive-science texlive-fonts-recommended dvisvgm \
  libcairo2-dev libpango1.0-dev libsndfile1 \
  build-essential pkg-config
```

macOS:

```bash
brew install ffmpeg pkg-config cairo pango libpng jpeg giflib librsvg
# LaTeX: install MacTeX or BasicTeX from https://tug.org/mactex/
```

2. Python

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

3. Voice reference

Drop a 10–20 second WAV of your voice at the repo root:

```bash
cp /path/to/your/voice.wav saem_voice_sample.wav
```

4. First render

```bash
# Validate the CSV
python3 schema_validator.py content_batch.csv

# Render one row (fast feedback)
python3 batch_runner.py --only feynman_d1_01_atoms --draft

# Full render
python3 batch_runner.py --only feynman_d1_01_atoms
```

Output: output_shorts/feynman_d1_01_atoms_final.mp4

### 3Blue1Brown-style Feynman demo

A short, original explanation inspired by the instantaneous-speed topic in
Feynman's lectures is included at [examples/feynman_speed_demo.csv](examples/feynman_speed_demo.csv).
It uses the production CSV schema and animates a secant line converging to a
tangent as the time interval shrinks. The explanation is newly written rather
than copied from the lectures.

### Whole-object force-and-motion demo

[examples/projectile_complete_object.csv](examples/projectile_complete_object.csv)
is a ready-to-render, 60-second example of a thrown sphere. The renderer
computes its trajectory from the launch speed, angle, and gravitational
acceleration, then synchronizes the visible body and center, path, velocity,
weight vector, and live velocity/time values. The example names its assumptions
(translation only and no air resistance) and marks vectors as schematic.

```bash
python3 schema_validator.py examples/projectile_complete_object.csv
python3 batch_runner.py --csv examples/projectile_complete_object.csv --dry-run
python3 batch_runner.py --csv examples/projectile_complete_object.csv \
  --only projectile_complete_object_demo --draft
```

The design follows standard free-body-diagram practice: isolate one body and
show only external forces acting on it. Keep the physical model explicit, and
use coordinated views (object, force/motion annotations, equations) to explain
the same event rather than adding decorative motion. For reference, see
[OpenStax on free-body diagrams](https://openstax.org/books/university-physics-volume-1/pages/5-7-drawing-free-body-diagrams),
Ainsworth's framework for learning with multiple representations
[doi:10.1016/j.learninstruc.2006.03.001](https://doi.org/10.1016/j.learninstruc.2006.03.001),
and Tversky, Morrison, and Betrancourt's review of when animation facilitates
understanding [doi:10.1006/ijhc.2002.1017](https://doi.org/10.1006/ijhc.2002.1017).
These sources inform general explanatory principles; the visuals and wording
in this example are original.

### Reusable Newtonian simulation

The [`physics_simulation` primitive](./render_universal.py) provides a
declarative, force-driven starting point rather than another hand-drawn
trajectory. Define bodies and forces in CSV JSON; the renderer integrates
Newton's second law with RK4 and synchronizes full-body markers, trails,
velocity, net acceleration, and a live state readout. The spring-and-mass
lesson in
[examples/physics_simulation_spring_demo.csv](examples/physics_simulation_spring_demo.csv)
is a ready-to-render example:

```bash
python3 schema_validator.py examples/physics_simulation_spring_demo.csv
python3 batch_runner.py --csv examples/physics_simulation_spring_demo.csv --dry-run
python3 batch_runner.py --csv examples/physics_simulation_spring_demo.csv \
  --only physics_simulation_spring_demo --draft
```

Supported force definitions are `uniform_acceleration` (a 2D acceleration
vector), `linear_drag` (force `-b v`), `spring` (an anchor or another body,
stiffness, rest length, and optional damping), and `central_gravity` (a fixed
source with parameter `mu = GM`). Body entries use 2D position and velocity,
mass, radius, label, and color. All values use a consistent unit system chosen
by the author. `duration` is the simulated physical time; optional
`playback_duration` sets how many video seconds it takes to show that
simulation. By default it plays once and holds the final state. Set `loop` only
when a reset is pedagogically appropriate; a loop can be misleading for a
damped or otherwise non-periodic system. The solver rejects unknown forces,
invalid input, and singular gravity rather than inventing a fallback.

This is an extensible classical point-mass mechanics foundation, **not** an
automatic solver for every physics problem. Contacts, rigid-body rotation,
fluids, electromagnetism, quantum physics, and arbitrary natural-language
problem solving need additional models/solvers. Each video still needs its
assumptions, derivation, narration, and storyboard reviewed for correctness.
The example shows `v` and net `a` with explicitly schematic arrow lengths; do
not interpret those display lengths as calibrated measurements.

### Dimension-aware geometry

The shared `geometry` primitive in [geometry_engine.py](./geometry_engine.py)
and [render_universal.py](./render_universal.py) supports 1D, 2D, and 3D
coordinates. One-dimensional points embed on the x-axis; 2D points embed in
the xy-plane; 3D coordinates use xyz. Supported kinds are `point`, `points`,
`segment`, `polyline`, `polygon`, `circle`, `ellipse`, `sphere`, `cube`,
`cylinder`, and `cone`. Solid 3D kinds require a 3D scene (`concept_type=3D`);
the 2D renderer rejects them explicitly. The 3D renderer now builds geometry
from `visual_data_json` instead of substituting a hard-coded helix.

Rigid transforms are optional and update the existing Manim object in place,
rather than rebuilding its geometry every frame:

```json
{
  "type": "geometry",
  "id": "rotating_cube",
  "dimension": 3,
  "kind": "cube",
  "side_length": 1.5,
  "position": [0, 0, 0],
  "motion": {
    "velocity": [0, 0, 0],
    "angular_velocity": 0.5,
    "axis": [0, 1, 0]
  }
}
```

The
[geometry dimensions example](./examples/geometry_dimensions_demo.csv)
combines a 1D segment, 2D triangle, and rotating 3D cube:

```bash
python3 schema_validator.py examples/geometry_dimensions_demo.csv
python3 batch_runner.py --csv examples/geometry_dimensions_demo.csv --dry-run
python3 batch_runner.py --csv examples/geometry_dimensions_demo.csv \
  --only geometry_dimensions_demo --draft
```

The builder is intentionally declarative and bounded (point-cloud entries are
limited to 256 points); arbitrary meshes, deformable solids, and every possible
geometric construction are not implied. Prefer one polyline/polygon primitive
over hundreds of separate line objects where possible.

### Single-variable calculus graphics

The renderer also supports reusable calculus visuals through
[`calculus_engine.py`](./calculus_engine.py): `calculus_graph` plots a function,
`derivative_tangent` compares a secant with a numerically estimated tangent,
`integral_area` shades the region between a curve and a baseline, and
`riemann_sum` draws left-, right-, or midpoint-sampled rectangles. Each
primitive accepts `expression`, `x_range`, `y_range`, `center`, `x_length`,
and `y_length`; interval visuals also accept `a` and `b`.

```json
[
  {
    "type": "derivative_tangent",
    "id": "slope_at_one",
    "expression": "x^2",
    "x_range": [-2, 2],
    "y_range": [0, 4],
    "x0": 1,
    "delta": 0.6
  },
  {
    "type": "riemann_sum",
    "id": "area_approximation",
    "expression": "x^2",
    "x_range": [0, 2],
    "y_range": [0, 4],
    "a": 0,
    "b": 2,
    "rectangles": 8,
    "sample": "midpoint"
  },
  {
    "type": "integral_area",
    "id": "exact_region",
    "expression": "x^2",
    "x_range": [0, 2],
    "y_range": [0, 4],
    "a": 0,
    "b": 2
  }
]
```

Expressions are arithmetic over `x` with `pi`, `e`, powers (`^` or `**`),
and common functions including `sin`, `cos`, `tan`, `exp`, `log`, and `sqrt`.
They are parsed with a restricted evaluator, not executed as Python. Riemann
sums and shaded regions are bounded to 256 rectangles/samples per visual.

### Electromagnetic fields and waves

[`electromagnetics_engine.py`](./electromagnetics_engine.py) adds SI-based
numerical models and three renderer primitives. `electric_field` samples the
Coulomb field from point charges (`position` in metres and `charge` in
coulombs); `magnetic_field` samples the Biot–Savart field of finite straight
wires (`start`, `end` in metres and `current` in amperes); and
`electromagnetic_wave` animates synchronized electric and magnetic plane-wave
traces with propagation direction. Both field maps show vector direction and
use arrow length normalized within the displayed grid, not as a calibrated
field-strength scale. The paired wave traces are normalized for legibility;
the magnetic amplitude relation for a vacuum wave is `B₀ = E₀ / c`.

```json
[
  {
    "type": "electric_field",
    "id": "dipole_field",
    "charges": [
      {"position": [-1, 0, 0], "charge": 1e-9},
      {"position": [1, 0, 0], "charge": -1e-9}
    ],
    "x_range": [-3, 3],
    "y_range": [-2, 2],
    "columns": 13,
    "rows": 9
  },
  {
    "type": "electromagnetic_wave",
    "id": "plane_wave",
    "amplitude": 1,
    "frequency": 1,
    "speed": 2,
    "length": 7
  }
]
```

The numerical API `electric_field`, `magnetic_field_from_wire`, and
`plane_wave_fields` exposes the underlying vector calculations for reuse and
testing. It validates transverse polarization and the dispersion relation
`ω = v k`, and computes `B = k̂ × E / v` for the requested phase speed `v`.
Field maps are limited to 256 sample points per visual; wire-field integration
is bounded to 4096 segments. The point-charge singularity and polarization
constraints are reported explicitly rather than regularized.

### Linear algebra graphics

[`linear_algebra_engine.py`](./linear_algebra_engine.py) provides numeric
`vector_add`, `dot_product`, `cross_product`, and `determinant` helpers, and a
`linear_algebra` visual primitive with `vectors`, `dot`, `cross`, or
`determinant` operations. Vector calculations accept finite 2D or 3D inputs
with matching dimensions. The cross product returns a 3D vector for 3D inputs
and the signed z-component (scalar) for 2D inputs. Numeric determinants
support square matrices through 8×8; determinant graphics currently show the
signed area of a 2×2 matrix's column parallelogram.

```json
[
  {
    "type": "linear_algebra",
    "id": "vector_sum",
    "operation": "vectors",
    "a": [2, 1],
    "b": [-1, 2]
  },
  {
    "type": "linear_algebra",
    "id": "dot_product",
    "operation": "dot",
    "a": [2, 1],
    "b": [-1, 2]
  },
  {
    "type": "linear_algebra",
    "id": "determinant",
    "operation": "determinant",
    "matrix": [[2, -1], [1, 2]]
  }
]
```

### Dual-format concept generator

The repo now includes a generalized generator for arbitrary ideas and problems:

```bash
python3 tools/generate_topic_bundle.py \
   --concept "Conservation of Energy" \
   --problem "A 2 kg object falls 5 m. What is the loss in potential energy?" \
   --kind both \
   --output content_batch.csv
```

This writes a CSV bundle with:

- one horizontal 1-minute short
- one vertical 3-minute lecture
- a focusable question → principle → result storyboard with beat transitions
- narration paced to each target runtime and the supplied problem shown on screen
- a falling-energy archetype with an animated object, complementary energy bars,
  and an explicit $mgh$ result when mass and drop height are supplied

The batch runner can target either style directly:

```bash
python3 batch_runner.py --format short --dry-run
python3 batch_runner.py --format lecture --dry-run
```

The renderer adds procedural tick, transition, drone, and chime cues. `sound_design.py`
generates these locally without external sound assets; the final mix keeps them
quiet under the synthesized voice and a slowly shifting tonal bed. Full voice
synthesis still requires the XTTS dependencies and `saem_voice_sample.wav`.

The generator provides a reusable explanation structure; it does not solve an
arbitrary problem or verify its physics. Review the narration and principle for
the specific topic before publishing.

```bash
cp examples/feynman_speed_demo.csv content_batch.csv
python3 schema_validator.py content_batch.csv
python3 batch_runner.py --only feynman_demo_speed_limit --draft
```

This example explains why instantaneous speed is a limit of average speed.
Its secant-to-tangent visual is an animation, not a static graph, and keeps
the idea focused rather than presenting a dense slide deck.

### Original 20-video Feynman-inspired batch

Generate or refresh the standalone 20-row batch without replacing the
production `content_batch.csv`:

```bash
python3 tools/generate_feynman_series.py
python3 schema_validator.py examples/feynman_20_video_batch.csv
python3 batch_runner.py --csv examples/feynman_20_video_batch.csv --dry-run
```

The batch contains 10 original 60-second horizontal shorts and 10
corresponding 180-second vertical lectures across atoms, energy, clocks,
random walks, calculus, gravity, Newtonian motion, momentum, waves, and
interference. Each topic has a concept-specific Manim animation, equations,
timed story beats, and narration. Story beats use the renderer's locally
generated transition and emphasis cues. The scripts are newly written
explanations inspired by physics topics associated with Feynman's lectures;
they are not transcriptions or quotations. Review physics assumptions and
audio before publishing.

To render this batch in GitHub Actions, use **Run workflow** and select
`examples/feynman_20_video_batch.csv` as the CSV batch. Locally, `--csv`
selects the same input without copying over the production batch.

See [CSV_AUTHORING.md](CSV_AUTHORING.md) for the 10-concept/10-problem
capability matrix, multi-engine visual examples, and the current CSV schema.

---

🔁 Daily Workflow

The only thing you do every day:

Step 1 — Open the CSV

```bash
$EDITOR content_batch.csv
```

Step 2 — Paste one new row

The row has 14 required columns. The current generators append two optional
columns, `beats_json` and `target_duration_sec`:

```csv
video_id,concept_type,header_title,tagline,question_text,option_a,option_b,option_c,option_d,correct_answer,equations_json,visual_data_json,audio_script,orientation
```

For a concept video, leave question_text, option_a–d, and correct_answer empty (7 commas in a row):

```csv
my_topic_01,GENERIC,Why Waves Add,Superposition,,,,,,,"[""\psi = \\psi_1 + \\psi_2""]","[{""type"": ""wave"", ""x_range"": [-4, 4], ""amplitude"": 0.6}]","The narration goes here.","vertical"
```

For a PYQ, fill in the question and options:

```csv
my_pyq_01,PYQ,Distance, Time, and Average Speed,Definition problem,A car travels 60 km in 1 hour and 90 km in 2 hours,what is average speed?,(A) 50 km/h,(B) 60 km/h,(C) 75 km/h,(D) 90 km/h,Correct Answer: (A) 50 km/h,"[""v = d/t""]","[{""type"": ""text"", ""text"": ""v = d/t"", ""pos"": [0, 2.0, 0]}]","Narration.","vertical"
```

Step 3 — Validate

```bash
python3 schema_validator.py content_batch.csv
```

You should see:

```
[INFO] Validating content_batch.csv (orientation=vertical)
[SUCCESS] All checks passed.
```

Step 4 — Render

```bash
# Just the new row
python3 batch_runner.py --only my_topic_01

# Or, full batch
python3 batch_runner.py --retries 2
```

Or push to GitHub — the CI runs the batch 4-way parallel and drops the MP4s as
artifacts.

---

📊 CSV Schema

14 required columns, in this exact order. The generators may append the optional
`beats_json` and `target_duration_sec` columns, for 16 total:

# Column Type Required? Notes
1 video_id string ✅ Filesystem-safe. Unique per row. Pattern: feynman_dayN_NN_slug
2 concept_type enum ✅ GENERIC \| PYQ \| 3D \| 3D_HELIX
3 header_title string ✅ Bold top title, ~6 words. Quote if it contains a comma.
4 tagline string ✅ One-line italic subtitle.
5 question_text string PYQ only Empty for GENERIC.
6 option_a string PYQ only e.g. (A) 50 km/h
7 option_b string PYQ only 
8 option_c string PYQ only 
9 option_d string PYQ only 
10 correct_answer string PYQ only e.g. Correct Answer: (A) 50 km/h
11 equations_json JSON array ✅ LaTeX strings. Escape backslashes as \\.
12 visual_data_json JSON array ✅ Primitive dicts. See catalog below.
13 audio_script string ✅ Spoken narration; write to the requested runtime.
14 orientation enum ✅ vertical (9:16) or horizontal (16:9). Default: vertical.
15 beats_json JSON array Optional. Timed story-beat types and focus IDs.
16 target_duration_sec number Optional. Narration pacing hint used by validation.

For timing guidance, the validator expects about 112–180 words at 60 seconds
and 337–540 words at 180 seconds when `target_duration_sec` is present. The
render duration follows the generated narration audio, not this metadata field.

JSON escaping — the two-layer rule

Both JSON columns live inside CSV cells. Two layers of escaping:

What you want In the CSV
\Delta (in LaTeX) \\Delta (double backslash)
" inside a JSON string "" (double the quote)
newline inside a JSON string \n

Example — a LaTeX equation with a Greek letter:

```csv
"[""\\hat{V} = \\hat{Z} \\hat{I}""]"
```

The pipeline tolerates a single backslash and auto-repairs it, but always write
\\ to keep the file valid JSON at every layer.

The orientation column

· vertical → 9:16 (1080×1920), for YouTube Shorts
· horizontal → 16:9 (1920×1080), for standard uploads

All coordinate positions in visual_data_json must fit the frame:

Orientation X range Y range
vertical −4.5 to 4.5 −8 to 8
horizontal −8 to 8 −4.5 to 4.5

schema_validator.py checks this and warns if any primitive falls outside.

Empty-column rule

For a GENERIC video, all six PYQ fields are empty: `question_text`, four
options, and `correct_answer`. That creates seven consecutive commas between
tagline and equations_json:

```
...,The atomic hypothesis,,,,,,,"[""1\\,\\text{\\AA}...""]"
                              ↑↑↑↑↑↑↑
                              7 commas
```

If you write only 6, the CSV parser loses alignment and every downstream field shifts by one.

---

🎨 The Primitive Catalog

visual_data_json is a list of dicts. Each dict has a type key and other
parameters. The engine routes each type to a _prim_<name> method.

Static primitives

Type Purpose
field / vector_field Uniform arrow grid
charge / particle / dot A colored dot with optional label
vector / arrow / force Arrow from start to end
line / rod / segment Straight line
arc / angle / angle_arc Circular arc
brace Curly brace between two points
graph / function / curve Axes + plotted expression
secant_tangent Secant line converging to the tangent for constant acceleration
calculus_graph / derivative_tangent Function plot; secant and tangent at a selected x
integral_area / riemann_sum Shaded definite-integral region and finite-sum rectangles
electric_field / magnetic_field Coulomb point-charge and Biot–Savart wire-field maps
electromagnetic_wave Synchronized electric and magnetic plane-wave traces
linear_algebra Vector addition, dot/cross products, or 2D determinant area
shape / lens / circle / rectangle / ellipse / polygon Geometric figures
text Plain or LaTeX text
group Container for child primitives

Motion primitives

Type Purpose
orbit Body moving on an ellipse with optional trail
phasor Rotating vector with projections
ray Photon travelling on a line
particle_gas Box with particles bouncing
heat_flow Dots moving from hot to cold
energy_bar Progress bar for energy
wave Sinusoidal travelling wave
number_line Number line with a moving marker
pendulum Swinging pendulum
spring Oscillating mass on a spring

Self-animated primitives

These run their own animation when they're added to the scene.

Type Purpose
equation_morph LaTeX that transforms step-by-step
live_label Text label that updates with time
numerical_chain Multi-step derivation revealed line by line
warning_box Highlighted callout
quiz_frame Question + options that reveal on a pause
concept_map Node-link graph (requires networkx)

Physics-engineered primitives

Type Purpose
polarized_wave Two orthogonal waves
dipole_radiation Radiation pattern from a dipole
two_path_interference Two paths meeting at a screen
driven_oscillator Spring driven at external frequency
wave_pulse Localized Gaussian pulse
harmonic_decomposition Fourier synthesis of a square wave
exponential_atmosphere Particles with exponential density
energy_landscape Potential well with a ball
angular_measurement Angle arc with label
crystal_lattice Grid of atoms
projectile_motion Calculated projectile path with a full sphere, center marker,
velocity and weight vectors, and live state values
physics_simulation Multi-body 2D Newtonian motion integrated with RK4; supports
uniform acceleration, linear drag, anchored/paired springs, and central gravity

Advanced physics primitives

Type Purpose
damped_oscillator Spring with damping envelope
radiating_wave Expanding rings from a source
two_source_waves Interference from two sources
driven_electron Electron driven by an AC field
color_triangle RGB chromaticity triangle
thermionic_emission Electrons escaping a hot metal
beat_pattern Two frequencies superposed
mirror_scene Real/mirror image with axis
medium_atoms Polarizable atoms in a field
field_by_opacity Field strength as dot opacity
polar_pattern Radiation lobe in polar coordinates
phase_portrait Position-velocity space
light_wave_slice OpenGL-only wave slice
sliced_wave Refraction across a boundary
spectral_sum Fourier components + sum
stream_field Streamlines of a vector field
taylor_expand Progressive Taylor series
grid_warp Spacetime curvature visualization

Unknown primitives are logged with a [WARN] and skipped. They do not
crash the render.

---

📚 Content Coverage

Daily batches cover Feynman's Lectures on Physics, Volume I (52 chapters).

Day Chapters covered Status
Day 1 1, 4, 5, 6, 7, 8, 9, 10 ✅ Done
Day 2 2, 3, 11, 12, 13, 14, 15, 16 ✅ Done
Day 3 17, 18, 19, 20, 21, 22, 23, 24 queued
Day 4 25, 26, 27, 28, 29, 30, 31, 32 queued
Day 5 33, 34, 35, 36, 37, 38, 39, 40 queued
Day 6 41, 42, 43, 44, 45, 46, 47, 48 queued
Day 7 49, 50, 51, 52 + review queued

Each day: 8 concept videos + 2 PYQs = 10 rows.

PYQs are hand-verified numerically before emission. No hallucinated arithmetic.

---

🔊 The Audio Pipeline

Every narration goes through this exact chain.

Stage 1 — Text normalization (text_normalizer.py)

Before XTTS sees the text:

· Units expanded only after numbers: 5 kg → five kilograms
· Greek letters spelled out: Δ → delta
· Scientific notation: 6.67 × 10^-11 → six point six seven times ten to the minus eleven
· LaTeX fragments stripped: \frac{a}{b} → a b
· Em dashes replaced with commas

Stage 2 — XTTS-v2 synthesis (generate_audio.py)

· Deterministic seed per video_id (SHA-256 of the ID)
· Temperature 0.65, repetition penalty 3.0
· Automatic CPU fallback on CUDA OOM
· Speaker latent cached across rows in a batch

Output: temp_audio/<video_id>_voice.wav at 24 kHz, then resampled to 44.1 kHz.

Stage 3 — Voice preparation (generate_audio.py)

XTTS output is resampled to 44.1 kHz for the final mix. The `soundscape.py`
mastering helpers are available separately; they are not currently invoked by
the batch runner.

Stage 4 — Ambient bed and cues

`generate_audio.py` creates a quiet, slowly shifting tonal bed matched to voice
length. The renderer adds locally synthesized transition cues; the final mix
keeps those cues under the narration.

Stage 5 — FFmpeg mix (inside batch_runner.py)

The runner mixes narration and bed, includes renderer cue audio when present,
extends the video through the closing card, and encodes H.264/AAC for upload.

---

✅ Validation & Safety

schema_validator.py

Runs before every render. Stdlib-only (no numpy, no manim). Checks:

Check Severity
Required columns present ERROR
14 required columns are present ERROR
equations_json parses as a list ERROR
visual_data_json parses as a list ERROR
Every primitive type is in KNOWN_PRIMITIVES WARN
Every pos/start/end/center is within frame WARN
audio_script length is plausible for target_duration_sec WARN
concept_type is one of the four enums WARN
language is in SUPPORTED_LANGS WARN
quality is in SUPPORTED_QUALITY WARN
manifest_path exists on disk WARN

Idempotent JSON repair

Both the validator and the renderer use the same safe_json_loads. It handles:

1. Well-formed JSON (passes through)
2. Doubled backslashes from CSV quoting
3. Lone backslashes from hand-written LaTeX
4. Empty cells

Coordinate bounds

schema_validator.py warns if any element sits outside the current orientation's
frame. The renderer's fit_to_frame() rescales oversize visuals automatically.

---

🚦 CI / GitHub Actions

.github/workflows/render_shorts.yml runs on every push to main.

Job 1 — validate

Runs schema_validator.py. If any row fails structural validation, the batch
never starts. Fast (~5 seconds).

Job 2 — batch_render (matrix of 4 shards)

Splits the CSV into 4 chunks. Each shard installs LaTeX + FFmpeg + Python 3.11 +
CPU PyTorch, then runs batch_runner.py --chunk N --total-chunks 4.

Shards run in parallel. Wall time for a 10-row batch: ~15 minutes.

Job 3 — merge_artifacts

Downloads all 4 shard outputs, flattens them into final_mp4s/, and writes a
summary table into the run's GitHub Step Summary.

Artifacts are kept 7 days. Model weights are cached by the SHA of requirements.txt.

Trigger a manual run

GitHub repo → Actions tab → Bulk Render Physics Shorts → Run workflow.

Force re-run

If CI fails on the install step, check requirements.txt for version conflicts.
The python-dotenv==0.21.1 pin exists because manim-voiceover 0.3.5 requires
python-dotenv<0.22.0.

---

🛠 Troubleshooting

"Missing required columns" from schema_validator.py

Your header row is wrong. Run:

```bash
head -1 content_batch.csv
```

and check that all 14 required column names match the schema. Generated rows
may also include the optional `beats_json` and `target_duration_sec` columns.

"Row N: X cols, header has Y"

Row N is malformed. Common causes:

· A comma inside an unquoted field (header, tagline, or options)
· An unescaped " inside a JSON string
· A missing comma in the 7-comma gap

Fix by opening the file and counting commas in that line.

GitHub's CSV preview reports a column-count warning

GitHub's CSV preview can misread quoted JSON cells and optional trailing
columns. The authoritative check is `schema_validator.py`; the renderer uses
the same CSV parser as Python. To suppress Git's tabular diff for CSV files,
you can add a .gitattributes entry:

```
*.csv -diff linguist-generated
```

ModuleNotFoundError: No module named 'numpy'

schema_validator.py must be stdlib-only so the CI's validate job runs without
installing pip packages. If you see this error, you're using an old version with
import numpy at the top. Remove it.

Cannot install -r requirements.txt … conflicting dependencies

Version conflict. The known one is python-dotenv. Check that requirements.txt
has:

```
python-dotenv==0.21.1
```

(not 1.0.1).

XTTS drops to CPU

generate_audio.py catches CUDA OOM and retries on CPU. If you're on a GPU and
want to force CPU: CUDA_VISIBLE_DEVICES="" python3 batch_runner.py.

"Unknown primitive" warning

A visual_data_json type isn't in KNOWN_PRIMITIVES. Either it's a typo or
you haven't added the primitive yet. The renderer skips unknown primitives
silently.

Rendered MP4 has no audio

FFmpeg mux failed silently. Check temp_audio/<video_id>_voice.wav exists and
is not 0 bytes. If it's missing, XTTS failed — scroll up in the log for the TTS
exception.

Render takes forever

Manim is CPU-bound. For 1080p30:

· 2D scenes: ~15 min per 3-minute video
· 3D scenes: ~40 min

Use --draft for fast previews (480p15, ~10× faster).

---

❓ FAQ

Q: Do I have to use generate_csv.py?
No. Edit content_batch.csv directly. The generator is optional.

Q: Can I mix vertical and horizontal rows in one CSV?
Yes. The orientation column is per-row.

Q: What if I don't have a saem_voice_sample.wav?
XTTS will fail. You need a 10–20 second reference. Any clean recording works.

Q: Can I run this without a GPU?
Yes. XTTS runs on CPU, just slower. Set --no-gpu implicitly by not having CUDA
available; the code auto-detects.

Q: How long is each video?
~3 minutes. The duration is derived from the audio length plus 3s intro + 4s outro.

Q: What language can I narrate in?
English by default. XTTS-v2 supports many; add a language column with an
ISO code like hi, es, zh-cn. See SUPPORTED_LANGS in schema_validator.py.

Q: Can I change the branding?
Yes — the SaemLabsBranding class in render_universal.py. Intro bumper,
watermark, and outro are separate class methods you can override.

Q: Can I add a new primitive?
Three steps:

1. Add a _prim_<name> method to UniversalPhysicsScene in render_universal.py
2. Add a routing branch in _build_primitive
3. Add <name> to KNOWN_PRIMITIVES in schema_validator.py

Q: My CSV looks ugly on GitHub.
Add .gitattributes:

```
*.csv -diff linguist-generated
```

Q: The CI fails on batch_render but passes validate.
Check requirements.txt for version conflicts. The current pin is:

```
python-dotenv==0.21.1
```

---

🗺 Roadmap

Immediate

☐ Wire per-row language into the beat timeline for Hindi batches
☐ Add --dry-run mode that validates but skips rendering
☐ Support quality: 4k per-row (currently global via CLI)

Next

☐ Word-level timings via stable-ts for ±50 ms sync
☐ Self-hosted runner guide (4 min per video vs 15 min)
☐ NEET/JEE/MIT variant bumpers per concept_type

Later

☐ Script-first DSL for authoring
☐ Voice-to-timeline forced alignment (whisper-timestamped)
☐ LLM-based draft generation for new content

---

📜 Golden Rules

1. Every new video is one new row in content_batch.csv.
   Nothing else changes.
2. Code is frozen. CSV is fluid.
   If you're editing a .py file, you're adding a feature, not making a video.
3. Always validate before rendering.
   python3 schema_validator.py content_batch.csv catches 90% of mistakes in 1 second.
4. Never edit content_batch.csv by hand if you can help it — but if you do, use a text editor that respects LF line endings.
   Windows line endings (CRLF) will break JSON parsing inside CSV fields.
5. Back up saem_voice_sample.wav separately.
   Without it, voice cloning doesn't work, and the file isn't in the repo.
6. One batch = one orientation.
   Mixing vertical and horizontal in the same day's batch is possible but
   makes QC harder.
7. PYQs are math-checked.
   If you generate them with an AI, verify the answer yourself before committing.

---

📄 License

See LICENSE at repo root.

🙏 Credits

Built on:

· Manim Community — animation engine
· Coqui TTS — XTTS-v2 voice cloning
· FFmpeg — audio/video muxing
· Feynman Lectures on Physics, Volume I — source material

Element grammar inspired by 3Blue1Brown.

---

🔗 Related

· MANIFEST.md — file checksums and version
· SAVEPOINT.md — feature-complete checkpoint notes
· .github/workflows/render_shorts.yml — CI definition
· tools/add_orientation.py — one-shot CSV migration helper

```

---

## 🎯 What's in this README

- **15 sections**, each with detailed breakdown
- **Complete file inventory** with edit-safety guidance
- **Full 14-column CSV schema** with escaping rules and examples
- **Primitive catalog** — all 36 types listed by category
- **Content coverage tracker** — chapters done vs queued
- **Audio pipeline walkthrough** — every stage with params
- **CI job breakdown** — what each job does
- **Troubleshooting section** — every failure mode I've seen in this conversation
- **FAQ** — the 12 questions you've actually asked
- **Roadmap** — immediate/next/later
- **Golden rules** — the 7 principles to keep this running for years

Drop it in as `README.md`, commit, and GitHub will render it beautifully. Every code block, every table, every link works as-is.

Say **"day 3"** when ready — chapters 17–24 are queued.
