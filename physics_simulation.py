#!/usr/bin/env python3
"""physics_simulation.py — gen-2 engine: deterministic 2D Newtonian core.

Dependency stance (backend_policy):
  * "pure"  : own tool. Stdlib-only RK4 over flat float lists. The ruler.
  * "numpy" : select library. Adopted only when probe+witness pass AND the
              cost model says n_bodies*steps pays for it. Must match pure
              to 1e-9 on a frozen fixture (parity witness).
Witnesses are analytic closed forms (projectile parabola, drag exponential,
spring harmonic, Kepler circle) — no external data, no libraries (A0/A5).

Renderer contract v1: ROUTE_TABLE["physics_simulation"](scene, spec).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
try:
    from tools import backend_policy as bp
except Exception:                      # engine copied next to the policy
    import backend_policy as bp        # type: ignore

try:
    import numpy as _NP
except Exception:
    _NP = None

_ACCEL_THRESHOLD = 2000.0              # n*steps above which numpy pays


# ---------------------------------------------------------------- validation
def _vector(value, name):
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            v = [float(value[0]), float(value[1])]
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a two-dimensional vector.")
        if all(math.isfinite(c) for c in v):
            return v
    raise ValueError(f"{name} must contain two finite numbers.")


def _finite_number(value, name, minimum=None):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite number.")
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        suffix = f" >= {minimum}" if minimum is not None else ""
        raise ValueError(f"{name} must be finite and{suffix}.")
    return result


def _validate(bodies, forces):
    if not isinstance(bodies, list) or not bodies:
        raise ValueError("physics_simulation needs at least one body.")
    if not isinstance(forces, list):
        raise ValueError("physics_simulation forces must be a list.")
    masses, initial = [], []
    for i, b in enumerate(bodies):
        if not isinstance(b, dict):
            raise ValueError(f"Body {i} must be an object.")
        m = _finite_number(b.get("mass", 1.0), f"body {i} mass", minimum=0.0)
        if m == 0:
            raise ValueError(f"Body {i} mass must be greater than zero.")
        p = _vector(b.get("position", [0, 0]), f"body {i} position")
        v = _vector(b.get("velocity", [0, 0]), f"body {i} velocity")
        masses.append(m)
        initial.extend(p + v)
    n = len(masses)
    norm = []
    for i, f in enumerate(forces):
        if not isinstance(f, dict):
            raise ValueError(f"Force {i} must be an object.")
        kind = str(f.get("type", "")).lower()
        e = dict(f)
        e["type"] = kind
        targets = f.get("bodies", list(range(n)))
        if not isinstance(targets, list) or any(
                not isinstance(t, int) or not 0 <= t < n for t in targets):
            raise ValueError(f"Force {i} has invalid body indices.")
        e["bodies"] = targets
        if kind == "uniform_acceleration":
            e["acceleration"] = _vector(f.get("acceleration"),
                                        f"force {i} acceleration")
        elif kind == "linear_drag":
            e["coefficient"] = _finite_number(f.get("coefficient"),
                                              f"force {i} coefficient", 0.0)
        elif kind == "spring":
            bi = f.get("body")
            oi = f.get("other")
            if not isinstance(bi, int) or not 0 <= bi < n:
                raise ValueError(f"Spring {i} has an invalid body index.")
            if oi is not None and (not isinstance(oi, int)
                                   or not 0 <= oi < n or oi == bi):
                raise ValueError(f"Spring {i} has an invalid other index.")
            if oi is None and "anchor" not in f:
                raise ValueError(f"Spring {i} needs an anchor or other body.")
            e["body"], e["other"] = bi, oi
            if oi is None:
                e["anchor"] = _vector(f["anchor"], f"spring {i} anchor")
            e["stiffness"] = _finite_number(f.get("stiffness"),
                                            f"spring {i} stiffness", 0.0)
            e["rest_length"] = _finite_number(f.get("rest_length", 0.0),
                                              f"spring {i} rest_length", 0.0)
            e["damping"] = _finite_number(f.get("damping", 0.0),
                                          f"spring {i} damping", 0.0)
        elif kind == "central_gravity":
            s = f.get("source")
            if not isinstance(s, int) or not 0 <= s < n:
                raise ValueError(f"Central gravity {i} bad source index.")
            e["source"] = s
            e["mu"] = _finite_number(f.get("mu"), f"central gravity {i} mu", 0.0)
        else:
            raise ValueError(f"Unsupported force type '{kind}'.")
        norm.append(e)
    return masses, initial, norm


# ------------------------------------------------------- pure backend (ruler)
def _accel_pure(flat, masses, forces):
    n = len(masses)
    ax = [0.0] * n
    ay = [0.0] * n
    px = [flat[4 * i] for i in range(n)]
    py = [flat[4 * i + 1] for i in range(n)]
    vx = [flat[4 * i + 2] for i in range(n)]
    vy = [flat[4 * i + 3] for i in range(n)]
    for f in forces:
        k = f["type"]
        if k == "uniform_acceleration":
            gx, gy = f["acceleration"]
            for i in f["bodies"]:
                ax[i] += gx
                ay[i] += gy
        elif k == "linear_drag":
            c = f["coefficient"]
            for i in f["bodies"]:
                ax[i] -= c * vx[i] / masses[i]
                ay[i] -= c * vy[i] / masses[i]
        elif k == "spring":
            b, o = f["body"], f["other"]
            if o is None:
                dx, dy = px[b] - f["anchor"][0], py[b] - f["anchor"][1]
                ovx = ovy = 0.0
            else:
                dx, dy = px[b] - px[o], py[b] - py[o]
                ovx, ovy = vx[o], vy[o]
            L = math.hypot(dx, dy)
            if L <= 1e-12:
                continue
            ux, uy = dx / L, dy / L
            rel = (vx[b] - ovx) * ux + (vy[b] - ovy) * uy
            mag = -f["stiffness"] * (L - f["rest_length"]) - f["damping"] * rel
            fx, fy = mag * ux, mag * uy
            ax[b] += fx / masses[b]
            ay[b] += fy / masses[b]
            if o is not None:
                ax[o] -= fx / masses[o]
                ay[o] -= fy / masses[o]
        elif k == "central_gravity":
            s, mu = f["source"], f["mu"]
            for t in f["bodies"]:
                if t == s:
                    continue
                dx, dy = px[s] - px[t], py[s] - py[t]
                d = math.hypot(dx, dy)
                if d <= 1e-12:
                    raise ValueError("Central-gravity coincidence.")
                g = mu / d ** 3
                ax[t] += g * dx
                ay[t] += g * dy
    return ax, ay


def _deriv_pure(flat, masses, forces):
    n = len(masses)
    ax, ay = _accel_pure(flat, masses, forces)
    out = [0.0] * (4 * n)
    for i in range(n):
        out[4 * i] = flat[4 * i + 2]
        out[4 * i + 1] = flat[4 * i + 3]
        out[4 * i + 2] = ax[i]
        out[4 * i + 3] = ay[i]
    return out


def _axpy(s, h, k):
    return [s[i] + h * k[i] for i in range(len(s))]


def _rk4_mix(s, dt, k1, k2, k3, k4):
    c = dt / 6.0
    return [s[i] + c * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
            for i in range(len(s))]


def _integrate_pure(initial, masses, forces, duration, steps):
    dt = duration / steps
    s = list(initial)
    states = [list(s)]
    for _ in range(steps):
        k1 = _deriv_pure(s, masses, forces)
        k2 = _deriv_pure(_axpy(s, 0.5 * dt, k1), masses, forces)
        k3 = _deriv_pure(_axpy(s, 0.5 * dt, k2), masses, forces)
        k4 = _deriv_pure(_axpy(s, dt, k3), masses, forces)
        s = _rk4_mix(s, dt, k1, k2, k3, k4)
        if not all(math.isfinite(v) for v in s):
            raise ValueError("Physics simulation diverged (pure).")
        states.append(list(s))
    return states


# ---------------------------------------------------- numpy backend (select)
def _integrate_numpy(initial, masses, forces, duration, steps):
    np = _NP
    n = len(masses)
    m = np.asarray(masses, dtype=float)
    s = np.asarray(initial, dtype=float).reshape(n, 4)

    def accel(st):
        a = np.zeros((n, 2))
        pos, vel = st[:, :2], st[:, 2:]
        for f in forces:
            k = f["type"]
            idx = f["bodies"]
            if k == "uniform_acceleration":
                a[idx] += np.asarray(f["acceleration"], dtype=float)
            elif k == "linear_drag":
                a[idx] -= f["coefficient"] * vel[idx] / m[idx, None]
            elif k == "spring":
                b, o = f["body"], f["other"]
                if o is None:
                    d = pos[b] - np.asarray(f["anchor"], dtype=float)
                    ov = np.zeros(2)
                else:
                    d = pos[b] - pos[o]
                    ov = vel[o]
                L = float(np.hypot(d[0], d[1]))
                if L <= 1e-12:
                    continue
                u = d / L
                rel = float(np.dot(vel[b] - ov, u))
                mag = -f["stiffness"] * (L - f["rest_length"]) - f["damping"] * rel
                a[b] += mag * u / m[b]
                if o is not None:
                    a[o] -= mag * u / m[o]
            elif k == "central_gravity":
                src = f["source"]
                for t in idx:
                    if t == src:
                        continue
                    d = pos[src] - pos[t]
                    dist = float(np.hypot(d[0], d[1]))
                    if dist <= 1e-12:
                        raise ValueError("Central-gravity coincidence.")
                    a[t] += f["mu"] * d / dist ** 3
        return a

    def deriv(st):
        return np.column_stack((st[:, 2:], accel(st)))

    dt = duration / steps
    states = [s.reshape(-1).tolist()]
    for _ in range(steps):
        k1 = deriv(s)
        k2 = deriv(s + 0.5 * dt * k1)
        k3 = deriv(s + 0.5 * dt * k2)
        k4 = deriv(s + dt * k3)
        s = s + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        if not bool(np.all(np.isfinite(s))):
            raise ValueError("Physics simulation diverged (numpy).")
        states.append(s.reshape(-1).tolist())
    return states


# ------------------------------------------------------------- parity witness
_FROZEN = (
    [{"mass": 1.0, "position": [0.0, 0.0], "velocity": [0.0, 0.0]},
     {"mass": 2.0, "position": [3.0, 0.0], "velocity": [0.0, 1.0]},
     {"mass": 1.5, "position": [-2.0, 1.0], "velocity": [0.5, -0.5]}],
    [{"type": "uniform_acceleration", "acceleration": [0.0, -9.8]},
     {"type": "linear_drag", "coefficient": 0.3},
     {"type": "spring", "body": 1, "other": 0, "stiffness": 4.0,
      "rest_length": 1.0, "damping": 0.2},
     {"type": "central_gravity", "source": 0, "mu": 12.0, "bodies": [1, 2]}],
)


def _numpy_parity() -> bool:
    """Gate 2 for numpy: must reproduce the ruler on a frozen fixture."""
    if _NP is None:
        return False
    bodies, forces = _FROZEN
    masses, initial, norm = _validate(bodies, forces)
    a = _integrate_pure(initial, masses, norm, 2.0, 300)
    b = _integrate_numpy(initial, masses, norm, 2.0, 300)
    return max(abs(x - y) for ra, rb in zip(a, b)
               for x, y in zip(ra, rb)) <= 1e-9


bp.register("physics", bp.OWN_TOOL,
            probe=lambda: (True, "own tool, stdlib only"),
            witness=lambda: True,
            speedup=lambda size: 1.0)
bp.register("physics", "numpy",
            probe=lambda: bp.probe_import("numpy", ("array", "zeros", "hypot")),
            witness=_numpy_parity,
            speedup=lambda size: size / _ACCEL_THRESHOLD)


# ------------------------------------------------------------------ public API
class SimResult:
    __slots__ = ("masses", "forces", "states", "backend", "decision")

    def __init__(self, masses, forces, states, backend, decision):
        self.masses, self.forces = masses, forces
        self.states, self.backend, self.decision = states, backend, decision


def simulate_system(bodies, forces, duration, steps=600, backend="auto"):
    duration = _finite_number(duration, "duration", minimum=0.0)
    if duration == 0:
        raise ValueError("duration must be greater than zero.")
    if not isinstance(steps, int) or not 2 <= steps <= 10000:
        raise ValueError("steps must be an integer from 2 through 10000.")
    masses, initial, norm = _validate(bodies, forces)
    size = len(masses) * steps

    if backend == "auto":
        backend, decision = bp.choose("physics", size=size)
    else:
        decision = {"kind": "physics", "size": size,
                    "chosen": backend, "reason": "pinned by caller"}
        bp.record(decision)

    if backend == "numpy":
        if _NP is None:
            decision = dict(decision, chosen="pure",
                            reason=decision["reason"] + "; numpy gone at runtime")
            bp.record(decision)
            backend = "pure"
        else:
            try:
                states = _integrate_numpy(initial, masses, norm, duration, steps)
            except Exception as e:          # gate 6: degrade, don't deceive
                decision = dict(decision, chosen="pure",
                                reason=decision["reason"] + f"; numpy raised {e}")
                bp.record(decision)
                backend = "pure"
                states = _integrate_pure(initial, masses, norm, duration, steps)
    if backend == "pure":
        states = _integrate_pure(initial, masses, norm, duration, steps)
    return SimResult(masses, norm, states, backend, decision)


# ------------------------------------------------- analytic rulers (selftest)
def _close(got, want, tol):
    return all(abs(g - w) <= tol for g, w in zip(got, want))


def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    # R1 projectile parabola
    g, t = 9.8, 1.234
    r = simulate_system([{"mass": 2.0, "position": [1.0, -2.0],
                          "velocity": [10.0, 20.0]}],
                        [{"type": "uniform_acceleration",
                          "acceleration": [0.0, -g]}], t, 2000, "pure")
    want("ruler:projectile",
         _close(r.states[-1], [1 + 10 * t, -2 + 20 * t - .5 * g * t * t,
                               10.0, 20 - g * t], 1e-8))
    # R2 drag exponential
    c, m, t = 1.5, 2.0, 0.9
    k = c / m
    r = simulate_system([{"mass": m, "position": [0.0, 0.0],
                          "velocity": [4.0, 0.0]}],
                        [{"type": "linear_drag", "coefficient": c}],
                        t, 2000, "pure")
    e = math.exp(-k * t)
    want("ruler:drag",
         _close(r.states[-1], [4 * (1 - e) / k, 0.0, 4 * e, 0.0], 1e-8))
    # R3 spring harmonic
    kk, m, t = 8.0, 2.0, 1.1
    w = math.sqrt(kk / m)
    r = simulate_system([{"mass": m, "position": [0.6, 0.0],
                          "velocity": [0.0, 0.0]}],
                        [{"type": "spring", "body": 0, "other": None,
                          "anchor": [0.0, 0.0], "stiffness": kk,
                          "rest_length": 0.0, "damping": 0.0}],
                        t, 2000, "pure")
    want("ruler:spring",
         _close(r.states[-1], [0.6 * math.cos(w * t), 0.0,
                               -0.6 * w * math.sin(w * t), 0.0], 1e-8))
    # R4 Kepler circle
    mu, rr, t = 100.0, 5.0, 1.0
    w = math.sqrt(mu / rr ** 3)
    v = math.sqrt(mu / rr)
    r = simulate_system([{"mass": 1e6, "position": [0, 0], "velocity": [0, 0]},
                         {"mass": 1.0, "position": [rr, 0],
                          "velocity": [0.0, v]}],
                        [{"type": "central_gravity", "source": 0,
                          "mu": mu, "bodies": [1]}], t, 4000, "pure")
    want("ruler:kepler",
         _close(r.states[-1][4:], [rr * math.cos(w * t), rr * math.sin(w * t),
                                   -rr * w * math.sin(w * t),
                                   rr * w * math.cos(w * t)], 1e-6))
    # policy: small problems stay on the own tool even with numpy gated
    name, _ = bp.choose("physics", size=10)
    want("policy:small->pure", name == "pure")
    # parity witness when numpy exists
    if _NP is not None:
        want("parity:numpy", _numpy_parity())
    return checks


# ------------------------------------------------------- renderer contract v1
def route_physics_simulation(scene, spec):
    bodies = spec.get("bodies", [])
    if not bodies:
        return None
    res = simulate_system(bodies, spec.get("forces", []),
                          float(spec.get("duration", 4.0)),
                          int(spec.get("steps", 240)))
    from manim import VGroup, Dot, VMobject      # lazy: renderer-only import

    states = res.states
    stride = max(1, len(states) // 60)
    sampled = states[::stride] + [states[-1]]
    peak = 1e-9
    for flat in sampled:
        for i in range(len(res.masses)):
            peak = max(peak, abs(flat[4 * i]), abs(flat[4 * i + 1]))
    scale = float(spec.get("fit", 6.0)) / peak

    mobs = VGroup()
    for i, b in enumerate(bodies):
        pts = [(f[4 * i] * scale, f[4 * i + 1] * scale, 0.0) for f in sampled]
        color = b.get("color", "YELLOW")
        if spec.get("trail", True):
            mobs.add(VMobject(color=color).set_points_smoothly(pts))
        mobs.add(Dot(pts[-1], radius=float(b.get("radius", 0.12)),
                     color=color))
    print(f"[physics] backend={res.backend} ({res.decision.get('reason')})")
    return mobs


ROUTE_TABLE = {"physics_simulation": route_physics_simulation}

if __name__ == "__main__":
    fails = 0
    for name, ok, detail in selftest():
        print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
        fails += 0 if ok else 1
    for size in (500, 50000):
        n, rep = bp.choose("physics", size=size)
        print(f"size={size:>6} -> backend={n:<6} {rep['reason']}")
    sys.exit(1 if fails else 0)
