"""Validated rigid-body rotational mechanics and Manim visualization."""
from __future__ import annotations

import math

import numpy as np
from manim import Arrow, Circle, Dot, Line, Text, VGroup, always_redraw


def _finite(value, name):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite.")
    return number


def _positive(value, name):
    number = _finite(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be positive.")
    return number


def moment_of_inertia(shape, *, mass, radius=None, length=None):
    """Return I about the standard axis for common rigid-body shapes."""
    mass = _positive(mass, "mass")
    shape = str(shape).lower()
    if shape in ("solid_disk", "solid_cylinder"):
        radius = _positive(radius, "radius")
        return 0.5 * mass * radius ** 2
    if shape in ("hoop", "thin_ring"):
        radius = _positive(radius, "radius")
        return mass * radius ** 2
    if shape in ("rod_center", "rod_end"):
        length = _positive(length, "length")
        return mass * length ** 2 * (1 / 12 if shape == "rod_center" else 1 / 3)
    raise ValueError(
        "shape must be solid_disk, solid_cylinder, hoop, thin_ring, "
        "rod_center, or rod_end."
    )


def angular_acceleration(net_torque, inertia):
    """Return angular acceleration alpha = net torque / moment of inertia."""
    return _finite(net_torque, "net_torque") / _positive(inertia, "inertia")


def angular_velocity(initial_angular_velocity, angular_acceleration_value,
                     time):
    """Return angular velocity for constant angular acceleration."""
    omega0 = _finite(initial_angular_velocity, "initial_angular_velocity")
    alpha = _finite(angular_acceleration_value, "angular_acceleration")
    time = _finite(time, "time")
    if time < 0:
        raise ValueError("time must be non-negative.")
    return omega0 + alpha * time


def angular_displacement(initial_angle, initial_angular_velocity,
                         angular_acceleration_value, time):
    """Return angular position under constant angular acceleration."""
    angle = _finite(initial_angle, "initial_angle")
    omega0 = _finite(initial_angular_velocity, "initial_angular_velocity")
    alpha = _finite(angular_acceleration_value, "angular_acceleration")
    time = _finite(time, "time")
    if time < 0:
        raise ValueError("time must be non-negative.")
    return angle + omega0 * time + 0.5 * alpha * time ** 2


def rotational_kinetic_energy(inertia, angular_velocity_value):
    """Return rotational kinetic energy K = 1/2 I omega squared."""
    inertia = _positive(inertia, "inertia")
    omega = _finite(angular_velocity_value, "angular_velocity")
    return 0.5 * inertia * omega ** 2


def angular_momentum(inertia, angular_velocity_value):
    """Return scalar angular momentum L = I omega about the fixed axis."""
    inertia = _positive(inertia, "inertia")
    omega = _finite(angular_velocity_value, "angular_velocity")
    return inertia * omega


def build_rotational_visual(item, time_tracker):
    """Build an animated 2D rigid body with radius, omega, and torque cues."""
    if not isinstance(item, dict):
        raise ValueError("rotational_motion visual must be an object.")
    shape = str(item.get("shape", "solid_disk")).lower()
    mass = _positive(item.get("mass", 1.0), "mass")
    radius = _positive(item.get("radius", 1.0), "radius")
    length = _positive(item.get("length", 2.0 * radius), "length")
    inertia = moment_of_inertia(
        shape, mass=mass, radius=radius, length=length,
    )
    omega0 = _finite(item.get("angular_velocity", 1.0), "angular_velocity")
    torque = _finite(item.get("torque", 0.0), "torque")
    alpha = angular_acceleration(torque, inertia)
    theta0 = _finite(item.get("initial_angle", 0.0), "initial_angle")
    center = np.asarray(item.get("center", [0.0, 0.0, 0.0]), dtype=float)
    if center.shape != (3,) or not np.all(np.isfinite(center)):
        raise ValueError("center must be a finite 3D point.")
    display_radius = _positive(
        item.get("display_radius", min(1.5, max(0.75, radius))),
        "display_radius",
    )
    color = item.get("color", "#4CC9F0")
    torque_color = item.get("torque_color", "#F1C40F")
    point_radius = display_radius * (2 if shape == "rod_end" else 1)

    def state():
        time = time_tracker.get_value()
        angle = angular_displacement(theta0, omega0, alpha, time)
        omega = angular_velocity(omega0, alpha, time)
        radial = np.array([math.cos(angle), math.sin(angle), 0.0])
        tangent = np.array([-math.sin(angle), math.cos(angle), 0.0])
        point = center + radial * point_radius
        return angle, omega, radial, tangent, point

    if shape in ("rod_center", "rod_end"):
        def rod():
            angle = state()[0]
            direction = np.array([math.cos(angle), math.sin(angle), 0.0])
            start = center - direction * display_radius
            end = center + direction * display_radius
            if shape == "rod_end":
                start, end = center, center + direction * (2 * display_radius)
            return Line(start, end, color=color, stroke_width=7)

        body = always_redraw(rod)
    else:
        body = Circle(
            radius=display_radius,
            color=color,
            fill_color=color,
            fill_opacity=0.12 if shape in ("solid_disk", "solid_cylinder") else 0,
            stroke_width=3,
        ).move_to(center)

    spoke = always_redraw(
        lambda: Line(center, state()[4], color="#F1C40F", stroke_width=3)
    )
    marker = always_redraw(
        lambda: Dot(state()[4], radius=0.10, color="#FF4B4B")
    )

    def velocity_vector():
        _, omega, _, tangent, point = state()
        scaled = tangent * omega * point_radius * 0.18
        if np.linalg.norm(scaled) < 1e-8:
            return Dot(point, radius=0.03, color="#80ED99")
        return Arrow(point, point + scaled, buff=0, color="#80ED99",
                     stroke_width=2.5, max_tip_length_to_length_ratio=0.25)

    velocity_arrow = always_redraw(velocity_vector)
    axle = Dot(center, radius=0.11, color="#F2F3F5")
    labels = VGroup(
        Text(f"I = {inertia:g} kg·m²", font_size=18, color="#F2F3F5")
        .move_to(center + [0, -display_radius - 0.55, 0]),
        Text(f"τ = {torque:g} N·m   α = {alpha:g} rad/s²",
             font_size=17, color=torque_color)
        .move_to(center + [0, -display_radius - 1.0, 0]),
    )
    return VGroup(body, spoke, marker, velocity_arrow, axle, labels)