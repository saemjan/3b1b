#!/usr/bin/env python3
"""electromagnetics_engine.py — gen-3 SI field core + storyboard visuals.

Layering: validation -> pure field rulers (Coulomb, Biot-Savart, plane wave)
-> adaptive representation (auto log-scale arrows, adaptive wire segments,
wavelength-driven wave sampling) -> manim route (lazy import).

Dependency stance (tools/backend_policy):
  * pure stdlib core = THE RULER (list math, adaptive segment doubling)
  * numpy = select library for vectorized Biot-Savart; gated by probe +
    parity witness + cost; degrades to pure on any error.

Frozen witnesses (selftest, headless):
  * Coulomb: |E| = k q / r^2 radial (single charge)
  * dipole bisector: E = k q d / (r^2 + (d/2)^2)^(3/2) along the axis
  * finite wire: B = (mu0 I / 2 pi r) * (L/2)/sqrt(r^2 + (L/2)^2)
    matched by the adaptive segment integrator (rel <= 1e-6)
  * plane wave: B = n x E / c, E . n = 0, omega = c k enforced
  * singularity / transversality / segment-bound guards raise
  * pure <-> numpy parity; determinism

Renderer contract v1: ROUTE_TABLE[type](scene, spec); skins via scene.ctx.
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

VACUUM_PERMITTIVITY = 8.8541878128e-12
VACUUM_PERMEABILITY = 1.25663706212e-6
SPEED_OF_LIGHT = 1 / math.sqrt(VACUUM_PERMITTIVITY * VACUUM_PERMEABILITY)
COULOMB_CONSTANT = 1 / (4 * math.pi * VACUUM_PERMITTIVITY)


# ---------------------------------------------------------------- validation
def _vec3(value, name):
    if isinstance(value, (list, tuple)) and len(value) == 3:
        try:
            v = [float(c) for c in value]
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a finite 3D vector.")
        if all(math.isfinite(c) for c in v):
            return v
    raise ValueError(f"{name} must be a finite 3D vector.")


def _num(value, name, minimum=None, nonzero=False):
    try:
        out = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"{name} must be a finite number.") from e
    if not math.isfinite(out) or (minimum is not None and out < minimum) \
            or (nonzero and out == 0):
        raise ValueError(f"{name} must be finite"
                         + (f" >= {minimum}" if minimum is not None else "")
                         + (" and non-zero" if nonzero else "") + ".")
    return out


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def _norm(a):
    return math.sqrt(_dot(a, a))


# ------------------------------------------------------------- field rulers
def electric_field(point, charges, coulomb_constant=COULOMB_CONSTANT):
    p = _vec3(point, "field point")
    k = _num(coulomb_constant, "Coulomb constant", minimum=0, nonzero=True)
    if not isinstance(charges, (list, tuple)) or not charges:
        raise ValueError("charges must be a non-empty list.")
    out = [0.0, 0.0, 0.0]
    for i, src in enumerate(charges):
        if not isinstance(src, dict):
            raise ValueError(f"charge {i} must be an object.")
        sp = _vec3(src.get("position"), f"charge {i} position")
        q = _num(src.get("charge"), f"charge {i} value")
        d = [p[j] - sp[j] for j in range(3)]
        r2 = _dot(d, d)
        if r2 <= 1e-24:
            raise ValueError(f"electric field is singular at charge {i}.")
        s = k * q / r2 ** 1.5
        out = [out[j] + s * d[j] for j in range(3)]
    return out


def wire_field(point, start, end, current, segments=128,
               permeability=VACUUM_PERMEABILITY):
    """Pure Biot-Savart over segment midpoints (the ruler)."""
    p = _vec3(point, "field point")
    a = _vec3(start, "wire start")
    b = _vec3(end, "wire end")
    i = _num(current, "current")
    mu = _num(permeability, "permeability", minimum=0, nonzero=True)
    if isinstance(segments, bool) or not isinstance(segments, int) \
            or not 1 <= segments <= 4096:
        raise ValueError("segments must be an integer 1..4096.")
    dl = [(b[j] - a[j]) / segments for j in range(3)]
    if _norm(dl) <= 1e-15:
        raise ValueError("wire start and end must be distinct.")
    out = [0.0, 0.0, 0.0]
    for s in range(segments):
        mid = [a[j] + (s + 0.5) * dl[j] for j in range(3)]
        d = [p[j] - mid[j] for j in range(3)]
        r = _norm(d)
        if r <= 1e-12:
            raise ValueError("magnetic field is singular on the current wire.")
        c = _cross(dl, d)
        f = mu * i / (4 * math.pi) / r ** 3
        out = [out[j] + f * c[j] for j in range(3)]
    return out


def adaptive_wire_field(point, start, end, current, tol=1e-9,
                        segments=32, permeability=VACUUM_PERMEABILITY):
    """Representation adapts: double segments until change < tol (capped)."""
    prev = wire_field(point, start, end, current, segments, permeability)
    while segments < 2048:
        segments *= 2
        cur = wire_field(point, start, end, current, segments, permeability)
        n = _norm(cur)
        if n <= 0 or _norm([cur[j] - prev[j] for j in range(3)]) <= tol * max(n, 1e-300):
            return cur, segments
        prev = cur
    return prev, segments


def wire_field_np(point, start, end, current, segments=128,
                  permeability=VACUUM_PERMEABILITY):
    """Select-library twin: vectorized midpoints."""
    np = _NP
    p = np.asarray(_vec3(point, "field point"))
    a = np.asarray(_vec3(start, "wire start"))
    b = np.asarray(_vec3(end, "wire end"))
    i = _num(current, "current")
    mu = _num(permeability, "permeability", minimum=0, nonzero=True)
    dl = (b - a) / segments
    mid = a + (np.arange(segments)[:, None] + 0.5) * dl
    d = p - mid
    r = np.linalg.norm(d, axis=1)
    if np.any(r <= 1e-12):
        raise ValueError("magnetic field is singular on the current wire.")
    contrib = np.cross(dl, d) / r[:, None] ** 3
    return [float(v) for v in (mu * i / (4 * math.pi) * contrib.sum(axis=0))]


def plane_wave_fields(position, time, *, amplitude=1.0, omega=1.0,
                      wave_number=None, phase=0.0,
                      phase_speed=SPEED_OF_LIGHT,
                      direction=(1, 0, 0), polarization=(0, 1, 0)):
    p = _vec3(position, "wave position")
    n = _vec3(direction, "propagation direction")
    pol = _vec3(polarization, "polarization")
    t = _num(time, "wave time")
    a = _num(amplitude, "amplitude", minimum=0)
    w = _num(omega, "angular frequency", minimum=0)
    c = _num(phase_speed, "phase speed", minimum=0, nonzero=True)
    k = w / c if wave_number is None else _num(wave_number, "wave number",
                                               minimum=0)
    if not math.isclose(w, c * k, rel_tol=1e-8, abs_tol=1e-12):
        raise ValueError("plane wave must satisfy omega = c * k.")
    nn, pn = _norm(n), _norm(pol)
    if nn <= 1e-12 or pn <= 1e-12:
        raise ValueError("direction and polarization must be non-zero.")
    n = [v / nn for v in n]
    pol = [v / pn for v in pol]
    if abs(_dot(n, pol)) > 1e-8:
        raise ValueError("polarization must be transverse to propagation.")
    ang = k * _dot(n, p) - w * t + _num(phase, "phase")
    e = [a * math.cos(ang) * v for v in pol]
    b = [v / c for v in _cross(n, e)]
    return e, b


def _numpy_parity():
    if _NP is None:
        return False
    fixture = ((0.0, 0.7, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 2.0), 3.0)
    for seg in (64, 257):
        a = wire_field(*fixture, segments=seg)
        b = wire_field_np(*fixture, segments=seg)
        if max(abs(x - y) for x, y in zip(a, b)) > 1e-12:
            return False
    return True


if bp is not None:
    bp.register("em", bp.OWN_TOOL,
                probe=lambda: (True, "own tool, stdlib only"),
                witness=lambda: True,
                speedup=lambda size: 1.0)
    bp.register("em", "numpy",
                probe=lambda: bp.probe_import("numpy", ("cross", "linalg")),
                witness=_numpy_parity,
                speedup=lambda size: size / 2048.0)


def _backend(n):
    if bp is None:
        return "pure"
    name, _ = bp.choose("em", size=n)
    return name if (name == "numpy" and _NP is not None) else "pure"


# ------------------------------------------------------------------ skin
def _skin(ctx):
    if ctx is not None:
        return ctx

    class _Fallback:
        def color(self, spec, role="primary"):
            return (spec or {}).get("color", "#4CC9F0")
        def place(self, i, n, spec, default=(0, 0, 0)):
            p = (spec or {}).get("center", list(default))
            return tuple(list(p) + [0.0] * (3 - len(p)))
        def stroke(self):
            return 2.0
        def dot(self, spec):
            return float((spec or {}).get("radius", 0.13))
        def font(self, base):
            return base
        def opacity(self):
            return 0.25
    return _Fallback()


# ------------------------------------------------------- field grid visual
def _field_visual(spec, sk, magnetic):
    from manim import Arrow, Dot, Line, Text, VGroup
    key = "wires" if magnetic else "charges"
    sources = spec.get(key)
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"{key} must be a non-empty list.")
    x0, x1 = (_num(v, "x_range") for v in (spec.get("x_range", [-3, 3])))
    y0, y1 = (_num(v, "y_range") for v in (spec.get("y_range", [-2, 2])))
    if x0 >= x1 or y0 >= y1:
        raise ValueError("field ranges must be increasing.")
    cols = int(_num(spec.get("columns", 13), "columns"))
    rows = int(_num(spec.get("rows", 9), "rows"))
    if not (2 <= cols <= 20 and 2 <= rows <= 20 and rows * cols <= 256):
        raise ValueError("field grid must be 2..20 per axis, <=256 points.")
    seg = int(_num(spec.get("segments", 128), "segments"))
    if not 1 <= seg <= 4096:
        raise ValueError("segments must be 1..4096.")
    lo = _num(spec.get("arrow_min", 0.12), "arrow_min", minimum=0, nonzero=True)
    hi = _num(spec.get("arrow_max", 0.42), "arrow_max", minimum=lo)

    wires, charges = [], []
    if magnetic:
        for i, w in enumerate(sources):
            wires.append((_vec3(w.get("start"), f"wire {i} start"),
                          _vec3(w.get("end"), f"wire {i} end"),
                          _num(w.get("current"), f"wire {i} current")))
    else:
        for i, c in enumerate(sources):
            charges.append((_vec3(c.get("position"), f"charge {i} position"),
                            _num(c.get("charge"), f"charge {i} value")))

    backend = _backend(rows * cols * seg)
    samples = []
    for r in range(rows):
        for c in range(cols):
            px = x0 + (x1 - x0) * c / (cols - 1)
            py = y0 + (y1 - y0) * r / (rows - 1)
            p = [px, py, 0.0]
            if magnetic:
                singular = False
                for a, b, _ in wires:
                    ab = [b[j] - a[j] for j in range(3)]
                    denom = _dot(ab, ab)
                    t = max(0.0, min(1.0, _dot([p[j] - a[j] for j in range(3)], ab) / denom))
                    close = [a[j] + t * ab[j] - p[j] for j in range(3)]
                    if _norm(close) <= 1e-9:
                        singular = True
                        break
                if singular:
                    continue
                v = [0.0, 0.0, 0.0]
                for a, b, i_cur in wires:
                    fv = (wire_field_np(p, a, b, i_cur, seg)
                          if backend == "numpy"
                          else wire_field(p, a, b, i_cur, seg))
                    v = [v[j] + fv[j] for j in range(3)]
            else:
                if any(_norm([cp[j] - p[j] for j in range(3)]) <= 1e-12
                       for cp, _ in charges):
                    continue
                v = electric_field(p, [{"position": cp, "charge": q}
                                       for cp, q in charges])
            samples.append((p, v, _norm(v)))

    mags = [m for _, _, m in samples]
    mx = max(mags, default=0.0)
    mn = min((m for m in mags if m > 0), default=0.0)
    log_scale = mx > 0 and mn > 0 and mx / mn > 1e2     # adapts to dynamic range
    col = sk.color(spec, "field" if magnetic else "primary")
    arrows = VGroup()
    for p, v, m in samples:
        if m <= mx * 1e-10:
            continue
        frac = math.log10(m / mn) / math.log10(mx / mn) if log_scale else m / mx
        length = lo + (hi - lo) * frac
        end = [p[j] + v[j] / m * length for j in range(3)]
        arrows.add(Arrow(p, end, buff=0, color=col,
                         stroke_width=sk.stroke() - 0.2,
                         max_tip_length_to_length_ratio=0.28))
    marks = VGroup()
    if magnetic:
        for a, b, i_cur in wires:
            mid = [(a[j] + b[j]) / 2 for j in range(3)]
            marks.add(Line(a, b, color=sk.color(spec, "accent"),
                           stroke_width=sk.stroke() + 2))
            marks.add(Text(f"I={i_cur:g} A", font_size=sk.font(14),
                           color=sk.color(spec, "accent")).next_to(mid, [0, 1, 0], buff=0.12))
    else:
        for cp, q in charges:
            ccol = sk.color(spec, "alert") if q > 0 else sk.color(spec, "secondary")
            marks.add(VGroup(Dot(cp, radius=sk.dot(spec), color=ccol),
                             Text("+" if q > 0 else "−", font_size=sk.font(17),
                                  color="#FFFFFF").move_to(cp)))
    print(f"[em] field backend={backend} log_scale={log_scale} "
          f"points={len(samples)}")
    return VGroup(arrows, marks)


# ------------------------------------------------------------- wave visual
def _wave_visual(spec, sk):
    from manim import Arrow, Line, Text, VGroup, VMobject
    amp = _num(spec.get("amplitude", 1.0), "amplitude", minimum=0, nonzero=True)
    freq = _num(spec.get("frequency", 1.0), "frequency", minimum=0, nonzero=True)
    length = _num(spec.get("length", 7.0), "length", minimum=0, nonzero=True)
    speed = _num(spec.get("speed", 1.0), "speed", minimum=0, nonzero=True)
    rate = _num(spec.get("playback_rate", 1.0), "playback_rate", minimum=0)
    center = _vec3(spec.get("center", [0, 0, 0]), "wave center")
    lam = speed / freq
    n = max(16, min(512, int(length / lam * 12) or 16))   # samples follow wavelength
    xs = [-length / 2 + length * i / (n - 1) for i in range(n)]
    k = 2 * math.pi / lam
    w = 2 * math.pi * freq
    gap = amp * 2.5
    e_col = sk.color(spec, "primary")
    b_col = sk.color(spec, "secondary")
    curve_e, curve_b = VMobject(color=e_col), VMobject(color=b_col)

    def set_points(mob, off, t):
        pts = [[center[0] + x,
                center[1] + off + amp * math.sin(k * x - w * t),
                center[2]] for x in xs]
        mob.set_points_as_corners(pts)
        mob.set_stroke(width=sk.stroke())
        return mob

    state = {"t": 0.0}
    set_points(curve_e, 0.0, 0.0)
    set_points(curve_b, -gap, 0.0)

    def advance(mob, dt):
        state["t"] += dt * rate
        set_points(curve_e, 0.0, state["t"])
        set_points(curve_b, -gap, state["t"])

    grp = VGroup(
        Line([center[0] - length / 2, center[1], center[2]],
             [center[0] + length / 2, center[1], center[2]],
             color=sk.color(spec, "ink"), stroke_width=1),
        Line([center[0] - length / 2, center[1] - gap, center[2]],
             [center[0] + length / 2, center[1] - gap, center[2]],
             color=sk.color(spec, "ink"), stroke_width=1),
        curve_e, curve_b,
        Text("E field", font_size=sk.font(17), color=e_col
             ).move_to([center[0] - length / 2 + 0.7,
                        center[1] + amp * 1.7, center[2]]),
        Text("B field = E / c", font_size=sk.font(17), color=b_col
             ).move_to([center[0] - length / 2 + 1.0,
                        center[1] - gap + amp * 1.7, center[2]]),
        Arrow([center[0] - 0.5, center[1] - gap - amp, center[2]],
              [center[0] + 0.5, center[1] - gap - amp, center[2]],
              buff=0, color=sk.color(spec, "accent"), stroke_width=sk.stroke()),
    )
    grp.add_updater(advance)
    print(f"[em] wave samples={n} lambda={lam:.3f}")
    return grp


def route_em(scene, spec):
    if not isinstance(spec, dict):
        raise ValueError("electromagnetics visual must be an object.")
    sk = _skin(getattr(scene, "ctx", None))
    kind = str(spec.get("kind", spec.get("type", ""))).lower()
    if kind == "electric_field":
        return _field_visual(spec, sk, magnetic=False)
    if kind == "magnetic_field":
        return _field_visual(spec, sk, magnetic=True)
    if kind == "electromagnetic_wave":
        return _wave_visual(spec, sk)
    raise ValueError(f"unsupported electromagnetics visual kind: {kind}.")


class _NullScene:
    ctx = None


def build_electromagnetics_visual(item, kind=None, scene=None):
    spec = dict(item)
    if kind:
        spec["kind"] = kind
    return route_em(scene if scene is not None else _NullScene(), spec)


ROUTE_TABLE = {k: route_em for k in
               ("electric_field", "magnetic_field", "electromagnetic_wave")}


# ------------------------------------------------------------ witnesses
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    q, r = 2e-9, 0.5
    e = electric_field([r, 0, 0], [{"position": [0, 0, 0], "charge": q}])
    expect = COULOMB_CONSTANT * q / r ** 2
    want("ruler:coulomb", abs(e[0] - expect) <= 1e-9 * expect
         and abs(e[1]) + abs(e[2]) <= 1e-12, str(e))

    d, qq, yy = 0.2, 1e-9, 0.9
    pair = [{"position": [-d / 2, 0, 0], "charge": qq},
            {"position": [d / 2, 0, 0], "charge": -qq}]
    eb = electric_field([0, yy, 0], pair)
    closed = COULOMB_CONSTANT * qq * d / (yy ** 2 + (d / 2) ** 2) ** 1.5
    want("ruler:dipole-bisector", abs(eb[0] + closed) <= 1e-9 * closed
         and abs(eb[1]) <= 1e-12, str(eb))

    I, L, rr = 3.0, 2.0, 0.4
    b, segs = adaptive_wire_field([0, rr, 0], [0, 0, -L / 2], [0, 0, L / 2], I)
    exact = (VACUUM_PERMEABILITY * I / (2 * math.pi * rr)) \
            * (L / 2) / math.sqrt(rr ** 2 + (L / 2) ** 2)
    want("ruler:finite-wire", abs(b[1] - exact) <= 1e-6 * exact,
         f"{b[1]:.6e} vs {exact:.6e} segs={segs}")

    e_w, b_w = plane_wave_fields([0.3, 0, 0], 1e-9, amplitude=2.0,
                                 omega=6e8, phase_speed=SPEED_OF_LIGHT)
    want("ruler:wave-B=E/c",
         abs(_norm(b_w) * SPEED_OF_LIGHT - _norm(e_w)) <= 1e-9 * _norm(e_w))
    want("ruler:wave-transverse", abs(_dot(e_w, [1, 0, 0])) <= 1e-12)

    for bad, label in (({"position": [0, 0, 0], "charge": 1.0}, "singular"),):
        try:
            electric_field([0, 0, 0], [bad])
            want(f"guard:{label}", False)
        except ValueError:
            want(f"guard:{label}", True)
    try:
        plane_wave_fields([0, 0, 0], 0.0, omega=1.0, wave_number=2.0)
        want("guard:omega!=ck", False)
    except ValueError:
        want("guard:omega!=ck", True)
    try:
        plane_wave_fields([0, 0, 0], 0.0, polarization=(1, 0, 0))
        want("guard:non-transverse", False)
    except ValueError:
        want("guard:non-transverse", True)
    want("determinism:wire",
         wire_field([0, 0.4, 0], [0, 0, -1], [0, 0, 1], 2.0, 64)
         == wire_field([0, 0.4, 0], [0, 0, -1], [0, 0, 1], 2.0, 64))
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
    sys.exit(1 if fails else 0)
