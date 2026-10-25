#!/usr/bin/env python3
"""geometry_engine.py — gen-3 dimension-aware geometry core + visuals.

Dependency stance: pure stdlib point math is the ruler (lists, Rodrigues
rotation closed form); manim is imported lazily inside builders only.
No numpy anywhere — nothing here needs it (own tool wins outright).

Witnesses (frozen closed forms, headless selftest):
  * Rodrigues: R_z(pi/2)·(1,0,0) = (0,1,0); R_axis(2pi) = identity
  * translation is additive; rotate-then-translate composition determinism
  * validation rulers: bad dim / 3D-in-2D / unknown kind / >256 points raise

Renderer contract v1: ROUTE_TABLE["geometry"](scene, spec).
Skin from scene.ctx (style genome); explicit spec colors win.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MAX_POINTS = 256
_KINDS = ("point", "points", "segment", "polyline", "polygon",
          "circle", "ellipse", "sphere", "cube", "cylinder", "cone")


# ---------------------------------------------------------------- validation
def _vector(value, dimension, name):
    if isinstance(value, (list, tuple)) and len(value) == dimension:
        try:
            vec = [float(c) for c in value]
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a finite {dimension}D vector.")
        if all(math.isfinite(c) for c in vec):
            return vec + [0.0] * (3 - dimension)
    raise ValueError(f"{name} must be a finite {dimension}D vector.")


def _positive(value, name):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be finite and positive.")
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be finite and positive.")
    return number


def _embed_points(values, dimension, name="geometry points"):
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(f"{name} must be a non-empty list of points.")
    pts = []
    for p in values:
        if not isinstance(p, (list, tuple)) or len(p) != dimension:
            raise ValueError(f"{name} must be {dimension}D points.")
        row = [float(c) for c in p]
        if not all(math.isfinite(c) for c in row):
            raise ValueError(f"{name} must be finite.")
        pts.append(row + [0.0] * (3 - dimension))
    if len(pts) > MAX_POINTS:
        raise ValueError(f"{name} limited to {MAX_POINTS} points.")
    return pts


# ------------------------------------------- pure rigid motion (own tool)
def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def rotate_point(point, axis, theta):
    """Rodrigues closed form — the witnessable rotation ruler."""
    n = math.sqrt(_dot(axis, axis))
    if n <= 1e-12:
        if abs(theta) > 0:
            raise ValueError("rotation axis must be non-zero.")
        return list(point)
    k = [c / n for c in axis]
    c, s = math.cos(theta), math.sin(theta)
    kp = _cross(k, point)
    kp_dot = _dot(k, point)
    return [point[i] * c + kp[i] * s + k[i] * kp_dot * (1 - c) for i in range(3)]


def rigid_transform(point, velocity, angular_velocity, axis, t):
    """Closed-form pose at time t: rotate about origin then translate."""
    p = rotate_point(point, axis, angular_velocity * t)
    return [p[i] + velocity[i] * t for i in range(3)]


# ---------------------------------------------------------------- selftest
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    z = [0.0, 0.0, 1.0]
    q = rotate_point([1, 0, 0], z, math.pi / 2)
    want("ruler:rotz90", all(abs(a - b) <= 1e-12 for a, b in zip(q, [0, 1, 0])), str(q))
    ident = rotate_point([0.3, -0.7, 1.9], [1, 1, 0], 2 * math.pi)
    want("ruler:rot2pi", all(abs(a - b) <= 1e-9
                             for a, b in zip(ident, [0.3, -0.7, 1.9])))
    moved = rigid_transform([1, 0, 0], [2, 0, 0], 0.0, z, 3.0)
    want("ruler:translate", all(abs(a - b) <= 1e-12 for a, b in zip(moved, [7, 0, 0])))
    combo = rigid_transform([1, 0, 0], [0, 1, 0], math.pi / 2, z, 2.0)
    want("ruler:compose", all(abs(a - b) <= 1e-12 for a, b in zip(combo, [0, 3, 0])),
         str(combo))
    want("ruler:determinism",
         rotate_point([1, 2, 3], z, 0.7) == rotate_point([1, 2, 3], z, 0.7))
    for bad, label in (({"dimension": 4}, "dim"),
                       ({"dimension": 3, "kind": "sphere"}, "3d-in-2d"),
                       ({"dimension": 2, "kind": "nope"}, "kind"),
                       ({"dimension": 2, "kind": "points",
                         "points": [[0, 0]] * (MAX_POINTS + 1)}, "cap")):
        try:
            build_geometry(bad, allow_3d=False)
            want(f"guard:{label}", False)
        except ValueError:
            want(f"guard:{label}", True)
    return checks


# ------------------------------------------------------- builders (lazy manim)
def _skin(ctx):
    class _Fallback:
        def color(self, spec, role="primary"):
            return (spec or {}).get("color", "#4CC9F0")
        def place(self, i, n, spec, default=(0, 0, 0)):
            p = (spec or {}).get("position", list(default))
            p = list(p) + [0.0] * (3 - len(p))
            return tuple(p)
        def stroke(self):
            return 2.0
        def dot(self, spec):
            return float((spec or {}).get("radius", 0.06))
        def opacity(self):
            return 0.25
        def font(self, base):
            return base
    return ctx if ctx is not None else _Fallback()


def build_geometry(item, *, allow_3d):
    """Validate + build one geometry primitive. Manim imported lazily."""
    if not isinstance(item, dict):
        raise ValueError("geometry visual must be an object.")
    dimension = item.get("dimension", 2)
    if not isinstance(dimension, int) or dimension not in (1, 2, 3):
        raise ValueError("geometry dimension must be 1, 2, or 3.")
    if dimension == 3 and not allow_3d:
        raise ValueError("3D geometry must be rendered by a 3D scene.")
    kind = str(item.get("kind", "polyline")).lower()
    if kind not in _KINDS:
        raise ValueError(f"Unsupported geometry kind '{kind}'.")
    from manim import (Circle, Cone, Cube, Cylinder, Dot, Dot3D, Ellipse,
                       Line, Polygon, Sphere, VMobject, VGroup)
    color = item.get("color", "#4CC9F0")
    position = _vector(item.get("position", [0] * dimension), dimension,
                       "geometry position")
    opacity = float(item.get("fill_opacity", 0.25))
    if not math.isfinite(opacity) or not 0 <= opacity <= 1:
        raise ValueError("geometry fill_opacity must be between 0 and 1.")

    if kind in ("point", "points"):
        if kind == "point":
            pts = [position]
        else:
            pts = _embed_points(item.get("points"), dimension)
            off = position
            pts = [[p[i] + off[i] for i in range(3)] for p in pts]
        radius = _positive(item.get("radius", 0.06), "geometry radius")
        return VGroup(*[(Dot(p, radius=radius, color=color) if dimension < 3
                         else Dot3D(point=p, radius=radius, color=color))
                        for p in pts])

    if kind in ("segment", "polyline", "polygon"):
        pts = _embed_points(item.get("points"), dimension)
        off = position
        pts = [[p[i] + off[i] for i in range(3)] for p in pts]
        if kind == "segment" and len(pts) != 2:
            raise ValueError("segment geometry needs exactly two points.")
        if kind == "polygon" and len(pts) < 3:
            raise ValueError("polygon geometry needs at least three points.")
        if kind == "polygon":
            return Polygon(*pts, color=color, fill_color=color,
                           fill_opacity=opacity,
                           stroke_width=float(item.get("stroke_width", 2.0)))
        path = VMobject()
        path.set_points_as_corners(pts)
        path.set_stroke(color, width=float(item.get("stroke_width", 2.5)))
        return path

    if kind in ("circle", "ellipse"):
        if dimension == 1:
            raise ValueError(f"{kind} is not defined for 1D geometry.")
        if kind == "circle":
            radius = _positive(item.get("radius", 1.0), "geometry radius")
            return Circle(radius=radius, color=color, fill_color=color,
                          fill_opacity=opacity, stroke_width=2.0).move_to(position)
        width = _positive(item.get("width", 2.0), "geometry width")
        height = _positive(item.get("height", 1.0), "geometry height")
        return Ellipse(width=width, height=height, color=color,
                       fill_color=color, fill_opacity=opacity).move_to(position)

    # 3D solids
    if dimension != 3 or not allow_3d:
        raise ValueError(f"{kind} requires dimension=3 in a 3D scene.")
    if kind == "sphere":
        mob = Sphere(radius=_positive(item.get("radius", 1.0), "geometry radius"),
                     resolution=item.get("resolution", (12, 12)), color=color)
    elif kind == "cube":
        mob = Cube(side_length=_positive(item.get("side_length", 2.0),
                                         "geometry side_length"),
                   fill_color=color, fill_opacity=opacity,
                   stroke_width=float(item.get("stroke_width", 1.0)))
    elif kind == "cylinder":
        mob = Cylinder(radius=_positive(item.get("radius", 1.0), "geometry radius"),
                       height=_positive(item.get("height", 2.0), "geometry height"),
                       resolution=item.get("resolution", (12, 12)), color=color)
    else:
        mob = Cone(base_radius=_positive(item.get("radius", 1.0), "geometry radius"),
                   height=_positive(item.get("height", 2.0), "geometry height"),
                   color=color)
    return mob.move_to(position)


def add_rigid_motion(mobject, item, *, dimension):
    """One low-overhead in-place translation/rotation updater (render time)."""
    motion = item.get("motion")
    if motion is None:
        return mobject
    if not isinstance(motion, dict):
        raise ValueError("geometry motion must be an object.")
    velocity = _vector(motion.get("velocity", [0] * dimension), dimension,
                       "geometry velocity")
    angular = float(motion.get("angular_velocity", 0.0))
    if not math.isfinite(angular):
        raise ValueError("angular_velocity must be finite.")
    axis = _vector(motion.get("axis", [0, 0, 1]), 3, "rotation axis")
    if abs(angular) > 0 and math.sqrt(_dot(axis, axis)) <= 1e-12:
        raise ValueError("rotation axis must be non-zero.")

    def update(mob, dt):
        if any(velocity):
            mob.shift([velocity[0] * dt, velocity[1] * dt, velocity[2] * dt])
        if angular:
            mob.rotate(angular * dt, axis=axis, about_point=mob.get_center())
    mobject.add_updater(update)
    return mobject


def route_geometry(scene, spec):
    is_3d = isinstance(scene, object) and type(scene).__name__ == "Universal3DScene"
    allow_3d = bool(is_3d or spec.get("dimension", 2) == 3 and is_3d)
    allow_3d = bool(is_3d)
    sk = _skin(getattr(scene, "ctx", None))
    item = dict(spec)
    item.setdefault("color", None)
    if item["color"] is None:
        item.pop("color")           # let genome skin it unless teacher set one
        try:
            item["color"] = sk.color(spec, "primary")
        except Exception:
            item["color"] = "#4CC9F0"
    mob = build_geometry(item, allow_3d=allow_3d)
    return add_rigid_motion(mob, item, dimension=item.get("dimension", 2))


ROUTE_TABLE = {"geometry": route_geometry}

if __name__ == "__main__":
    fails = 0
    for name, ok, detail in selftest():
        print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
        fails += 0 if ok else 1
    sys.exit(1 if fails else 0)
