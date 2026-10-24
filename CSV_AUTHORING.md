# CSV Authoring Guide

**Generators first.** Hand-editing is the last resort. Preferred order:
`tools/author.py` (interactive) → `make_batch.py`-style Python writers
(`csv.DictWriter` + `json.dumps`) → `tools/generate_topic_bundle.py` →
direct edit only for one-off experiments.

## Schema (14 required + 2 optional)
video_id, concept_type (GENERIC|PYQ|3D|3D_HELIX), header_title, tagline,
question_text, option_a..d, correct_answer, equations_json,
visual_data_json, audio_script, orientation (vertical|horizontal),
[beats_json], [target_duration_sec]

GENERIC rows: the six PYQ cells stay empty → seven consecutive commas.
Escaping: write JSON with `json.dumps`; LaTeX backslashes doubled (`\\Delta`).
`safe_json_loads` repairs lone backslashes, but never rely on repair.

## Orientation vs --format (the truth, per code)
- `--format short` keeps **vertical** rows (9:16)
- `--format lecture` keeps **horizontal** rows (16:9)
- `--format both` (default) keeps everything
- empty orientation counts as vertical
Filenames like `*_short.csv` are conventions only; trust the cell.

## Length bands
target 60 s → 112–180 words; 180 s → 337–540 words (≈ round(words/2.5) s).
`target_duration_sec` retunes the band; it does not lock output length
(audio duration + cards does).

## Beats skeleton (60–180 s)
hook → promise → law → experiment → emphasis → midpoint → punchline → cta
`focus` must equal a visual `id`. Easing: soft|land|launch|snap|linear.
Transitions: wipe|push|iris|zoom_blur (renderer v3; v2 holds).

## Narration trust (oracle v2)
Impossible claims (fourth law of motion, sound in vacuum, gravity strongest)
are hard errors. "studies show", bare DOIs, and absolute proof claims are
warnings: name the source or cut the line before publish.

## Validate before anything else
python3 schema_validator.py <csv> --require-oracle
python3 batch_runner.py --csv <csv> --dry-run
