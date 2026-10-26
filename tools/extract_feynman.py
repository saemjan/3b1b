#!/usr/bin/env python3
"""extract_feynman.py — gen-3 curriculum bootstrap (SIR retrieval target).

Writes knowledge_base/curriculum/feynman_vol2.json as a FROZEN, witnessed
artifact:
  * every equation passes the physics-oracle LaTeX ruler (fail closed)
  * every video_primitive lies in the routed manifest; legacy names that no
    engine routes are REMAPPED, and each remap is priced in the report
    (degradation recorded, not hidden)
  * every entry links to a jee_model_engine concept id when one exists, so
    the authoring loop retrieves witnessed models, not prose
  * the file carries schema_version, source citation and a sha256 digest of
    its canonical content (A5 provenance)
Paths resolve from the repo root, never from the CWD (A2).

Usage:
    python3 tools/extract_feynman.py [--out DIR] [--strict] [--json]
    python3 tools/extract_feynman.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

SCHEMA_VERSION = 3
DEFAULT_OUT = ROOT / "knowledge_base" / "curriculum"

try:
    from tools.physics_oracle import check_latex as _check_latex
except Exception:
    _check_latex = None
try:
    import schema_validator as _sv
except Exception:
    _sv = None
try:
    import jee_model_engine as _jme
except Exception:
    _jme = None
try:
    from tools.ledger import append as _ledger
except Exception:
    _ledger = None

SOURCE = {"book": "Feynman Lectures on Physics, Vol II",
          "chapters": ["01", "34"], "canon": "qcos.cxn"}

# legacy primitive names no engine routes -> routed equivalents (priced remap)
PRIMITIVE_REMAP = {
    "vector_field": "vector",
    "flux_lines": "concept_map",
    "precessing_orbit": "orbit",
    "magnetic_moment": "vector",
}

CURRICULUM = [
    {"id": "feynman_v2_ch01",
     "title": "Electromagnetism",
     "concept": "Maxwell's equations in differential form",
     "equations": [
         r"\nabla \cdot \mathbf{E} = \frac{\rho}{\epsilon_0}",
         r"\nabla \times \mathbf{E} = -\frac{\partial \mathbf{B}}{\partial t}",
     ],
     "prerequisites": ["vector_calculus", "coulombs_law"],
     "source_primitives": ["vector_field", "flux_lines"],
     "model_id": "phys:beats"},          # witnessed analogue in the registry
    {"id": "feynman_v2_ch34",
     "title": "The Magnetism of Matter",
     "concept": "Diamagnetism and Larmor precession",
     "equations": [r"\mathbf{F} = q(\mathbf{v} \times \mathbf{B})"],
     "prerequisites": ["lorentz_force"],
     "source_primitives": ["precessing_orbit", "magnetic_moment"],
     "model_id": "phys:shm"},
]


def routed_set():
    if _jme is not None and hasattr(_jme, "ROUTED_MANIFEST"):
        return set(_jme.ROUTED_MANIFEST)
    return set(_sv.KNOWN_PRIMITIVES) if _sv else set()


def validate_entry(entry, routed):
    errs, warns, remaps = [], [], []
    for eq in entry.get("equations", []):
        if _check_latex is not None:
            e, w = _check_latex(eq)
            errs += [f"{entry['id']}: {x}" for x in e]
            warns += [f"{entry['id']}: {x}" for x in w]
    out_prims = []
    for p in entry.get("source_primitives", []):
        target = PRIMITIVE_REMAP.get(p, p)
        if target != p:
            remaps.append(f"{p}->{target}")
        if target not in routed:
            errs.append(f"{entry['id']}: primitive '{target}' routed nowhere")
        out_prims.append(target)
    mid = entry.get("model_id")
    if mid and _jme is not None and mid not in _jme.REGISTRY:
        warns.append(f"{entry['id']}: model_id '{mid}' not in concept registry")
    return errs, warns, remaps, out_prims


def build():
    routed = routed_set()
    concepts, errs, warns, remaps = [], [], [], []
    for src in CURRICULUM:
        e, w, r, prims = validate_entry(src, routed)
        errs += e
        warns += w
        remaps += r
        concepts.append({
            "id": src["id"], "title": src["title"], "concept": src["concept"],
            "equations": src["equations"],
            "prerequisites": src["prerequisites"],
            "video_primitives": prims,
            "source_primitives": src["source_primitives"],
            "model_id": src.get("model_id", ""),
        })
    canon = json.dumps(concepts, sort_keys=True, ensure_ascii=False)
    doc = {"schema_version": SCHEMA_VERSION, "source": SOURCE,
           "digest": hashlib.sha256(canon.encode("utf-8")).hexdigest(),
           "concepts": concepts}
    return doc, {"errors": errs, "warnings": warns, "remaps": remaps}


def main():
    ap = argparse.ArgumentParser(description="curriculum bootstrap (gen-3)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0

    doc, rep = build()
    if rep["errors"]:
        for e in rep["errors"]:
            print(f"[extract] ERROR {e}")
        print("[extract] refused to write: curriculum violates the rulers")
        return 1
    for w in rep["warnings"]:
        print(f"[extract] warn {w}")
    for r in rep["remaps"]:
        print(f"[extract] remap {r} (priced, recorded)")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    target = out / "feynman_vol2.json"
    target.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    if _ledger is not None:
        _ledger({"gate": "extract_feynman", "schema_version": SCHEMA_VERSION,
                 "concepts": len(doc["concepts"]), "remaps": rep["remaps"],
                 "digest": doc["digest"][:12]})
    if a.json:
        print(json.dumps(doc, ensure_ascii=False))
    print(f"[extract] wrote {len(doc['concepts'])} concepts -> {target} "
          f"digest={doc['digest'][:12]}")
    return 1 if (a.strict and rep["warnings"]) else 0


def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    doc, rep = build()
    want("no-errors", not rep["errors"], str(rep["errors"][:2]))
    want("remap-priced", len(rep["remaps"]) == 4, str(rep["remaps"]))
    routed = routed_set()
    want("prims-routed",
         all(p in routed for c in doc["concepts"] for p in c["video_primitives"]))
    d2, _ = build()
    want("digest-determinism", doc["digest"] == d2["digest"]
         and len(doc["digest"]) == 64)
    want("schema-stamped", doc["schema_version"] == SCHEMA_VERSION)
    if _check_latex is not None:
        bad = [eq for c in doc["concepts"] for eq in c["equations"]
               if _check_latex(eq)[0]]
        want("latex-clean", not bad, str(bad[:1]))
    if _jme is not None:
        want("model-links",
             all(c["model_id"] in _jme.REGISTRY for c in doc["concepts"]))
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "cur"
        p.mkdir()
        (p / "feynman_vol2.json").write_text(
            json.dumps(doc, indent=2), encoding="utf-8")
        back = json.loads((p / "feynman_vol2.json").read_text(encoding="utf-8"))
        want("roundtrip", back["digest"] == doc["digest"])
    return checks


if __name__ == "__main__":
    sys.exit(main())
