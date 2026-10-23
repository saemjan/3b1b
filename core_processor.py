#!/usr/bin/env python3
"""Core Processor: CODEX cognitive algorithm + three engines over the Math Brain oracle.

Engines:
  1 Scientific  — saemcli solve()/soul as ground truth & integrity gate
  2 Learner     — BKT baseline; pluggable slot for H7 quantum candidate (gates Q0-Q4)
  3 Visual      — primitive/beats selection (bridge handles layout)
Commands:
  python core_processor.py soul [--accept]
  python core_processor.py generate --seed N --orientation horizontal|vertical
  python core_processor.py verify --csv content/master_horizontal.csv
  python core_processor.py codex "log line"
"""
import csv, json, subprocess, sys, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SAEMCLI = ROOT / "build" / "saemcli"
SOUL_DB = ROOT / "knowledge_base" / "soul.json"
THINK = ROOT / "THINK.md"

def cli(*args):
    r = subprocess.run([str(SAEMCLI), *args], capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit(f"saemcli failed: {r.stderr}")
    return json.loads(r.stdout)

# ── Engine 1: Scientific oracle + soul gate ────────────────────────────
def soul() -> str: return cli("soul")["soul"]

def soul_gate(accept=False):
    SOUL_DB.parent.mkdir(parents=True, exist_ok=True)
    cur = soul()
    prev = json.loads(SOUL_DB.read_text()).get("soul") if SOUL_DB.exists() else None
    if prev != cur:
        if accept:
            SOUL_DB.write_text(json.dumps({"soul": cur}, indent=2))
            print(f"[soul] updated fingerprint -> {cur[:16]}…")
        else:
            print(f"[soul] DRIFT: engine changed ({prev} -> {cur}). Review, then --accept.")
            return False
    return True

def solve_check(qid: str, params: dict, want):
    got = cli("solve", qid, json.dumps(params))
    return got == want or (isinstance(got,(int,float)) and isinstance(want,(int,float))
                           and abs(got-want) <= 1e-9)

# ── Engine 2: Learner model (BKT baseline, pluggable) ──────────────────
class LearnerModel:
    """Baseline = BKT. Candidate slot reserved for H7 (quantum-probability)."""
    GATES = ["Q0_definition","Q1_reproducibility","Q2_offline_benchmark",
             "Q3_educational_pilot","Q4_production_approval"]
    def __init__(self): self.p = {}; self.candidate = None; self.gates = {}
    def update(self, skill, correct):
        pk = self.p.get(skill, 0.1)
        slip, guess, learn = 0.1, 0.25, 0.3
        lik_k = (1-slip) if correct else slip
        lik_n = guess if correct else (1-guess)
        post = pk*lik_k / (pk*lik_k + (1-pk)*lik_n)
        self.p[skill] = post + (1-post)*learn
        return self.p[skill]
    def propose_candidate(self, name, evidence: dict):
        self.candidate = name; self.gates = evidence
    def candidate_promotable(self): return all(self.gates.get(g) for g in self.GATES)

# ── CODEX loop (the cognitive algorithm) ───────────────────────────────
def codex_append(line: str):
    t = THINK.read_text()
    t = t.replace("## 4. Open hypotheses", f"- {line}\n\n## 4. Open hypotheses", 1)
    THINK.write_text(t); print(f"[codex] {line}")

def verify_csv(path: Path):
    bad = 0
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            vid = row["video_id"]
            rec = ROOT/"content"/"receipts"/f"{vid}.json"
            if not rec.exists(): continue
            r = json.loads(rec.read_text())
            if r.get("soul") != soul():
                print(f"[verify] {vid}: receipt soul mismatch"); bad += 1
            if r.get("id") and cli("known", r["id"])["known"]:
                ok = solve_check(r["id"], r.get("params", {}), r.get("answer"))
                if not ok: print(f"[verify] {vid}: solve() disagrees"); bad += 1
    print("[verify] OK" if bad == 0 else f"[verify] {bad} problem(s)")
    return bad == 0

def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["soul","generate","verify","codex"])
    p.add_argument("--accept", action="store_true")
    p.add_argument("--seed", type=int, default=20261023)
    p.add_argument("--orientation", default="horizontal")
    p.add_argument("--csv", default="content/master_horizontal.csv")
    p.add_argument("text", nargs="?", default="")
    a = p.parse_args()

    if a.cmd == "soul":  sys.exit(0 if soul_gate(a.accept) else 1)
    if a.cmd == "generate":
        if not soul_gate(): sys.exit(1)
        subprocess.run([sys.executable, "tools/math_brain_bridge.py",
                        "--seed", str(a.seed), "--orientation", a.orientation,
                        "--out", a.csv], check=True)
        codex_append(f"generate seed={a.seed} orient={a.orientation} soul={soul()[:12]}")
    if a.cmd == "verify": sys.exit(0 if (soul_gate() and verify_csv(ROOT/a.csv)) else 1)
    if a.cmd == "codex": codex_append(a.text)

if __name__ == "__main__":
    main()
