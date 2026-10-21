#!/usr/bin/env python3
"""Interactive Feynman/3b1b scene author → content/specs.json → CSVs → validate. (R10)"""
import json, os, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "content" / "specs.json"

def ask(q, d=""):
    v = input(f"{q} [{d}]: ").strip()
    return v or d

specs = json.loads(SPEC.read_text()) if SPEC.exists() else {"horizontal": [], "vertical": []}
orient = ask("orientation (horizontal/vertical)", "vertical")
script = ask("Feynman-style script (plain language, ≥200 words)")
words = len(script.split())
print(f"  → {words} words ≈ {round(words/2.5)}s speech (R4: duration auto-derived)")
spec = {
    "id": ask("video_id", f"{orient[:2]}_new_{len(specs[orient])+1}"),
    "concept_type": ask("concept_type", "MECHANICS"),
    "header_title": ask("header_title"), "tagline": ask("tagline"),
    "question_text": ask("MCQ question"),
    "option_a": ask("A"), "option_b": ask("B"), "option_c": ask("C"), "option_d": ask("D"),
    "correct_answer": ask("correct (A/B/C/D)", "B"),
    "equations": [e for e in ask("equations LaTeX (comma-separated)", "").split(",") if e.strip()],
    "primitive": ask("primitive (falling_energy / two_path_interference / particle_gas …)"),
    "math_text": ask("math_text"), "caption": ask("caption"),
    "color": ask("hex color", "#4CC9F0"), "script": script,
}
specs[orient].append(spec)
SPEC.write_text(json.dumps(specs, indent=2, ensure_ascii=False))
subprocess.run([sys.executable, "tools/generate_universal_master_csvs.py"], cwd=ROOT, check=True)
rc = subprocess.run([sys.executable, "schema_validator.py", f"content/master_{orient}.csv"],
                    cwd=ROOT, env={**os.environ, "SAEM_ORIENTATION": orient}).returncode
print("\n✅ validated — next: git commit -m 'content: %s [render]'  (or dispatch with only=%s)"
      % (spec['id'], spec['id']) if rc == 0 else "\n❌ validation failed — fix and re-run")
sys.exit(rc)
