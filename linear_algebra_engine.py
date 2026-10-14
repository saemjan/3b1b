"""Validated vector and determinant calculations with Manim visual builders."""
from __future__ import annotations

import math

import numpy as np
from manim import Arrow, DashedLine, Dot, Line, Polygon, Text, VGroup, config


def _vector(value, name, *, dimensions=(2, 3)):
    try:
        vector = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        allowed = " or ".join(str(dimension) for dimension in dimensions)
        raise ValueError(f"{name} must be a finite {allowed}D vector.") from exc
    if (vector.ndim != 1 or len(vector) not in dimensions
            or not np.all(np.isfinite(vector))):
        allowed = " or ".join(str(dimension) for dimension in dimensions)
        raise ValueError(f"{name} must be a finite {allowed}D vector.")
    return vector


def vector_add(left, right):
    """Add two finite vectors with the same 2D or 3D dimension."""
    a = _vector(left, "left vector")
    b = _vector(right, "right vector")
    if a.shape != b.shape:
        raise ValueError("vector dimensions must match.")
    return a + b


def dot_product(left, right):
    """Return the scalar dot product of same-dimensional 2D or 3D vectors."""
    a = _vector(left, "left vector")
    b = _vector(right, "right vector")
    if a.shape != b.shape:
        raise ValueError("vector dimensions must match.")
    return float(np.dot(a, b))


def cross_product(left, right):
    """Return the 3D cross product, or signed scalar area for 2D vectors."""
    a = _vector(left, "left vector")
    b = _vector(right, "right vector")
    if a.shape != b.shape:
        raise ValueError("vector dimensions must match.")
    if len(a) == 2:
        return float(a[0] * b[1] - a[1] * b[0])
    return np.cross(a, b)


def determinant(matrix):
    """Compute a finite square matrix determinant using pivoted elimination."""
    try:
        values = np.asarray(matrix, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("matrix must contain finite numeric values.") from exc
    if (values.ndim != 2 or values.shape[0] != values.shape[1]
            or not 1 <= values.shape[0] <= 8
            or not np.all(np.isfinite(values))):
        raise ValueError("matrix must be finite and square with size 1 through 8.")
    values = values.copy()
    sign = 1.0
    result = 1.0
    for column in range(values.shape[0]):
        pivot = column + int(np.argmax(np.abs(values[column:, column])))
        pivot_value = values[pivot, column]
        if pivot_value == 0:
            return 0.0
        if pivot != column:
            values[[column, pivot]] = values[[pivot, column]]
            sign = -sign
        pivot_value = values[column, column]
        result *= pivot_value
        if column + 1 < values.shape[0]:
            factors = values[column + 1:, column] / pivot_value
            values[column + 1:, column + 1:] -= (
                factors[:, None] * values[column, column + 1:]
            )
    return float(sign * result)


def _finite_number(value, name):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite.")
    return number


def _canvas(item):
    center = item.get("center", [0, 0])
    try:
        center = [float(value) for value in center]
        scale = float(item.get("scale", 1.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("diagram center and scale must be numeric.") from exc
    if (len(center) not in (2, 3)
            or not all(math.isfinite(value) for value in center)
            or not math.isfinite(scale) or scale <= 0):
        raise ValueError("diagram center must be finite and scale must be positive.")
    if len(center) == 2:
        center.append(0.0)
    return np.array(center), scale


def _arrow(origin, vector, *, color, scale, label):
    endpoint = origin + np.array([vector[0], vector[1], 0.0]) * scale
    if np.linalg.norm(endpoint - origin) < 1e-8:
        point = Dot(origin, radius=0.045, color=color)
        return VGroup(
            point,
            Text(label, font_size=18, color=color).next_to(
                point, np.array([1.0, 1.0, 0.0]),
            ),
        )
    arrow = Arrow(
        origin, endpoint, buff=0, color=color, stroke_width=4,
        max_tip_length_to_length_ratio=0.18,
    )
    label_mob = Text(label, font_size=18, color=color)
    label_mob.next_to(endpoint, np.array([1.0, 1.0, 0.0]), buff=0.08)
    return VGroup(arrow, label_mob)


def _draw_vectors(item, *, operation):
    a = _vector(item.get("a"), "a", dimensions=(2,))
    b = _vector(item.get("b"), "b", dimensions=(2,))
    center, scale = _canvas(item)
    origin = center.copy()
    group = VGroup()
    axes_extent = max(np.linalg.norm(a), np.linalg.norm(b),
                      np.linalg.norm(a + b), 1.0) * scale * 1.25
    group.add(
        Line(origin + [-axes_extent, 0, 0], origin + [axes_extent, 0, 0],
             color="#555B66", stroke_width=1),
        Line(origin + [0, -axes_extent, 0], origin + [0, axes_extent, 0],
             color="#555B66", stroke_width=1),
        Dot(origin, radius=0.04, color="#F2F3F5"),
        _arrow(origin, a, color=item.get("a_color", "#4CC9F0"),
               scale=scale, label="a"),
        _arrow(origin, b, color=item.get("b_color", "#F1C40F"),
               scale=scale, label="b"),
    )
    if operation == "vectors":
        result = a + b
        a_scaled = np.array([a[0], a[1], 0.0]) * scale
        b_scaled = np.array([b[0], b[1], 0.0]) * scale
        result_scaled = np.array([result[0], result[1], 0.0]) * scale
        head = origin + a_scaled
        result_end = origin + result_scaled
        group.add(
            DashedLine(origin, head, color="#4CC9F0", stroke_width=1.5),
            DashedLine(head, result_end, color="#F1C40F", stroke_width=1.5),
            _arrow(origin, result, color=item.get("result_color", "#2ECC71"),
                   scale=scale, label="a + b"),
            Text(
                f"a + b = ({result[0]:g}, {result[1]:g})",
                font_size=20, color=item.get("result_color", "#2ECC71"),
            ).move_to(center + [0, -axes_extent - 0.35, 0]),
        )
    elif operation == "dot":
        value = dot_product(a, b)
        norm_product = np.linalg.norm(a) * np.linalg.norm(b)
        if norm_product == 0:
            angle_label = "undefined"
        else:
            cosine = float(np.clip(np.dot(a, b) / norm_product, -1.0, 1.0))
            angle_label = f"{math.degrees(math.acos(cosine)):.1f}°"
        group.add(Text(
            f"a · b = {value:g}    θ = {angle_label}",
            font_size=22, color=item.get("result_color", "#2ECC71"),
        ).move_to(center + [0, -axes_extent - 0.35, 0]))
    elif operation == "cross":
        value = cross_product(a, b)
        group.add(Text(
            f"a × b = {value:g}  (signed z-component)",
            font_size=20,
            color=item.get("result_color", "#2ECC71" if value >= 0 else "#FF4B4B"),
        ).move_to(center + [0, -axes_extent - 0.35, 0]))
    return group


def _draw_determinant(item):
    matrix = item.get("matrix")
    try:
        values = np.asarray(matrix, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("determinant visual requires a finite 2x2 matrix.") from exc
    if values.shape != (2, 2) or not np.all(np.isfinite(values)):
        raise ValueError("determinant visual requires a finite 2x2 matrix.")
    value = determinant(values)
    center, scale = _canvas(item)
    a, b = values[:, 0], values[:, 1]
    if max(np.linalg.norm(a), np.linalg.norm(b)) * scale > 2.7:
        scale *= 2.7 / (max(np.linalg.norm(a), np.linalg.norm(b)) * scale)
    origin = center.copy()
    endpoint_a = origin + [a[0] * scale, a[1] * scale, 0]
    endpoint_b = origin + [b[0] * scale, b[1] * scale, 0]
    endpoint_sum = endpoint_a + endpoint_b - origin
    area_color = item.get(
        "area_color", "#2ECC71" if value >= 0 else "#FF4B4B",
    )
    parallelogram = Polygon(
        origin, endpoint_a, endpoint_sum, endpoint_b,
        color=area_color, fill_color=area_color,
        fill_opacity=0.2, stroke_width=2,
    )
    return VGroup(
        Line(origin + [-3, 0, 0], origin + [3, 0, 0],
             color="#555B66", stroke_width=1),
        Line(origin + [0, -2.5, 0], origin + [0, 2.5, 0],
             color="#555B66", stroke_width=1),
        parallelogram,
        _arrow(origin, a, color="#4CC9F0", scale=scale, label="column 1"),
        _arrow(origin, b, color="#F1C40F", scale=scale, label="column 2"),
        Text(
            f"det(A) = {value:g}    signed area = {value:g}",
            font_size=21, color=area_color,
        ).move_to(center + [0, -3.2, 0]),
    )


def build_linear_algebra_visual(item):
    """Build a vector, dot, cross, or 2D determinant visualization."""
    if not isinstance(item, dict):
        raise ValueError("linear algebra visual must be an object.")
    operation = str(item.get("operation", "vectors")).lower()
    if operation in ("vectors", "dot", "cross"):
        return _draw_vectors(item, operation=operation)
    if operation == "determinant":
        return _draw_determinant(item)
    raise ValueError(
        "linear algebra operation must be vectors, dot, cross, or determinant."
    )
