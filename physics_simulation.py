#!/usr/bin/env python3
"""physics_simulation.py — gen-3 deterministic 2D Newtonian engine.

Layering (xv6-style, top to bottom):
    validation -> force laws -> integrator -> stability guard -> witnesses -> route

Dependency stance (backend_policy, frozen):
    "pure"  = own stdlib tool = THE RULER (list-of-floats RK4/symplectic core)
    "numpy" = select library, adopted only when probe+witness+cost gates pass,
              and only for integrator="rk4"; every other integrator runs pure.

Numerics (Strang, CSE ch.5):
    rk4        4th order, stable for |lambda*dt| <~ 2.78
    leapfrog   velocity-Verlet, symplectic: bounded energy error for Hamiltonians
    euler_semi 1st order symplectic, cheapest
    trapezoid  Crank-Nicolson flavour, A-stable (one fixed-point correction)
  A stability guard computes omega_max from springs/orbits and FAILS CLOSED
  (ValueError) when dt*omega_max leaves the method's region.

Witnesses (Euler closed forms, frozen; run headless in selftest/CI):
    projectile parabola, drag exponential, spring harmonic, Kepler circle,
    energy-drift bound for conservative runs, pure<->numpy parity, determinism.

Renderer contract v1: ROUTE_TABLE["physics_simulation"](scene, spec).
The route skins itself from scene.ctx (StyleContext) when present.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from tools import backend_policy as bp
except Exception:
    try:
        import backend_policy as bp          # type: ignore
    except Exception:
        bp = None

try:
    import numpy as _NP
except Exception:
    _NP = None

INTEGRATORS = ("rk4", "leapfrog", "euler_semi", "trapezoid")
_STABILITY = {"rk4": 2.78, "leapfrog": 2.0, "euler_semi": 2.0,
              "trapezoid": math.inf}          # A-stable: no explicit limit
_ACCEL_THRESHOLD = 2000.0                     # n*steps above which numpy pays


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
            bi, oi = f.get("body"), f.get("other")
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


# ------------------------------------------------- stability guard (Strang)
def _omega_max(masses, initial, forces):
    n = len(masses)
    pos = [(initial[4 * i], initial[4 * i + 1]) for i in range(n)]
    omega = 0.0
    for f in forces:
        if f["type"] == "spring" and f["stiffness"] > 0:
            omega = max(omega, math.sqrt(f["stiffness"] / masses[f["body"]]))
        elif f["type"] == "central_gravity":
            s = f["source"]
            for t in f["bodies"]:
                if t == s:
                    continue
                r = math.hypot(pos[s][0] - pos[t][0], pos[s][1] - pos[t][1])
                if r > 1e-9:
                    omega = max(omega, math.sqrt(f["mu"] / r ** 3))
    return omega


def stability_report(masses, initial, forces, duration, steps, integrator):
    dt = duration / steps
    omega = _omega_max(masses, initial, forces)
    limit = _STABILITY[integrator]
    ratio = omega * dt
    ok = bool(ratio <= limit) if math.isfinite(limit) else True
    return {"integrator": integrator, "dt": dt, "omega_max": omega,
            "limit": limit, "ratio": ratio, "ok": ok}


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


def _step_rk4(s, dt, masses, forces):
    k1 = _deriv_pure(s, masses, forces)
    k2 = _deriv_pure(_axpy(s, 0.5 * dt, k1), masses, forces)
    k3 = _deriv_pure(_axpy(s, 0.5 * dt, k2), masses, forces)
    k4 = _deriv_pure(_axpy(s, dt, k3), masses, forces)
    c = dt / 6.0
    return [s[i] + c * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
            for i in range(len(s))]


def _step_leapfrog(s, dt, masses, forces):          # velocity Verlet
    n = len(masses)
    ax, ay = _accel_pure(s, masses, forces)
    half = [(s[4 * i + 2] + 0.5 * dt * ax[i], s[4 * i + 3] + 0.5 * dt * ay[i])
            for i in range(n)]
    out = list(s)
    for i in range(n):
        out[4 * i] = s[4 * i] + dt * half[i][0]
        out[4 * i + 1] = s[4 * i + 1] + dt * half[i][1]
    ax2, ay2 = _accel_pure(out, masses, forces)
    for i in range(n):
        out[4 * i + 2] = half[i][0] + 0.5 * dt * ax2[i]
        out[4 * i + 3] = half[i][1] + 0.5 * dt * ax2[i]
    return out


def _step_euler_semi(s, dt, masses, forces):         # symplectic Euler
    n = len(masses)
    ax, ay = _accel_pure(s, masses, forces)
    out = list(s)
    for i in range(n):
        vx = s[4 * i + 2] + dt * ax[i]
        vy = s[4 * i + 3] + dt * ay[i]
        out[4 * i + 2] = vx
        out[4 * i + 3] = vy
        out[4 * i] = s[4 * i] + dt * vx
        out[4 * i + 1] = s[4 * i + 1] + dt * vy
    return out


def _step_trapezoid(s, dt, masses, forces):          # Crank-Nicolson flavour
    n = len(masses)
    a1x, a1y = _accel_pure(s, masses, forces)
    pred = list(s)
    for i in range(n):
        pred[4 * i + 2] = s[4 * i + 2] + dt * a1x[i]
        pred[4 * i + 3] = s[4 * i + 3] + dt * a1y[i]
        pred[4 * i] = s[4 * i] + dt * s[4 * i + 2]
        pred[4 * i + 1] = s[4 * i + 1] + dt * s[4 * i + 3]
    a2x, a2y = _accel_pure(pred, masses, forces)
    out = list(s)
    for i in range(n):
        vx = s[4 * i + 2] + 0.5 * dt * (a1x[i] + a2x[i])
        vy = s[4 * i + 3] + 0.5 * dt * (a1y[i] + a2y[i])
        out[4 * i + 2] = vx
        out[4 * i + 3] = vy
        out[4 * i] = s[4 * i] + 0.5 * dt * (s[4 * i + 2] + vx)
        out[4 * i + 1] = s[4 * i + 1] + 0.5 * dt * (s[4 * i + 3] + vy)
    return out


_STEPS = {"rk4": _step_rk4, "leapfrog": _step_leapfrog,
          "euler_semi": _step_euler_semi, "trapezoid": _step_trapezoid}


def _integrate_pure(initial, masses, forces, duration, steps, integrator):
    step = _STEPS[integrator]
    dt = duration / steps
    s = list(initial)
    states = [list(s)]
    for _ in range(steps):
        s = step(s, dt, masses, forces)
        if not all(math.isfinite(v) for v in s):
            raise ValueError(f"Physics simulation diverged ({integrator}).")
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
                mag = (-f["stiffness"] * (L - f["rest_length"])
                       - f["damping"] * rel)
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
        return np.column_stack((st[:, 2:], accel(st))).reshape(-1)

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


# ------------------------------------------------------------------- energy
def energy(masses, flat, forces):
    """Total mechanical energy, or None when the system is non-conservative."""
    n = len(masses)
    ke = 0.0
    for i in range(n):
        ke += 0.5 * masses[i] * (flat[4 * i + 2] ** 2 + flat[4 * i + 3] ** 2)
    pe = 0.0
    pos = [(flat[4 * i], flat[4 * i + 1]) for i in range(n)]
    for f in forces:
        k = f["type"]
        if k == "spring":
            if f["damping"] != 0:
                return None
            b, o = f["body"], f["other"]
            if o is None:
                L = math.hypot(pos[b][0] - f["anchor"][0],
                               pos[b][1] - f["anchor"][1])
            else:
                L = math.hypot(pos[b][0] - pos[o][0], pos[b][1] - pos[o][1])
            pe += 0.5 * f["stiffness"] * (L - f["rest_length"]) ** 2
        elif k == "central_gravity":
            s = f["source"]
            for t in f["bodies"]:
                if t == s:
                    continue
                r = math.hypot(pos[s][0] - pos[t][0], pos[s][1] - pos[t][1])
                if r <= 1e-12:
                    return None
                pe -= masses[t] * f["mu"] / r
        elif k == "uniform_acceleration":
            gx, gy = f["acceleration"]
            for i in f["bodies"]:
                pe -= masses[i] * (gx * pos[i][0] + gy * pos[i][1])
        else:
            return None
    return ke + pe


# ------------------------------------------------------------- backend gates
def _numpy_parity() -> bool:
    if _NP is None:
        return False
    bodies = [{"mass": 1.0, "position": [0, 0], "velocity": [0, 0]},
              {"mass": 2.0, "position": [3, 0], "velocity": [0, 1]},
              {"mass": 1.5, "position": [-2, 1], "velocity": [0.5, -0.5]}]
    forces = [{"type": "uniform_acceleration", "acceleration": [0, -9.8]},
              {"type": "linear_drag", "coefficient": 0.3},
              {"type": "spring", "body": 1, "other": 0, "stiffness": 4.0,
               "rest_length": 1.0, "damping": 0.2},
              {"type": "central_gravity", "source": 0, "mu": 12.0,
               "bodies": [1, 2]}]
    masses, initial, norm = _validate(bodies, forces)
    a = _integrate_pure(initial, masses, norm, 2.0, 300, "rk4")
    b = _integrate_numpy(initial, masses, norm, 2.0, 300)
    return max(abs(x - y) for ra, rb in zip(a, b)
               for x, y in zip(ra, rb)) <= 1e-9


if bp is not None:
    bp.register("physics", bp.OWN_TOOL,
                probe=lambda: (True, "own tool, stdlib only"),
                witness=lambda: True,
                speedup=lambda size: 1.0)
    bp.register("physics", "numpy",
                probe=lambda: bp.probe_import("numpy", ("array", "zeros", "hypot")),
                witness=_numpy_parity,
                speedup=lambda size: size / _ACCEL_THRESHOLD)


# ---------------------------------------------------------------- public API
class SimResult:
    __slots__ = ("masses", "forces", "states", "backend", "integrator",
                 "decision", "stability")

    def __init__(self, masses, forces, states, backend, integrator,
                 decision, stability):
        self.masses, self.forces, self.states = masses, forces, states
        self.backend, self.integrator = backend, integrator
        self.decision, self.stability = decision, stability


def simulate_system(bodies, forces, duration, steps=600,
                    integrator="rk4", backend="auto"):
    duration = _finite_number(duration, "duration", minimum=0.0)
    if duration == 0:
        raise ValueError("duration must be greater than zero.")
    if not isinstance(steps, int) or not 2 <= steps <= 20000:
        raise ValueError("steps must be an integer from 2 through 20000.")
    if integrator not in INTEGRATORS:
        raise ValueError(f"integrator must be one of {INTEGRATORS}.")
    masses, initial, norm = _validate(bodies, forces)

    stab = stability_report(masses, initial, norm, duration, steps, integrator)
    if not stab["ok"]:
        raise ValueError(
            f"stability guard: dt*omega={stab['ratio']:.3f} exceeds "
            f"{integrator} limit {stab['limit']:.2f}; increase steps.")

    size = len(masses) * steps
    if backend == "auto" and bp is not None and integrator == "rk4":
        backend, decision = bp.choose("physics", size=size)
    else:
        backend = "pure" if backend == "auto" else backend
        decision = {"kind": "physics", "size": size, "chosen": backend,
                    "reason": "pinned by caller / non-rk4 integrator"}
        if bp is not None:
            bp.record(decision)

    if backend == "numpy":
        if _NP is None:
            backend = "pure"
            decision = dict(decision, chosen="pure",
                            reason=decision["reason"] + "; numpy gone at runtime")
        else:
            try:
                states = _integrate_numpy(initial, masses, norm, duration, steps)
            except Exception as e:                     # degrade, don't deceive
                backend = "pure"
                decision = dict(decision, chosen="pure",
                                reason=decision["reason"] + f"; numpy raised {e}")
                states = _integrate_pure(initial, masses, norm, duration,
                                         steps, integrator)
    if backend == "pure":
        states = _integrate_pure(initial, masses, norm, duration, steps,
                                 integrator)
    return SimResult(masses, norm, states, backend, integrator, decision, stab)


# ------------------------------------------------------ renderer contract v1
def route_physics_simulation(scene, spec):
    from manim import VGroup, Dot, VMobject, Arrow      # lazy: renderer-only

    bodies = spec.get("bodies", [])
    if not bodies:
        return None
    res = simulate_system(bodies, spec.get("forces", []),
                          float(spec.get("duration", 4.0)),
                          int(spec.get("steps", 240)),
                          integrator=spec.get("integrator", "rk4"))
    ctx = getattr(scene, "ctx", None)
    col = ctx.color(spec, "primary") if ctx else spec.get("color", "YELLOW")
    acc = ctx.color(spec, "accent") if ctx else "RED"
    stroke = ctx.stroke() if ctx else 3.0
    radius = ctx.dot(spec) if ctx else float(spec.get("radius", 0.12))

    states = res.states
    stride = max(1, len(states) // 60)
    sampled = states[::stride] + [states[-1]]
    n = len(res.masses)
    peak = 1e-9
    for flat in sampled:
        for i in range(n):
            peak = max(peak, abs(flat[4 * i]), abs(flat[4 * i + 1]))
    scale = float(spec.get("fit", 6.0)) / peak

    mobs = VGroup()
    for i, b in enumerate(bodies):
        pts = [(f[4 * i] * scale, f[4 * i + 1] * scale, 0.0) for f in sampled]
        if spec.get("trail", True):
            mobs.add(VMobject(color=col, stroke_width=stroke)
                     .set_points_smoothly(pts))
        mobs.add(Dot(pts[-1], radius=radius, color=col))
        if spec.get("vectors"):
            v = sampled[-1]
            mobs.add(Arrow(pts[-1],
                           (pts[-1][0] + v[4 * i + 2] * scale * 0.2,
                            pts[-1][1] + v[4 * i + 3] * scale * 0.2, 0.0),
                           buff=0, color=acc, stroke_width=stroke))
    print(f"[physics] backend={res.backend} integrator={res.integrator} "
          f"dt*w={res.stability['ratio']:.3f} ({res.decision.get('reason')})")
    return mobs


ROUTE_TABLE = {"physics_simulation": route_physics_simulation}


# ---------------------------------------------------- frozen witness suite
def _close(got, want, tol):
    return all(abs(g - w) <= tol for g, w in zip(got, want))


def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    g, t = 9.8, 1.234
    r = simulate_system([{"mass": 2.0, "position": [1, -2], "velocity": [10, 20]}],
                        [{"type": "uniform_acceleration",
                          "acceleration": [0, -g]}], t, 2000, "rk4", "pure")
    want("ruler:projectile",
         _close(r.states[-1], [1 + 10 * t, -2 + 20 * t - .5 * g * t * t,
                               10.0, 20 - g * t], 1e-8))

    c, m, t = 1.5, 2.0, 0.9
    k = c / m
    e = math.exp(-k * t)
    r = simulate_system([{"mass": m, "position": [0, 0], "velocity": [4, 0]}],
                        [{"type": "linear_drag", "coefficient": c}],
                        t, 2000, "trapezoid", "pure")
    want("ruler:drag(trapezoid)",
         _close(r.states[-1], [4 * (1 - e) / k, 0.0, 4 * e, 0.0], 1e-7))

    kk, m, t = 8.0, 2.0, 1.1
    w = math.sqrt(kk / m)
    r = simulate_system([{"mass": m, "position": [0.6, 0], "velocity": [0, 0]}],
                        [{"type": "spring", "body": 0, "other": None,
                          "anchor": [0, 0], "stiffness": kk,
                          "rest_length": 0.0, "damping": 0.0}],
                        t, 2000, "rk4", "pure")
    want("ruler:spring",
         _close(r.states[-1], [0.6 * math.cos(w * t), 0.0,
                               -0.6 * w * math.sin(w * t), 0.0], 1e-8))

    mu, rr, t = 100.0, 5.0, 1.0
    w = math.sqrt(mu / rr ** 3)
    v = math.sqrt(mu / rr)
    r = simulate_system([{"mass": 1e6, "position": [0, 0], "velocity": [0, 0]},
                         {"mass": 1.0, "position": [rr, 0], "velocity": [0, v]}],
                        [{"type": "central_gravity", "source": 0, "mu": mu,
                          "bodies": [1]}], t, 4000, "leapfrog", "pure")
    want("ruler:kepler(leapfrog)",
         _close(r.states[-1][4:], [rr * math.cos(w * t), rr * math.sin(w * t),
                                   -rr * w * math.sin(w * t),
                                   rr * w * math.cos(w * t)], 1e-6))

    bodies = [{"mass": 1.0, "position": [0.6, 0], "velocity": [0, 0.9]}]
    forces = [{"type": "spring", "body": 0, "other": None, "anchor": [0, 0],
               "stiffness": 4.0, "rest_length": 0.0, "damping": 0.0}]
    r = simulate_system(bodies, forces, 5.0, 2000, "leapfrog", "pure")
    e0 = energy(r.masses, r.states[0], r.forces)
    e1 = energy(r.masses, r.states[-1], r.forces)
    want("energy:leapfrog-drift", e0 is not None and abs(e1 - e0) <= 1e-4 * abs(e0),
         f"E0={e0} E1={e1}")

    try:
        simulate_system(bodies, forces, 5.0, 8, "leapfrog", "pure")
        want("guard:stability-fails-closed", False, "no ValueError raised")
    except ValueError:
        want("guard:stability-fails-closed", True)

    a = simulate_system(bodies, forces, 1.0, 300, "rk4", "pure").states
    b = simulate_system(bodies, forces, 1.0, 300, "rk4", "pure").states
    want("determinism:pure", a == b)

    if _NP is not None:
        want("parity:numpy", _numpy_parity())
    else:
        want("parity:numpy", True, "skipped (numpy absent)")
    return checks


if __name__ == "__main__":
    fails = 0
    for name, ok, detail in selftest():
        print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
        fails += 0 if ok else 1
    if bp is not None:
        for size in (500, 50000):
            n, rep = bp.choose("physics", size=size)
            print(f"size={size:>6} -> backend={n:<6} {rep['reason']}")
    sys.exit(1 if fails else 0)
