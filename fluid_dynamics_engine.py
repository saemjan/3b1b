"""Validated fluid-mechanics calculations and Manim visuals."""
from __future__ import annotations

import math

import numpy as np
from manim import Arrow, Dot, Line, Polygon, Rectangle, Text, VGroup, VMobject


STANDARD_GRAVITY = 9.80665


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


def hydrostatic_pressure(density, depth, surface_pressure=0.0,
                         gravity=STANDARD_GRAVITY):
    """Return pressure at depth; default surface pressure is gauge zero."""
    density = _positive(density, "density")
    depth = _finite(depth, "depth")
    surface_pressure = _finite(surface_pressure, "surface_pressure")
    gravity = _positive(gravity, "gravity")
    if depth < 0 or surface_pressure < 0:
        raise ValueError("depth and surface_pressure must be non-negative.")
    return surface_pressure + density * gravity * depth


def continuity_velocity(area_in, velocity_in, area_out):
    """Return outlet velocity from incompressible continuity, A1*v1=A2*v2."""
    area_in = _positive(area_in, "area_in")
    velocity_in = _finite(velocity_in, "velocity_in")
    area_out = _positive(area_out, "area_out")
    return area_in * velocity_in / area_out


def bernoulli_pressure(pressure_in, density, velocity_in, velocity_out,
                       height_in=0.0, height_out=0.0,
                       gravity=STANDARD_GRAVITY):
    """Return ideal outlet pressure for steady, incompressible flow."""
    pressure_in = _finite(pressure_in, "pressure_in")
    density = _positive(density, "density")
    velocity_in = _finite(velocity_in, "velocity_in")
    velocity_out = _finite(velocity_out, "velocity_out")
    height_in = _finite(height_in, "height_in")
    height_out = _finite(height_out, "height_out")
    gravity = _positive(gravity, "gravity")
    if pressure_in < 0:
        raise ValueError("pressure_in must be non-negative absolute pressure.")
    pressure_out = (
        pressure_in
        + 0.5 * density * (velocity_in ** 2 - velocity_out ** 2)
        + density * gravity * (height_in - height_out)
    )
    if pressure_out < 0:
        raise ValueError("Bernoulli result is negative absolute pressure.")
    return pressure_out


def reynolds_number(density, velocity, characteristic_length,
                    dynamic_viscosity):
    """Return the dimensionless Reynolds number for a Newtonian fluid."""
    density = _positive(density, "density")
    velocity = _finite(velocity, "velocity")
    characteristic_length = _positive(
        characteristic_length, "characteristic_length",
    )
    dynamic_viscosity = _positive(dynamic_viscosity, "dynamic_viscosity")
    return density * abs(velocity) * characteristic_length / dynamic_viscosity


def _venturi_visual(item):
    inlet_height = _positive(item.get("inlet_height", 1.8), "inlet_height")
    throat_height = _positive(item.get("throat_height", 0.9), "throat_height")
    length = _positive(item.get("length", 8.0), "length")
    if throat_height > inlet_height:
        raise ValueError("throat_height must not exceed inlet_height.")
    inlet_velocity = _finite(item.get("inlet_velocity", 1.0), "inlet_velocity")
    if inlet_velocity <= 0:
        raise ValueError("Venturi visual inlet_velocity must be positive.")
    density = _positive(item.get("density", 1000.0), "density")
    inlet_pressure = _finite(item.get("inlet_pressure", 101325.0), "inlet_pressure")
    if inlet_pressure < 0:
        raise ValueError("inlet_pressure must be non-negative.")
    pos = np.asarray(item.get("center", [0.0, -0.2, 0.0]), dtype=float)
    if pos.shape != (3,) or not np.all(np.isfinite(pos)):
        raise ValueError("center must be a finite 3D point.")
    count = item.get("particle_count", 14)
    if isinstance(count, bool) or not isinstance(count, int) or not 4 <= count <= 40:
        raise ValueError("particle_count must be an integer from 4 through 40.")

    x0, x1 = pos[0] - length / 2, pos[0] + length / 2
    throat_x = pos[0]

    def half_height(x):
        normalized = min(1.0, abs(x - throat_x) / (length * 0.24))
        smooth = normalized * normalized * (3 - 2 * normalized)
        return throat_height / 2 + (inlet_height - throat_height) * smooth / 2

    x_values = np.linspace(x0, x1, 96)
    top = [pos + [x - pos[0], half_height(x), 0] for x in x_values]
    bottom = [pos + [x - pos[0], -half_height(x), 0] for x in x_values]
    pipe = Polygon(
        *(top + bottom[::-1]),
        color=item.get("pipe_color", "#4CC9F0"),
        fill_color=item.get("fluid_color", "#3498DB"),
        fill_opacity=0.10,
        stroke_width=0,
    )
    top_wall = VMobject().set_points_as_corners(top).set_stroke(
        item.get("pipe_color", "#4CC9F0"), width=3,
    )
    bottom_wall = VMobject().set_points_as_corners(bottom).set_stroke(
        item.get("pipe_color", "#4CC9F0"), width=3,
    )

    velocity_out = continuity_velocity(
        inlet_height, inlet_velocity, throat_height,
    )
    pressure_out = bernoulli_pressure(
        inlet_pressure, density, inlet_velocity, velocity_out,
        item.get("height_in", 0.0), item.get("height_out", 0.0),
    )
    labels = VGroup(
        Text(f"A₁v₁ = A₂v₂   v₂ = {velocity_out:g} m/s",
             font_size=18, color="#F1C40F")
        .move_to([pos[0], pos[1] + inlet_height / 2 + 0.8, 0]),
        Text(f"p₁ = {inlet_pressure:g} Pa",
             font_size=16, color="#F2F3F5")
        .move_to([x0 + length * 0.18, pos[1] - inlet_height / 2 - 0.45, 0]),
        Text(f"p₂ = {pressure_out:g} Pa",
             font_size=16, color="#F2F3F5")
        .move_to([throat_x, pos[1] - throat_height / 2 - 0.45, 0]),
    )

    particles = VGroup()
    flow_color = item.get("fluid_color", "#3498DB")
    for index in range(count):
        fraction = index / count
        offset_fraction = ((index % 5) - 2) / 6
        initial_x = x0 + fraction * length
        dot = Dot(
            [initial_x, pos[1] + offset_fraction * 2 * half_height(initial_x), 0],
            radius=0.065,
            color=flow_color,
        )

        def advance(mob, dt, offset_fraction=offset_fraction):
            x = mob.get_center()[0]
            local_height = 2 * half_height(x)
            local_velocity = inlet_velocity * inlet_height / local_height
            x += local_velocity * dt
            if x > x1:
                x = x0 + (x - x1)
            mob.move_to([
                x,
                pos[1] + offset_fraction * 2 * half_height(x),
                0,
            ])

        dot.add_updater(advance)
        particles.add(dot)

    return VGroup(pipe, top_wall, bottom_wall, particles, labels)


def _hydrostatic_visual(item):
    density = _positive(item.get("density", 1000.0), "density")
    max_depth = _positive(item.get("max_depth", 4.0), "max_depth")
    pos = np.asarray(item.get("center", [0.0, 0.0, 0.0]), dtype=float)
    if pos.shape != (3,) or not np.all(np.isfinite(pos)):
        raise ValueError("center must be a finite 3D point.")
    width, height = 2.8, max_depth * 1.25
    top_y = pos[1] + height / 2
    tank = Rectangle(
        width=width, height=height, color="#4CC9F0",
        fill_color="#3498DB", fill_opacity=0.12,
    ).move_to(pos)
    surface = Line(
        [pos[0] - width / 2, top_y - 0.12, 0],
        [pos[0] + width / 2, top_y - 0.12, 0],
        color="#4CC9F0", stroke_width=2,
    )
    pressure_arrows = VGroup()
    for depth in np.linspace(max_depth / 4, max_depth, 4):
        y = top_y - 0.12 - depth
        pressure = hydrostatic_pressure(density, depth)
        arrow_length = 0.35 + 0.8 * depth / max_depth
        pressure_arrows.add(
            Arrow(
                [pos[0] + width / 2 + 0.15, y, 0],
                [pos[0] + width / 2 + 0.15 + arrow_length, y, 0],
                buff=0, color="#F1C40F", stroke_width=2.5,
            ),
            Text(f"h={depth:g} m  p={pressure:.0f} Pa",
                 font_size=15, color="#F2F3F5")
            .move_to([pos[0] + width / 2 + 1.8, y + 0.28, 0]),
        )
    return VGroup(tank, surface, pressure_arrows)


def build_fluid_visual(item):
    """Build an animated Venturi flow or a hydrostatic-pressure diagram."""
    if not isinstance(item, dict):
        raise ValueError("fluid_dynamics visual must be an object.")
    operation = str(item.get("operation", "venturi")).lower()
    if operation == "venturi":
        return _venturi_visual(item)
    if operation == "hydrostatic":
        return _hydrostatic_visual(item)
    raise ValueError("fluid_dynamics operation must be venturi or hydrostatic.")