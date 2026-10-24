#!/usr/bin/env python3
"""
Concrete first step from FUTURE_ARCHITECTURE.md:
Bootstrap knowledge_base/curriculum/feynman_vol2.json.
This gives the LLM authoring loop a trustworthy, schema-compliant
retrieval target before it writes a single script.
"""
import json
import os

def main():
    out_dir = "knowledge_base/curriculum"
    os.makedirs(out_dir, exist_ok=True)
    
    # Seeded directly from Feynman Vol 2 (Electromagnetism & Matter)
    curriculum = [
        {
            "id": "feynman_v2_ch01",
            "title": "Electromagnetism",
            "concept": "Maxwell's Equations in differential form",
            "equations": [
                "\\nabla \\cdot \\mathbf{E} = \\frac{\\rho}{\\epsilon_0}",
                "\\nabla \\times \\mathbf{E} = -\\frac{\\partial \\mathbf{B}}{\\partial t}"
            ],
            "prerequisites": ["vector_calculus", "coulombs_law"],
            "video_primitives": ["vector_field", "flux_lines"]
        },
        {
            "id": "feynman_v2_ch34",
            "title": "The Magnetism of Matter",
            "concept": "Diamagnetism and Larmor precession",
            "equations": ["\\mathbf{F} = q(\\mathbf{v} \\times \\mathbf{B})"],
            "prerequisites": ["lorentz_force"],
            "video_primitives": ["precessing_orbit", "magnetic_moment"]
        }
    ]
    
    out_path = os.path.join(out_dir, "feynman_vol2.json")
    with open(out_path, "w") as f:
        json.dump(curriculum, f, indent=2)
    print(f"Wrote {len(curriculum)} concepts to {out_path}")

if __name__ == "__main__":
    main()
