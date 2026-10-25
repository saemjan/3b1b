#!/usr/bin/env python3
"""CI gate: a batch that repeats a look fails, exactly like a physics drift fails."""
import csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import style_genome as sg

WINDOW, MIN_DIST = 12, sg.MIN_NOVELTY

def recent_from_ledger(path: Path):
    gens = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try: rec = json.loads(line)
            except Exception: continue
            if rec.get("genome"):
                gens.append(sg.Genome(**rec["genome"]))
    return gens[-WINDOW:]

def main():
    ledger = Path(sys.argv[1] if len(sys.argv) > 1 else "logs/style_ledger.jsonl")
    batch  = Path(sys.argv[2] if len(sys.argv) > 2 else "content_batch.csv")
    recent = recent_from_ledger(ledger)
    made = []
    for row in csv.DictReader(batch.open(encoding="utf-8")):
        g, _ = sg.fresh_genome(row.get("video_id", "?"),
                               row.get("concept_type", "GENERIC"), "batch",
                               recent + made)
        made.append(g)
    bad = [(i, j, round(sg.distance(made[i], made[j]), 3))
           for i in range(len(made)) for j in range(i + 1, len(made))
           if sg.distance(made[i], made[j]) < MIN_DIST]
    if bad:
        print(f"[style-gate] FAIL repeated looks: {bad}")
        return 1
    print(f"[style-gate] ok: {len(made)} genomes, all >= {MIN_DIST} apart "
          f"and >= {MIN_DIST} from last {len(recent)} lessons")
    return 0

if __name__ == "__main__":
    sys.exit(main())
