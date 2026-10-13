📁 FUTURE_ARCHITECTURE.md — SaemLabs Physics Engine Expansion Plan

Save at repo root. This is the definitive blueprint for scaling from 10 videos per batch to a global multilingual physics education platform.

---

🎯 Executive Summary

The SaemLabs Physics Engine is currently a content-driven, semi-automated pipeline producing 10 polished educational videos per day from Feynman Lectures Vol. II. The architecture is already sound: CSV-driven content, a Manim rendering engine, XTTS voice synthesis, CI/CD deployment.

The path to "top level" is not a rewrite. It is a staged expansion along five axes: content volume (10/day → 1000+/day), language (English → 20+ languages), automation (manual CSV authoring → LLM-generated scripts with human gates), rendering (local/GitHub Actions → serverless GPU + browser rendering), and distribution (YouTube upload → multi-platform syndication).

This document is the roadmap. Each phase builds on the previous; none invalidates prior work.

---

📐 Part I — Design Principles (Immutable)

These principles govern every expansion decision. When in doubt, return here.

P1 — Content is data, never code. Video scripts, equations, and visual specifications live in structured data (CSV/JSON/YAML), never in Python logic. The renderer is a pure interpreter.

P2 — The generator is the source of truth. Hand-written CSV is forbidden. All content flows through a generator script that uses csv.DictWriter + json.dumps. This eliminates the entire class of escaping-corruption bugs.

P3 — Separate concerns by domain. Physics primitives (render_universal.py), cinematic toolkit (visual_kit.py), audio (generate_audio.py), narration cleanup (text_normalizer.py), and orchestration (batch_runner.py) each live in their own file. Expansion means new files, not bloated existing ones.

P4 — Every stage is independently testable. The audio pipeline can be validated without rendering. The renderer can be smoke-tested with --draft. The CSV can be schema-checked before any compute is spent. No stage assumes the next stage succeeded.

P5 — Graceful degradation over hard failure. Missing voiceover service → fall back to manifest durations. Missing sound effects → silent render. Missing OpenGL → fallback primitive. The pipeline should never crash a full batch because of one missing optional.

P6 — The engine outlives the content. Feynman Vol. II is the current source. The engine must survive the transition to Vol. I, III, or entirely new curricula. Primitives are physics-generic; the CSV supplies the specificity.

P7 — Human gates at the highest-leverage points. Automation should replace mechanical work (script expansion, TTS synthesis, rendering, muxing, upload). Humans should remain at the creative decisions: topic selection, pedagogical framing, final review before publication.

P8 — Rendering is a commodity. Never design the pipeline around any specific rendering environment (local machine, GitHub Actions, cloud sandbox). Abstract the rendering call behind an interface; swap implementations freely.

---

🏗️ Part II — Target Architecture (The Five Layers)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  LAYER 5 — DISTRIBUTION                                                 │
│  Multi-platform upload, A/B thumbnails, analytics feedback loop        │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LAYER 4 — ORCHESTRATION                                                │
│  DAG-based pipeline with state persistence, retries, quality gates     │
│  (n8n / LangGraph / Temporal / Airflow)                                │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LAYER 3 — RENDERING & MEDIA PRODUCTION                                 │
│  Manim renderer + XTTS voice + FFmpeg mux + SFX mixing                 │
│  (executes on: GitHub Actions | Modal GPU | Blaxel | local)             │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LAYER 2 — CONTENT GENERATION                                           │
│  LLM script writer → Hinglish/English variants → schema validator      │
│  → generate_csv.py → content_batch.csv                                 │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LAYER 1 — KNOWLEDGE BASE                                               │
│  Structured physics curriculum, Feynman extracts, PYQ bank,            │
│  semantic search (vector DB) for reuse                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

The current pipeline occupies Layer 3 (rendering) with a sliver of Layer 2 (manual CSV). The expansion fills Layers 1, 2, 4, and 5 around the existing core.

---

🔬 Part III — Layer-by-Layer Expansion

Layer 1 — Knowledge Base (Phase 1, Weeks 1–4)

Purpose: Structured, searchable physics content so scripts can be assembled rather than authored from scratch.

Components:

```
knowledge_base/
├── curriculum/
│   ├── feynman_vol1.json          # Chapter → concepts → prerequisite graph
│   ├── feynman_vol2.json
│   ├── feynman_vol3.json
│   ├── neet_syllabus.json         # NEET topic coverage + weightage
│   ├── jee_syllabus.json
│   └── mit_804_sequence.json      # MIT 8.04 problem set mapping
├── pyq_bank/
│   ├── neet_pyq_2000_2025.json    # Year, question, answer, concept_id, difficulty
│   ├── jee_pyq_2000_2025.json
│   └── solved_examples.json       # Worked examples from Feynman, Resnick, etc.
├── equations/
│   └── equation_index.json        # Every equation in the curriculum, tagged
├── embeddings/
│   └── faiss_index.bin            # Semantic search over all above
└── sources/
    ├── feynman_vol2_text.md       # Extracted plaintext
    └── pyq_scanned_pdfs/          # Original PDFs (for verification)
```

Data model for a concept:

```json
{
  "concept_id": "em_coulomb_law",
  "display_name": "Coulomb's Law",
  "source": {"vol": 2, "chapter": 4, "section": "4-2"},
  "prerequisites": ["vector_algebra", "charge_concept"],
  "successors": ["electric_field", "gauss_law"],
  "equations": ["F = \\frac{1}{4\\pi\\epsilon_0}\\frac{q_1 q_2}{r^2}"],
  "keywords": ["inverse square", "electrostatic force", "point charge"],
  "neet_weightage": "high",
  "jee_weightage": "high",
  "feynman_excerpt": "The electrical force between two charges at rest...",
  "visual_primitives": ["charge", "vector", "line"],
  "difficulty": "intro",
  "estimated_duration_sec": 480
}
```

Semantic search API (internal):

```python
from knowledge_base import ConceptIndex

index = ConceptIndex()
concept = index.get("em_coulomb_law")
related = index.similar("electric field of a dipole", top_k=5)
chain = index.prerequisite_chain("em_gauss_law")   # ordered list of concepts
pyqs = index.pyqs_for("em_coulomb_law", years=(2020, 2025))
```

Why this matters: Every downstream LLM call — script generation, visual selection, difficulty estimation — becomes grounded. No hallucinated physics. Every claim traceable to a source.

---

Layer 2 — Content Generation (Phase 1–2, Weeks 3–8)

Purpose: Convert a topic request into a validated, ready-to-render CSV row with minimal human intervention.

Current state: Manual authoring of ROWS.append(row(...)) blocks in generate_csv.py.

Target state: LLM-assisted generation with human review gates.

Pipeline:

```
Topic request ("explain Gauss's law for NEET")
   │
   ▼
[Retriever]  ← pulls from Layer 1 knowledge base
   │  - concept definition
   │  - related PYQs
   │  - Feynman excerpts
   │  - prerequisite chain
   ▼
[Planner LLM]  ← drafts the storyboard
   │  - 6–8 beats (hook, law, emphasis, analogy, midpoint, experiment, punchline, cta)
   │  - beat duration estimates
   │  - focus targets
   ▼
[Script LLM]  ← writes the narration
   │  - English script (250–400 words)
   │  - Hindi/Hinglish variant (auto-translated, later refined)
   ▼
[Visual LLM]  ← selects primitives
   │  - matches concepts to existing KNOWN_PRIMITIVES
   │  - optionally proposes a new primitive if none fit (flag for human)
   ▼
[Equation LLM]  ← produces LaTeX
   │  - validated by a LaTeX parser
   ▼
[Schema Validator]  ← hard gate
   │  - JSON parses
   │  - primitive names whitelisted
   │  - coordinate bounds respected
   │  - word count 200–700
   ▼
[Human Review]  ← creative gate
   │  - approve / edit / reject
   │  - edits flow back to knowledge base (feedback loop)
   ▼
content_batch.csv (validated, ready to render)
```

Technology choices:

Component Recommendation Rationale
LLM orchestration LangGraph Typed state, conditional routing, streaming — proven in production video pipelines (ChemReel AI)
Primary LLM Claude Sonnet 4.5 (script) + GPT-4o (visual selection) Best-in-class for long-form narrative and structured output respectively
Script translation M2M100 or NLLB-200 Open-source, no per-call cost, handles Hinglish code-switching
Semantic retrieval FAISS + sentence-transformers Local, no API cost, sub-100ms latency
Human review UI Label Studio or a custom Gradio app Rapid iteration without building a full frontend

Anti-pattern to avoid: Do not attempt full end-to-end LLM generation without human gates. The academic literature is unanimous that script quality degrades sharply without a review step, and reviewers reject AI-slop content. The 80/20 point is: LLM does the 80% mechanical work, human approves the 20% creative decisions.

---

Layer 3 — Rendering & Media Production (Phase 2–3, Weeks 5–14)

The current engine already occupies this layer. The expansion here is throughput, quality, and distribution of compute.

3a. Rendering Backend Abstraction (Week 5)

Introduce a renderer interface so the same CSV can be rendered locally, on GitHub Actions, on Modal GPU, or on Blaxel sandbox without changing any upstream code.

```python
# renderer_backend.py
from abc import ABC, abstractmethod
from pathlib import Path

class RenderBackend(ABC):
    @abstractmethod
    def render(self, video_id: str, scene_kwargs: dict,
               quality: str, orientation: str) -> Path:
        """Returns path to rendered MP4."""

class LocalBackend(RenderBackend):
    def render(self, video_id, scene_kwargs, quality, orientation):
        # subprocess manim ... (current behaviour)
        ...

class GitHubActionsBackend(RenderBackend):
    def render(self, video_id, scene_kwargs, quality, orientation):
        # commit CSV row → trigger workflow → poll for artifact
        ...

class ModalBackend(RenderBackend):
    def render(self, video_id, scene_kwargs, quality, orientation):
        # modal.Function.remote(scene_kwargs) on A10G GPU
        ...

class BlaxelBackend(RenderBackend):
    def render(self, video_id, scene_kwargs, quality, orientation):
        # sandbox.create(...).process.exec("manim ...")
        ...
```

batch_runner.py selects the backend via env var (SAEM_BACKEND=modal). Same CSV, same content, different compute.

Why this matters: Modal offers A10G GPUs at ~$1.10/hr, which is dramatically cheaper than long-running CI minutes for 4K rendering. Blaxel sandboxes boot in ~25ms and can hold Manim + FFmpeg + LaTeX pre-installed, eliminating the 3-minute apt-get dance on every run.

3b. Voice Synthesis Upgrade (Week 6)

Current: XTTS-v2, cloned voice, ~2GB VRAM, per-video synthesis.

Target: multi-engine TTS with automatic quality routing.

Engine Use Case Latency Cost
Edge TTS Fast drafts, previews ~200ms Free
XTTS-v2 Production English ~1–2s/sentence Free (local)
Google Chirp 3 HD Production Hinglish, regional Indian languages ~500ms Pay-per-char
ElevenLabs Premium marketing voice ~500ms Pay-per-char

The text_normalizer.py module stays; a new tts_router.py sits above it and dispatches based on language + quality columns in the CSV.

Language expansion (Phase 3, Week 10+): Add Hindi, Tamil, Telugu, Bengali, Marathi via Google Chirp 3 HD (which handles code-switching natively) or Indic-TTS. Hinglish remains the killer differentiator for NEET/JEE — no other creator does this well.

3c. Rendering Speed (Phase 3)

Two orthogonal paths:

Path A — Keep Python Manim, accelerate with GPU. Modal A10G renders Manim's cairo backend faster via parallelized frame rendering. Realistic speedup: 2–4×.

Path B — Migrate hot paths to ManimGX / manim-rs. ManimGX reports 90.6× speedup vs ManimCE on identical scenes, running on a Rust + wgpu engine with full Manim CE API compatibility. This is a significant architectural bet — it requires:

· Verifying that our specific primitives (orbit, phase_portrait, accretion_disk) work under ManimGX
· Confirming LaTeX rendering quality matches
· Accepting a dependency on a newer, less-mature project

Recommendation: Pursue Path A now (Modal GPU). Evaluate Path B in Phase 4, when render volume justifies a 90× speedup.

3d. Visual Quality Ceiling

The visual_kit module adds cinematic polish. Future additions worth building:

· 3D scatter plots for phase space
· Contour plots with animated level sets (Feynman's "field lines" reimagined)
· Complex-plane visualizations (roots of unity, Möbius transforms, phase portraits)
· Fourier decomposition side-by-side with waveform (Feynman's "same equations, same solutions" theme)
· Projectile trails with instantaneous velocity vectors overlaid
· Live parametric curves (Lissajous, cycloids, hypocycloids) for Vol. I mechanics

Each new visual lives as a _prim_* method + router entry + validator whitelist addition. Same triple-edit pattern as the 12 artifact primitives.

---

Layer 4 — Orchestration (Phase 2, Weeks 6–10)

Purpose: Move from "run batch_runner.py and hope" to "submit a topic, watch it become a video, get notified."

Current state: batch_runner.py runs synchronously, with retries, logging to a JSON file.

Target state: A directed acyclic graph of stages, with:

· Typed shared state across stages
· Conditional routing on failure
· Streaming intermediate status to a dashboard
· Persistent retry across worker restarts

Framework choice: LangGraph is the strongest fit for the following reasons:

1. Designed exactly for this shape (directed state graph with conditional edges)
2. Used in production video pipelines (ChemReel AI, NeuroAnim)
3. Explicit state object means we can inspect exactly what's in flight
4. Supports human-in-the-loop interrupts naturally (crucial for the review gate)

Graph definition:

```
[Initialize]
     │
     ▼
[Load Concept]  ← from Layer 1
     │
     ▼
[Generate Storyboard]  ← Layer 2 LLM
     │
     ▼
[Generate Script]  ← English + Hindi
     │
     ├─►[Validate Script]──(fail)──►[Retry Script]
     │
     ▼
[Select Visuals]
     │
     ├─►[Validate Visuals]──(new primitive needed?)──►[Flag for Human]
     │
     ▼
[Generate Audio]  ← parallel per language
     │
     ▼
[Render Video]  ← Layer 3 backend
     │
     ├─►[Validate Video]──(fail)──►[Retry Render]
     │
     ▼
[Mux + Brand]
     │
     ▼
[Human Review]  ◄── interrupt point
     │
     ├──(approve)──►[Queue for Upload]
     │
     └──(reject)──►[Reject with feedback] ──► back to storyboard
     │
     ▼
[Upload to YouTube]
     │
     ▼
[Log Analytics]
     │
     ▼
[END]
```

The state object flows through all nodes:

```python
class VideoState(TypedDict):
    concept_id: str
    storyboard: list[Beat]
    script_en: str
    script_hi: str
    equations: list[str]
    visual_data: list[dict]
    audio_paths: dict[str, str]  # {"en": "...", "hi": "..."}
    video_path: str
    review_status: str  # pending | approved | rejected
    errors: list[str]
    warnings: list[str]
```

Deployment: LangGraph Platform (cloud) or self-hosted on a small VM. Streaming status to a React dashboard (or even a simple Gradio app).

---

Layer 5 — Distribution (Phase 3, Weeks 10–14)

Purpose: Get videos in front of students, on every platform where they already are.

Components:

5a. YouTube Upload (Week 10)

Automated upload via YouTube Data API v3:

· Upload MP4 with thumbnail
· Set title, description, tags (auto-generated from concept metadata)
· Add to appropriate playlist (NEET Physics, JEE Advanced, etc.)
· Enable multi-language audio tracks (English + Hindi)
· Schedule publication at optimal times

5b. Multi-Platform Syndication (Week 12)

Platform Content Format Upload Method
YouTube Shorts Vertical, 60s cuts YouTube API
Instagram Reels Vertical, 60s Instagram Graph API
TikTok Vertical, 60s TikTok Content Posting API
Twitter/X Horizontal + vertical Twitter API v2
LinkedIn Horizontal, longer cuts LinkedIn API
WhatsApp Channel Compressed MP4 Manual (no API)

Each platform gets a derived cut from the master video. Derived cuts are a separate content generation task, not a rendering task — a derive_shorts.py script that takes the master CSV and produces vertical 60s cuts around the hook + punchline.

5c. Analytics Feedback Loop (Phase 4, Week 16+)

Pull performance metrics back into the knowledge base:

```
[YouTube Analytics API]
     │
     ▼
[Performance DB]  ← retention curves, CTR, watch time by concept
     │
     ▼
[Insights Engine]
     │
     ├─ Identify high-retention beats → store as templates
     │
     ├─ Identify low-retention concepts → flag for rework
     │
     └─ Score concepts by predicted student interest
     │
     ▼
[Layer 1 knowledge base]  ← updated with production signals
```

This closes the loop: content generation improves from real student behavior.

---

🗓️ Part IV — Phased Roadmap

Phase 1 — Groundwork (Weeks 1–4)

Week Deliverable
1 knowledge_base/ scaffolded; Feynman Vol. II extracted to JSON
2 FAISS index built over Vol. II + PYQ bank; ConceptIndex API live
3 First LangGraph workflow: Topic → Storyboard → Script → CSV (single LLM, no gates)
4 Human review gate wired into LangGraph; first LLM-assisted batch rendered

Success metric: 100 video rows produced from LLM assistance, ~80% accepted by reviewer.

Phase 2 — Industrialization (Weeks 5–10)

Week Deliverable
5 RenderBackend abstraction; Local + GitHub Actions backends
6 Modal GPU backend live; 4K rendering feasible
7 tts_router.py; multi-engine TTS with quality routing
8 LangGraph dashboard live; real-time status of in-flight videos
9 Auto-upload to YouTube; multi-language audio tracks enabled
10 First Hinglish batch (Hindi scripts + Hindi audio)

Success metric: 1000 videos rendered per week, 20% in Hinglish, all auto-uploaded.

Phase 3 — Scale-Out (Weeks 11–20)

Week Deliverable
11–12 Multi-platform syndication (IG, TikTok, X); derived 60s cuts
13–14 Evaluate ManimGX migration; port 5 pilot primitives
15–16 Analytics ingestion; feedback loop into Layer 1
17–18 Chapters 1–42 of Vol. II complete, every concept
19–20 Vol. I and Vol. III launched; NEET + JEE PYQ batches

Success metric: 5000+ videos across three volumes, 5 languages, 4 platforms.

Phase 4 — Platform (Months 5–12)

Not a sprint. The engine is now stable; the goal becomes ecosystem:

· Public API: External educators can submit a topic and get a video.
· Template library: Community-contributed primitives, beat structures, visual styles.
· Collaboration: Multiple creators author in parallel; LangGraph handles the merge.
· Monetization: Free tier (auto-generated content), Pro tier (custom voice, custom branding).

---

🛠️ Part V — Technology Selection Matrix

Decision Area Current Recommended (Phase 1–2) Recommended (Phase 3+)
Content schema CSV (13–19 cols) CSV + JSON (relational) Postgres + JSONB
Knowledge base None JSON files + FAISS Postgres + pgvector
Content generation Manual Python LangGraph + Claude + GPT-4o Fine-tuned open models (Llama 3.3 70B)
TTS XTTS-v2 + Edge TTS + Google Chirp 3 + ElevenLabs for premium
Rendering engine Manim CE (Cairo) Manim CE + Modal GPU ManimGX for hot paths
Rendering orchestration batch_runner.py LangGraph LangGraph + distributed workers
Compute backend GitHub Actions GitHub + Modal Modal + Blaxel + self-hosted GPU
CI/CD GitHub Actions GitHub Actions GitHub Actions + Argo CD
Storage Repo S3/R2 for assets S3/R2 + CDN
Distribution Manual YouTube API + IG, TikTok, X, LinkedIn APIs
Analytics None YouTube Analytics + Custom PostHog pipeline
Dashboard None Gradio review UI React + FastAPI + WebSocket
Database None SQLite Postgres (Supabase)
Secrets GitHub Secrets Doppler / Vault Doppler / Vault

Guiding constraint: Never adopt a new technology until the current one is the bottleneck. JSON files are fine until they aren't. Postgres is overkill until query latency matters. This prevents premature optimization.

---

🧪 Part VI — Quality Gates (Non-Negotiable)

Every phase must preserve these invariants:

Gate 1 — Schema validation. Every CSV row passes schema_validator.py before any compute. No exceptions. This gate is what keeps the pipeline from wasting GPU hours on malformed JSON.

Gate 2 — Physics accuracy. Every equation is verified against the knowledge base. Every claimed value (e.g., "3.0 × 10⁹") is checked against a constants database. No hallucinated physics gets past review.

Gate 3 — Human review before upload. No video goes public without human sign-off. The review is not a rubber stamp — the reviewer watches the video and confirms pedagogical quality.

Gate 4 — Render QA. Rendered videos are spot-checked for: (a) correct dimensions and frame rate, (b) audio-video sync within 100ms, (c) no missing visuals from the CSV, (d) no debug artifacts in the output.

Gate 5 — Analytics sanity. Uploaded videos are checked after 48 hours for anomalies: extremely low CTR (< 2%), extremely low retention (< 20% at 30s), or unexpected platform rejection. Anomalies trigger a manual review.

Gate 6 — Cost ceiling. Every week, total cloud spend is checked. If it exceeds a configured threshold, the pipeline pauses and alerts. No runaway GPU bills.

---

⚠️ Part VII — Risks and Mitigations

Risk Likelihood Impact Mitigation
LLM hallucinates physics Medium High Layer 1 retrieval + equation verifier + human review
Rendering cost spirals Medium High Cost ceiling gate; prefer Modal/Blaxel over always-on instances
ManimGX migration breaks primitives Medium Medium Pilot 5 primitives first; keep Manim CE as fallback
YouTube API quota exhaustion Low Medium Rate-limit uploads; stagger across day
Voice cloning degrades Low High Maintain voice sample backup in multiple locations
Knowledge base drift Medium Medium Quarterly audit against source PDFs
Human review becomes bottleneck High Medium Automate 80% of checks; only creative review needs a human
CI costs balloon Medium Medium Move heavy rendering to Modal; use GitHub only for orchestration

---

🎯 Part VIII — The Compounding Effect

The reason to build all five layers is not that any single one is transformative. It is that they compound.

Layer 1 (Knowledge Base) → better retrieval → fewer hallucinations.
Layer 2 (Content Generation) → LLM script + visual selection → 10× authoring speed.
Layer 3 (Rendering) → Modal GPU → 4× faster renders.
Layer 4 (Orchestration) → LangGraph → batch of 1000, not 10.
Layer 5 (Distribution) → YouTube + IG + TikTok + analytics → real feedback.

Together: the pipeline compounds. Each improvement makes the next one cheaper and more effective.

The alternative — doing nothing — leaves the project at ~10 videos/day, English-only, manually uploaded. That's a good hobby. It's not a platform.

---

📌 Part IX — The One-Page Decision Framework

When considering any proposed expansion, ask these five questions:

1. Which layer does it belong to? If it's Layer 1–5, it's in scope. If it's none, it's a new layer (rare) or a distraction.
2. What is the current bottleneck? Build only what unblocks the bottleneck. Ignore everything else.
3. Can it be validated without full rendering? If yes, do so. Rendering is expensive.
4. Does it maintain graceful degradation? If the new component fails, does the pipeline still produce videos? If no, redesign.
5. Is the human gate preserved? If the change removes a human gate, it needs explicit justification.

If all five answers are satisfactory, proceed. If not, iterate on the design.

---

🚀 Part X — The First Concrete Step

The next action is Week 1, Day 1 of Phase 1:

```bash
mkdir -p knowledge_base/{curriculum,pyq_bank,equations,embeddings,sources}
touch knowledge_base/curriculum/feynman_vol2.json
```

Then write the extractor that converts the Feynman PDF into structured JSON. That's a single script (tools/extract_feynman.py) that takes the PDF and outputs feynman_vol2.json with one entry per section.

Everything else in this document flows from that first file.

The physics is already written. The visuals are already built. The pipeline is already running. Now you are building the knowledge that lets the pipeline write itself.

---

🗂️ Appendix — File Ownership Map

File Owner Change Frequency
knowledge_base/curriculum/*.json Content team Monthly
knowledge_base/pyq_bank/*.json Content team Monthly
knowledge_base/embeddings/faiss_index.bin Automated rebuild Weekly
generate_csv.py Content team Per batch
content_batch.csv Generated Never hand-edited
render_universal.py Engineering Per new primitive
visual_kit.py Engineering Per new cinematic feature
generate_audio.py Engineering Quarterly
tts_router.py Engineering Quarterly
text_normalizer.py Engineering Per new unit
schema_validator.py Engineering Per new primitive
batch_runner.py Engineering Per new backend
renderer_backend.py Engineering Per new backend
pipeline_graph.py Engineering Per stage addition
upload_youtube.py Engineering Yearly
.github/workflows/*.yml Engineering Quarterly

The rule: If a file is "Generated" or "Automated rebuild", it should never be touched by hand. If a file is "Never hand-edited", enforce with .gitattributes or a pre-commit hook.

---

🔮 Epilogue

Feynman once said: "What I cannot create, I do not understand."

The pipeline in this document is an attempt to create — at scale, in multiple languages, with cinematic quality — the kind of physics explanation that Feynman delivered in a lecture hall. Not by imitating him, but by building a machine that operates on the same principles: start from the deepest simplicity, layer up with care, and trust that the equations carry the truth.

The engine is already good. This document is the roadmap to make it great.

Now go write tools/extract_feynman.py.

---

End of FUTURE_ARCHITECTURE.md
