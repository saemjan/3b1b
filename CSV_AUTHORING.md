# CSV Authoring for the Video Engine

This pipeline turns one CSV row into one rendered video. Keep the row factual and focused: one question, one governing idea, one visual explanation, and one conclusion.

## Existing 10 + 10 Series

The generated batch at [examples/feynman_20_video_batch.csv](examples/feynman_20_video_batch.csv) contains ten vertical lectures and ten matching horizontal short problems. Regenerate it with `python3 tools/generate_feynman_series.py`.

| Vertical concept | Horizontal problem | Main visual capability |
|---|---|---|
| Atoms explain ordinary matter | How do molecular motion and collisions explain material behavior? | `particle_gas` |
| Energy changes form in a fall | How much potential energy changes for a 2 kg object falling 5 m? | `falling_energy` |
| Periodic motion measures time | How does pendulum length set its period and frequency? | `pendulum` |
| Random steps produce a predictable spread | What is the typical displacement after $N$ unbiased steps? | `random_walk` |
| Instantaneous speed is a derivative | What is the speed at $t=2.4$ s for constant acceleration? | `secant_tangent` |
| Gravity guides an orbit | Why does a satellite keep falling without reaching Earth? | `orbit` |
| Net force changes velocity | How do horizontal motion and gravity combine in a projectile path? | `projectile_motion` |
| Momentum is exchanged in collisions | What happens to two carts' velocities during an isolated collision? | `momentum_exchange` |
| A wave carries a pattern | How are wave speed, frequency, and wavelength related? | `wave` |
| Superposition creates interference | Which path differences produce constructive or destructive interference? | `two_source_waves` |

The vertical rows introduce a concept; each horizontal row turns its paired idea into a short problem. Across the 20 rows, the batch also exercises equations, focusable story beats, titles/captions, orientation-specific framing, narration, and locally generated audio cues.

## Schema

There are 14 required columns. Current generator output appends two optional columns, making 16 columns total, in this order:

```text
video_id,concept_type,header_title,tagline,question_text,option_a,option_b,option_c,option_d,correct_answer,equations_json,visual_data_json,audio_script,orientation,beats_json,target_duration_sec
```

| Column | How to author it |
|---|---|
| `video_id` | Unique, filesystem-safe ID; use a short lowercase slug. |
| `concept_type` | Usually `GENERIC`; use `PYQ` only with a real question, at least two options, and a verified answer. |
| `header_title` | Short, specific claim or question; avoid long sentences. |
| `tagline` | One concise supporting idea. |
| `question_text` | The actual problem for `PYQ`; for a concept row, it can still hold the question shown on screen. |
| `option_a`–`option_d` | Leave empty unless the row is an actual multiple-choice question. |
| `correct_answer` | Leave empty unless the answer is known and checked. Never invent a result. |
| `equations_json` | JSON list of LaTeX strings. Escape backslashes for JSON, then quote the whole cell for CSV. |
| `visual_data_json` | JSON list of primitive objects. One row may combine several engine types. |
| `audio_script` | Spoken explanation. The script's actual audio length controls render timing. |
| `orientation` | `vertical` for 9:16 lecture or `horizontal` for 16:9 short. Set it on every row. |
| `beats_json` | Optional JSON list of supported beat objects. Each `focus` must match a visual object's `id`. |
| `target_duration_sec` | Optional pacing hint for validation: use `60` for shorts and `180` for lectures. It does not force render duration. |

The validator's approximate narration windows are 112–180 words for a 60-second row and 337–540 words for a 180-second row. Natural pauses, TTS speed, language, and pronunciation affect final duration, so render a draft and listen before publishing.

## Combining Engines

`visual_data_json` is an array, not a single drawing. Combine independently supported primitives in one row when each advances the same explanation. This example puts a geometric path, a calculus curve, and a vector construction in one horizontal problem:

```json
[
  {
    "type": "geometry",
    "id": "path",
    "dimension": 2,
    "kind": "polyline",
    "points": [[-6, -1], [-4, 2], [-2, 2]],
    "color": "#4CC9F0"
  },
  {
    "type": "calculus_graph",
    "id": "height_curve",
    "expression": "x^2/2+0.5",
    "x_range": [-2, 2],
    "y_range": [-1, 3],
    "x_length": 4,
    "y_length": 2.5,
    "center": [0, 0, 0]
  },
  {
    "type": "linear_algebra",
    "id": "velocity_vectors",
    "operation": "vectors",
    "a": [2, 1],
    "b": [-1, 2],
    "center": [4.5, -0.1, 0],
    "scale": 0.35
  }
]
```

The renderer also routes `electric_field`, `magnetic_field`, and `electromagnetic_wave`; `physics_simulation`; `geometry`; `calculus_graph`, `derivative_tangent`, `integral_area`, and `riemann_sum`; and `linear_algebra`. Core motion primitives include `falling_energy`, `projectile_motion`, `momentum_exchange`, `pendulum`, `wave`, and `two_source_waves`. Check the renderer router and the primitive-specific tests before using a new type.

For story beats, give every focused visual a stable ID, then reference that ID in `beats_json`:

```json
[
  {"type": "hook", "focus": "path"},
  {"type": "law", "focus": "height_curve", "transition": "wipe"},
  {"type": "punchline", "focus": "velocity_vectors"}
]
```

Use only the supported beat types documented by `schema_validator.py`. Keep the screen uncluttered: two or three related visual primitives are usually clearer than stacking every available engine into one frame. Check both orientations for clipping; vertical bounds are approximately $x\in[-4.5,4.5]$, $y\in[-8,8]$, while horizontal bounds are approximately $x\in[-8,8]$, $y\in[-4.5,4.5]$.

## Write and Validate

Prefer Python's CSV and JSON serializers over building CSV lines by hand. They handle commas, quotes, backslashes, and nested data correctly:

```python
import csv
import json

row = {
    "video_id": "projectile_velocity_short",
    "concept_type": "GENERIC",
    "header_title": "Why the Path Curves",
    "tagline": "One launch, two independent motions",
    "question_text": "How far does a ball travel before it lands?",
    "option_a": "", "option_b": "", "option_c": "", "option_d": "",
    "correct_answer": "",
    "equations_json": json.dumps([r"x=v_0t", r"y=y_0+v_{0y}t-\frac12gt^2"]),
    "visual_data_json": json.dumps([
        {"type": "projectile_motion", "id": "path", "v0": 8,
         "angle": 35, "g": 9.8, "color": "#4CC9F0"},
        {"type": "vector", "id": "launch_velocity",
         "start": [-2, -1, 0], "end": [-0.5, 0, 0],
         "color": "#F1C40F"},
    ]),
    "audio_script": "Write and review narration appropriate to the target duration.",
    "orientation": "horizontal",
    "beats_json": json.dumps([
        {"type": "hook", "focus": "path"},
        {"type": "emphasis", "focus": "launch_velocity"},
    ]),
    "target_duration_sec": 60,
}

columns = list(row)
with open("my_batch.csv", "w", newline="", encoding="utf-8") as output:
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerow(row)
```

Then validate, inspect the planned rows, and render a draft:

```bash
python3 schema_validator.py my_batch.csv
python3 batch_runner.py --csv my_batch.csv --dry-run --format both
python3 batch_runner.py --csv my_batch.csv --only projectile_velocity_short --draft
```

`--format short` selects horizontal rows; `--format lecture` selects vertical rows; `--format both` includes every row and preserves its per-row orientation. The GitHub workflow offers the checked-in Feynman batch and production CSV as inputs, and can generate a concept/problem bundle from dispatch inputs.

The GitHub runner does not contain a private voice reference by default. If
`saem_voice_sample.wav` is absent, Actions uses duration-matched silent audio so
the visual render can still complete. Add the private sample through an
appropriately secured workflow setup when narrated output is required.

A valid CSV is not proof that the physics is correct. State assumptions, check units and calculations, inspect a draft in the target orientation, and review the synthesized narration before upload.
