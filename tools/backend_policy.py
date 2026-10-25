#!/usr/bin/env python3
"""backend_policy.py — dependency negotiation: own tools first, select
libraries only when proven and paying.

Constitutional role:
  * The repo must run on a bare machine: stdlib-only "own tools" are the
    ruler and the default backend.
  * An external library may be adopted ONLY when it (1) imports with the
    API we need, (2) passes a frozen parity witness against the ruler, and
    (3) its cost model beats the ruler at the current problem size.
  * Every decision is deterministic, pinnable via SAEM_BACKEND, and
    recorded so the render ledger can receipt it (A5).

Engine usage:
    from tools import backend_policy as bp
    bp.register("physics", "pure",  probe=lambda: (True, "own tool"),
                witness=lambda: True, speedup=lambda size: 1.0)
    bp.register("physics", "numpy", probe=lambda: bp.probe_import("numpy"),
                witness=my_parity,  speedup=lambda size: size / 2000.0)
    name, report = bp.choose("physics", size=n_bodies * steps)
"""
from __future__ import annotations

import importlib
import os
from typing import Callable, Dict, List, Tuple

OWN_TOOL = "pure"

_REGISTRY: Dict[str, List[dict]] = {}
_GATE_CACHE: Dict[Tuple[str, str], dict] = {}
_DECISIONS: List[dict] = []


def probe_import(module: str, attrs: Tuple[str, ...] = ()) -> Tuple[bool, str]:
    """Gate 1: importable and API-complete?"""
    try:
        mod = importlib.import_module(module)
    except Exception as e:
        return False, f"import failed: {type(e).__name__}: {e}"
    missing = [a for a in attrs if not hasattr(mod, a)]
    if missing:
        return False, f"missing api: {missing}"
    return True, "ok"


def register(kind: str, backend: str, probe: Callable, witness: Callable,
             speedup: Callable[[float], float]) -> None:
    priority = 0 if backend == OWN_TOOL else 1
    entry = {"backend": backend, "probe": probe,
             "witness": witness, "speedup": speedup, "priority": priority}
    bucket = _REGISTRY.setdefault(kind, [])
    bucket[:] = [e for e in bucket if e["backend"] != backend]
    bucket.append(entry)
    bucket.sort(key=lambda e: e["priority"])
    _GATE_CACHE.pop((kind, backend), None)


def _gate(kind: str, entry: dict) -> dict:
    """Gates 1+2, memoized per process."""
    key = (kind, entry["backend"])
    if key in _GATE_CACHE:
        return _GATE_CACHE[key]
    try:
        ok, why = entry["probe"]()
        if ok:
            passed = bool(entry["witness"]())
            ok, why = passed, ("witness ok" if passed else "parity witness failed")
    except Exception as e:
        ok, why = False, f"gate raised: {type(e).__name__}: {e}"
    res = {"ok": ok, "why": why}
    _GATE_CACHE[key] = res
    return res


def choose(kind: str, size: float = 1.0) -> Tuple[str, dict]:
    """Gates 3+4+5: cost model, pin, record."""
    entries = _REGISTRY.get(kind)
    if not entries:
        raise KeyError(f"no backends registered for kind {kind!r}")

    report = {"kind": kind, "size": size, "considered": []}
    gated = []
    for e in entries:
        g = _gate(kind, e)
        report["considered"].append({"backend": e["backend"], **g})
        if g["ok"]:
            gated.append(e)
    if not gated:
        raise RuntimeError(f"no gated backend for kind {kind!r}: {report}")

    chosen, reason = None, ""
    forced = os.environ.get("SAEM_BACKEND", "auto").strip()
    if forced != "auto":
        hit = [e for e in gated if e["backend"] == forced]
        if hit:
            chosen, reason = hit[0], f"pinned by SAEM_BACKEND={forced}"
        else:
            reason = f"pinned {forced} not gated; auto fallback"

    if chosen is None:  # gate 3: cost model, own tool wins ties
        best = None
        for e in gated:
            try:
                s = float(e["speedup"](size))
            except Exception:
                s = 0.0
            key = (s, -e["priority"])
            if best is None or key > best[0]:
                best = (key, e, s)
        chosen = best[1]
        reason = (reason + "; " if reason else "") + \
            f"cost model speedup={best[2]:.2f}x at size={size:g}"

    report.update({"chosen": chosen["backend"], "reason": reason})
    _DECISIONS.append(report)
    return chosen["backend"], report


def record(report: dict) -> None:
    _DECISIONS.append(report)


def decisions() -> List[dict]:
    return list(_DECISIONS)


def reset() -> None:
    _GATE_CACHE.clear()
