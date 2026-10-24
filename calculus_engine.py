"""Safe single-variable calculus visuals for Manim storyboards."""
from __future__ import annotations

import ast
import math
import operator

from manim import Axes, Dot, Polygon, VGroup, Line, config

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "abs": abs,
    "acos": math.acos,
    "asin": math.asin,
    "atan": math.atan,
    "ceil": math.ceil,
    "cos": math.cos,
    "cosh": math.cosh,
    "exp": math.exp,
    "floor": math.floor,
    "log": math.log,
    "max": max,
    "min": min,
    "sin": math.sin,
    "sinh": math.sinh,
    "sqrt": math.sqrt,
    "tan": math.tan,
    "tanh": math.tanh,
}

def compile_expression(expression):
    """Compile a bounded arithmetic expression in x without Python eval."""
    source = str(expression).strip()
    if not source or len(source) > 200:
        raise ValueError("calculus expression must contain 1 to 200 characters.")
    source = source.replace("^", "**")
    try:
        tree = ast.parse(source, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise ValueError(f"invalid calculus expression: {expression!r}.") from exc

    def evaluate_node(node, x, depth=0):
        # Euler's Canon: Computations must be strictly bounded and finite.
        if depth > 32:
            raise ValueError("calculus expression AST depth limit (32) exceeded.")
        
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(
                    node.value, (int, float)):
                raise ValueError("calculus expressions only allow real numbers.")
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id == "x":
                return x
            if node.id == "pi":
                return math.pi
            if node.id == "e":
                return math.e
            raise ValueError(f"unsupported name in calculus expression: {node.id}.")
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            left = evaluate_node(node.left, x, depth + 1)
            right = evaluate_node(node.right, x, depth + 1)
            if isinstance(node.op, ast.Pow) and abs(right) > 64:
                raise ValueError("calculus expression exponent is limited to 64.")
            return _BINARY_OPERATORS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
            return _UNARY_OPERATORS[type(node.op)](evaluate_node(node.operand, x, depth + 1))
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in _FUNCTIONS and not node.keywords):
            args = [evaluate_node(arg, x, depth + 1) for arg in node.args]
            return _FUNCTIONS[node.func.id](*args)
        raise ValueError("calculus expression contains an unsupported operation.")

    def function(x):
        try:
            result = float(evaluate_node(tree.body, float(x)))
        except (ArithmeticError, TypeError, ValueError) as exc:
            raise ValueError(
                f"could not evaluate calculus expression {expression!r} "
                f"at x={x!r}: {exc}"
            ) from exc
        if not math.isfinite(result):
            raise ValueError(
                f"calculus expression {expression!r} is non-finite at x={x!r}."
            )
        return result

    return function

def _range(value, default, name):
    if value is None:
        value = default
    if not isinstance(value, (list, tuple)) or len(value) not in (2, 3):
        raise ValueError(f"{name} must contain min, max, and optional step.")
    try:
        low, high = float(value[0]), float(value[1])
        step = float(value[2]) if len(value) == 3 else (high - low) / 5
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} values must be finite numbers.") from exc
    if not all(math.isfinite(v) for v in (low, high, step)):
        raise ValueError(f"{name} values must be finite numbers.")
    if low >= high or step <= 0:
        raise ValueError(f"{name} min must be below max and step must be positive.")
    return low, high, step

def _axes(item):
    x_min, x_max, x_step = _range(
        item.get("x_range"), [-4, 4], "x_range",
    )
    y_min, y_max, y_step = _range(
        item.get("y_range"), [-3, 3], "y_range",
    )
    try:
        x_length = float(item.get("x_length", config.frame_width * 0.78))
        y_length = float(item.get("y_length", config.frame_height * 0.27))
        center = [float(value) for value in item.get("center", [0, 0, 0])]
    except (TypeError, ValueError) as exc:
        raise ValueError("calculus axes dimensions and center must be numeric.") from exc
    if (not math.isfinite(x_length) or not math.isfinite(y_length)
            or x_length <= 0 or y_length <= 0):
        raise ValueError("calculus axes dimensions must be finite and positive.")
    if (len(center) not in (2, 3)
            or not all(math.isfinite(value) for value in center)):
        raise ValueError("calculus axes center must be a finite 2D or 3D point.")
    if len(center) == 2:
        center.append(0.0)
    axes = Axes(
        x_range=[x_min, x_max, x_step],
        y_range=[y_min, y_max, y_step],
        x_length=x_length,
        y_length=y_length,
        axis_config={"color": "#8A8F9C", "stroke_width": 1.7},
    ).move_to(center)
    return axes, (x_min, x_max), (y_min, y_max)

def _function_graph(axes, function, x_range, item):
    return axes.plot(
        function,
        x_range=x_range,
        color=item.get("color", "#F2F3F5"),
        stroke_width=float(item.get("stroke_width", 3.0)),
    )

def _validate_interval(item, x_bounds):
    try:
        start = float(item.get("a", x_bounds[0]))
        end = float(item.get("b", x_bounds[1]))
    except (TypeError, ValueError) as exc:
        raise ValueError("calculus interval endpoints must be finite numbers.") from exc
    if not math.isfinite(start) or not math.isfinite(end) or start >= end:
        raise ValueError("calculus interval must have finite endpoints with a < b.")
    if start < x_bounds[0] or end > x_bounds[1]:
        raise ValueError("calculus interval must lie within x_range.")
    return start, end

def _bounded_integer(value, name, maximum):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer between 1 and {maximum}.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be an integer between 1 and {maximum}."
        ) from exc
    if (not math.isfinite(number) or not number.is_integer()
            or not 1 <= number <= maximum):
        raise ValueError(f"{name} must be an integer between 1 and {maximum}.")
    return int(number)

def _clip_line(x0, y0, x1, y1, xmin, xmax, ymin, ymax):
    """Liang-Barsky line clipping algorithm. Ensures mathematical perfection at boundaries."""
    dx = x1 - x0
    dy = y1 - y0
    p = [-dx, dx, -dy, dy]
    q = [x0 - xmin, xmax - x0, y0 - ymin, ymax - y0]
    u1, u2 = 0.0, 1.0
    for i in range(4):
        if p[i] == 0:
            if q[i] < 0:
                return None  # Line is parallel and outside the clipping window
        else:
            t = q[i] / p[i]
            if p[i] < 0:
                if t > u2: return None
                if t > u1: u1 = t
            else:
                if t < u1: return None
                if t < u2: u2 = t
    cx0 = x0 + u1 * dx
    cy0 = y0 + u1 * dy
    cx1 = x0 + u2 * dx
    cy1 = y0 + u2 * dy
    return (cx0, cy0), (cx1, cy1)

def build_calculus_visual(item, *, kind):
    """Build a graph, derivative, integral region, or Riemann-sum visual."""
    axes, x_bounds, y_bounds = _axes(item)
    function = compile_expression(item.get("expression", "x"))
    graph = _function_graph(axes, function, list(x_bounds), item)
    visuals = [axes]

    if kind == "calculus_graph":
        visuals.append(graph)
        return VGroup(*visuals)

    if kind == "derivative_tangent":
        try:
            x0 = float(item.get("x0", sum(x_bounds) / 2))
            delta = float(item.get("delta", (x_bounds[1] - x_bounds[0]) / 4))
            step = float(item.get("difference_step", 1e-4))
        except (TypeError, ValueError) as exc:
            raise ValueError("derivative positions and steps must be finite numbers.") from exc
        if not all(math.isfinite(value) for value in (x0, delta, step)):
            raise ValueError("derivative positions and steps must be finite numbers.")
        if x0 < x_bounds[0] or x0 > x_bounds[1] or delta == 0 or step <= 0:
            raise ValueError("x0 must lie in x_range; delta and difference_step must be non-zero and positive.")
        x1 = x0 + delta
        if x1 < x_bounds[0] or x1 > x_bounds[1]:
            raise ValueError("x0 + delta must lie within x_range.")
        y0 = function(x0)
        y1 = function(x1)
        left_room, right_room = x0 - x_bounds[0], x_bounds[1] - x0
        if left_room > 0 and right_room > 0:
            h = min(step, left_room, right_room)
            slope = (function(x0 + h) - function(x0 - h)) / (2 * h)
        elif right_room > 0:
            h = min(step, right_room)
            slope = (function(x0 + h) - y0) / h
        elif left_room > 0:
            h = min(step, left_room)
            slope = (y0 - function(x0 - h)) / h
        else:
            raise ValueError("x0 must have neighboring points to estimate a derivative.")
        secant_slope = (y1 - y0) / delta
        
        span = max(x_bounds[1] - x_bounds[0], y_bounds[1] - y_bounds[0]) * 10
        
        if abs(slope) > 1e12: # Practically vertical tangent
            t_start, t_end = (x0, y_bounds[0]), (x0, y_bounds[1])
        else:
            tangent_far_x1 = x0 - span
            tangent_far_y1 = y0 - slope * span
            tangent_far_x2 = x0 + span
            tangent_far_y2 = y0 + slope * span
            clipped_tangent = _clip_line(tangent_far_x1, tangent_far_y1, tangent_far_x2, tangent_far_y2,
                                         x_bounds[0], x_bounds[1], y_bounds[0], y_bounds[1])
            t_start, t_end = clipped_tangent if clipped_tangent else ((x0, y0), (x0, y0))

        if abs(secant_slope) > 1e12:
            s_start, s_end = (x0, y_bounds[0]), (x0, y_bounds[1])
        else:
            secant_intercept = y0 - secant_slope * x0
            secant_far_x1 = x0 - span
            secant_far_y1 = secant_slope * secant_far_x1 + secant_intercept
            secant_far_x2 = x0 + span
            secant_far_y2 = secant_slope * secant_far_x2 + secant_intercept
            clipped_secant = _clip_line(secant_far_x1, secant_far_y1, secant_far_x2, secant_far_y2,
                                        x_bounds[0], x_bounds[1], y_bounds[0], y_bounds[1])
            s_start, s_end = clipped_secant if clipped_secant else ((x0, y0), (x1, y1))

        visuals.extend([
            graph,
            Line(axes.c2p(*t_start), axes.c2p(*t_end), color=item.get("tangent_color", "#2ECC71"), stroke_width=3),
            Line(axes.c2p(*s_start), axes.c2p(*s_end), color=item.get("secant_color", "#F1C40F"), stroke_width=2.5),
            Dot(axes.c2p(x0, y0), radius=0.065, color="#2ECC71"),
            Dot(axes.c2p(x1, y1), radius=0.055, color="#F1C40F"),
        ])
        return VGroup(*visuals)

    if kind == "integral_area":
        start, end = _validate_interval(item, x_bounds)
        try:
            baseline = float(item.get("baseline", 0.0))
            opacity = float(item.get("fill_opacity", 0.28))
        except (TypeError, ValueError) as exc:
            raise ValueError("integral display settings must be numeric.") from exc
        samples = _bounded_integer(item.get("samples", 64), "integral samples", 256)
        if not math.isfinite(baseline) or not y_bounds[0] <= baseline <= y_bounds[1]:
            raise ValueError("integral baseline must be finite and lie within y_range.")
        if not 1 <= samples <= 256:
            raise ValueError("integral samples must be between 1 and 256.")
        if not math.isfinite(opacity) or not 0 <= opacity <= 1:
            raise ValueError("integral fill_opacity must be between 0 and 1.")
        shaded = VGroup()
        step = (end - start) / samples
        fill = item.get("area_color", "#4CC9F0")
        for index in range(samples):
            x_left = start + index * step
            x_right = x_left + step
            shaded.add(Polygon(
                axes.c2p(x_left, baseline),
                axes.c2p(x_left, function(x_left)),
                axes.c2p(x_right, function(x_right)),
                axes.c2p(x_right, baseline),
                color=fill,
                fill_color=fill,
                fill_opacity=opacity,
                stroke_width=0,
            ))
        visuals.extend([shaded, graph])
        return VGroup(*visuals)

    if kind == "riemann_sum":
        start, end = _validate_interval(item, x_bounds)
        try:
            baseline = float(item.get("baseline", 0.0))
            opacity = float(item.get("fill_opacity", 0.35))
        except (TypeError, ValueError) as exc:
            raise ValueError("Riemann-sum settings must be numeric.") from exc
        count = _bounded_integer(
            item.get("rectangles", 8), "Riemann rectangles", 256,
        )
        sample_type = str(item.get("sample", "midpoint")).lower()
        if sample_type not in ("left", "right", "midpoint"):
            raise ValueError("Riemann sample must be left, right, or midpoint.")
        if not math.isfinite(baseline) or not y_bounds[0] <= baseline <= y_bounds[1]:
            raise ValueError("Riemann baseline must be finite and lie within y_range.")
        if not math.isfinite(opacity) or not 0 <= opacity <= 1:
            raise ValueError("Riemann fill_opacity must be between 0 and 1.")
        rectangles = VGroup()
        width = (end - start) / count
        fill = item.get("area_color", "#F1C40F")
        for index in range(count):
            left = start + index * width
            right = left + width
            if sample_type == "left":
                sample_x = left
            elif sample_type == "right":
                sample_x = right
            else:
                sample_x = (left + right) / 2
            height = function(sample_x)
            rectangles.add(Polygon(
                axes.c2p(left, baseline),
                axes.c2p(left, height),
                axes.c2p(right, height),
                axes.c2p(right, baseline),
                color=fill,
                fill_color=fill,
                fill_opacity=opacity,
                stroke_width=0.6,
            ))
        visuals.extend([rectangles, graph])
        return VGroup(*visuals)

    raise ValueError(f"unsupported calculus visual kind: {kind}.")
