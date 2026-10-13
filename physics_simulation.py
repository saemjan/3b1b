"""Small, deterministic 2D Newtonian simulator for renderer primitives."""
from __future__ import annotations

import math

import numpy as np


def _vector(value, name):
    try:
        result = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a two-dimensional vector.") from exc
    if result.shape != (2,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain two finite numbers.")
    return result


def _finite_number(value, name, *, minimum=None):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number.") from exc
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        suffix = f" >= {minimum}" if minimum is not None else ""
        raise ValueError(f"{name} must be finite and{suffix}.")
    return result


def _validate(bodies, forces):
    if not isinstance(bodies, list) or not bodies:
        raise ValueError("physics_simulation needs at least one body.")
    if not isinstance(forces, list):
        raise ValueError("physics_simulation forces must be a list.")

    masses = []
    initial = []
    for index, body in enumerate(bodies):
        if not isinstance(body, dict):
            raise ValueError(f"Body {index} must be an object.")
        mass = _finite_number(body.get("mass", 1.0), f"body {index} mass",
                              minimum=0.0)
        if mass == 0:
            raise ValueError(f"Body {index} mass must be greater than zero.")
        position = _vector(body.get("position", [0, 0]),
                           f"body {index} position")
        velocity = _vector(body.get("velocity", [0, 0]),
                           f"body {index} velocity")
        masses.append(mass)
        initial.append(np.concatenate((position, velocity)))

    normalized = []
    count = len(bodies)
    for index, force in enumerate(forces):
        if not isinstance(force, dict):
            raise ValueError(f"Force {index} must be an object.")
        kind = str(force.get("type", "")).lower()
        entry = dict(force)
        entry["type"] = kind
        targets = force.get("bodies", list(range(count)))
        if not isinstance(targets, list) or any(
                not isinstance(target, int) or not 0 <= target < count
                for target in targets):
            raise ValueError(f"Force {index} has invalid body indices.")
        entry["bodies"] = targets

        if kind == "uniform_acceleration":
            entry["acceleration"] = _vector(
                force.get("acceleration"), f"force {index} acceleration",
            )
        elif kind == "linear_drag":
            entry["coefficient"] = _finite_number(
                force.get("coefficient"), f"force {index} coefficient",
                minimum=0.0,
            )
        elif kind == "spring":
            body_index = force.get("body")
            other_index = force.get("other")
            if not isinstance(body_index, int) or not 0 <= body_index < count:
                raise ValueError(f"Spring {index} has an invalid body index.")
            if other_index is not None and (
                    not isinstance(other_index, int)
                    or not 0 <= other_index < count
                    or other_index == body_index):
                raise ValueError(f"Spring {index} has an invalid other index.")
            if other_index is None and "anchor" not in force:
                raise ValueError(f"Spring {index} needs an anchor or other body.")
            entry["body"] = body_index
            entry["other"] = other_index
            if other_index is None:
                entry["anchor"] = _vector(
                    force["anchor"], f"spring {index} anchor",
                )
            entry["stiffness"] = _finite_number(
                force.get("stiffness"), f"spring {index} stiffness",
                minimum=0.0,
            )
            entry["rest_length"] = _finite_number(
                force.get("rest_length", 0.0), f"spring {index} rest_length",
                minimum=0.0,
            )
            entry["damping"] = _finite_number(
                force.get("damping", 0.0), f"spring {index} damping",
                minimum=0.0,
            )
        elif kind == "central_gravity":
            source = force.get("source")
            if not isinstance(source, int) or not 0 <= source < count:
                raise ValueError(
                    f"Central gravity {index} has an invalid source index."
                )
            entry["source"] = source
            entry["mu"] = _finite_number(
                force.get("mu"), f"central gravity {index} mu",
                minimum=0.0,
            )
        else:
            raise ValueError(
                f"Unsupported force type '{kind}'. Supported types are "
                "uniform_acceleration, linear_drag, spring, and "
                "central_gravity."
            )
        normalized.append(entry)
    return np.asarray(masses), np.asarray(initial), normalized


def accelerations(state, masses, forces):
    """Evaluate net acceleration for each body at a flattened RK state."""
    body_states = np.asarray(state, dtype=float).reshape(len(masses), 4)
    result = np.zeros((len(masses), 2), dtype=float)
    positions = body_states[:, :2]
    velocities = body_states[:, 2:]

    for force in forces:
        kind = force["type"]
        if kind == "uniform_acceleration":
            result[force["bodies"]] += force["acceleration"]
        elif kind == "linear_drag":
            coefficient = force["coefficient"]
            for target in force["bodies"]:
                result[target] -= coefficient * velocities[target] / masses[target]
        elif kind == "spring":
            body_index = force["body"]
            other_index = force["other"]
            if other_index is None:
                displacement = positions[body_index] - force["anchor"]
                anchor_velocity = np.zeros(2)
            else:
                displacement = positions[body_index] - positions[other_index]
                anchor_velocity = velocities[other_index]
            length = np.linalg.norm(displacement)
            if length <= 1e-12:
                continue
            direction = displacement / length
            relative_speed = np.dot(
                velocities[body_index] - anchor_velocity, direction,
            )
            magnitude = (
                -force["stiffness"] * (length - force["rest_length"])
                - force["damping"] * relative_speed
            )
            applied = magnitude * direction
            result[body_index] += applied / masses[body_index]
            if other_index is not None:
                result[other_index] -= applied / masses[other_index]
        elif kind == "central_gravity":
            source = force["source"]
            for target in force["bodies"]:
                if target == source:
                    continue
                displacement = positions[source] - positions[target]
                distance = np.linalg.norm(displacement)
                if distance <= 1e-12:
                    raise ValueError(
                        "Central-gravity source and target positions coincide."
                    )
                result[target] += (
                    force["mu"] * displacement / distance ** 3
                )
    if not np.all(np.isfinite(result)):
        raise ValueError("Physics simulation produced non-finite acceleration.")
    return result


def simulate_system(bodies, forces, duration, steps=600):
    """Return validated bodies, forces, and RK4 states shaped (steps+1,n,4)."""
    duration = _finite_number(duration, "duration", minimum=0.0)
    if duration == 0:
        raise ValueError("duration must be greater than zero.")
    if not isinstance(steps, int) or not 2 <= steps <= 10000:
        raise ValueError("steps must be an integer from 2 through 10000.")
    masses, initial, normalized_forces = _validate(bodies, forces)
    dt = duration / steps
    states = np.empty((steps + 1, len(masses), 4), dtype=float)
    state = initial.reshape(-1)
    states[0] = state.reshape(len(masses), 4)

    def derivative(current):
        current_bodies = current.reshape(len(masses), 4)
        return np.column_stack((
            current_bodies[:, 2:],
            accelerations(current, masses, normalized_forces),
        )).reshape(-1)

    for step in range(steps):
        k1 = derivative(state)
        k2 = derivative(state + dt * k1 / 2)
        k3 = derivative(state + dt * k2 / 2)
        k4 = derivative(state + dt * k3)
        state = state + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        if not np.all(np.isfinite(state)):
            raise ValueError(
                f"Physics simulation diverged at step {step + 1}; "
                "reduce duration, increase steps, or review force parameters."
            )
        states[step + 1] = state.reshape(len(masses), 4)
    return masses, normalized_forces, states
