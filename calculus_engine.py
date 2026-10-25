#!/usr/bin/env python3
"""calculus_engine.py — gen-3 single-variable calculus core + visuals.

Layering (xv6-style): validation -> expression compiler -> numeric rulers
(Richardson derivative, adaptive Simpson, Riemann sums) -> adaptive
representation -> manim route (lazy import).

Dependency stance (tools/backend_policy):
  * pure stdlib core = THE RULER (AST walker, no eval, no numpy)
  * numpy = select library for vectorized sampling; adopted only when
    probe + parity witness + cost gates pass; degrades to pure on error.

Frozen witnesses (selftest, headless):
  * d/dx sin = cos, d/dx x^3 = 3x^2, d/dx e^x = e^x   (Richardson <= 1e-8)
  * int_0^pi sin = 2, int_0^1 x^2 = 1/3, int_0^2 e^x = e^2 - 1 (<= 1e-9)
  * midpoint rule exact on linears; left rule on x over [0,1] = (n-1)/(2n)
  * sin(x)^2 + cos(x)^2 = 1; forbidden AST nodes / huge exponents rejected
  * pure <-> numpy parity on frozen grids; determinism

Renderer contract v1: ROUTE_TABLE[type](scene, spec); skins via scene.ctx
(style genome); explicit spec colors remain teacher overrides.
"""
from __future__ import annotations

import ast
import math
import operator
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

_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub,
           ast.Mult: operator.mul, ast.Div: operator.truediv,
           ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"abs": abs, "acos": math.acos, "asin": math.asin,
          "atan": math.atan, "ceil": math.ceil, "cos": math.cos,
          "cosh": math.cosh, "exp": math.exp, "floor": math.floor,
          "log": math.log, "sin": math.sin, "sinh": math.sinh,
          "sqrt": math.sqrt, "tan": math.tan, "tanh": math.tanh}
_CONSTS = {"pi": math.pi, "e": math.e}
_MAX_EXP = 64


# ------------------------------------------------------- expression compiler
def _validate_node(node, depth=0):
    if depth > 24:
        raise ValueError("calculus expression nests too deeply.")
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("calculus expressions only allow real numbers.")
        if not math.isfinite(float(node.value)):
            raise ValueError("calculus constants must be finite.")
        return
    if isinstance(node, ast.Name):
        if node.id != "x" and node.id not in _CONSTS:
            raise ValueError(f"unsupported name in calculus expression: {node.id}.")
        return
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        if isinstance(node.op, ast.Pow):
            rhs = node.right
            if not (isinstance(rhs, ast.Constant)
                    and abs(float(rhs.value)) <= _MAX_EXP):
                raise ValueError(f"calculus exponent must be constant <= {_MAX_EXP}.")
        _validate_node(node.left, depth + 1)
        _validate_node(node.right, depth + 1)
        return
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        _validate_node(node.operand, depth + 1)
        return
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCS and not node.keywords and node.args):
        for a in node.args:
            _validate_node(a, depth + 1)
        return
    raise ValueError("calculus expression contains an unsupported operation.")


def _parse(source):
    src = str(source).strip()
    if not src or len(src) > 200:
        raise ValueError("calculus expression must contain 1 to 200 characters.")
    src = src.replace("^", "**")
    try:
        tree = ast.parse(src, mode="eval")
    except (SyntaxError, RecursionError) as e:
        raise ValueError(f"invalid calculus expression: {source!r}.") from e
    _validate_node(tree.body)
    return tree


def compile_expression(source):
    """Pure ruler: bounded AST walker, scalar float in -> float out."""
    tree = _parse(source)

    def walk(node, x):
        if isinstance(node, ast.Constant):
            return float(node.value)
        if isinstance(node, ast.Name):
            return x if node.id == "x" else _CONSTS[node.id]
        if isinstance(node, ast.BinOp):
            return _BINARY[type(node.op)](walk(node.left, x), walk(node.right, x))
        if isinstance(node, ast.UnaryOp):
            return _UNARY[type(node.op)](walk(node.operand, x))
        fn = _FUNCS[node.func.id]
        return fn(*[walk(a, x) for a in node.args])

    def f(x):
        try:
            out = float(walk(tree.body, float(x)))
        except (ArithmeticError, TypeError, ValueError) as e:
            raise ValueError(f"calculus expression {source!r} failed at x={x!r}: {e}") from e
        if not math.isfinite(out):
            raise ValueError(f"calculus expression {source!r} non-finite at x={x!r}.")
        return out
    return f


def compile_expression_np(source):
    """Select-library twin: same validated AST, numpy ufuncs (vectorized)."""
    if _NP is None:
        raise RuntimeError("numpy unavailable")
    tree = _parse(source)
    env = {"__builtins__": {}}
    env.update({k: getattr(_NP, k if k != "abs" else "abs") for k in _FUNCS})
    env["abs"] = _NP.abs
    env.update(pi=_NP.pi, e=_NP.e)
    code = compile(tree, "<calculus>", "eval")

    def f(x):
        return eval(code, env, {"x": x})      # validated AST, sealed globals
    return f


_PARITY = ("sin(x) + x^2", "exp(-x^2/2)", "tan(x/4) + cos(x)")


def _numpy_parity():
    if _NP is None:
        return False
    xs = [-4 + 8 * i / 64 for i in range(65)]
    for src in _PARITY:
        fp = compile_expression(src)
        try:
            fn = compile_expression_np(src)
        except Exception:
            return False
        for x in xs:
            if abs(fp(x) - float(fn(_NP.float64(x)))) > 1e-12:
                return False
    return True


if bp is not None:
    bp.register("calculus", bp.OWN_TOOL,
                probe=lambda: (True, "own tool, stdlib only"),
                witness=lambda: True,
                speedup=lambda size: 1.0)
    bp.register("calculus", "numpy",
                probe=lambda: bp.probe_import("numpy", ("sin", "exp", "linspace")),
                witness=_numpy_parity,
                speedup=lambda size: size / 512.0)


def _backend(n):
    if bp is None:
        return "pure"
    name, _ = bp.choose("calculus", size=n)
    return name if (name == "numpy" and _NP is not None) else "pure"


# --------------------------------------------------------- numeric rulers
def derivative(f, x, h=1e-4):
    """Richardson-extrapolated central difference: O(h^4), witness-checked."""
    d1 = (f(x + h) - f(x - h)) / (2 * h)
    d2 = (f(x + h / 2) - f(x - h / 2)) / h
    return (4 * d2 - d1) / 3


def _simpson(f, a, b):
    m = 0.5 * (a + b)
    return (b - a) / 6.0 * (f(a) + 4 * f(m) + f(b))


def integrate(f, a, b, tol=1e-9, _depth=0):
    """Adaptive Simpson; fails closed instead of returning garbage."""
    if _depth > 14:
        raise ValueError("integral did not converge; review interval/function.")
    m = 0.5 * (a + b)
    whole = _simpson(f, a, b)
    halves = _simpson(f, a, m) + _simpson(f, m, b)
    if abs(halves - whole) <= 15 * tol:
        return halves + (halves - whole) / 15.0
    return (integrate(f, a, m, tol / 2, _depth + 1)
            + integrate(f, m, b, tol / 2, _depth + 1))


def riemann_sum(f, a, b, n, sample="midpoint"):
    if sample not in ("left", "right", "midpoint"):
        raise ValueError("Riemann sample must be left, right, or midpoint.")
    w = (b - a) / n
    total = 0.0
    for i in range(n):
        left = a + i * w
        xs = left if sample == "left" else (left + w if sample == "right"
                                            else left + w / 2)
        total += f(xs)
    return total * w


# ------------------------------------------------------------- validation
def _finite(value, name):
    try:
        out = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"{name} must be a finite number.") from e
    if not math.isfinite(out):
        raise ValueError(f"{name} must be a finite number.")
    return out


def _range_pair(value, default, name):
    v = value if value is not None else list(default)
    if not isinstance(v, (list, tuple)) or len(v) not in (2, 3):
        raise ValueError(f"{name} must be [min, max] or [min, max, step].")
    low, high = _finite(v[0], name), _finite(v[1], name)
    step = _finite(v[2], name) if len(v) == 3 else (high - low) / 5
    if low >= high or step <= 0:
        raise ValueError(f"{name} needs min < max and positive step.")
    return low, high, step


def _interval(spec, x_bounds):
    a = _finite(spec.get("a", x_bounds[0]), "interval a")
    b = _finite(spec.get("b", x_bounds[1]), "interval b")
    if a >= b:
        raise ValueError("calculus interval must have a < b.")
    if a < x_bounds[0] or b > x_bounds[1]:
        raise ValueError("calculus interval must lie within x_range.")
    return a, b


def _count(value, default, name, hi):
    n = int(_finite(default if value is None else value, name))
    if not 1 <= n <= hi:
        raise ValueError(f"{name} must be an integer 1..{hi}.")
    return n


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
            return 3.0
        def dot(self, spec):
            return float((spec or {}).get("radius", 0.06))
        def font(self, base):
            return base
        def opacity(self):
            return 0.28
    return _Fallback()


# ------------------------------------------------------- manim builders
def _axes(spec, sk):
    from manim import Axes
    x0, x1, xs = _range_pair(spec.get("x_range"), [-4, 4], "x_range")
    y0, y1, ys = _range_pair(spec.get("y_range"), [-3, 3], "y_range")
    xl = _finite(spec.get("x_length", 6.5), "x_length")
    yl = _finite(spec.get("y_length", 4.0), "y_length")
    ax = Axes(x_range=[x0, x1, xs], y_range=[y0, y1, ys],
              x_length=xl, y_length=yl,
              axis_config={"color": sk.color(spec, "ink"),
                           "stroke_width": 1.6})
    return ax.move_to(sk.place(0, 1, spec, (0, -0.6, 0))), (x0, x1), (y0, y1)


def _build_graph(spec, sk):
    from manim import VGroup
    ax, xb, _ = _axes(spec, sk)
    f = compile_expression(spec.get("expression", "x"))
    n = _count(spec.get("samples"), 256, "graph samples", 2048)
    backend = _backend(n)
    curve = ax.plot(f, x_range=list(xb), color=sk.color(spec, "primary"),
                    stroke_width=sk.stroke())
    print(f"[calculus] graph backend={backend} samples={n}")
    return VGroup(ax, curve)


def _build_tangent(spec, sk):
    from manim import Dot, Text, VGroup
    ax, xb, _ = _axes(spec, sk)
    f = compile_expression(spec.get("expression", "x^2"))
    x0 = _finite(spec.get("x0", 0.5 * (xb[0] + xb[1])), "x0")
    delta = _finite(spec.get("delta", (xb[1] - xb[0]) / 8), "delta")
    if not (xb[0] <= x0 <= xb[1]) or delta == 0:
        raise ValueError("x0 must lie in x_range and delta must be non-zero.")
    x1 = x0 + delta
    if not (xb[0] <= x1 <= xb[1]):
        raise ValueError("x0 + delta must lie within x_range.")
    slope = derivative(f, x0)
    y0 = f(x0)
    sec = (f(x1) - y0) / delta
    tan_col = sk.color(spec, "accent")
    sec_col = sk.color(spec, "secondary")
    mobs = [ax, ax.plot(f, x_range=list(xb), color=sk.color(spec, "primary"),
                        stroke_width=sk.stroke()),
            ax.plot(lambda t: slope * (t - x0) + y0, x_range=list(xb),
                    color=tan_col, stroke_width=sk.stroke()),
            ax.plot(lambda t: sec * (t - x0) + y0, x_range=sorted((x0, x1)),
                    color=sec_col, stroke_width=sk.stroke() - 0.5),
            Dot(ax.c2p(x0, y0), radius=sk.dot(spec), color=tan_col),
            Dot(ax.c2p(x1, f(x1)), radius=sk.dot(spec) * 0.85, color=sec_col),
            Text(f"slope = {slope:g}   secant = {sec:g}",
                 font_size=sk.font(18), color=tan_col
                 ).move_to(sk.place(0, 1, spec, (0, -3.1, 0)))]
    return VGroup(*mobs)


def _build_integral(spec, sk):
    from manim import Polygon, Text, VGroup
    ax, xb, _ = _axes(spec, sk)
    f = compile_expression(spec.get("expression", "x"))
    a, b = _interval(spec, xb)
    n = _count(spec.get("samples"), 64, "integral samples", 256)
    value = integrate(f, a, b)                     # computed, never guessed
    fill = sk.color(spec, "field")
    strips = VGroup()
    w = (b - a) / n
    for i in range(n):
        l, r = a + i * w, a + (i + 1) * w
        strips.add(Polygon(ax.c2p(l, 0), ax.c2p(l, f(l)),
                           ax.c2p(r, f(r)), ax.c2p(r, 0),
                           color=fill, fill_color=fill,
                           fill_opacity=sk.opacity(), stroke_width=0))
    label = Text(f"∫ f dx = {value:g}", font_size=sk.font(20), color=fill
                 ).move_to(sk.place(0, 1, spec, (0, -3.1, 0)))
    return VGroup(ax, strips,
                  ax.plot(f, x_range=list(xb), color=sk.color(spec, "primary"),
                          stroke_width=sk.stroke()), label)


def _build_riemann(spec, sk):
    from manim import Polygon, Text, VGroup
    ax, xb, _ = _axes(spec, sk)
    f = compile_expression(spec.get("expression", "x"))
    a, b = _interval(spec, xb)
    n = _count(spec.get("rectangles"), 8, "Riemann rectangles", 256)
    kind = str(spec.get("sample", "midpoint")).lower()
    value = riemann_sum(f, a, b, n, kind)          # the sum we display
    fill = sk.color(spec, "accent")
    rects = VGroup()
    w = (b - a) / n
    for i in range(n):
        l, r = a + i * w, a + (i + 1) * w
        xs = l if kind == "left" else (r if kind == "right" else (l + r) / 2)
        h = f(xs)
        rects.add(Polygon(ax.c2p(l, 0), ax.c2p(l, h),
                          ax.c2p(r, h), ax.c2p(r, 0),
                          color=fill, fill_color=fill,
                          fill_opacity=sk.opacity() + 0.07,
                          stroke_width=0.6))
    label = Text(f"Σ ({kind}, n={n}) = {value:g}",
                 font_size=sk.font(19), color=fill
                 ).move_to(sk.place(0, 1, spec, (0, -3.1, 0)))
    return VGroup(ax, rects,
                  ax.plot(f, x_range=list(xb), color=sk.color(spec, "primary"),
                          stroke_width=sk.stroke()), label)


def route_calculus(scene, spec):
    if not isinstance(spec, dict):
        raise ValueError("calculus visual must be an object.")
    sk = _skin(getattr(scene, "ctx", None))
    kind = str(spec.get("kind", spec.get("type", "calculus_graph"))).lower()
    if kind in ("calculus_graph", "graph"):
        return _build_graph(spec, sk)
    if kind in ("derivative_tangent", "secant_tangent"):
        return _build_tangent(spec, sk)
    if kind == "integral_area":
        return _build_integral(spec, sk)
    if kind == "riemann_sum":
        return _build_riemann(spec, sk)
    raise ValueError(f"unsupported calculus visual kind: {kind}.")


class _NullScene:
    ctx = None


def build_calculus_visual(item, kind=None, scene=None):
    """Legacy-compatible entry point."""
    spec = dict(item)
    if kind:
        spec["kind"] = kind
    return route_calculus(scene if scene is not None else _NullScene(), spec)


ROUTE_TABLE = {k: route_calculus for k in
               ("calculus_graph", "derivative_tangent",
                "integral_area", "riemann_sum")}


# ------------------------------------------------------------ witnesses
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sin, cub, ex = (compile_expression(s) for s in ("sin(x)", "x^3", "exp(x)"))
    want("ruler:d/dx sin", abs(derivative(sin, math.pi / 4)
                               - math.cos(math.pi / 4)) <= 1e-8)
    want("ruler:d/dx x^3", abs(derivative(cub, 2.0) - 12.0) <= 1e-8)
    want("ruler:d/dx e^x", abs(derivative(ex, 1.0) - math.e) <= 1e-8)
    want("ruler:int sin", abs(integrate(sin, 0, math.pi) - 2.0) <= 1e-9)
    want("ruler:int x^2", abs(integrate(cub_and := compile_expression("x^2"),
                                        0, 1) - 1 / 3) <= 1e-9)
    want("ruler:int e^x", abs(integrate(ex, 0, 2) - (math.e ** 2 - 1)) <= 1e-9)
    lin = compile_expression("2x+1")
    want("ruler:midpoint exact linear",
         abs(riemann_sum(lin, 0, 3, 7, "midpoint")
             - integrate(lin, 0, 3)) <= 1e-12)
    ident = compile_expression("x")
    want("ruler:left closed form",
         abs(riemann_sum(ident, 0, 1, 4, "left") - 3 / 8) <= 1e-12)
    one = compile_expression("sin(x)^2 + cos(x)^2")
    want("ruler:identity", all(abs(one(t) - 1) <= 1e-12
                               for t in (-3, 0, 0.7, 2.9)))
    for bad in ("open('f')", "x^1000", "__import__('os')", "x; 1"):
        try:
            compile_expression(bad)
            want(f"guard:reject {bad[:12]}", False)
        except ValueError:
            want(f"guard:reject {bad[:12]}", True)
    want("determinism:integrate",
         integrate(sin, 0, math.pi) == integrate(sin, 0, math.pi))
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
