#!/usr/bin/env python3
"""linear_algebra_engine.py — gen-3 validated linear algebra core + visuals.

Dependency stance (tools/backend_policy):
  * "pure"  = own stdlib tool = THE RULER (list-of-lists elimination, <= 8x8)
  * "numpy" = select library, adopted only when probe+witness pass AND the
    cost model says n^3 pays for it (n >= 7). Degrades to pure on any error.

Witnesses (frozen closed forms, run headless in selftest / CI):
  * Strang ch.1: det(K_n) = n+1, det(T_n) = 1, det(B_n) = 0, det(C_n) = 0
    for the -1,2,-1 families (K fixed-fixed, T free-fixed, B free-free,
    C circulant) — machine-checked for n = 1..8
  * K3 solve ruler: K3 x = e2  =>  x = (1/2, 1, 1/2)
  * A A^-1 = I, dot/cross closed forms, pure<->numpy parity, determinism

Renderer contract v1: ROUTE_TABLE["linear_algebra"](scene, spec).
Look is skinned from scene.ctx (style genome); explicit spec colors still
win (teacher override). No manim/numpy import at module top.
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

MAX_N = 8
_EPS = 1e-12
_ACCEL_N = 6          # n >= 7 -> numpy pays (cost model size = n^3)


# ---------------------------------------------------------------- validation
def _vector(value, name, dimensions=(2, 3)):
    if isinstance(value, (list, tuple)) and len(value) in dimensions:
        try:
            vec = [float(c) for c in value]
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a finite vector.")
        if all(math.isfinite(c) for c in vec):
            return vec
    allowed = " or ".join(str(d) for d in dimensions)
    raise ValueError(f"{name} must be a finite {allowed}D vector.")


def _finite(value, name):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite number.")
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number.")
    return number


def _matrix(value, name="matrix", square=False, max_n=MAX_N):
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{name} must be a list of rows.")
    rows = []
    width = None
    for r in value:
        if not isinstance(r, (list, tuple)):
            raise ValueError(f"{name} rows must be lists.")
        row = []
        for c in r:
            row.append(_finite(c, name))
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ValueError(f"{name} rows must share one width.")
        rows.append(row)
    n, m = len(rows), width or 0
    if not 1 <= n <= max_n or not 1 <= m <= max_n:
        raise ValueError(f"{name} dimensions must be 1..{max_n}.")
    if square and n != m:
        raise ValueError(f"{name} must be square.")
    return rows


# ------------------------------------------------------- pure core (ruler)
def vector_add(left, right):
    a, b = _vector(left, "left vector"), _vector(right, "right vector")
    if len(a) != len(b):
        raise ValueError("vector dimensions must match.")
    return [x + y for x, y in zip(a, b)]


def dot_product(left, right):
    a, b = _vector(left, "left vector"), _vector(right, "right vector")
    if len(a) != len(b):
        raise ValueError("vector dimensions must match.")
    return sum(x * y for x, y in zip(a, b))


def cross_product(left, right):
    a, b = _vector(left, "left vector"), _vector(right, "right vector")
    if len(a) != len(b):
        raise ValueError("vector dimensions must match.")
    if len(a) == 2:
        return a[0] * b[1] - a[1] * b[0]
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def _det_pure(rows):
    n = len(rows)
    m = [list(r) for r in rows]
    sign, det = 1.0, 1.0
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) <= _EPS:
            return 0.0
        if piv != col:
            m[col], m[piv] = m[piv], m[col]
            sign = -sign
        det *= m[col][col]
        inv = 1.0 / m[col][col]
        for r in range(col + 1, n):
            f = m[r][col] * inv
            if f:
                for c in range(col, n):
                    m[r][c] -= f * m[col][c]
    return sign * det


def _solve_pure(rows, rhs):
    n = len(rows)
    a = [list(r) + [rhs[i]] for i, r in enumerate(rows)]
    tol = _EPS * max(1.0, max(abs(v) for r in rows for v in r)) * n
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) <= tol:
            raise ValueError("matrix is singular; system has no unique solution.")
        if piv != col:
            a[col], a[piv] = a[piv], a[col]
        inv = 1.0 / a[col][col]
        for c in range(col, n + 1):
            a[col][c] *= inv
        for r in range(n):
            if r != col and a[r][col]:
                f = a[r][col]
                for c in range(col, n + 1):
                    a[r][c] -= f * a[col][c]
    return [a[i][n] for i in range(n)]


def _inv_pure(rows):
    n = len(rows)
    eye = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    cols = []
    for j in range(n):
        cols.append(_solve_pure(rows, [eye[i][j] for i in range(n)]))
    return [[cols[j][i] for j in range(n)] for i in range(n)]


def _matmul_pure(a, b):
    n, k, m = len(a), len(b), len(b[0])
    if k != len(a[0]) or len(b[0]) != m:
        raise ValueError("matrix shapes must be compatible.")
    bt = list(zip(*b))
    return [[sum(a[i][t] * bt[j][t] for t in range(k)) for j in range(m)]
            for i in range(n)]


# ------------------------------------------------- numpy core (select lib)
def _det_numpy(rows):
    return float(_NP.linalg.det(_NP.asarray(rows, dtype=float)))


def _solve_numpy(rows, rhs):
    try:
        return [float(v) for v in
                _NP.linalg.solve(_NP.asarray(rows, dtype=float),
                                 _NP.asarray(rhs, dtype=float))]
    except _NP.linalg.LinAlgError as e:
        raise ValueError(f"matrix is singular; system has no unique solution. ({e})")


def _inv_numpy(rows):
    try:
        return [[float(v) for v in row] for row in
                _NP.linalg.inv(_NP.asarray(rows, dtype=float))]
    except _NP.linalg.LinAlgError as e:
        raise ValueError(f"matrix is singular and has no inverse. ({e})")


def _backend(n):
    if bp is None or n <= _ACCEL_N or _NP is None:
        return "pure"
    name, _ = bp.choose("linalg", size=n * n * n)
    return name if (name == "numpy" and _NP is not None) else "pure"


def determinant(matrix):
    rows = _matrix(matrix, square=True)
    if _backend(len(rows)) == "numpy":
        try:
            return _det_numpy(rows)
        except Exception:
            pass
    return _det_pure(rows)


def solve_linear_system(matrix, right_hand_side):
    rows = _matrix(matrix, square=True)
    rhs = _vector(right_hand_side, "right_hand_side",
                  dimensions=tuple(range(1, MAX_N + 1)))
    if len(rhs) != len(rows):
        raise ValueError("right_hand_side length must match matrix rows.")
    if _backend(len(rows)) == "numpy":
        try:
            return _solve_numpy(rows, rhs)
        except ValueError:
            raise
        except Exception:
            pass
    return _solve_pure(rows, rhs)


def matrix_inverse(matrix):
    rows = _matrix(matrix, square=True)
    if _backend(len(rows)) == "numpy":
        try:
            return _inv_numpy(rows)
        except ValueError:
            raise
        except Exception:
            pass
    return _inv_pure(rows)


def matrix_vector_product(matrix, vector):
    rows = _matrix(matrix)
    vec = _vector(vector, "vector", dimensions=tuple(range(1, MAX_N + 1)))
    if len(vec) != len(rows[0]):
        raise ValueError("matrix columns must match vector dimensions.")
    return [dot_product(r, vec) for r in rows]


def matrix_multiply(left, right):
    return _matmul_pure(_matrix(left, "left matrix"),
                        _matrix(right, "right matrix"))


# ------------------------------------------------------- backend witnesses
def _k(n):  # Strang fixed-fixed second-difference matrix
    return [[2.0 if i == j else -1.0 if abs(i - j) == 1 else 0.0
             for j in range(n)] for i in range(n)]


def _t(n):  # free-fixed (top entry 1)
    m = _k(n)
    m[0][0] = 1.0
    return m


def _b(n):  # free-free (both ends 1) -> singular
    m = _k(n)
    m[0][0] = 1.0
    m[n - 1][n - 1] = 1.0
    return m


def _c(n):  # circulant -> singular
    m = _k(n)
    m[0][n - 1] = -1.0
    m[n - 1][0] = -1.0
    return m


def _numpy_parity() -> bool:
    if _NP is None:
        return False
    fixtures = [_k(8), _t(8), _c(7)]
    for rows in fixtures:
        if abs(_det_pure(rows) - _det_numpy(rows)) > 1e-6:
            return False
    rhs = [1.0, 2.0, 3.0, 1.0, 2.0, 3.0, 1.0, 2.0]
    a = _solve_pure(_k(8), rhs)
    b = _solve_numpy(_k(8), rhs)
    return max(abs(x - y) for x, y in zip(a, b)) <= 1e-8


if bp is not None:
    bp.register("linalg", bp.OWN_TOOL,
                probe=lambda: (True, "own tool, stdlib only"),
                witness=lambda: True,
                speedup=lambda size: 1.0)
    bp.register("linalg", "numpy",
                probe=lambda: bp.probe_import("numpy", ("linalg", "asarray")),
                witness=_numpy_parity,
                speedup=lambda size: size / (_ACCEL_N + 1) ** 3)


# ------------------------------------------------------------- selftest
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    for n in range(1, MAX_N + 1):
        want(f"ruler:detK{n}", abs(_det_pure(_k(n)) - (n + 1)) <= 1e-9,
             f"got {_det_pure(_k(n))}")
        want(f"ruler:detT{n}", abs(_det_pure(_t(n)) - 1.0) <= 1e-9)
        if n >= 2:
            want(f"ruler:detB{n}", abs(_det_pure(_b(n))) <= 1e-9)
            want(f"ruler:detC{n}", abs(_det_pure(_c(n))) <= 1e-9)
    x = _solve_pure(_k(3), [0.0, 1.0, 0.0])
    want("ruler:solveK3", all(abs(a - b) <= 1e-12
                              for a, b in zip(x, [0.5, 1.0, 0.5])), str(x))
    inv = matrix_inverse(_k(4))
    prod = _matmul_pure(_k(4), inv)
    want("ruler:inverse", all(abs(prod[i][j] - (1.0 if i == j else 0.0)) <= 1e-9
                              for i in range(4) for j in range(4)))
    want("dot", dot_product([1, 2], [3, 4]) == 11)
    want("cross2d", cross_product([1, 2], [3, 4]) == -2)
    want("cross3d", cross_product([1, 0, 0], [0, 1, 0]) == [0, 0, 1])
    want("add", vector_add([1, 2], [3, 4]) == [4, 6])
    try:
        solve_linear_system(_b(4), [1, 0, 0, 0])
        want("singular-raises", False)
    except ValueError:
        want("singular-raises", True)
    want("determinism", _det_pure(_k(6)) == _det_pure(_k(6)))
    if _NP is not None:
        want("parity:numpy", _numpy_parity())
    else:
        want("parity:numpy", True, "skipped (numpy absent)")
    if bp is not None:
        want("policy:small->pure", bp.choose("linalg", size=8)[0] == "pure")
    return checks


# ------------------------------------------------------- visuals (lazy manim)
def _skin(ctx):
    class _Fallback:
        def color(self, spec, role="primary"):
            return (spec or {}).get("color", "#4CC9F0")
        def place(self, i, n, spec, default=(0, 0, 0)):
            p = (spec or {}).get("center", spec.get("pos") if spec else None) or list(default)
            return tuple(list(p) + [0.0] * (3 - len(p)))
        def stroke(self):
            return 2.0
        def dot(self, spec):
            return float((spec or {}).get("radius", 0.045))
        def font(self, base):
            return base
        def opacity(self):
            return 0.2
    return ctx if ctx is not None else _Fallback()


def _col(sk, spec, key, role, default):
    if spec.get(key):
        return spec[key]
    if spec.get("color"):
        return spec["color"]
    try:
        return sk.color({"role": role}, role)
    except Exception:
        return default


def _axes(sk, center, extent, spec):
    from manim import Line
    ink = _col(sk, spec, "axis_color", "ink", "#555B66")
    return [
        Line(center + [-extent, 0, 0], center + [extent, 0, 0],
             color=ink, stroke_width=sk.stroke()),
        Line(center + [0, -extent * 0.8, 0], center + [0, extent * 0.8, 0],
             color=ink, stroke_width=sk.stroke()),
    ]


def _arrow(sk, origin, vec2, color, label, scale):
    from manim import Arrow, Dot, Text, VGroup
    import numpy as _np_local  # manim env already provides vectors; keep stdlib math
    end = [origin[0] + vec2[0] * scale, origin[1] + vec2[1] * scale, 0.0]
    if math.hypot(end[0] - origin[0], end[1] - origin[1]) < 1e-8:
        pt = Dot(origin, radius=sk.dot(None), color=color)
        return VGroup(pt, Text(label, font_size=sk.font(18), color=color)
                      .next_to(pt, [1.0, 1.0, 0.0]))
    ar = Arrow(origin, end, buff=0, color=color, stroke_width=sk.stroke() + 2,
               max_tip_length_to_length_ratio=0.18)
    lb = Text(label, font_size=sk.font(18), color=color).next_to(end, [1, 1, 0], buff=0.08)
    return VGroup(ar, lb)


def _draw_vectors(spec, sk):
    from manim import DashedLine, Text, VGroup
    a = _vector(spec.get("a"), "a", dimensions=(2,))
    b = _vector(spec.get("b"), "b", dimensions=(2,))
    op = str(spec.get("operation", "vectors")).lower()
    center = sk.place(0, 1, spec, (0, 0, 0))
    scale = _finite(spec.get("scale", 1.0), "scale")
    extent = max(math.hypot(*a), math.hypot(*b),
                 math.hypot(a[0] + b[0], a[1] + b[1]), 1.0) * scale * 1.25
    ca = _col(sk, spec, "a_color", "primary", "#4CC9F0")
    cb = _col(sk, spec, "b_color", "secondary", "#F1C40F")
    cr = _col(sk, spec, "result_color", "accent", "#2ECC71")
    group = VGroup(*_axes(sk, center, extent, spec),
                   _arrow(sk, center, a, ca, "a", scale),
                   _arrow(sk, center, b, cb, "b", scale))
    below = [center[0], center[1] - extent - 0.35, 0.0]
    if op == "vectors":
        res = [a[0] + b[0], a[1] + b[1]]
        head = [center[0] + a[0] * scale, center[1] + a[1] * scale, 0.0]
        tail = [center[0] + res[0] * scale, center[1] + res[1] * scale, 0.0]
        group.add(DashedLine(center, head, color=ca, stroke_width=1.5),
                  DashedLine(head, tail, color=cb, stroke_width=1.5),
                  _arrow(sk, center, res, cr, "a + b", scale),
                  Text(f"a + b = ({res[0]:g}, {res[1]:g})",
                       font_size=sk.font(20), color=cr).move_to(below))
    elif op == "dot":
        value = dot_product(a, b)
        na, nb = math.hypot(*a), math.hypot(*b)
        if na * nb == 0:
            angle = "undefined"
        else:
            cosv = max(-1.0, min(1.0, value / (na * nb)))
            angle = f"{math.degrees(math.acos(cosv)):.1f}°"
        group.add(Text(f"a · b = {value:g}    θ = {angle}",
                       font_size=sk.font(22), color=cr).move_to(below))
    elif op == "cross":
        value = cross_product(a, b)
        group.add(Text(f"a × b = {value:g}  (signed z-component)",
                       font_size=sk.font(20),
                       color=cr if value >= 0 else _col(sk, spec, "alert_color", "alert", "#FF4B4B")
                       ).move_to(below))
    else:
        raise ValueError("vector operation must be vectors, dot, or cross.")
    return group


def _draw_determinant(spec, sk):
    from manim import Line, Polygon, Text, VGroup
    rows = _matrix(spec.get("matrix"), "determinant matrix", square=True, max_n=2)
    if len(rows) != 2:
        raise ValueError("determinant visual requires a finite 2x2 matrix.")
    value = determinant(rows)
    center = sk.place(0, 1, spec, (0, 0, 0))
    scale = _finite(spec.get("scale", 1.0), "scale")
    col1, col2 = [rows[0][0], rows[1][0]], [rows[0][1], rows[1][1]]
    peak = max(math.hypot(*col1), math.hypot(*col2)) * scale
    if peak > 2.7:
        scale *= 2.7 / peak
    ea = [center[0] + col1[0] * scale, center[1] + col1[1] * scale, 0.0]
    eb = [center[0] + col2[0] * scale, center[1] + col2[1] * scale, 0.0]
    es = [ea[0] + eb[0] - center[0], ea[1] + eb[1] - center[1], 0.0]
    area = _col(sk, spec, "area_color", "accent",
                "#2ECC71" if value >= 0 else "#FF4B4B")
    return VGroup(
        Line(center + [-3, 0, 0], center + [3, 0, 0], color="#555B66", stroke_width=1),
        Line(center + [0, -2.5, 0], center + [0, 2.5, 0], color="#555B66", stroke_width=1),
        Polygon(center, ea, es, eb, color=area, fill_color=area,
                fill_opacity=sk.opacity(), stroke_width=sk.stroke()),
        _arrow(sk, center, col1, _col(sk, spec, "a_color", "primary", "#4CC9F0"), "column 1", scale),
        _arrow(sk, center, col2, _col(sk, spec, "b_color", "secondary", "#F1C40F"), "column 2", scale),
        Text(f"det(A) = {value:g}    signed area = {value:g}",
             font_size=sk.font(21), color=area).move_to([center[0], center[1] - 3.2, 0]),
    )


def _draw_transform(spec, sk):
    from manim import DashedLine, Line, Polygon, Text, VGroup
    rows = _matrix(spec.get("matrix"), "transform matrix", square=True, max_n=2)
    if len(rows) != 2:
        raise ValueError("matrix transform visual requires a 2x2 matrix.")
    op = str(spec.get("operation", "transform")).lower()
    vector = result = None
    if op == "matrix_vector":
        vector = _vector(spec.get("vector"), "vector", dimensions=(2,))
        result = matrix_vector_product(rows, vector)
    center = sk.place(0, 1, spec, (0, 0, 0))
    scale = _finite(spec.get("scale", 1.0), "scale")
    c1, c2 = [rows[0][0], rows[1][0]], [rows[0][1], rows[1][1]]
    extent = max(math.hypot(c1[0] + c2[0], c1[1] + c2[1]),
                 math.hypot(*c1), math.hypot(*c2), 1.0)
    if vector is not None:
        extent = max(extent, math.hypot(*vector), math.hypot(*result))
    scale *= min(1.0, 2.6 / (extent * scale))
    corners = [center,
               [center[0] + c1[0] * scale, center[1] + c1[1] * scale, 0],
               [center[0] + (c1[0] + c2[0]) * scale, center[1] + (c1[1] + c2[1]) * scale, 0],
               [center[0] + c2[0] * scale, center[1] + c2[1] * scale, 0]]
    area = _col(sk, spec, "area_color", "accent", "#2ECC71")
    group = VGroup(
        Line(center + [-3, 0, 0], center + [3, 0, 0], color="#555B66", stroke_width=1),
        Line(center + [0, -2.5, 0], center + [0, 2.5, 0], color="#555B66", stroke_width=1),
        Polygon(*corners, color=area, fill_color=area,
                fill_opacity=sk.opacity() * 0.7, stroke_width=sk.stroke()),
        _arrow(sk, center, c1, _col(sk, spec, "a_color", "primary", "#4CC9F0"), "A e1", scale),
        _arrow(sk, center, c2, _col(sk, spec, "b_color", "secondary", "#F1C40F"), "A e2", scale),
    )
    if vector is not None:
        group.add(
            DashedLine(center, [center[0] + vector[0] * scale,
                                center[1] + vector[1] * scale, 0],
                       color="#8A8F9C", stroke_width=1.5),
            _arrow(sk, center, result, _col(sk, spec, "alert_color", "alert", "#FF4B4B"), "A v", scale),
            Text(f"A v = ({result[0]:g}, {result[1]:g})",
                 font_size=sk.font(19),
                 color=_col(sk, spec, "alert_color", "alert", "#FF4B4B")
                 ).move_to([center[0], center[1] - 3.0, 0]),
        )
    else:
        group.add(Text(f"det(A) = {determinant(rows):g}", font_size=sk.font(20),
                       color=area).move_to([center[0], center[1] - 3.0, 0]))
    return group


def _draw_solve(spec, sk):
    from manim import DOWN, Text, VGroup
    rows = _matrix(spec.get("matrix"), "system matrix", square=True, max_n=2)
    if len(rows) != 2:
        raise ValueError("linear-system visual requires a 2x2 matrix.")
    rhs = _vector(spec.get("rhs"), "rhs", dimensions=(2,))
    sol = solve_linear_system(rows, rhs)
    center = sk.place(0, 1, spec, (0, 0, 0))
    ink = _col(sk, spec, "ink_color", "ink", "#F2F3F5")
    ok = _col(sk, spec, "result_color", "accent", "#2ECC71")
    r1 = Text(f"{rows[0][0]:g}x + {rows[0][1]:g}y = {rhs[0]:g}",
              font_size=sk.font(24), color=ink)
    r2 = Text(f"{rows[1][0]:g}x + {rows[1][1]:g}y = {rhs[1]:g}",
              font_size=sk.font(24), color=ink)
    rs = Text(f"x = {sol[0]:g}     y = {sol[1]:g}", font_size=sk.font(26), color=ok)
    return VGroup(r1, r2, rs).arrange(DOWN, buff=0.42).move_to(center)


def route_linear_algebra(scene, spec):
    if not isinstance(spec, dict):
        raise ValueError("linear algebra visual must be an object.")
    sk = _skin(getattr(scene, "ctx", None))
    op = str(spec.get("operation", "vectors")).lower()
    if op in ("vectors", "dot", "cross"):
        return _draw_vectors(dict(spec, operation=op), sk)
    if op == "determinant":
        return _draw_determinant(spec, sk)
    if op in ("matrix_vector", "transform"):
        return _draw_transform(dict(spec, operation=op), sk)
    if op == "solve":
        return _draw_solve(spec, sk)
    raise ValueError("linear algebra operation must be vectors, dot, cross, "
                     "determinant, matrix_vector, transform, or solve.")


def build_linear_algebra_visual(item, scene=None):
    """Legacy-compatible entry point (no scene => fallback skin)."""
    return route_linear_algebra(scene if scene is not None else _NullScene(), item)


class _NullScene:
    ctx = None


ROUTE_TABLE = {"linear_algebra": route_linear_algebra}

if __name__ == "__main__":
    fails = 0
    for name, ok, detail in selftest():
        print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
        fails += 0 if ok else 1
    sys.exit(1 if fails else 0)
