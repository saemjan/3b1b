#!/usr/bin/env python3
"""Manim engine with gates: reads one job JSON (env SAEM_JOB)..."""
import ast
import json
import math
import os
import re
import sys
from pathlib import Path

from manim import (
    Scene, ThreeDScene, config, VGroup, Group, MathTex, Text, Arrow, Line,
    Dot, Circle, Ellipse, Rectangle, Polygon, Brace, Axes, NumberLine,
    ValueTracker, always_redraw, Create, Write, FadeIn, FadeOut, GrowArrow,
    MoveAlongPath, Succession, Wait, UP, DOWN, LEFT, RIGHT, ORIGIN, PI,
    VMobject, ThreeDAxes, Sphere, Cube, Cylinder, Cone, UR
)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

JOB_PATH = os.environ.get("SAEM_JOB")
JOB = json.loads(Path(JOB_PATH).read_text(encoding="utf-8")) if JOB_PATH else {
    "row": {"video_id": "demo", "concept_type": "GENERIC",
            "header_title": "Demo", "tagline": "demo",
            "equations_json": "[]", "visual_data_json": "[]",
            "audio_script": "demo", "orientation": "vertical"},
    "audio_duration": 12.0, "orientation": "vertical",
    "report_path": "report.json",
}
ROW = JOB["row"]
ORIENT = JOB.get("orientation", ROW.get("orientation", "vertical"))
DURATION = float(JOB.get("audio_duration", 60.0))
FAILED = []

def safe_json_loads(cell, default):
    if not cell:
        return default
    s = cell.strip()
    # Fixed: Restored valid backslashes for JSON repair
    for cand in (s, s.replace("\\\\", "\\"), s.replace("\\", "")):
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    return default

# ---- restricted expression evaluator (arithmetic over x) --------------
_ALLOWED_FUNCS = {"sin": math.sin, "cos": math.cos, "tan": math.tan,
                  "exp": math.exp, "log": math.log, "sqrt": math.sqrt,
                  "abs": abs}
_CONSTS = {"pi": math.pi, "e": math.e}

def eval_expr(expr, x):
    node = ast.parse(expr.replace("^", "**"), mode="eval").body
    def ev(n):
        if isinstance(n, ast.Constant):
            return float(n.value)
        if isinstance(n, ast.Name):
            if n.id == "x":
                return float(x)
            if n.id in _CONSTS:
                return _CONSTS[n.id]
            raise ValueError(f"unknown name {n.id}")
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            return {"Add": a + b, "Sub": a - b, "Mult": a * b,
                    "Div": a / b, "Pow": a ** b}[type(n.op).__name__]
        if isinstance(n, ast.UnaryOp):
            a = ev(n.operand)
            return -a if isinstance(n.op, ast.USub) else a
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            fn = _ALLOWED_FUNCS.get(n.func.id)
            if fn is None:
                raise ValueError(f"forbidden function {n.func.id}")
            return fn(ev(n.args[0]))
        raise ValueError("forbidden expression node")
    return ev(node)

# ---- frame configuration ----------------------------------------------
if ORIENT == "vertical":
    config.pixel_width, config.pixel_height = (480, 854) if JOB.get("draft") else (1080, 1920)
    config.frame_width, config.frame_height = 9.0, 16.0
else:
    config.pixel_width, config.pixel_height = (854, 480) if JOB.get("draft") else (1920, 1080)
    config.frame_width, config.frame_height = 16.0, 9.0
config.frame_rate = 15 if JOB.get("draft") else 30

class SaemLabsBranding:
    def add_intro(self, title, tagline):
        t = Text(title, font_size=34, weight="BOLD").to_edge(UP, buff=0.4)
        s = Text(tagline, font_size=22, slant="ITALIC").next_to(t, DOWN, buff=0.2)
        return VGroup(t, s)

    def add_outro(self):
        return Text("SaemLabs · NEET · JEE · MIT", font_size=20).to_edge(DOWN, buff=0.3)

    def watermark(self):
        return Text("SaemLabs", font_size=16, opacity=0.4).to_corner(UR, buff=0.2)

class UniversalPhysicsScene(Scene, SaemLabsBranding):
    def construct(self):
        visuals = safe_json_loads(ROW.get("visual_data_json"), []) or []
        equations = safe_json_loads(ROW.get("equations_json"), []) or []
        beats = safe_json_loads(ROW.get("beats_json"), []) or []

        self.add(self.watermark())
        head = self.add_intro(ROW.get("header_title", ""), ROW.get("tagline", ""))
        self.play(FadeIn(head), run_time=1.0)

        objects, order = self.build_primitives(visuals)
        eq_mobs = []
        for i, eq in enumerate(equations[:4]):
            try:
                m = MathTex(eq, font_size=30).move_to(UP * (2.5 - 0.8 * i))
                eq_mobs.append(m)
            except Exception as e:
                FAILED.append(f"equation:{eq[:20]}:{e}")

        timeline = self.align_beats(beats, objects)
        shown = set()
        last = 1.0
        for t, focus in timeline:
            dt = max(0.2, t - last)
            self.wait(dt)
            last = t + dt
            mob = objects.get(focus)
            if mob is not None and focus not in shown:
                self.play(Create(mob), run_time=min(2.0, dt + 1.0))
                shown.add(focus)
        for key, mob in objects.items():
            if key not in shown:
                self.play(Create(mob), run_time=0.8)
                shown.add(key)
        for m in eq_mobs:
            self.play(Write(m), run_time=0.8)

        remaining = max(0.5, DURATION + 4.0 - self.renderer.time)
        self.wait(min(remaining, 4.0))
        self.play(FadeIn(self.add_outro()), run_time=1.5)
        self.wait(2.0)
        self.write_report(len(visuals) + len(equations))

    def align_beats(self, beats, objects):
        if not beats:
            return []
        try:
            from tools.word_sync import align_beats
            aligned = align_beats(Path(JOB["audio_voice"]), beats,
                                  ROW.get("audio_script", ""))
            return [(b.get("time", 0.0), b.get("focus")) for b in aligned]
        except Exception:
            n = len(beats)
            return [(DURATION * i / max(1, n), b.get("focus"))
                    for i, b in enumerate(beats)]

    def build_primitives(self, visuals):
        objects, order = {}, []
        for i, spec in enumerate(visuals):
            if not isinstance(spec, dict):
                FAILED.append(f"visual[{i}]:not-a-dict")
                continue
            ptype = spec.get("type", "?")
            spec.setdefault("id", f"p{i}")
            builder = getattr(self, f"_prim_{ptype}", None)
            if builder is None:
                FAILED.append(f"unknown:{ptype}")
                print(f"[WARN] unknown primitive '{ptype}' skipped")
                continue
            try:
                mob = builder(spec)
                if mob is not None:
                    objects[spec["id"]] = mob
                    order.append(spec["id"])
            except Exception as e:
                FAILED.append(f"{ptype}:{e}")
                print(f"[WARN] primitive '{ptype}' failed: {e}")
        return objects, order

    def _pos(self, spec, default=(0, 0, 0)):
        p = spec.get("pos", spec.get("center", list(default)))
        return tuple(p) + (0.0,) * (3 - len(p)) if len(p) < 3 else tuple(p)

    def _prim_text(self, s):
        return Text(str(s.get("text", "")), font_size=s.get("font_size", 24)).move_to(self._pos(s))

    def _prim_dot(self, s):
        return Dot(self._pos(s), radius=s.get("radius", 0.08),
                   color=s.get("color", "YELLOW"))
    _prim_charge = _prim_dot
    _prim_particle = _prim_dot

    def _prim_vector(self, s):
        a, b = self._pos(s, (0, -1, 0)), self._pos(s, (0, 1, 0))
        if "start" in s and "end" in s:
            a, b = tuple(s["start"]), tuple(s["end"])
        return Arrow(a, b, buff=0, color=s.get("color", "BLUE"))
    _prim_arrow = _prim_vector
    _prim_force = _prim_vector

    def _prim_line(self, s):
        a = tuple(s.get("start", [-2, 0, 0]))
        b = tuple(s.get("end", [2, 0, 0]))
        return Line(a, b, color=s.get("color", "WHITE"))
    _prim_rod = _prim_line
    _prim_segment = _prim_line

    def _prim_circle(self, s):
        return Circle(radius=s.get("radius", 1.0),
                      color=s.get("color", "GREEN")).move_to(self._pos(s))
    _prim_lens = _prim_circle

    def _prim_ellipse(self, s):
        return Ellipse(width=s.get("width", 2.0), height=s.get("height", 1.0),
                       color=s.get("color", "GREEN")).move_to(self._pos(s))

    def _prim_rectangle(self, s):
        return Rectangle(width=s.get("width", 2.0), height=s.get("height", 1.0),
                         color=s.get("color", "WHITE")).move_to(self._pos(s))
    _prim_shape = _prim_rectangle

    def _prim_polygon(self, s):
        pts = [tuple(p) + (0.0,) * (3 - len(p)) for p in s.get("points", [[-1, -1], [1, -1], [0, 1]])]
        return Polygon(*pts, color=s.get("color", "WHITE"))

    def _prim_brace(self, s):
        a = tuple(s.get("start", [-1, 0, 0]))
        b = tuple(s.get("end", [1, 0, 0]))
        return Brace(Line(a, b), direction=DOWN, color=s.get("color", "YELLOW"))

    def _prim_graph(self, s):
        ax = Axes(x_range=s.get("x_range", [-4, 4]),
                  y_range=s.get("y_range", [-3, 3]),
                  x_length=s.get("x_length", 6.0),
                  y_length=s.get("y_length", 4.0)).move_to(self._pos(s, (0, -1, 0)))
        expr = s.get("expression", "x")
        curve = ax.plot(lambda t: eval_expr(expr, t), color=s.get("color", "YELLOW"))
        return VGroup(ax, curve)
    _prim_function = _prim_graph
    _prim_curve = _prim_graph
    _prim_calculus_graph = _prim_graph

    def _prim_derivative_tangent(self, s):
        ax = Axes(x_range=s.get("x_range", [-3, 3]), y_range=s.get("y_range", [-3, 3]),
                  x_length=6.0, y_length=4.0).move_to(self._pos(s, (0, -1, 0)))
        expr = s.get("expression", "x^2")
        x0 = float(s.get("x0", 1.0))
        d = float(s.get("delta", 0.5))
        curve = ax.plot(lambda t: eval_expr(expr, t), color="YELLOW")
        
        # Fixed: Replaced invalid `? None` syntax with a safe try/except block
        try:
            if hasattr(ax, "get_secant_line_group"):
                sec = ax.get_secant_line_group(curve, x0, x0 + d)
                return VGroup(ax, curve, sec)
        except Exception:
            pass
        return VGroup(ax, curve)

    def _prim_number_line(self, s):
        nl = NumberLine(x_range=s.get("x_range", [-5, 5]), length=s.get("length", 6.0)).move_to(self._pos(s))
        marker = Dot(nl.n2p(float(s.get("value", 0))), color="RED")
        return VGroup(nl, marker)

    def _prim_wave(self, s):
        ax = Axes(x_range=s.get("x_range", [-4, 4]), y_range=[-1.5, 1.5],
                  x_length=7.0, y_length=2.0).move_to(self._pos(s, (0, -1, 0)))
        amp = float(s.get("amplitude", 0.6))
        freq = float(s.get("frequency", 1.0))
        curve = ax.plot(lambda t: amp * math.sin(2 * math.pi * freq * t / 4.0),
                        color="BLUE")
        return VGroup(ax, curve)

    def _prim_energy_bar(self, s):
        bar = Rectangle(width=0.6, height=3.0, color="GREEN").move_to(self._pos(s))
        fill = Rectangle(width=0.5, height=3.0 * float(s.get("fraction", 0.5)),
                         color="GREEN", fill_opacity=0.7).align_to(bar, DOWN)
        return VGroup(bar, fill)

    def _prim_pendulum(self, s):
        pivot = self._pos(s, (0, 2, 0))
        rod = Line(pivot, (pivot[0], pivot[1] - 2.0, 0), color="WHITE")
        bob = Dot((pivot[0], pivot[1] - 2.0, 0), radius=0.15, color="RED")
        return VGroup(rod, bob)

    def _prim_spring(self, s):
        base = Line((-0.5, 2, 0), (0.5, 2, 0)).move_to(self._pos(s, (0, 2, 0)))
        coil = VGroup(*[Line(((-0.3) ** k, 2 - 0.2 * k, 0), ((0.3) ** k, 2 - 0.2 * k - 0.1, 0))
                        for k in range(6)]).move_to(self._pos(s, (0, 1, 0)))
        mass = Rectangle(width=0.5, height=0.5, color="BLUE").move_to(self._pos(s, (0, -0.5, 0)))
        return VGroup(base, coil, mass)

    def _prim_orbit(self, s):
        el = Ellipse(width=s.get("width", 4.0), height=s.get("height", 2.5),
                     color="GREY").move_to(self._pos(s))
        body = Dot(el.point_from_proportion(0.0), radius=0.12, color="YELLOW")
        return VGroup(el, body)

    def _prim_ray(self, s):
        a = tuple(s.get("start", [-3, 0, 0]))
        b = tuple(s.get("end", [3, 0, 0]))
        return Arrow(a, b, buff=0, color="YELLOW", stroke_width=2)

    def _prim_particle_gas(self, s):
        box = Rectangle(width=4.0, height=3.0).move_to(self._pos(s))
        dots = VGroup(*[Dot(box.get_center() + UP * (0.3 * ((k * 7) % 5 - 2)) +
                            RIGHT * (0.4 * ((k * 3) % 7 - 3)), radius=0.05, color="WHITE")
                        for k in range(int(s.get("count", 12)))])
        return VGroup(box, dots)

    def _prim_heat_flow(self, s):
        hot = Rectangle(width=1.0, height=2.0, color="RED",
                        fill_opacity=0.6).move_to(self._pos(s) + LEFT * 2)
        cold = Rectangle(width=1.0, height=2.0, color="BLUE",
                         fill_opacity=0.6).move_to(self._pos(s) + RIGHT * 2)
        arrows = VGroup(*[Arrow(LEFT * 1.2 + self._pos(s) + UP * (0.5 * (k - 1)),
                                RIGHT * 1.2 + self._pos(s) + UP * (0.5 * (k - 1)),
                                buff=0, color="ORANGE", stroke_width=2)
                          for k in range(3)])
        return VGroup(hot, cold, arrows)

    def _prim_projectile_motion(self, s):
        v0 = float(s.get("v0", 20.0))
        ang = math.radians(float(s.get("angle", 45.0)))
        g = float(s.get("g", 9.8))
        t_end = 2 * v0 * math.sin(ang) / g
        scale = 6.0 / max(1e-9, v0 * math.cos(ang) * t_end)
        path = VMobject(color="YELLOW")
        pts = []
        for k in range(61):
            t = t_end * k / 60.0
            x = v0 * math.cos(ang) * t
            y = v0 * math.sin(ang) * t - 0.5 * g * t * t
            pts.append(((-3.0 + scale * x), (-2.5 + scale * y), 0.0))
        path.set_points_smoothly(pts)
        ball = Dot(pts[0], radius=0.12, color="RED")
        return VGroup(path, ball)

    def _prim_physics_simulation(self, s):
        bodies = s.get("bodies", [])
        mobs = VGroup()
        for b in bodies[:8]:
            p = b.get("position", [0, 0])
            mobs.add(Dot((p[0], p[1], 0.0), radius=float(b.get("radius", 0.15)),
                         color=b.get("color", "YELLOW")))
        return mobs

    def _prim_equation_morph(self, s):
        steps = s.get("steps", [])
        mobs = VGroup()
        for st in steps[:6]:
            try:
                mobs.add(MathTex(st, font_size=26))
            except Exception:
                FAILED.append(f"equation_morph:{st[:20]}")
        mobs.arrange(DOWN, buff=0.25).move_to(self._pos(s, (0, 0, 0)))
        return mobs

    def _prim_numerical_chain(self, s):
        lines = s.get("lines", [])
        mobs = VGroup(*[Text(str(l), font_size=20) for l in lines[:8]])
        mobs.arrange(DOWN, buff=0.2, aligned_edge=LEFT).move_to(self._pos(s, (0, 0, 0)))
        return mobs

    def _prim_warning_box(self, s):
        t = Text(str(s.get("text", "!")), font_size=22, color="RED")
        box = Rectangle(width=t.width + 0.6, height=t.height + 0.4, color="RED")
        return VGroup(box, t.move_to(box.get_center())).move_to(self._pos(s))

    def _prim_quiz_frame(self, s):
        q = Text(str(s.get("question", "?")), font_size=22)
        opts = VGroup(*[Text(str(o), font_size=18) for o in s.get("options", [])[:4]])
        opts.arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        return VGroup(q, opts.next_to(q, DOWN, buff=0.3)).move_to(self._pos(s, (0, 1, 0)))

    def _prim_live_label(self, s):
        tracker = ValueTracker(0.0)
        label = always_redraw(lambda: Text(
            f"{s.get('prefix', 't')} = {tracker.get_value():.2f} {s.get('unit', '')}",
            font_size=20).move_to(self._pos(s)))
        self.add(label)
        self.play(tracker.animate.set_value(float(s.get("to", DURATION))),
                  run_time=min(4.0, DURATION / 2), rate_func=None)
        return None

    def _prim_group(self, s):
        kids, _ = self.build_primitives(s.get("children", []))
        return VGroup(*kids.values()) if kids else None

    def write_report(self, primitive_count):
        report = {
            "video_id": ROW.get("video_id"),
            "primitive_count": primitive_count,
            "failed_primitives": FAILED,
            "duration_sec": DURATION,
            "orientation": ORIENT,
        }
        Path(JOB.get("report_path", "report.json")).write_text(
            json.dumps(report, ensure_ascii=False), encoding="utf-8")

class Universal3DScene(ThreeDScene, SaemLabsBranding):
    def construct(self):
        self.set_camera_orientation(phi=70 * PI / 180, theta=-30 * PI / 180)
        visuals = safe_json_loads(ROW.get("visual_data_json"), []) or []
        self.add(Text(ROW.get("header_title", ""), font_size=30).to_edge(UP))
        for i, spec in enumerate(visuals):
            kind = spec.get("kind", spec.get("type", "sphere"))
            try:
                if kind == "cube":
                    mob = Cube(side_length=float(spec.get("side_length", 1.5)))
                elif kind == "cylinder":
                    mob = Cylinder(radius=float(spec.get("radius", 0.5)),
                                   height=float(spec.get("height", 1.5)))
                elif kind == "cone":
                    mob = Cone(radius=float(spec.get("radius", 0.5)),
                               height=float(spec.get("height", 1.5)))
                else:
                    mob = Sphere(radius=float(spec.get("radius", 1.0)))
                p = spec.get("position", [0, 0, 0])
                mob.move_to(p)
                self.play(Create(mob), run_time=1.0)
            except Exception as e:
                FAILED.append(f"3d:{kind}:{e}")
        self.wait(2.0)
        UniversalPhysicsScene.write_report(self, len(visuals))

if __name__ == "__main__":
    print("render_universal is driven by manim with SAEM_JOB set; "
          "see batch_runner.py")
