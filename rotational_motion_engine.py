#!/usr/bin/env python3
"""rotational_motion_engine.py — gen-3 rigid-body rotation core + visuals.

Layering (xv6-style): validation -> closed-form kinematics (THE RULER)
-> independent theorem witnesses -> adaptive manim route (lazy import).

Dependency stance (tools/backend_policy):
  * pure stdlib closed forms = ruler; nothing here needs numpy to be RIGHT
  * numpy = select library for vectorized trajectory sampling only
    (kind="rotational"), admitted after probe + parity witness + cost gate

Frozen witnesses (selftest, headless, no manim/numpy):
  * parallel-axis theorem:  I(rod_end) = I(rod_center) + m (L/2)^2
  * dm integration (Simpson, own tool):  disk -> m R^2 / 2, rod -> m L^2 / 12
  * work-energy:  tau * dtheta = 1/2 I (w^2 - w0^2)
  * power:        dK/dt = tau * w          * torque: dL/dt = tau
  * Newton I for rotation: tau = 0 => w constant, theta linear
  * pure <-> numpy parity; determinism; guards raise

Renderer contract v1: ROUTE_TABLE["rotational_motion"](scene, spec).
The updater reads state_at(t) — closed form, no hidden state (A2).
Look comes from scene.ctx (style genome); spec colors remain overrides.
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

SHAPES = ("solid_disk", "solid_cylinder", "hoop", "thin_ring",
          "rod_center", "rod_end")


# ---------------------------------------------------------------- validation
def _finite(value, name):
    try:
        out = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"{name} must be a finite number.") from e
    if not math.isfinite(out):
        raise ValueError(f"{name} must be a finite number.")
    return out


def _positive(value, name):
    out = _finite(value, name)
    if out <= 0:
        raise ValueError(f"{name} must be positive.")
    return out


# ------------------------------------------------------- inertia (the table)
def moment_of_inertia(shape, *, mass, radius=None, length=None):
    """I about the standard axis for common rigid bodies (pure, O(1))."""
    m = _positive(mass, "mass")
    s = str(shape).lower()
    if s in ("solid_disk", "solid_cylinder"):
        r = _positive(radius, "radius")
        return 0.5 * m * r * r
    if s in ("hoop", "thin_ring"):
        r = _positive(radius, "radius")
        return m * r * r
    if s in ("rod_center", "rod_end"):
        L = _positive(length, "length")
        return m * L * L * (1 / 12 if s == "rod_center" else 1 / 3)
    raise ValueError(f"shape must be one of {SHAPES}.")


# ------------------------------------------- independent dm integration ruler
def _simpson(f, a, b, n=200):
    if n % 2:
        n += 1
    h = (b - a) / n
    total = f(a) + f(b)
    for i in range(1, n):
        total += f(a + i * h) * (4 if i % 2 else 2)
    return total * h / 3


def inertia_from_dm(kind, *, mass, radius=None, length=None):
    """Integrate r^2 dm from first principles — witness for the table."""
    m = _positive(mass, "mass")
    if kind == "solid_disk":
        R = _positive(radius, "radius")
        return _simpson(lambda r: r * r * (2 * m * r / (R * R)), 0.0, R)
    if kind in ("rod_center", "rod_end"):
        L = _positive(length, "length")
        if kind == "rod_center":
            return _simpson(lambda x: x * x * (m / L), -L / 2, L / 2)
        return _simpson(lambda x: x * x * (m / L), 0.0, L)
    raise ValueError("inertia_from_dm supports solid_disk, rod_center, rod_end.")


# ------------------------------------------------- kinematics (closed forms)
def angular_acceleration(net_torque, inertia):
    return _finite(net_torque, "net_torque") / _positive(inertia, "inertia")


def angular_velocity(w0, alpha, t):
    t = _finite(t, "time")
    if t < 0:
        raise ValueError("time must be non-negative.")
    return _finite(w0, "initial_angular_velocity") + _finite(alpha, "alpha") * t


def angular_displacement(theta0, w0, alpha, t):
    t = _finite(t, "time")
    if t < 0:
        raise ValueError("time must be non-negative.")
    return (_finite(theta0, "initial_angle")
            + _finite(w0, "initial_angular_velocity") * t
            + 0.5 * _finite(alpha, "alpha") * t * t)


def rotational_kinetic_energy(inertia, omega):
    return 0.5 * _positive(inertia, "inertia") * _finite(omega, "omega") ** 2


def angular_momentum(inertia, omega):
    return _positive(inertia, "inertia") * _finite(omega, "omega")


def state_at(theta0, w0, alpha, t):
    """One pure call = full rigid-body state. The updater's only source."""
    w = angular_velocity(w0, alpha, t)
    return {
        "t": t,
        "theta": angular_displacement(theta0, w0, alpha, t),
        "omega": w,
        "alpha": alpha,
    }


# ------------------------------------------------ trajectory sampling (gate)
def _traj_pure(theta0, w0, alpha, duration, n):
    dt = duration / n
    return [(i * dt,
             angular_displacement(theta0, w0, alpha, i * dt),
             angular_velocity(w0, alpha, i * dt)) for i in range(n + 1)]


def _traj_numpy(theta0, w0, alpha, duration, n):
    np = _NP
    ts = np.linspace(0.0, duration, n + 1)
    th = theta0 + w0 * ts + 0.5 * alpha * ts * ts
    om = w0 + alpha * ts
    return [(float(a), float(b), float(c)) for a, b, c in zip(ts, th, om)]


def _numpy_parity():
    if _NP is None:
        return False
    a = _traj_pure(0.3, 1.1, -0.7, 4.0, 256)
    b = _traj_numpy(0.3, 1.1, -0.7, 4.0, 256)
    return max(abs(x - y) for ra, rb in zip(a, b)
               for x, y in zip(ra, rb)) <= 1e-12


if bp is not None:
    bp.register("rotational", bp.OWN_TOOL,
                probe=lambda: (True, "own tool, stdlib only"),
                witness=lambda: True,
                speedup=lambda size: 1.0)
    bp.register("rotational", "numpy",
                probe=lambda: bp.probe_import("numpy", ("linspace",)),
                witness=_numpy_parity,
                speedup=lambda size: size / 512.0)


def sample_trajectory(theta0, w0, alpha, duration, n=128):
    n = int(_finite(n, "samples"))
    if not 2 <= n <= 4096:
        raise ValueError("samples must be an integer 2..4096.")
    duration = _positive(duration, "duration")
    backend = "pure"
    if bp is not None:
        name, _ = bp.choose("rotational", size=n)
        backend = name if (name == "numpy" and _NP is not None) else "pure"
    if backend == "numpy":
        try:
            return _traj_numpy(theta0, w0, alpha, duration, n), backend
        except Exception:
            backend = "pure"
    return _traj_pure(theta0, w0, alpha, duration, n), backend


# ------------------------------------------------------- manim route (lazy)
def route_rotational(scene, spec):
    from manim import (Arrow, Circle, Dot, Line, Text, ValueTracker,
                       VGroup, always_redraw)

    if not isinstance(spec, dict):
        raise ValueError("rotational_motion visual must be an object.")
    ctx = getattr(scene, "ctx", None)
    shape = str(spec.get("shape", "solid_disk")).lower()
    mass = _positive(spec.get("mass", 1.0), "mass")
    radius = _positive(spec.get("radius", 1.0), "radius")
    length = _positive(spec.get("length", 2.0 * radius), "length")
    inertia = moment_of_inertia(shape, mass=mass, radius=radius, length=length)
    w0 = _finite(spec.get("angular_velocity", 1.0), "angular_velocity")
    torque = _finite(spec.get("torque", 0.0), "torque")
    alpha = angular_acceleration(torque, inertia)
    th0 = _finite(spec.get("initial_angle", 0.0), "initial_angle")
    dur = _positive(spec.get("duration", 4.0), "duration")
    center = list(spec.get("center", [0.0, 0.0, 0.0]))
    center = [float(c) for c in (center + [0.0] * 3)[:3]]
    disp_r = _positive(spec.get("display_radius",
                                min(1.5, max(0.75, radius))), "display_radius")

    col_body = spec.get("color") or (ctx.color(spec, "primary") if ctx else "#4CC9F0")
    col_spoke = ctx.color(spec, "accent") if ctx else "#F1C40F"
    col_mark = ctx.color(spec, "alert") if ctx else "#FF4B4B"
    col_vel = ctx.color(spec, "secondary") if ctx else "#80ED99"
    col_ink = ctx.color(spec, "ink") if ctx else "#F2F3F5"
    fs = ctx.font(18) if ctx else 18
    sw = ctx.stroke() if ctx else 3.0

    tracker = spec.get("tracker")
    if tracker is None:
        tracker = ValueTracker(0.0)
        if ctx is not None:
            try:
                scene.play(tracker.animate.set_value(dur),
                           run_time=ctx.run_time(min(4.0, dur)),
                           rate_func=ctx.rate_func())
            except Exception:
                pass
        else:
            tracker.set_value(dur)

    def st():
        return state_at(th0, w0, alpha, tracker.get_value())

    if shape in ("rod_center", "rod_end"):
        def body():
            ang = st()["theta"]
            d = [math.cos(ang), math.sin(ang), 0.0]
            if shape == "rod_end":
                a = center
                b = [center[i] + d[i] * 2 * disp_r for i in range(3)]
            else:
                a = [center[i] - d[i] * disp_r for i in range(3)]
                b = [center[i] + d[i] * disp_r for i in range(3)]
            return Line(a, b, color=col_body, stroke_width=sw + 4)
        body_mob = always_redraw(body)
    else:
        body_mob = Circle(radius=disp_r, color=col_body, fill_color=col_body,
                          fill_opacity=0.12 if shape.startswith(("solid",)) else 0,
                          stroke_width=sw).move_to(center)

    def spoke():
        ang = st()["theta"]
        r = disp_r * (2 if shape == "rod_end" else 1)
        return Line(center, [center[0] + r * math.cos(ang),
                             center[1] + r * math.sin(ang), 0.0],
                    color=col_spoke, stroke_width=sw - 1)

    def marker():
        ang = st()["theta"]
        r = disp_r * (2 if shape == "rod_end" else 1)
        return Dot([center[0] + r * math.cos(ang),
                    center[1] + r * math.sin(ang), 0.0],
                   radius=(ctx.dot(spec) if ctx else 0.10) * 1.4, color=col_mark)

    def velocity_arrow():
        s = st()
        ang = s["theta"]
        r = disp_r * (2 if shape == "rod_end" else 1)
        p = [center[0] + r * math.cos(ang), center[1] + r * math.sin(ang), 0.0]
        tang = [-math.sin(ang), math.cos(ang), 0.0]
        mag = s["omega"] * r * 0.18
        if abs(mag) < 1e-8:
            return Dot(p, radius=0.03, color=col_vel)
        return Arrow(p, [p[i] + tang[i] * mag for i in range(3)], buff=0,
                     color=col_vel, stroke_width=sw - 1,
                     max_tip_length_to_length_ratio=0.25)

    # adaptive label set: show only cues the physics makes meaningful
    labels = VGroup()
    rows = [f"I = {inertia:g} kg·m²"]
    if torque:
        rows.append(f"τ = {torque:g} N·m   α = {alpha:g} rad/s²")
    live = always_redraw(lambda: Text(
        f"ω = {st()['omega']:.2f} rad/s   θ = {st()['theta']:.2f} rad"
        + (f"   K = {rotational_kinetic_energy(inertia, st()['omega']):.2f} J"
           if spec.get("show_energy", bool(torque or w0)) else ""),
        font_size=fs - 1, color=col_ink)
        .move_to([center[0], center[1] - disp_r - 1.0, 0.0]))
    for k, row in enumerate(rows):
        labels.add(Text(row, font_size=fs, color=col_ink)
                   .move_to([center[0], center[1] - disp_r - 0.55 - 0.45 * k, 0.0]))

    print(f"[rotational] shape={shape} I={inertia:g} alpha={alpha:g} "
          f"backend-aware samples on request")
    return VGroup(body_mob, always_redraw(spoke), always_redraw(marker),
                  always_redraw(velocity_arrow),
                  Dot(center, radius=0.11, color=col_ink), labels, live)


class _NullScene:
    ctx = None


def build_rotational_visual(item, time_tracker=None):
    """Legacy-compatible entry point."""
    spec = dict(item)
    if time_tracker is not None:
        spec["tracker"] = time_tracker
    return route_rotational(_NullScene(), spec)


ROUTE_TABLE = {"rotational_motion": route_rotational}


# ------------------------------------------------------------ frozen witness
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    m, R, L = 2.0, 0.5, 1.2
    want("ruler:parallel-axis",
         abs(moment_of_inertia("rod_end", mass=m, length=L)
             - (moment_of_inertia("rod_center", mass=m, length=L)
                + m * (L / 2) ** 2)) <= 1e-12)
    want("ruler:dm-disk",
         abs(inertia_from_dm("solid_disk", mass=m, radius=R)
             - 0.5 * m * R * R) <= 1e-9)
    want("ruler:dm-rod",
         abs(inertia_from_dm("rod_center", mass=m, length=L)
             - m * L * L / 12) <= 1e-9)

    I = moment_of_inertia("solid_disk", mass=m, radius=R)
    w0, tau, t = 1.5, 0.8, 2.0
    al = angular_acceleration(tau, I)
    dth = angular_displacement(0.0, w0, al, t)
    wt = angular_velocity(w0, al, t)
    want("witness:work-energy",
         abs(tau * dth - 0.5 * I * (wt ** 2 - w0 ** 2)) <= 1e-9)
    h = 1e-5
    K = lambda tt: rotational_kinetic_energy(I, angular_velocity(w0, al, tt))
    Lm = lambda tt: angular_momentum(I, angular_velocity(w0, al, tt))
    want("witness:power", abs((K(t + h) - K(t - h)) / (2 * h) - tau * wt) <= 1e-6)
    want("witness:dL/dt=tau", abs((Lm(t + h) - Lm(t - h)) / (2 * h) - tau) <= 1e-6)
    want("witness:newton-I",
         angular_velocity(2.0, 0.0, 9.0) == 2.0
         and abs(angular_displacement(1.0, 2.0, 0.0, 3.0) - 7.0) <= 1e-12)

    a, _ = sample_trajectory(0.0, w0, al, 2.0, 64)
    b, _ = sample_trajectory(0.0, w0, al, 2.0, 64)
    want("determinism:trajectory", a == b)
    if _NP is not None:
        want("parity:numpy", _numpy_parity())
    else:
        want("parity:numpy", True, "skipped (numpy absent)")
    for bad, label in ((dict(shape="nope", mass=1), "shape"),
                       (dict(shape="hoop", mass=-1, radius=1), "mass"),
                       ):
        try:
            moment_of_inertia(bad["shape"], mass=bad["mass"], radius=1)
            want(f"guard:{label}", False)
        except ValueError:
            want(f"guard:{label}", True)
    try:
        angular_velocity(1, 1, -1)
        want("guard:negative-time", False)
    except ValueError:
        want("guard:negative-time", True)
    return checks


if __name__ == "__main__":
    fails = 0
    for name, ok, detail in selftest():
        print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
        fails += 0 if ok else 1
    sys.exit(1 if fails else 0)
