#!/usr/bin/env python3
"""style_belief.py — Bernoulli beliefs over style genes (A4: no gene is
declared good without moral certainty; cog.next: explore the least certain)."""
import json, math
from pathlib import Path

SLIP, GUESS, BAR = 0.10, 0.25, 1000.0   # same caps as qcos.cxn


def observe(beliefs, gene_key, success):
    p, q = 1 - SLIP, GUESS
    cur = beliefs.get(gene_key, {"logodds": 0.0, "shots": 0})
    cur["logodds"] += math.log(p / q) if success else math.log((1 - p) / (1 - q))
    cur["shots"] += 1
    beliefs[gene_key] = cur
    return beliefs


def next_to_explore(beliefs):
    """Farthest from moral certainty = most informative dimension to mutate."""
    best = min(beliefs.items(), key=lambda kv: abs(kv[1]["logodds"]), default=None)
    return best[0] if best else None


def promoted(beliefs, gene_key):
    return abs(beliefs.get(gene_key, {"logodds": 0.0})["logodds"]) >= math.log(BAR)


def load(path): 
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else {}


def save(path, beliefs):
    Path(path).write_text(json.dumps(beliefs, indent=2))
