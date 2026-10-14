"""Numerical electromagnetic field models and storyboard visuals."""
from __future__ import annotations

import math

import numpy as np
from manim import Arrow, Dot, Line, Text, VGroup, VMobject, config


VACUUM_PERMITTIVITY = 8.8541878128e-12
VACUUM_PERMEABILITY = 1.25663706212e-6
SPEED_OF_LIGHT = 1 / math.sqrt(VACUUM_PERMITTIVITY * VACUUM_PERMEABILITY)
COULOMB_CONSTANT = 1 / (4 * math.pi * VACUUM_PERMITTIVITY)


def _finite_vector(value, name, *, dimension=3):
    try:
        vector = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite {dimension}D vector.") from exc
    if vector.shape != (dimension,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite {dimension}D vector.")
    return vector


def _finite_number(value, name, *, nonzero=False):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite.") from exc
    if not math.isfinite(number) or (nonzero and number == 0):
        qualifier = "finite and non-zero" if nonzero else "finite"
        raise ValueError(f"{name} must be {qualifier}.")
    return number


def electric_field(point, charges, *, coulomb_constant=COULOMB_CONSTANT):
    """Return the SI electric field from point charges at a 3D position.

    Each charge is a mapping with ``position`` in metres and ``charge`` in
    coulombs. The field is undefined at a point-charge location and raises
    ``ValueError`` there rather than silently regularizing the singularity.
    """
    position = _finite_vector(point, "field point")
    constant = _finite_number(coulomb_constant, "Coulomb constant")
    if constant <= 0:
        raise ValueError("Coulomb constant must be positive.")
    if not isinstance(charges, (list, tuple)) or not charges:
        raise ValueError("charges must be a non-empty list.")
    result = np.zeros(3)
    for index, source in enumerate(charges):
        if not isinstance(source, dict):
            raise ValueError(f"charge {index} must be an object.")
        source_position = _finite_vector(
            source.get("position"), f"charge {index} position",
        )
        charge = _finite_number(source.get("charge"), f"charge {index} value")
        displacement = position - source_position
        distance_squared = float(np.dot(displacement, displacement))
        if distance_squared <= 1e-24:
            raise ValueError(f"electric field is singular at charge {index}.")
        result += constant * charge * displacement / distance_squared**1.5
    return result


def magnetic_field_from_wire(
        point, start, end, current, *, segments=128,
        permeability=VACUUM_PERMEABILITY):
    """Approximate a finite straight wire's SI magnetic field via Biot-Savart."""
    position = _finite_vector(point, "field point")
    wire_start = _finite_vector(start, "wire start")
    wire_end = _finite_vector(end, "wire end")
    current = _finite_number(current, "current")
    permeability = _finite_number(permeability, "permeability")
    if permeability <= 0:
        raise ValueError("permeability must be positive.")
    if isinstance(segments, bool) or not isinstance(segments, int) \
            or not 1 <= segments <= 4096:
        raise ValueError("segments must be an integer between 1 and 4096.")
    length_vector = wire_end - wire_start
    if np.linalg.norm(length_vector) <= 1e-12:
        raise ValueError("wire start and end must be distinct.")
    dl = length_vector / segments
    midpoints = wire_start + (np.arange(segments)[:, None] + 0.5) * dl
    displacement = position - midpoints
    distances = np.linalg.norm(displacement, axis=1)
    if np.any(distances <= 1e-12):
        raise ValueError("magnetic field is singular on the current wire.")
    contributions = np.cross(dl, displacement) / distances[:, None]**3
    return permeability * current / (4 * math.pi) * contributions.sum(axis=0)


def plane_wave_fields(
        position, time, *, electric_amplitude=1.0, angular_frequency=1.0,
        wave_number=None, phase=0.0, phase_speed=SPEED_OF_LIGHT,
        propagation_direction=(1, 0, 0), polarization=(0, 1, 0)):
    """Return E and B vectors for a vacuum plane wave in SI-compatible units.

    ``polarization`` must be transverse to propagation_direction. The wave
    propagates in the supplied direction with B = direction × E / c.
    """
    point = _finite_vector(position, "wave position")
    direction = _finite_vector(propagation_direction, "propagation direction")
    polarization = _finite_vector(polarization, "polarization")
    time = _finite_number(time, "wave time")
    amplitude = _finite_number(electric_amplitude, "electric amplitude")
    omega = _finite_number(angular_frequency, "angular frequency")
    phase_speed = _finite_number(phase_speed, "phase speed")
    if phase_speed <= 0:
        raise ValueError("phase speed must be positive.")
    if wave_number is None:
        wave_number = omega / phase_speed
    wave_number = _finite_number(wave_number, "wave number")
    phase = _finite_number(phase, "wave phase")
    if amplitude < 0 or omega < 0 or wave_number < 0:
        raise ValueError("wave amplitude, angular frequency, and wave number must be non-negative.")
    if not math.isclose(
            omega, phase_speed * wave_number, rel_tol=1e-8, abs_tol=1e-12):
        raise ValueError("plane-wave parameters must satisfy omega = phase_speed * wave_number.")
    direction_norm = np.linalg.norm(direction)
    polarization_norm = np.linalg.norm(polarization)
    if direction_norm <= 1e-12 or polarization_norm <= 1e-12:
        raise ValueError("propagation direction and polarization must be non-zero.")
    direction /= direction_norm
    polarization /= polarization_norm
    if abs(float(np.dot(direction, polarization))) > 1e-8:
        raise ValueError("polarization must be perpendicular to propagation direction.")
    angle = wave_number * float(np.dot(direction, point)) - omega * time + phase
    electric = amplitude * math.cos(angle) * polarization
    magnetic = np.cross(direction, electric) / SPEED_OF_LIGHT
    return electric, magnetic


def _field_visual(item, *, magnetic):
    sources_key = "wires" if magnetic else "charges"
    sources = item.get(sources_key)
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"{sources_key} must be a non-empty list.")
    try:
        x_range = [float(value) for value in item.get("x_range", [-3, 3])]
        y_range = [float(value) for value in item.get("y_range", [-2, 2])]
        columns = item.get("columns", 13)
        rows = item.get("rows", 9)
        segments = item.get("segments", 64)
        arrow_min = float(item.get("arrow_min", 0.12))
        arrow_max = float(item.get("arrow_max", 0.42))
    except (TypeError, ValueError) as exc:
        raise ValueError("field grid, range, and arrow dimensions must be numeric.") from exc
    if (len(x_range) != 2 or len(y_range) != 2
            or not all(math.isfinite(v) for v in x_range + y_range)
            or x_range[0] >= x_range[1] or y_range[0] >= y_range[1]):
        raise ValueError("field x_range and y_range must be increasing finite pairs.")
    if (isinstance(columns, bool) or not isinstance(columns, int)
            or isinstance(rows, bool) or not isinstance(rows, int)
            or not 2 <= columns <= 20 or not 2 <= rows <= 20
            or rows * columns > 256):
        raise ValueError("field grid must have 2-20 rows and columns and at most 256 points.")
    if (isinstance(segments, bool) or not isinstance(segments, int)
            or not 1 <= segments <= 4096):
        raise ValueError("wire integration segments must be an integer between 1 and 4096.")
    if (not math.isfinite(arrow_min) or not math.isfinite(arrow_max)
            or arrow_min <= 0 or arrow_max < arrow_min):
        raise ValueError("field arrow lengths must be finite, positive, and ordered.")

    if magnetic:
        wires = []
        for index, wire in enumerate(sources):
            if not isinstance(wire, dict):
                raise ValueError(f"wire {index} must be an object.")
            wires.append((
                _finite_vector(wire.get("start"), f"wire {index} start"),
                _finite_vector(wire.get("end"), f"wire {index} end"),
                _finite_number(wire.get("current"), f"wire {index} current"),
            ))

        def field_at(point):
            result = np.zeros(3)
            for start, end, current in wires:
                result += magnetic_field_from_wire(
                    point, start, end, current,
                    segments=segments,
                )
            return result
    else:
        charges = []
        for index, charge in enumerate(sources):
            if not isinstance(charge, dict):
                raise ValueError(f"charge {index} must be an object.")
            charges.append({
                "position": _finite_vector(
                    charge.get("position"), f"charge {index} position",
                ),
                "charge": _finite_number(
                    charge.get("charge"), f"charge {index} value",
                ),
            })

        def field_at(point):
            return electric_field(point, charges)

    samples = []
    for y in np.linspace(y_range[0], y_range[1], rows):
        for x in np.linspace(x_range[0], x_range[1], columns):
            point = np.array([x, y, 0.0])
            if magnetic:
                singular = False
                for start, end, _ in wires:
                    segment = end - start
                    fraction = np.clip(
                        np.dot(point - start, segment) / np.dot(segment, segment),
                        0.0, 1.0,
                    )
                    if np.linalg.norm(point - (start + fraction * segment)) <= 1e-9:
                        singular = True
                        break
                if singular:
                    continue
            elif any(
                    np.linalg.norm(point - charge["position"]) <= 1e-12
                    for charge in charges):
                continue
            vector = field_at(point)
            samples.append((point, vector, float(np.linalg.norm(vector))))
    max_magnitude = max((sample[2] for sample in samples), default=0)

    color = item.get("color", "#4CC9F0" if not magnetic else "#E67E22")
    arrows = VGroup()
    for point, vector, magnitude in samples:
        if magnitude <= max_magnitude * 1e-10 or magnitude == 0:
            continue
        length = arrow_min + (arrow_max - arrow_min) * (
            magnitude / max_magnitude
        )
        end = point + vector / magnitude * length
        arrows.add(Arrow(
            point, end, buff=0, color=color, stroke_width=1.8,
            max_tip_length_to_length_ratio=0.28,
        ))

    source_marks = VGroup()
    if magnetic:
        for start, end, current in wires:
            wire = Line(start, end, color="#F1C40F", stroke_width=4)
            source_marks.add(wire)
            midpoint = (start + end) / 2
            source_marks.add(Text(
                f"I={current:g} A", font_size=14, color="#F1C40F",
            ).next_to(midpoint, np.array([0.0, 1.0, 0.0]), buff=0.12))
    else:
        for charge in charges:
            position = charge["position"]
            value = charge["charge"]
            mark_color = "#FF4B4B" if value > 0 else "#00D2FF"
            dot = Dot(position, radius=0.13, color=mark_color)
            label = Text(
                "+" if value > 0 else "−", font_size=17, color="#FFFFFF",
            ).move_to(position)
            source_marks.add(VGroup(dot, label))
    return VGroup(arrows, source_marks)


def _wave_visual(item):
    try:
        amplitude = float(item.get("amplitude", 1.0))
        frequency = float(item.get("frequency", 1.0))
        phase = float(item.get("phase", 0.0))
        length = float(item.get("length", config.frame_width * 0.78))
        speed = float(item.get("speed", 1.0))
        center = [float(value) for value in item.get("center", [0, 0, 0])]
        rate = float(item.get("playback_rate", 1.0))
        samples = item.get("samples", 100)
    except (TypeError, ValueError) as exc:
        raise ValueError("wave visual settings must be numeric.") from exc
    if not all(math.isfinite(v) for v in (
            amplitude, frequency, phase, length, speed, rate)):
        raise ValueError("wave visual settings must be finite.")
    if amplitude <= 0 or frequency <= 0 or length <= 0 or speed <= 0:
        raise ValueError("wave amplitude, frequency, length, and speed must be positive.")
    if (len(center) != 3 or not all(math.isfinite(value) for value in center)):
        raise ValueError("wave center must be a finite 3D point.")
    x_origin, y_origin, _ = center
    if isinstance(samples, bool) or not isinstance(samples, int) \
            or not 16 <= samples <= 512:
        raise ValueError("wave samples must be an integer between 16 and 512.")
    horizontal_bounds = (-config.frame_width / 2, config.frame_width / 2)
    vertical_bounds = (-config.frame_height / 2, config.frame_height / 2)
    if (x_origin - length / 2 < horizontal_bounds[0] + 0.2
            or x_origin + length / 2 > horizontal_bounds[1] - 0.2):
        raise ValueError("wave length and center must fit within the frame width.")
    if (y_origin + 1.75 * amplitude > vertical_bounds[1] - 0.2
            or y_origin - 3.5 * amplitude < vertical_bounds[0] + 0.2):
        raise ValueError("wave amplitude and center must fit within the frame height.")
    wavelength = speed / frequency
    wave_number = 2 * math.pi / wavelength
    omega = 2 * math.pi * frequency
    x_values = np.linspace(-length / 2, length / 2, samples)
    row_gap = amplitude * 2.5
    curve_e = VMobject(color=item.get("electric_color", "#4CC9F0"))
    curve_b = VMobject(color=item.get("magnetic_color", "#F1C40F"))

    def set_wave_points(mob, x_offset, t):
        points = [
            np.array([
                x_origin + x,
                y_origin + x_offset
                + amplitude * math.sin(wave_number * x - omega * t + phase),
                center[2],
            ])
            for x in x_values
        ]
        mob.set_points_as_corners(points)
        mob.set_stroke(width=3)
        return mob

    elapsed = 0.0
    set_wave_points(curve_e, 0, 0)
    set_wave_points(curve_b, -row_gap, 0)

    def advance(mob, dt):
        nonlocal elapsed
        elapsed += dt * rate
        set_wave_points(curve_e, 0, elapsed)
        set_wave_points(curve_b, -row_gap, elapsed)

    group = VGroup(
        Line(
            [x_origin - length / 2,             y_origin, center[2]],
            [x_origin + length / 2, y_origin, center[2]],
            color="#8A8F9C",
        ),
        Line(
            [x_origin - length / 2, y_origin - row_gap, center[2]],
            [x_origin + length / 2, y_origin - row_gap, center[2]],
            color="#8A8F9C",
        ),
        curve_e,
        curve_b,
        Text(
            "E field  |  E₀",
            font_size=18,
            color=item.get("electric_color", "#4CC9F0"),
        ).move_to([x_origin - length / 2 + 0.65, y_origin + amplitude * 1.75, center[2]]),
        Text(
            "B field  |  B₀ = E₀ / c",
            font_size=18,
            color=item.get("magnetic_color", "#F1C40F"),
        ).move_to([x_origin - length / 2 + 0.9, y_origin - row_gap + amplitude * 1.75, center[2]]),
        Arrow(
            [x_origin - 0.5, y_origin - row_gap - amplitude * 1.0, center[2]],
            [x_origin + 0.5, y_origin - row_gap - amplitude * 1.0, center[2]],
            buff=0,
            color="#2ECC71",
            stroke_width=3,
        ),
        Text(
            "propagation  →",
            font_size=16,
            color="#2ECC71",
        ).move_to([x_origin + 1.7, y_origin - row_gap - amplitude * 1.0, center[2]]),
    )
    group.add_updater(advance)
    return group


def build_electromagnetics_visual(item, *, kind):
    """Build a static-field or animated plane-wave graphic."""
    if kind == "electric_field":
        return _field_visual(item, magnetic=False)
    if kind == "magnetic_field":
        return _field_visual(item, magnetic=True)
    if kind == "electromagnetic_wave":
        return _wave_visual(item)
    raise ValueError(f"unsupported electromagnetics visual kind: {kind}.")
