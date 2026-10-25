#!/usr/bin/env python3
"""style_genome.py — representation layer: never frozen, always witnessed.

Constitutional placement (IR ladder):
  SIR  intent      topic / audience / concept  (what must be understood)
  DIR  genome      palette, layout, motion, voice, skin   (THIS FILE)
  CIR  schedule    pace + entrance order derived from genome
  MIR  micro-ops   render_universal skins primitives from the genome

The frozen analytic rulers (projectile parabola, drag exponential,
spring harmonic, Kepler circle) are CORRECTNESS WITNESSES. They run
headless in engine selftests / CI. They never touch this file and never
touch the render path. Truth is frozen; style is not.
"""
from __future__ import annotations

import colorsys
import hashlib
import json
import math
import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

PALETTE_FAMILIES = ("complementary", "triadic", "analogous", "split", "mono-ramp")
LAYOUT_FAMILIES = ("grid-jitter", "golden-spiral", "radial", "diagonal-flow", "stacked-band")
MOTION_FAMILIES = ("crisp", "elastic", "glide", "staccato", "breathing")
ENTRANCE_GRAMMARS = ("create", "write", "grow", "fade-scale", "trace")
VOICE_GRAMMARS = ("question-first", "picture-first", "contrast", "story-arc", "myth-bust")
RATE_FUNC = {"crisp": "smooth", "elastic": "ease_out_back", "glide": "ease_in_out_sine",
             "staccato": "rush_from", "breathing": "ease_in_out_sine"}

MIN_NOVELTY = 0.35          # distance floor vs recent lessons
_F = lambda x: round(float(x), 4)


def _sha(*parts: str) -> int:
    return int.from_bytes(
        hashlib.sha256("|".join(parts).encode("utf-8")).digest()[:8], "big")


@dataclass
class Genome:
    seed_text: str
    palette_family: str; hue_base: float; hue_spread: float
    sat: Tuple[float, float]; val: Tuple[float, float]
    layout_family: str; layout_jitter: float
    motion_family: str; overshoot: float
    entrance: str; voice: str
    stroke: float; dot_radius: float; label_scale: float
    pace: float; opacity: float

    def dict(self) -> Dict:
        return asdict(self)

    # ---- representation outputs -------------------------------------
    def palette(self, n: int = 6) -> List[str]:
        offs = {"complementary": [0, .5, .06, .56, .25, .75],
                "triadic": [0, 1/3, 2/3, .12, .45, .78],
                "analogous": [0, .06, .12, .18, -.06, .30],
                "split": [0, .42, .58, .10, .50, .90],
                "mono-ramp": [0, 0, 0, 0, 0, 0]}[self.palette_family]
        cols = []
        for k in range(n):
            h = (self.hue_base + offs[k % 6] * self.hue_spread * 2) % 1.0
            if self.palette_family == "mono-ramp":
                s, v = self.sat[0] - 0.08 * (k % 3), self.val[0] - 0.12 * k
            else:
                s = self.sat[k % 2]; v = self.val[k % 2]
            s = min(1.0, max(0.15, s)); v = min(1.0, max(0.25, v))
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            cols.append("#%02x%02x%02x" % (round(r*255), round(g*255), round(b*255)))
        return cols

    def slot(self, i: int, n: int, fw: float, fh: float) -> Tuple[float, float]:
        rng = random.Random(_sha(self.seed_text, "slot", str(i)))
        jx = rng.uniform(-self.layout_jitter, self.layout_jitter)
        jy = rng.uniform(-self.layout_jitter, self.layout_jitter)
        f = self.layout_family
        if f == "grid-jitter":
            cols = max(1, math.ceil(math.sqrt(n)))
            rows = max(1, math.ceil(n / cols))
            r, c = divmod(i, cols)
            x, y = -fw/2 + fw*(c+.5)/cols, fh/2 - fh*(r+.5)/rows
        elif f == "golden-spiral":
            ang = (i+1) * 2.399963229728653
            rad = min(fw, fh) * 0.42 * math.sqrt((i+1)/max(1, n))
            x, y = rad*math.cos(ang), rad*math.sin(ang)
        elif f == "radial":
            ang = 2*math.pi*i/max(1, n)
            rad = min(fw, fh) * 0.35
            x, y = rad*math.cos(ang), rad*math.sin(ang)
        elif f == "diagonal-flow":
            t = i/max(1, n-1) if n > 1 else .5
            x, y = -fw/2 + fw*t, fh/2 - fh*t*0.8
        else:
            x, y = -fw/2 + fw*((i//3 % 4)+.5)/4, fh/2 - fh*((i % 3)+.5)/3
        mx, my = fw*0.08, fh*0.08
        x = max(-fw/2+mx, min(fw/2-mx, x + jx*fw))
        y = max(-fh/2+my, min(fh/2-my, y + jy*fh))
        return _F(x), _F(y)

    def rate_func_name(self) -> str:
        return RATE_FUNC[self.motion_family]


# ---- derivation / novelty / evolution --------------------------------
def derive(content_key: str, topic: str, audience: str, generation: int) -> Genome:
    rng = random.Random(_sha(content_key, topic, audience, str(generation)))
    mot = rng.choice(MOTION_FAMILIES)
    return Genome(
        seed_text=f"{content_key}|{topic}|{audience}|g{generation}",
        palette_family=rng.choice(PALETTE_FAMILIES),
        hue_base=_F(rng.random()), hue_spread=_F(rng.uniform(0.08, 0.45)),
        sat=(_F(rng.uniform(0.55, 0.95)), _F(rng.uniform(0.35, 0.70))),
        val=(_F(rng.uniform(0.75, 1.00)), _F(rng.uniform(0.50, 0.85))),
        layout_family=rng.choice(LAYOUT_FAMILIES),
        layout_jitter=_F(rng.uniform(0.02, 0.12)),
        motion_family=mot,
        overshoot=_F(rng.uniform(0.0, 0.35) if mot in ("elastic", "crisp")
                     else rng.uniform(0.0, 0.15)),
        entrance=rng.choice(ENTRANCE_GRAMMARS), voice=rng.choice(VOICE_GRAMMARS),
        stroke=_F(rng.uniform(2.0, 5.0)), dot_radius=_F(rng.uniform(0.06, 0.16)),
        label_scale=_F(rng.uniform(0.80, 1.25)), pace=_F(rng.uniform(0.85, 1.25)),
        opacity=_F(rng.uniform(0.75, 1.0)))


def distance(a: Genome, b: Genome) -> float:
    dh = abs(a.hue_base - b.hue_base); dh = min(dh, 1 - dh)
    d = 2*dh
    d += 0 if a.palette_family == b.palette_family else 1
    d += 0 if a.layout_family == b.layout_family else 1
    d += 0 if a.motion_family == b.motion_family else 1
    d += 0 if a.voice == b.voice else 1
    d += abs(a.pace - b.pace) + 4*abs(a.stroke - b.stroke)/3
    return d / 7.0


def fresh_genome(content_key, topic, audience, recent: List[Genome],
                 min_dist: float = MIN_NOVELTY, tries: int = 24):
    """Never repeat a look: resample generations until novel vs memory."""
    for gen in range(tries):
        g = derive(content_key, topic, audience, gen)
        if not recent or min(distance(g, r) for r in recent) >= min_dist:
            return g, gen
    g = derive(content_key, topic, audience, tries)
    return mutate(g, random.Random(_sha(content_key, "fallback"))), tries


def mutate(g: Genome, rng: random.Random, rate: float = 0.25) -> Genome:
    d = g.dict()
    if rng.random() < rate: d["palette_family"] = rng.choice(PALETTE_FAMILIES)
    if rng.random() < rate: d["hue_base"] = _F((d["hue_base"] + rng.uniform(-.2, .2)) % 1)
    if rng.random() < rate: d["layout_family"] = rng.choice(LAYOUT_FAMILIES)
    if rng.random() < rate: d["motion_family"] = rng.choice(MOTION_FAMILIES)
    if rng.random() < rate: d["voice"] = rng.choice(VOICE_GRAMMARS)
    if rng.random() < rate: d["entrance"] = rng.choice(ENTRANCE_GRAMMARS)
    if rng.random() < rate: d["pace"] = _F(min(1.4, max(0.7, d["pace"] + rng.uniform(-.15, .15))) )
    if rng.random() < rate: d["stroke"] = _F(min(6, max(1.5, d["stroke"] + rng.uniform(-1, 1))))
    d["seed_text"] = g.seed_text + f"~mut{rng.getrandbits(16):x}"
    return Genome(**d)


def crossover(a: Genome, b: Genome, rng: random.Random) -> Genome:
    da, db = a.dict(), b.dict()
    d = {k: (da[k] if rng.random() < 0.5 else db[k]) for k in da}
    d["seed_text"] = f"{a.seed_text}x{b.seed_text}"
    return Genome(**d)


def evolve(scored: List[Tuple[Genome, float]], rng: random.Random) -> Genome:
    """Survival of the clearest: QA/teacher-scored genomes breed the next look."""
    scored = sorted(scored, key=lambda t: t[1], reverse=True)
    if len(scored) >= 2:
        top = scored[:max(1, len(scored)//3)]
        child = crossover(rng.choice(top)[0], rng.choice(scored[:len(scored)//2])[0], rng)
    elif scored:
        child = scored[0][0]
    else:
        child = derive("genesis", "general", "any", rng.randrange(10**6))
    return mutate(child, rng)


# ---- content-aware primitive suggestions (replaces frozen TOPIC_PRIMS)
TOPIC_POOLS = {
    "kinematics": ["projectile_motion", "graph", "vector", "number_line", "live_label"],
    "emwave":     ["wave", "ray", "ellipse", "live_label"],
    "twoslit":    ["wave", "graph", "dot", "brace"],
    "ratchet":    ["pendulum", "spring", "energy_bar", "live_label"],
    "betatron":   ["orbit", "vector", "circle", "live_label"],
    "masers":     ["energy_bar", "dot", "wave", "numerical_chain"],
}
DEFAULT_POOL = ["graph", "vector", "dot", "energy_bar", "live_label"]


def suggest_visuals(topic: str, rng: random.Random, count: int = 3) -> List[Dict]:
    pool = TOPIC_POOLS.get(topic, DEFAULT_POOL)
    specs = []
    for t in rng.sample(pool, k=min(count, len(pool))):
        s: Dict = {"type": t}
        if t == "projectile_motion":
            s["v0"] = round(rng.uniform(10, 30), 1)
            s["angle"] = rng.choice([30, 37, 45, 53, 60])
        elif t == "graph":
            s["expression"] = rng.choice(["x", "x^2/4", "sin(x)", "cos(x)/2", "x^3/8 - x"])
        elif t == "wave":
            s["amplitude"] = round(rng.uniform(0.4, 1.0), 2)
            s["frequency"] = round(rng.uniform(0.5, 2.0), 2)
        elif t == "vector":
            s["start"] = [round(rng.uniform(-3, -1), 1), round(rng.uniform(-2, 0), 1)]
            s["end"] = [round(rng.uniform(1, 3), 1), round(rng.uniform(0, 2), 1)]
        elif t == "energy_bar":
            s["fraction"] = round(rng.uniform(0.3, 0.9), 2)
        elif t == "orbit":
            s["width"] = round(rng.uniform(3, 5), 1)
            s["height"] = round(rng.uniform(2, 3), 1)
        specs.append(s)
    return specs


# ---- frozen-in-time check that the STYLE layer itself behaves ---------
def selftest():
    checks = []
    g1 = derive("row-1", "kinematics", "jee", 0)
    g2 = derive("row-1", "kinematics", "jee", 0)
    checks.append(("style-determinism",
                   json.dumps(g1.dict(), sort_keys=True) == json.dumps(g2.dict(), sort_keys=True), ""))
    g3 = derive("row-2", "kinematics", "jee", 0)
    checks.append(("style-content-sensitivity", g1.seed_text != g3.seed_text
                   and (g1.hue_base != g3.hue_base or g1.layout_family != g3.layout_family), ""))
    recent = [derive(f"old{i}", "kinematics", "jee", 0) for i in range(8)]
    g, gen = fresh_genome("row-99", "kinematics", "jee", recent)
    checks.append(("style-novelty", min(distance(g, r) for r in recent) >= MIN_NOVELTY,
                   f"gen={gen}"))
    cols = g.palette()
    checks.append(("palette-valid", all(c.startswith("#") and len(c) == 7 for c in cols), ""))
    x, y = g.slot(2, 5, 9.0, 16.0)
    checks.append(("slot-in-frame", abs(x) <= 4.5 and abs(y) <= 8.0, f"({x},{y})"))
    return checks


if __name__ == "__main__":
    import sys
    fails = 0
    for name, ok, detail in selftest():
        print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
        fails += 0 if ok else 1
    sys.exit(1 if fails else 0)
