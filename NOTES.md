I have completed a deep analysis of the `saemjan/3b1b` repository. The system is a highly advanced, data-driven educational video pipeline designed to synthesize "3Blue1Brown-style visual elegance" with "Feynman’s narrative voice." It transforms structured CSV data into fully rendered, narrated, and mixed MP4 videos (both 9:16 Shorts and 16:9 standard formats) for complex physics concepts.

Below is the technical breakdown, processing logic, and a roadmap for improvement, which has been saved in `Task.md`.

# Task.md: 3b1b & Feynman Video Pipeline Deep Research

## 1. Executive Summary
The repository is a highly automated, data-driven educational video pipeline. It turns Feynman’s Lectures on Physics (and other physics topics) into daily 3-minute vertical/horizontal videos automatically. It combines the visual grammar of 3Blue1Brown (dark backgrounds, glowing math, smooth easing) with Feynman’s pedagogical style (starting with a tangible observation and proposing a simple "bookkeeping" model).

## 2. Technical Capabilities & Architecture

### Core Tech Stack
- **Animation Engine:** Manim Community Edition (Cairo backend).
- **Voice Synthesis:** Coqui TTS (XTTS-v2) for reference-conditioned voice cloning.
- **Audio Mastering:** Custom `soundscape.py` chain (HPF, Compress, LUFS normalization, ambient tonal beds).
- **Media Muxing:** FFmpeg for combining video, cloned voice, ambient bed, and synthesized sound cues.
- **Orchestration:** Python (`batch_runner.py`), GitHub Actions (for 4-way parallel CI rendering).
- **Generative Tools:** `generate_feynman_series.py`, `generate_topic_bundle.py` (Python scripts that construct schema-compliant CSVs).

### Domain-Specific Physics Engines
The renderer dynamically routes `visual_data_json` to specialized numerical engines:
1.  **Calculus:** Secant/tangent limits, Riemann sums, exact integral areas.
2.  **Electromagnetism:** Coulomb fields, Biot-Savart wires, plane-wave traces.
3.  **Fluid Dynamics:** Venturi flow, Bernoulli pressure, hydrostatics.
4.  **Linear Algebra:** Dot/cross products, 2D transforms, matrix solves.
5.  **Physics Simulation:** RK4 integration for Newtonian mechanics (springs, central gravity, linear drag).
6.  **Rotational Motion:** Moments of inertia, torque-driven angular kinematics.
7.  **Geometry:** 1D/2D/3D dimension-checked builders and rigid transforms.

## 3. Input, Output & Processing Pipeline

### A. Input (The Source of Truth)
The pipeline is entirely driven by `content_batch.csv` (or example CSVs) and an audio reference.
- **`saem_voice_sample.wav`:** 10–20s clean voice recording used by XTTS-v2 to clone the narrator's voice.
- **`content_batch.csv`:** A 14-to-16 column structured file containing:
  - `video_id`, `concept_type`, `header_title`, `tagline`
  - `equations_json` (LaTeX arrays)
  - `visual_data_json` (Array of primitive dictionaries)
  - `audio_script` (Spoken narration)
  - `beats_json` (Optional: timed story beats like hook, promise, law, punchline)
  - `orientation` (`vertical` 9:16 or `horizontal` 16:9)

### B. Processing (The Pipeline)
The orchestration happens in 4 main stages (`batch_runner.py`):
1.  **Validation (`schema_validator.py`):** A standard-library-only pre-flight check. Verifies JSON integrity, primitive names against a whitelist, coordinate bounds, and PYQ structures.
2.  **Audio Synthesis (`generate_audio.py` & `soundscape.py`):** Normalizes text (strips LaTeX, expands units). XTTS-v2 synthesizes the script with a deterministic seed. Applies a mastering chain (DC remove → HPF 80Hz → Compress 3:1 → LPF 12kHz → -14 LUFS). Generates a quiet, shifting ambient tonal bed.
3.  **Visual Rendering (`render_universal.py` & `visual_kit.py`):** Manim parses the JSON and builds the scene. Routes `visual_data_json` to ~50+ `_prim_*` methods (e.g., `_prim_falling_energy`, `_prim_random_walk`). Uses `CameraDirector` and `visual_kit` to apply cinematic transitions, spotlighting, and camera shakes based on `beats_json`.
4.  **Final Muxing (FFmpeg):** Mixes the raw video, mastered voice, ambient bed, and localized transition sound cues. Adds intro bumpers and outro cards. Encodes to H.264/AAC in `output_shorts/<video_id>_final.mp4`.

## 4. Generating "3b1b in Feynman Language"
The repository natively supports this blend of styles through its **Story Beat Engine** and **Declarative Primitives**:

- **The Feynman "Language" (Narrative):** Handled via the `audio_script` and `generate_feynman_series.py`. Scripts are written to mimic Feynman's pedagogical style: starting with a tangible observation, proposing a microscopic/simple bookkeeping model (e.g., "Energy is a bookkeeping law"), and avoiding jargon where possible.
- **The 3b1b "Style" (Visuals):** Handled via `visual_kit.py` and `render_universal.py`. Uses dark backgrounds, glowing math symbols, synchronized reveals, and smooth easing functions (`ease_for`). Employs `morph_tex` for equation transformations, `stagger_reveal` for building concepts, and `focus_on` for camera direction.
- **Connecting Both (Beats):** The `beats_json` column maps narrative beats to visual primitives. A beat like `{"type": "law", "focus": "model"}` triggers an equation card emphasis and a cinematic zoom, directly tying Feynman's "aha!" moments to 3b1b's visual cues.

## 5. How to Improve Results (Roadmap & Enhancements)

### A. Content & LLM Integration (Layer 2)
- **Current State:** CSVs are manually edited or generated via rigid Python templates.
- **Improvement:** Implement a **LangGraph-based LLM pipeline**.
  - **Step 1:** Ground the LLM in a vector database (FAISS) containing `feynman_vol*.json`, NEET/JEE PYQs, and MIT syllabi.
  - **Step 2:** Use an LLM (e.g., Claude Sonnet) to draft storyboards/scripts constrained to the CSV JSON schema.
  - **Step 3:** Enforce a **Human-in-the-Loop review gate** before rendering to prevent hallucinated physics.

### B. Rendering Speed & Quality (Layer 3)
- **Current State:** Local or GitHub Actions CPU rendering takes ~15–40 mins per video.
- **Improvement:**
  - **Abstract the Renderer:** Create a `RenderBackend` interface to dispatch rendering to **Modal (A10G GPUs)** or Blaxel sandboxes, cutting render times drastically.
  - **ManimGX Migration:** Evaluate migrating hot visual paths (like `random_walk`, `particle_gas`) to ManimGX (wgpu/Rust), which boasts up to 90x speedups.
  - **Word-Level Sync:** Integrate `stable-ts` or Whisper forced-alignment for ±50ms audio-to-visual synchronization (word highlighting).

### C. Audio & Localization
- **Current State:** Single XTTS-v2 voice, English only.
- **Improvement:** Implement a `tts_router.py` that selects engines based on the `language` and `quality` columns.
  - Edge TTS for rapid drafts.
  - Google Chirp 3 HD or ElevenLabs for native Hinglish (crucial for NEET/JEE audiences).
  - Wire the currently unused `soundscape.py` mastering chain directly into the active batch runner.

### D. Advanced Physics Primitives
- Expand `visual_data_json` with new domain engines:
  - **Quantum/Electrodynamics:** True Feynman diagrams (probability amplitudes, path integrals), complex-plane wave functions.
  - **Thermodynamics:** PV-diagram trackers, entropy particle distributions.
  - **Relativity:** Grid warp spacetime visualizations, light cones.

### E. Automated Distribution (Layer 5)
- Add a `derive_shorts.py` module that automatically cuts 180s lectures into 60s vertical "hook + punchline" clips.
- Automate multi-platform syndication via YouTube Data API, Instagram Graph API, and TikTok APIs, injecting analytics back into the knowledge base.

## 6. Immediate Action Items
1.  [ ] **Run Validation:** `python3 schema_validator.py examples/feynman_20_video_batch.csv`
2.  [ ] **Test Render:** `python3 batch_runner.py --csv examples/feynman_20_video_batch.csv --only feynman_atomic_hypothesis_short --draft`
3.  [ ] **Knowledge Base Setup:** Initialize `knowledge_base/curriculum/feynman_vol2.json` to begin grounding future LLM generations.
4.  [ ] **Soundscape Integration:** Update `batch_runner.py` to actually call `soundscape.py` for the final audio mix, rather than just raw XTTS output.
5.  [ ] **ManimGX Audit:** Run the current primitive suite against ManimGX to identify the top 5 most CPU-intensive scenes for migration.

***

I have successfully analyzed the repository and saved this comprehensive documentation in `Task.md` within the project structure. Let me know if you would like to drill down into any specific file, such as the `_prim_*` methods in `render_universal.py` or the orchestration logic in `batch_runner.py`.
