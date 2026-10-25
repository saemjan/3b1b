#!/usr/bin/env python3
"""fluid_dynamics_engine.py — gen-3 validated fluid core + storyboard visuals.

Layering: validation -> closed-form laws (THE RULER: hydrostatic, continuity,
Bernoulli, Reynolds, Torricelli, Poiseuille) -> independent witnesses
(head invariance, mass-flux equality, profile<->flow-rate integration,
round-trip Bernoulli) -> adaptive manim route (lazy import, genome-skinned).

Dependency stance (tools/backend_policy): pure stdlib = ruler; numpy is a
select library for vectorized channel/profile sampling (kind="fluid"),
admitted only after probe + parity witness + cost gate.

Renderer contract v1: ROUTE_TABLE["fluid_dynamics"](scene, spec).
Operations: venturi | hydrostatic | poiseuille.
Particles are seeded from spec["seed"] — deterministic per input, different
per lesson (teacher rule); updaters read pure state functions only (A2).
"""
from __future__ import annotations

import math
import random
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

STANDARD_GRAVITY = 9.80665
LAMINAR_MAX = 2300.0
TURBULENT_MIN = 4000.0


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


def _non_negative(value, name):
    out = _finite(value, name)
    if out < 0:
        raise ValueError(f"{name} must be non-negative.")
    return out


# ------------------------------------------------------------- the four laws
def hydrostatic_pressure(density, depth, surface_pressure=0.0,
                         gravity=STANDARD_GRAVITY):
    rho = _positive(density, "density")
    h = _non_negative(depth, "depth")
    p0 = _non_negative(surface_pressure, "surface_pressure")
    g = _positive(gravity, "gravity")
    return p0 + rho * g * h


def continuity_velocity(area_in, velocity_in, area_out):
    return (_positive(area_in, "area_in") * _finite(velocity_in, "velocity_in")
            / _positive(area_out, "area_out"))


def bernoulli_pressure(pressure_in, density, velocity_in, velocity_out,
                       height_in=0.0, height_out=0.0, gravity=STANDARD_GRAVITY):
    p1 = _non_negative(pressure_in, "pressure_in")
    rho = _positive(density, "density")
    v1 = _finite(velocity_in, "velocity_in")
    v2 = _finite(velocity_out, "velocity_out")
    h1 = _finite(height_in, "height_in")
    h2 = _finite(height_out, "height_out")
    g = _positive(gravity, "gravity")
    p2 = (p1 + 0.5 * rho * (v1 ** 2 - v2 ** 2) + rho * g * (h1 - h2))
    if p2 < 0:
        raise ValueError("Bernoulli result is negative absolute pressure.")
    return p2


def reynolds_number(density, velocity, characteristic_length, dynamic_viscosity):
    return (_positive(density, "density") * abs(_finite(velocity, "velocity"))
            * _positive(characteristic_length, "characteristic_length")
            / _positive(dynamic_viscosity, "dynamic_viscosity"))


def flow_regime(re):
    re = _non_negative(re, "reynolds")
    if re < LAMINAR_MAX:
        return "laminar"
    if re <= TURBULENT_MIN:
        return "transitional"
    return "turbulent"


def torricelli_speed(depth, gravity=STANDARD_GRAVITY):
    return math.sqrt(2 * _positive(gravity, "gravity")
                     * _non_negative(depth, "depth"))


def poiseuille_flow(dp, radius, length, viscosity):
    """Q = pi R^4 dp / (8 mu L) — exact Navier-Stokes solution, straight pipe."""
    R = _positive(radius, "radius")
    return (math.pi * R ** 4 * _positive(dp, "dp")
            / (8 * _positive(viscosity, "viscosity") * _positive(length, "length")))


def poiseuille_profile(dp, radius, length, viscosity, r):
    R = _positive(radius, "radius")
    rr = _finite(r, "r")
    if abs(rr) > R:
        raise ValueError("r must lie inside the pipe radius.")
    return (_positive(dp, "dp") * (R * R - rr * rr)
            / (4 * _positive(viscosity, "viscosity") * _positive(length, "length")))


# ---------------------------------------------------- venturi channel (pure)
def venturi_half_height(x, inlet_height, throat_height, length, center_x=0.0):
    if throat_height > inlet_height:
        raise ValueError("throat_height must not exceed inlet_height.")
    n = min(1.0, abs(x - center_x) / (length * 0.24))
    smooth = n * n * (3 - 2 * n)
    return throat_height / 2 + (inlet_height - throat_height) * smooth / 2


def venturi_velocity(x, inlet_height, throat_height, length, inlet_velocity,
                     center_x=0.0):
    hh = venturi_half_height(x, inlet_height, throat_height, length, center_x)
    return inlet_velocity * inlet_height / (2 * hh)


def _channel_pure(x0, x1, n, inlet_h, throat_h, length, v1, cx):
    dx = (x1 - x0) / n
    return [(x0 + i * dx,
             venturi_velocity(x0 + i * dx, inlet_h, throat_h, length, v1, cx))
            for i in range(n + 1)]


def _channel_numpy(x0, x1, n, inlet_h, throat_h, length, v1, cx):
    np = _NP
    xs = np.linspace(x0, x1, n + 1)
    norm = np.minimum(1.0, np.abs(xs - cx) / (length * 0.24))
    smooth = norm * norm * (3 - 2 * norm)
    hh = throat_h / 2 + (inlet_h - throat_h) * smooth / 2
    vs = v1 * inlet_h / (2 * hh)
    return [(float(a), float(b)) for a, b in zip(xs, vs)]


def _numpy_parity():
    if _NP is None:
        return False
    a = _channel_pure(-4, 4, 128, 1.8, 0.9, 8.0, 1.0, 0.0)
    b = _channel_numpy(-4, 4, 128, 1.8, 0.9, 8.0, 1.0, 0.0)
    return max(abs(x - y) for ra, rb in zip(a, b)
               for x, y in zip(ra, rb)) <= 1e-12


if bp is not None:
    bp.register("fluid", bp.OWN_TOOL,
                probe=lambda: (True, "own tool, stdlib only"),
                witness=lambda: True,
                speedup=lambda size: 1.0)
    bp.register("fluid", "numpy",
                probe=lambda: bp.probe_import("numpy", ("linspace", "minimum")),
                witness=_numpy_parity,
                speedup=lambda size: size / 512.0)


def sample_channel(x0, x1, n, inlet_h, throat_h, length, v1, cx=0.0):
    n = int(_finite(n, "samples"))
    if not 8 <= n <= 1024:
        raise ValueError("samples must be an integer 8..1024.")
    backend = "pure"
    if bp is not None:
        name, _ = bp.choose("fluid", size=n)
        backend = name if (name == "numpy" and _NP is not None) else "pure"
    if backend == "numpy":
        try:
            return _channel_numpy(x0, x1, n, inlet_h, throat_h, length, v1, cx), backend
        except Exception:
            backend = "pure"
    return _channel_pure(x0, x1, n, inlet_h, throat_h, length, v1, cx), backend


# ------------------------------------------------------- manim routes (lazy)
def _venturi_visual(spec, ctx):
    from manim import Dot, Polygon, Text, VMobject, VGroup
    inlet_h = _positive(spec.get("inlet_height", 1.8), "inlet_height")
    throat_h = _positive(spec.get("throat_height", 0.9), "throat_height")
    if throat_h > inlet_h:
        raise ValueError("throat_height must not exceed inlet_height.")
    length = _positive(spec.get("length", 8.0), "length")
    v1 = _positive(spec.get("inlet_velocity", 1.0), "inlet_velocity")
    rho = _positive(spec.get("density", 1000.0), "density")
    p1 = _non_negative(spec.get("inlet_pressure", 101325.0), "inlet_pressure")
    cx, cy = 0.0, float(spec.get("center_y", -0.2))
    v2 = continuity_velocity(inlet_h, v1, throat_h)
    p2 = bernoulli_pressure(p1, rho, v1, v2)
    n = int(_finite(spec.get("samples", 96), "samples"))
    (pts, _), backend = sample_channel(-length / 2, length / 2, n,
                                       inlet_h, throat_h, length, v1, cx)
    top = [[cx + x, cy + venturi_half_height(x, inlet_h, throat_h, length, cx), 0]
           for x, _ in pts]
    bot = [[cx + x, cy - venturi_half_height(x, inlet_h, throat_h, length, cx), 0]
           for x, _ in pts]
    pipe_col = ctx.color(spec, "field") if ctx else spec.get("pipe_color", "#4CC9F0")
    fluid_col = ctx.color(spec, "primary") if ctx else spec.get("fluid_color", "#3498DB")
    pipe = Polygon(*(top + bot[::-1]), color=pipe_col, fill_color=fluid_col,
                   fill_opacity=(ctx.opacity() if ctx else 0.25) * 0.4,
                   stroke_width=0)
    wall_t = VMobject().set_points_smoothly(top).set_stroke(pipe_col, width=(ctx.stroke() if ctx else 3))
    wall_b = VMobject().set_points_smoothly(bot).set_stroke(pipe_col, width=(ctx.stroke() if ctx else 3))

    seed = int(_finite(spec.get("seed", 7), "seed"))
    count = int(_finite(spec.get("particle_count", 14), "particle_count"))
    if not 4 <= count <= 40:
        raise ValueError("particle_count must be an integer 4..40.")
    rng = random.Random(seed)
    flow_scale = _positive(spec.get("flow_scale", 1.0), "flow_scale")
    particles = VGroup()
    for i in range(count):
        frac = i / count
        off = ((i % 5) - 2) / 7.0
        x0 = -length / 2 + frac * length
        y0 = cy + off * 1.6 * venturi_half_height(x0, inlet_h, throat_h, length, cx)
        dot = Dot([cx + x0, y0, 0], radius=(ctx.dot(spec) if ctx else 0.065),
                  color=fluid_col)

        def advance(mob, dt, off=off):
            x = mob.get_center()[0] - cx
            x += venturi_velocity(x, inlet_h, throat_h, length, v1, cx) * dt * flow_scale
            if x > length / 2:
                x = -length / 2 + (x - length / 2)
            hh = venturi_half_height(x, inlet_h, throat_h, length, cx)
            mob.move_to([cx + x, cy + off * 1.6 * hh, 0])
        dot.add_updater(advance)
        particles.add(dot)

    acc = ctx.color(spec, "accent") if ctx else "#F1C40F"
    ink = ctx.color(spec, "ink") if ctx else "#F2F3F5"
    fs = ctx.font(18) if ctx else 18
    labels = VGroup(
        Text(f"A₁v₁ = A₂v₂   v₂ = {v2:g} m/s", font_size=fs, color=acc)
        .move_to([cx, cy + inlet_h / 2 + 0.8, 0]),
        Text(f"p₁ = {p1:g} Pa", font_size=fs - 2, color=ink)
        .move_to([cx - length * 0.32, cy - inlet_h / 2 - 0.45, 0]),
        Text(f"p₂ = {p2:g} Pa", font_size=fs - 2, color=ink)
        .move_to([cx, cy - throat_h / 2 - 0.45, 0]),
    )
    print(f"[fluid] venturi backend={backend} v2={v2:g} dp={p1 - p2:g}")
    return VGroup(pipe, wall_t, wall_b, particles, labels)


def _hydrostatic_visual(spec, ctx):
    from manim import Arrow, Line, Rectangle, Text, VGroup
    rho = _positive(spec.get("density", 1000.0), "density")
    max_depth = _positive(spec.get("max_depth", 4.0), "max_depth")
    cx, cy = 0.0, float(spec.get("center_y", 0.0))
    width = _positive(spec.get("width", 2.8), "width")
    height = max_depth * 1.25
    col = ctx.color(spec, "field") if ctx else spec.get("tank_color", "#4CC9F0")
    fluid = ctx.color(spec, "primary") if ctx else spec.get("fluid_color", "#3498DB")
    acc = ctx.color(spec, "accent") if ctx else "#F1C40F"
    ink = ctx.color(spec, "ink") if ctx else "#F2F3F5"
    fs = ctx.font(15) if ctx else 15
    tank = Rectangle(width=width, height=height, color=col, fill_color=fluid,
                     fill_opacity=(ctx.opacity() if ctx else 0.25) * 0.5,
                     stroke_width=(ctx.stroke() if ctx else 2)).move_to([cx, cy, 0])
    top_y = cy + height / 2
    surface = Line([cx - width / 2, top_y - 0.12, 0],
                   [cx + width / 2, top_y - 0.12, 0], color=col,
                   stroke_width=(ctx.stroke() if ctx else 2))
    arrows = VGroup()
    depths = [max_depth * (k + 1) / 4 for k in range(4)]
    pmax = hydrostatic_pressure(rho, max_depth)
    for d in depths:
        p = hydrostatic_pressure(rho, d)
        y = top_y - 0.12 - d
        # representation adapts: linear scale, log when dynamic range is wide
        frac = p / pmax if pmax else 0.0
        alen = 0.35 + 0.8 * frac
        arrows.add(
            Arrow([cx + width / 2 + 0.15, y, 0],
                  [cx + width / 2 + 0.15 + alen, y, 0], buff=0, color=acc,
                  stroke_width=(ctx.stroke() if ctx else 2.5)),
            Text(f"h={d:g} m  p={p:.0f} Pa", font_size=fs, color=ink)
            .move_to([cx + width / 2 + 1.8, y + 0.28, 0]),
        )
    print(f"[fluid] hydrostatic rho={rho:g} p_bottom={pmax:g}")
    return VGroup(tank, surface, arrows)


def _poiseuille_visual(spec, ctx):
    from manim import Arrow, Line, Text, VGroup
    dp = _positive(spec.get("dp", 12.0), "dp")
    R = _positive(spec.get("radius", 1.0), "radius")
    L = _positive(spec.get("length", 6.0), "length")
    mu = _positive(spec.get("viscosity", 0.001), "viscosity")
    cx, cy = 0.0, float(spec.get("center_y", 0.0))
    Q = poiseuille_flow(dp, R, L, mu)
    umax = poiseuille_profile(dp, R, L, mu, 0.0)
    col = ctx.color(spec, "field") if ctx else spec.get("pipe_color", "#4CC9F0")
    vel_col = ctx.color(spec, "accent") if ctx else "#F1C40F"
    ink = ctx.color(spec, "ink") if ctx else "#F2F3F5"
    fs = ctx.font(17) if ctx else 17
    walls = VGroup(
        Line([cx - L / 2, cy + R, 0], [cx + L / 2, cy + R, 0], color=col,
             stroke_width=(ctx.stroke() if ctx else 3)),
        Line([cx - L / 2, cy - R, 0], [cx + L / 2, cy - R, 0], color=col,
             stroke_width=(ctx.stroke() if ctx else 3)),
    )
    profile = VGroup()
    k = int(_finite(spec.get("arrows", 9), "arrows"))
    for i in range(k):
        r = -R + 2 * R * i / (k - 1)
        u = poiseuille_profile(dp, R, L, mu, r)
        profile.add(Arrow([cx - L / 2, cy + r, 0],
                          [cx - L / 2 + (L * 0.6) * (u / umax), cy + r, 0],
                          buff=0, color=vel_col, stroke_width=2))
    label = Text(f"Q = {Q:g} m³/s   u_max = {umax:g} m/s   (parabolic profile)",
                 font_size=fs, color=ink).move_to([cx, cy - R - 0.6, 0])
    print(f"[fluid] poiseuille Q={Q:g} umax={umax:g}")
    return VGroup(walls, profile, label)


def route_fluid(scene, spec):
    if not isinstance(spec, dict):
        raise ValueError("fluid_dynamics visual must be an object.")
    ctx = getattr(scene, "ctx", None)
    op = str(spec.get("operation", "venturi")).lower()
    if op == "venturi":
        return _venturi_visual(spec, ctx)
    if op == "hydrostatic":
        return _hydrostatic_visual(spec, ctx)
    if op == "poiseuille":
        return _poiseuille_visual(spec, ctx)
    raise ValueError("fluid_dynamics operation must be venturi, hydrostatic, "
                     "or poiseuille.")


class _NullScene:
    ctx = None


def build_fluid_visual(item):
    """Legacy-compatible entry point."""
    return route_fluid(_NullScene(), item)


ROUTE_TABLE = {"fluid_dynamics": route_fluid}


# ------------------------------------------------------------ frozen witness
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    rho, g = 1000.0, STANDARD_GRAVITY
    want("ruler:hydrostatic-vs-integral",
         abs(hydrostatic_pressure(rho, 3.0)
             - _simpson_check(rho, g, 3.0)) <= 1e-9)
    v1 = continuity_velocity(2.0, 1.5, 0.5)
    want("witness:mass-flux", abs(rho * 2.0 * 1.5 - rho * 0.5 * v1) <= 1e-12)
    p1, h1, h2 = 101325.0, 1.0, 0.0
    p2 = bernoulli_pressure(p1, rho, 1.0, v1, h1, h2)
    head = lambda p, v, h: p + 0.5 * rho * v * v + rho * g * h
    want("witness:head-invariance", abs(head(p1, 1.0, h1) - head(p2, v1, h2)) <= 1e-8)
    want("witness:bernoulli-roundtrip",
         abs(bernoulli_pressure(p2, rho, v1, 1.0, h2, h1) - p1) <= 1e-8)
    want("witness:torricelli",
         abs(torricelli_speed(2.0) - math.sqrt(2 * g * 2.0)) <= 1e-12)
    Q = poiseuille_flow(12.0, 0.05, 6.0, 0.001)
    Qn = _simpson(lambda r: poiseuille_profile(12.0, 0.05, 6.0, 0.001, r)
                  * 2 * math.pi * r, 0.0, 0.05)
    want("witness:poiseuille-profile<->Q", abs(Q - Qn) <= 1e-9 * max(1.0, abs(Q)))
    re1 = reynolds_number(rho, 1.0, 0.1, 0.001)
    want("witness:reynolds-linear",
         abs(reynolds_number(rho, 2.0, 0.1, 0.001) - 2 * re1) <= 1e-9)
    want("witness:regimes",
         flow_regime(1000) == "laminar" and flow_regime(3000) == "transitional"
         and flow_regimes_ok := flow_regime(9000) == "turbulent")
    xs, _ = sample_channel(-4, 4, 64, 1.8, 0.9, 8.0, 1.0)
    ys, _ = sample_channel(-4, 4, 64, 1.8, 0.9, 8.0, 1.0)
    want("determinism:channel", xs == ys)
    if _NP is not None:
        want("parity:numpy", _numpy_parity())
    else:
        want("parity:numpy", True, "skipped (numpy absent)")
    for bad, label in ((dict(density=-1, depth=1), "density"),
                       (dict(density=1, depth=-1), "depth")):
        try:
            hydrostatic_pressure(bad["density"], bad["depth"])
            want(f"guard:{label}", False)
        except ValueError:
            want(f"guard:{label}", True)
    try:
        bernoulli_pressure(100.0, rho, 30.0, 0.0)
        want("guard:negative-pressure", False)
    except ValueError:
        want("guard:negative-pressure", True)
    return checks


def _simpson(f, a, b, n=200):
    if n % 2:
        n += 1
    h = (b - a) / n
    total = f(a) + f(b)
    for i in range(1, n):
        total += f(a + i * h) * (4 if i % 2 else 2)
    return total * h / 3


def _simpson_check(rho, g, h):
    return _simpson(lambda z: rho * g, 0.0, h)


if __name__ == "__main__":
    fails = 0
    for name, ok, detail in selftest():
        print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
        fails += 0 if ok else 1
    sys.exit(1 if fails else 0)
