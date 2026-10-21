#!/usr/bin/env python3
import re, sys, datetime
from pathlib import Path
THINK = Path("THINK.md")
SIGS = [(r"Missing required columns: \[([^\]]+)\]", "R1"),
        (r"unknown concept_type '(\w+)'", "R5"),
        (r"\d+ words \(want \d+-\d+\)", "R4"),
        (r"DeprecationWarning", "R6"),
        (r"Downloading model to", "R7")]
def main(run, gate, *logs):
    txt = "\n".join(Path(p).read_text(errors="ignore") for p in logs if p)
    hits = {r: len(re.findall(p, txt)) for p, r in SIGS}
    hits = {r: n for r, n in hits.items() if n}
    mins = re.findall(r"Done in ([\d.]+) min", txt)
    wall = f"~{sum(float(m) for m in mins):.0f}m" if mins else "–"
    entry = (f"- #{run} {gate} {datetime.date.today():%Y-%m-%d} wall={wall} "
             f"sigs={hits or 'clean'}")
    t = THINK.read_text()
    t = t.replace("## 4. Open hypotheses", entry + "\n\n## 4. Open hypotheses", 1)
    THINK.write_text(t); print(entry)
if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], *sys.argv[3:])
