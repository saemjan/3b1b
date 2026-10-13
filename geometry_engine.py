"""Dimension-aware geometry builders and in-place rigid motion helpers."""
from __future__ import annotations

import math

import numpy as np
from manim import (
    Circle, Cone, Cube, Cylinder, Dot, Dot3D, Ellipse, Line, Polygon,
    Sphere, VMobject, VGroup,
)


def _vector(value, dimension, name):
    try:
        vector = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite {dimension}D vector.") from exc
    if vector.shape != (dimension,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite {dimension}D vector.")
    return np.pad(vector, (0, 3 - dimension))


def _positive(value, name):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite and positive.") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be finite and positive.")
    return number


def _embed_points(values, dimension):
    try:
        points = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("geometry points must be a finite coordinate list.") from exc
    if (points.ndim != 2 or points.shape[1] != dimension
            or len(points) == 0 or not np.all(np.isfinite(points))):
        raise ValueError(
            f"geometry points must be a non-empty list of {dimension}D points."
        )
    return np.pad(points, ((0, 0), (0, 3 - dimension)))


def build_geometry(item, *, allow_3d):
    """Build a geometry primitive from dimensioned coordinates.

    Supported kinds: point, points, segment, polyline, polygon, circle,
    ellipse, sphere, cube, cylinder, and cone.
    """
    dimension = item.get("dimension", 2)
    if not isinstance(dimension, int) or dimension not in (1, 2, 3):
        raise ValueError("geometry dimension must be 1, 2, or 3.")
    if dimension == 3 and not allow_3d:
        raise ValueError("3D geometry must be rendered by a 3D scene.")
    kind = str(item.get("kind", "polyline")).lower()
    color = item.get("color", "#4CC9F0")
    position = _vector(item.get("position", [0] * dimension),
                       dimension, "geometry position")
    opacity = float(item.get("fill_opacity", 0.25))
    if not math.isfinite(opacity) or not 0 <= opacity <= 1:
        raise ValueError("geometry fill_opacity must be between 0 and 1.")

    if kind in ("point", "points"):
        if kind == "point":
            points = _vector(item.get("position", [0] * dimension),
                             dimension, "geometry position").reshape(1, 3)
        else:
            points = _embed_points(item.get("points"), dimension)
            points += position
        if len(points) > 256:
            raise ValueError("geometry point clouds are limited to 256 points.")
        radius = _positive(item.get("radius", 0.06), "geometry radius")
        return VGroup(*[
            (Dot(point, radius=radius, color=color) if dimension < 3
             else Dot3D(point=point, radius=radius, color=color))
            for point in points
        ])

    if kind in ("segment", "polyline", "polygon"):
        points = _embed_points(item.get("points"), dimension) + position
        if kind == "segment" and len(points) != 2:
            raise ValueError("segment geometry needs exactly two points.")
        if kind == "polygon" and len(points) < 3:
            raise ValueError("polygon geometry needs at least three points.")
        if kind == "polygon":
            return Polygon(
                *points,
                color=color,
                fill_color=color,
                fill_opacity=opacity,
                stroke_width=float(item.get("stroke_width", 2.0)),
            )
        path = VMobject()
        path.set_points_as_corners(points)
        path.set_stroke(color, width=float(item.get("stroke_width", 2.5)))
        return path

    if kind in ("circle", "ellipse"):
        if dimension == 1:
            raise ValueError(
                f"{kind} is not defined for 1D geometry; use segment instead."
            )
        center = position
        if kind == "circle":
            radius = _positive(item.get("radius", 1.0), "geometry radius")
            return Circle(
                radius=radius, color=color, fill_color=color,
                fill_opacity=opacity, stroke_width=2.0,
            ).move_to(center)
        width = _positive(item.get("width", 2.0), "geometry width")
        height = _positive(item.get("height", 1.0), "geometry height")
        return Ellipse(
            width=width, height=height, color=color,
            fill_color=color, fill_opacity=opacity,
        ).move_to(center)

    if kind in ("sphere", "cube", "cylinder", "cone"):
        if dimension != 3 or not allow_3d:
            raise ValueError(f"{kind} requires dimension=3 in a 3D scene.")
        if kind == "sphere":
            mob = Sphere(
                radius=_positive(item.get("radius", 1.0), "geometry radius"),
                resolution=item.get("resolution", (12, 12)),
                color=color,
            )
        elif kind == "cube":
            mob = Cube(
                side_length=_positive(
                    item.get("side_length", 2.0), "geometry side_length",
                ),
                fill_color=color,
                fill_opacity=opacity,
                stroke_width=float(item.get("stroke_width", 1.0)),
            )
        elif kind == "cylinder":
            mob = Cylinder(
                radius=_positive(item.get("radius", 1.0), "geometry radius"),
                height=_positive(item.get("height", 2.0), "geometry height"),
                resolution=item.get("resolution", (12, 12)),
                color=color,
            )
        else:
            mob = Cone(
                base_radius=_positive(
                    item.get("radius", 1.0), "geometry radius",
                ),
                height=_positive(item.get("height", 2.0), "geometry height"),
                color=color,
            )
        return mob.move_to(position)

    raise ValueError(
        f"Unsupported geometry kind '{kind}'. Supported kinds are point, "
        "points, segment, polyline, polygon, circle, ellipse, sphere, cube, "
        "cylinder, and cone."
    )


def add_rigid_motion(mobject, item, *, dimension):
    """Attach one low-overhead in-place translation/rotation updater."""
    motion = item.get("motion")
    if motion is None:
        return mobject
    if not isinstance(motion, dict):
        raise ValueError("geometry motion must be an object.")
    velocity = _vector(
        motion.get("velocity", [0] * dimension),
        dimension,
        "geometry velocity",
    )
    try:
        angular_velocity = float(motion.get("angular_velocity", 0.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("angular_velocity must be finite.") from exc
    if not math.isfinite(angular_velocity):
        raise ValueError("angular_velocity must be finite.")
    axis = _vector(motion.get("axis", [0, 0, 1]), 3, "rotation axis")
    axis_length = np.linalg.norm(axis)
    if abs(angular_velocity) > 0 and axis_length <= 1e-12:
        raise ValueError("rotation axis must be non-zero.")
    if axis_length > 0:
        axis = axis / axis_length

    def update(mob, dt):
        if np.any(velocity):
            mob.shift(velocity * dt)
        if angular_velocity:
            mob.rotate(
                angular_velocity * dt,
                axis=axis,
                about_point=mob.get_center(),
            )

    mobject.add_updater(update)
    return mobject
