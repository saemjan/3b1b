#!/usr/bin/env python3
"""Bridge: Math Brain core (saemcli) -> 3b1b CSV schema + solve receipts."""
import csv, json, subprocess, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAEMCLI = ROOT / "build" / "saemcli"
RECEIPTS = ROOT / "content" / "receipts"
RECEIPTS.mkdir(parents=True, exist_ok=True)

FIELDNAMES = ["video_id","concept_type","header_title","tagline","question_text",
              "option_a","option_b","option_c","option_d","correct_answer",
              "equations_json","visual_data_json","audio_script","orientation",
              "beats_json","target_duration_sec"]

def cli(*args):
    r = subprocess.run([str(SAEMCLI), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"saemcli failed: {r.stderr}")
    return json.loads(r.stdout)

def concept_of(topic: str) -> str:
    t = topic.lower()
    for k, v in (("mech","MECHANICS"),("rot","MECHANICS"),("grav","MECHANICS"),
                 ("elec","ELECTROMAGNETISM"),("mag","ELECTROMAGNETISM"),("circ","ELECTROMAGNETISM"),
                 ("therm","THERMODYNAMICS"),("heat","THERMODYNAMICS"),("gas","THERMODYNAMICS"),
                 ("wave","WAVES"),("opt","WAVES"),("sound","WAVES"),
                 ("quant","QUANTUM"),("atom","QUANTUM"),("nuc","QUANTUM"),("mod","QUANTUM")):
        if k in t: return v
    return "PROBLEM"

def primitive_of(topic: str) -> str:
    t = topic.lower()
    for k, v in (("rot","rotational_motion"),("mech","projectile_motion"),("grav","projectile_motion"),
                 ("elec","electric_field"),("mag","magnetic_field"),("circ","induction_coil"),
                 ("therm","particle_gas"),("heat","particle_gas"),("gas","particle_gas"),
                 ("opt","two_path_interference"),("wave","wave_pulse"),("sound","beat_pattern"),
                 ("quant","two_path_interference"),("atom","bohr_orbit_photon"),("nuc","potential_well")):
        if k in t: return v
    return "calculus_graph"

def letter_of(q: dict) -> str:
    ans = q.get("answer", "")
    for i, opt in enumerate(q.get("options", [])):
        if ans in (opt.get("key"), opt.get("text")):
            return "ABCD"[i]
    return ans

def layout(orientation: str):
    if orientation == "vertical":
        return [0.0,6.8,0.0],[0.0,1.0,0.0],[0.0,-2.8,0.0],[0.0,-6.7,0.0],34,26,24
    return [0.0,3.8,0.0],[0.0,0.4,0.0],[0.0,-1.8,0.0],[0.0,-3.6,0.0],32,24,22

def beats(orientation: str):
    if orientation == "vertical":
        return [{"type":"hook","focus":"model"},{"type":"promise","focus":"math","transition":"push"},
                {"type":"experiment","focus":"model","transition":"wipe"},
                {"type":"law","focus":"math","transition":"zoom_blur"},
                {"type":"emphasis","focus":"model","transition":"push"},
                {"type":"punchline","focus":"caption","transition":"wipe"}]
    return [{"type":"hook","focus":"model"},{"type":"promise","focus":"math","transition":"push"},
            {"type":"experiment","focus":"model","transition":"wipe"},
            {"type":"law","focus":"math","transition":"zoom_blur"},
            {"type":"midpoint","focus":"model","transition":"push"},
            {"type":"emphasis","focus":"math","transition":"zoom_blur"},
            {"type":"punchline","focus":"caption","transition":"push"},
            {"type":"cta","focus":"caption","transition":"wipe"}]

def row_from_question(q: dict, orientation: str, seed: int) -> dict:
    topic = q.get("topic", "PROBLEM")
    tp, mp, xp, cp, ts, xs, cs = layout(orientation)
    opts = (q.get("options") or [])[:4]
    while len(opts) < 4: opts.append({"key": "-", "text": "-"})
    script = (q.get("explanation") or q.get("text", "")).strip()
    words = len(script.split())
    vid = f"mb_{q.get('gen', q.get('topic','x'))}_{seed}"
    row = {
        "video_id": vid,
        "concept_type": concept_of(topic),
        "header_title": q.get("topic", topic).title(),
        "tagline": q.get("gen", "computed"),
        "question_text": q.get("text", ""),
        "option_a": opts[0]["text"], "option_b": opts[1]["text"],
        "option_c": opts[2]["text"], "option_d": opts[3]["text"],
        "correct_answer": letter_of(q),
        "equations_json": json.dumps([], ensure_ascii=False),
        "visual_data_json": json.dumps([
            {"type":"text","id":"title","text":q.get("topic","").title(),"pos":tp,"color":"#F2F3F5","font_size":ts},
            {"type":primitive_of(topic),"id":"model","pos":mp,"color":"#4CC9F0"},
            {"type":"text","id":"math","text":str(q.get("answer","")),"pos":xp,"color":"#8AC926","font_size":xs},
            {"type":"text","id":"caption","text":q.get("gen","computed"),"pos":cp,"color":"#F1C40F","font_size":cs},
        ], ensure_ascii=False),
        "audio_script": script,
        "orientation": orientation,
        "beats_json": json.dumps(beats(orientation), ensure_ascii=False),
        "target_duration_sec": max(30, int(round(words / 2.5))),   # R4 honesty
    }
    receipt = {"video_id": vid, "seed": seed, "id": q.get("gen"),
               "answer": q.get("answer"), "soul": cli("soul")["soul"],
               "ts": datetime.date.today().isoformat()}
    (RECEIPTS / f"{vid}.json").write_text(json.dumps(receipt, indent=2))
    return row

def generate(seed: int, y0: int, y1: int, orientation: str, out_csv: Path):
    bank = cli("bank", str(seed), str(y0), str(y1))
    qs = bank.get("questions") if isinstance(bank, dict) else bank
    if not isinstance(qs, list):
        raise SystemExit("unexpected bank shape; inspect: saemcli bank ...")
    rows = [row_from_question(q, orientation, seed) for q in qs]
    with open(out_csv, "a", newline="", encoding="utf-8") as f:   # R1: plain utf-8
        w = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
        if out_csv.stat().st_size == 0: w.writeheader()
        w.writerows(rows)
    print(f"✓ appended {len(rows)} Math Brain rows -> {out_csv}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=20261023)
    p.add_argument("--y0", type=int, default=2007)
    p.add_argument("--y1", type=int, default=2025)
    p.add_argument("--orientation", default="horizontal")
    p.add_argument("--out", default="content/master_horizontal.csv")
    a = p.parse_args()
    generate(a.seed, a.y0, a.y1, a.orientation, ROOT / a.out)
