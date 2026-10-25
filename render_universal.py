#!/usr/bin/env python3
"""render_universal.py — gen-3 manim renderer (QCOS factory layer).

Meaning is frozen, representation evolves:
  * numbers/physics arrive pre-computed (core + engines) — A0
  * LOOK comes from tools/style_genome (palette/layout/motion/voice/pace),
    novel against logs/style_ledger.jsonl, never repeated — the teacher rule
  * witnesses (golden, rulers, parity) live in CI, never in this file — A5
  * report receipts core_source_id, narration hash, engines, genome, backend
    decisions for the append-only ledger.

Engine contract v1: ROUTE_TABLE[type](scene, spec); engines may read
scene.ctx (StyleContext) to wear the batch's look.
"""
from __future__ import annotations

import ast
import hashlib
import importlib
import json
import math
import os
import random
import re
import sys
from pathlib import Path

from manim import (
    Scene, ThreeDScene, config, VGroup, MathTex, Text, Arrow, Line,
    Dot, Circle, Ellipse, Rectangle, Polygon, Brace, Axes, NumberLine,
    ValueTracker, always_redraw, Create, Write, FadeIn, FadeOut, GrowArrow,
    UP, DOWN, LEFT, RIGHT, ORIGIN, PI, VMobject,
    Sphere, Cube, Cylinder, Cone, UR, RED, linear,
    rate_functions as _RF,
)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:
    from tools import style_genome as sg
except Exception:
    sg = None
try:
    from tools import backend_policy as bp
except Exception:
    bp = None

ENGINE_MODULES = (
    "calculus_engine", "electromagnetics_engine", "fluid_dynamics_engine",
    "geometry_engine", "linear_algebra_engine", "rotational_motion_engine",
    "physics_simulation",
)
_ENGINES = None


def _load_engines():
    table, loaded = {}, []
    for name in ENGINE_MODULES:
        try:
            mod = importlib.import_module(name)
        except Exception as e:
            print(f"[WARN] engine {name} unavailable: {e}")
            continue
        routes = getattr(mod, "ROUTE_TABLE", None)
        if not isinstance(routes, dict):
            routes = {a[len("build_"):]: getattr(mod, a)
                      for a in dir(mod) if a.startswith("build_")}
        if routes:
            loaded.append(name)
            for t, fn in routes.items():
                table.setdefault(t, (name, fn))
    return table, loaded


def engine_table():
    global _ENGINES
    if _ENGINES is None:
        _ENGINES = _load_engines()[0]
    return _ENGINES


# ---- job / frame -----------------------------------------------------------
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
CORE_ID = os.environ.get("SAEM_SOURCE_ID", "")


def apply_frame_config(job):
    draft = bool(job.get("draft"))
    if ORIENT == "vertical":
        config.pixel_width, config.pixel_height = (480, 854) if draft else (1080, 1920)
        config.frame_width, config.frame_height = 9.0, 16.0
    else:
        config.pixel_width, config.pixel_height = (854, 480) if draft else (1920, 1080)
        config.frame_width, config.frame_height = 16.0, 9.0
    config.frame_rate = 15 if draft else 30


apply_frame_config(JOB)


def safe_json_loads(cell, default):
    if not cell:
        return default
    s = cell.strip()
    for cand in (s, s.replace("\\\\", "\\"), re.sub(r"\\(?!\\)", r"\\\\", s)):
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    return default


def narration_hash(script: str) -> str:
    spoken = script
    try:
        import text_normalizer as tn
        spoken = tn.normalize(script)
    except Exception:
        pass
    return hashlib.sha256(spoken.encode("utf-8")).hexdigest()[:16]


# ---- restricted expression evaluator (arithmetic over x) ------------------
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


# ---- style context: the evolving representation layer ---------------------
ROLE_INDEX = {"primary": 0, "secondary": 1, "accent": 2,
              "alert": 3, "ink": 4, "field": 5}


class StyleContext:
    """DIR->CIR->MIR bridge. Genome decides look; specs decide meaning."""

    def __init__(self, genome, fw, fh, generation=None):
        self.g = genome
        self.fw, self.fh = fw, fh
        self.generation = generation
        self._cols = genome.palette(6) if genome else None
        self._rng = random.Random((genome.seed_text if genome else "fallback")
                                  + "|ctx")

    def color(self, spec, role_default="primary"):
        if isinstance(spec, dict) and spec.get("color"):
            return spec["color"]                      # teacher override wins
        if not self._cols:
            return {"primary": "YELLOW", "accent": "RED",
                    "alert": "RED", "ink": "WHITE"}.get(role_default, "YELLOW")
        role = (spec or {}).get("role", role_default)
        return self._cols[ROLE_INDEX.get(role, 0) % 6]

    def place(self, i, n, spec, default=(0, 0, 0)):
        if isinstance(spec, dict):
            p = spec.get("pos", spec.get("center"))
            if p:
                p = list(p) + [0.0] * (3 - len(p))
                return tuple(p)
        if self.g:
            x, y = self.g.slot(i, max(1, n), self.fw * 0.86, self.fh * 0.80)
            return (x, y, 0.0)
        return tuple(default)

    def run_time(self, base):
        return base * (self.g.pace if self.g else 1.0)

    def stroke(self):
        return self.g.stroke if self.g else 3.0

    def dot(self, spec):
        return float((spec or {}).get("radius",
                                      self.g.dot_radius if self.g else 0.08))

    def opacity(self):
        return self.g.opacity if self.g else 1.0

    def font(self, base):
        return int(base * (self.g.label_scale if self.g else 1.0))

    def rate_func(self):
        if self.g and _RF is not None:
            return getattr(_RF, self.g.rate_func_name(), _RF.smooth)
        return linear

    def entrance(self, mob):
        tag = self.g.entrance if self.g else "create"
        if tag == "write":
            return Write(mob)
        if tag == "grow":
            return GrowArrow(mob) if isinstance(mob, Arrow) else Create(mob)
        if tag == "fade-scale":
            return FadeIn(mob, scale=0.8)
        return Create(mob)

    def equation_slot(self, i, total):
        top = self.fh / 2 - 1.1 - 0.9 * i
        if self.g:
            x = self.g.slot(i, max(1, total), self.fw * 0.55, 1.0)[0]
            return (x, top, 0.0)
        return (0.0, top, 0.0)

    def camera(self):
        if self.g:
            r = random.Random(self.g.seed_text + "|cam")
            return (math.radians(r.uniform(55, 80)),
                    math.radians(r.uniform(-60, -10)))
        return (70 * PI / 180, -30 * PI / 180)


def _recent_genomes(limit=12):
    path = ROOT / "logs" / "style_ledger.jsonl"
    out = []
    if sg is None or not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except Exception:
            continue
        g = rec.get("genome")
        if isinstance(g, dict):
            try:
                out.append(sg.Genome(**g))
            except Exception:
                pass
    return out[-limit:]


def make_context():
    fw, fh = config.frame_width, config.frame_height
    if sg is None:
        return StyleContext(None, fw, fh)
    g, gen = sg.fresh_genome(ROW.get("video_id", "demo"),
                             ROW.get("concept_type", "GENERIC"),
                             JOB.get("audience", "jee"),
                             _recent_genomes())
    return StyleContext(g, fw, fh, generation=gen)


# ---- branding + reporting mix-in ------------------------------------------
class SaemLabsBranding:
    def add_intro(self, title, tagline, ctx):
        t = Text(title, font_size=ctx.font(34), weight="BOLD").to_edge(UP, buff=0.4)
        s = Text(tagline, font_size=ctx.font(22), slant="ITALIC").next_to(t, DOWN, buff=0.2)
        return VGroup(t, s)

    def add_outro(self, ctx):
        return Text("SaemLabs · NEET · JEE · MIT",
                    font_size=ctx.font(20)).to_edge(DOWN, buff=0.3)

    def watermark(self, ctx):
        return Text("SaemLabs", font_size=ctx.font(16),
                    opacity=0.4).to_corner(UR, buff=0.2)


class ReportMixin:
    """Deterministic clock + provenance report, shared by 2D and 3D scenes."""

    def _init_report(self):
        self.failed = []
        self.engines_used = set()
        self._clock = 0.0
        self.ctx = None

    def play(self, *animations, **kwargs):
        rt = kwargs.get("run_time", 1.0)
        res = super().play(*animations, **kwargs)
        self._clock += rt
        return res

    def wait(self, duration=1.0, **kwargs):
        res = super().wait(duration, **kwargs)
        self._clock += duration
        return res

    def write_report(self, primitive_count):
        ctx = self.ctx
        report = {
            "video_id": ROW.get("video_id"),
            "schema_version": 3,
            "core_source_id": CORE_ID or None,
            "narration_hash": narration_hash(ROW.get("audio_script", "")),
            "primitive_count": primitive_count,
            "failed_primitives": self.failed,
            "engines_used": sorted(self.engines_used),
            "routing_parity": parity_report(),
            "backend_decisions": bp.decisions() if bp else [],
            "style": {
                "genome": ctx.g.dict() if (ctx and ctx.g) else None,
                "generation": getattr(ctx, "generation", None),
            },
            "duration_sec": DURATION,
            "orientation": ORIENT,
        }
        Path(JOB.get("report_path", "report.json")).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


# ---- 2D scene ---------------------------------------------------------------
class UniversalPhysicsScene(ReportMixin, Scene, SaemLabsBranding):
    def construct(self):
        self._init_report()
        self.ctx = make_context()
        ctx = self.ctx
        visuals = safe_json_loads(ROW.get("visual_data_json"), []) or []
        equations = safe_json_loads(ROW.get("equations_json"), []) or []
        beats = safe_json_loads(ROW.get("beats_json"), []) or []

        self.add(self.watermark(ctx))
        head = self.add_intro(ROW.get("header_title", ""),
                              ROW.get("tagline", ""), ctx)
        self.play(FadeIn(head), run_time=ctx.run_time(1.0))

        objects, order = self.build_primitives(visuals, ctx)
        eq_mobs = []
        for i, eq in enumerate(equations[:4]):
            try:
                eq_mobs.append(MathTex(eq, font_size=ctx.font(30))
                               .move_to(ctx.equation_slot(i, len(equations))))
            except Exception as e:
                self.failed.append(f"equation:{eq[:20]}:{e}")

        timeline = self.align_beats(beats, objects)
        shown, last = set(), 1.0
        for t, focus in timeline:
            dt = max(0.2, t - last)
            self.wait(dt)
            last = t + dt
            mob = objects.get(focus)
            if mob is not None and focus not in shown:
                self.play(ctx.entrance(mob),
                          run_time=ctx.run_time(min(2.0, dt + 1.0)),
                          rate_func=ctx.rate_func())
                shown.add(focus)
        for key, mob in objects.items():
            if key not in shown:
                self.play(ctx.entrance(mob), run_time=ctx.run_time(0.8),
                          rate_func=ctx.rate_func())
                shown.add(key)
        for m in eq_mobs:
            self.play(Write(m), run_time=ctx.run_time(0.8))

        remaining = max(0.5, DURATION + 4.0 - self._clock)
        self.wait(min(remaining, 4.0))
        self.play(FadeIn(self.add_outro(ctx)), run_time=ctx.run_time(1.5))
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

    def build_primitives(self, visuals, ctx):
        objects, order = {}, []
        for i, spec in enumerate(visuals):
            if not isinstance(spec, dict):
                self.failed.append(f"visual[{i}]:not-a-dict")
                continue
            ptype = spec.get("type", "?")
            spec.setdefault("id", f"p{i}")
            builder = getattr(self, f"_prim_{ptype}", None)
            src = "inline"
            if builder is None:
                hit = engine_table().get(ptype)
                if hit is not None:
                    src, fn = hit
                    builder = (lambda _fn=fn: (lambda s, _c: _fn(self, s)))()
            if builder is None:
                self.failed.append(f"unknown:{ptype}")
                print(f"[WARN] unknown primitive '{ptype}' skipped")
                continue
            try:
                mob = builder(spec, ctx)
                if mob is not None:
                    objects[spec["id"]] = mob
                    order.append(spec["id"])
                    if src != "inline":
                        self.engines_used.add(src)
            except Exception as e:
                self.failed.append(f"{ptype}:{e}")
                print(f"[WARN] primitive '{ptype}' failed via {src}: {e}")
        return objects, order

    # static -------------------------------------------------------------
    def _prim_text(self, s, ctx):
        return Text(str(s.get("text", "")), font_size=ctx.font(24),
                    color=ctx.color(s, "ink")).move_to(ctx.place(0, 1, s))

    def _prim_dot(self, s, ctx):
        return Dot(ctx.place(0, 1, s), radius=ctx.dot(s),
                   color=ctx.color(s, "accent"), fill_opacity=ctx.opacity())
    _prim_charge = _prim_dot
    _prim_particle = _prim_dot

    def _prim_vector(self, s, ctx):
        if "start" in s and "end" in s:
            a, b = tuple(s["start"]) + (0.0,), tuple(s["end"]) + (0.0,)
        else:
            a, b = (0, -1, 0), (0, 1, 0)
        return Arrow(a, b, buff=0, color=ctx.color(s),
                     stroke_width=ctx.stroke())
    _prim_arrow = _prim_vector
    _prim_force = _prim_vector

    def _prim_line(self, s, ctx):
        return Line(tuple(s.get("start", [-2, 0, 0])),
                    tuple(s.get("end", [2, 0, 0])),
                    color=ctx.color(s, "ink"), stroke_width=ctx.stroke())
    _prim_rod = _prim_line
    _prim_segment = _prim_line

    def _prim_circle(self, s, ctx):
        return Circle(radius=s.get("radius", 1.0), color=ctx.color(s),
                      stroke_width=ctx.stroke()).move_to(ctx.place(0, 1, s))
    _prim_lens = _prim_circle

    def _prim_ellipse(self, s, ctx):
        return Ellipse(width=s.get("width", 2.0), height=s.get("height", 1.0),
                       color=ctx.color(s),
                       stroke_width=ctx.stroke()).move_to(ctx.place(0, 1, s))

    def _prim_rectangle(self, s, ctx):
        return Rectangle(width=s.get("width", 2.0), height=s.get("height", 1.0),
                         color=ctx.color(s, "ink"),
                         stroke_width=ctx.stroke()).move_to(ctx.place(0, 1, s))
    _prim_shape = _prim_rectangle

    def _prim_polygon(self, s, ctx):
        pts = [tuple(p) + (0.0,) * (3 - len(p))
               for p in s.get("points", [[-1, -1], [1, -1], [0, 1]])]
        return Polygon(*pts, color=ctx.color(s, "ink"),
                       stroke_width=ctx.stroke())

    def _prim_brace(self, s, ctx):
        a = tuple(s.get("start", [-1, 0, 0]))
        b = tuple(s.get("end", [1, 0, 0]))
        return Brace(Line(a, b), direction=DOWN, color=ctx.color(s, "accent"))

    def _prim_graph(self, s, ctx):
        ax = Axes(x_range=s.get("x_range", [-4, 4]),
                  y_range=s.get("y_range", [-3, 3]),
                  x_length=s.get("x_length", 6.0),
                  y_length=s.get("y_length", 4.0)).move_to(ctx.place(0, 1, s, (0, -1, 0)))
        curve = ax.plot(lambda t: eval_expr(s.get("expression", "x"), t),
                        color=ctx.color(s), stroke_width=ctx.stroke())
        return VGroup(ax, curve)
    _prim_function = _prim_graph
    _prim_curve = _prim_graph
    _prim_calculus_graph = _prim_graph

    def _prim_derivative_tangent(self, s, ctx):
        ax = Axes(x_range=s.get("x_range", [-3, 3]),
                  y_range=s.get("y_range", [-3, 3]),
                  x_length=6.0, y_length=4.0).move_to(ctx.place(0, 1, s, (0, -1, 0)))
        expr = s.get("expression", "x^2")
        x0, d = float(s.get("x0", 1.0)), float(s.get("delta", 0.5))
        curve = ax.plot(lambda t: eval_expr(expr, t),
                        color=ctx.color(s), stroke_width=ctx.stroke())
        mobs = [ax, curve]
        sec = None
        for maker in (lambda: ax.get_secant_line_group(curve, x0, d),
                      lambda: ax.get_secant_line(curve, x0, dx=d)):
            try:
                sec = maker()
                break
            except Exception:
                sec = None
        if sec is None:
            try:
                p1 = ax.c2p(x0, eval_expr(expr, x0))
                p2 = ax.c2p(x0 + d, eval_expr(expr, x0 + d))
                sec = Line(p1, p2, color=ctx.color(s, "secondary"),
                           stroke_width=ctx.stroke())
            except Exception:
                sec = None
        if sec is not None:
            mobs.append(sec)
        if s.get("tangent"):
            try:
                h = 1e-4
                slope = (eval_expr(expr, x0 + h) - eval_expr(expr, x0 - h)) / (2 * h)
                c = ax.c2p(x0, eval_expr(expr, x0))
                mobs.append(Line(c + LEFT * 1.2 + DOWN * 1.2 * slope,
                                 c + RIGHT * 1.2 + UP * 1.2 * slope,
                                 color=ctx.color(s, "accent"),
                                 stroke_width=ctx.stroke()))
            except Exception:
                self.failed.append("derivative_tangent:tangent")
        return VGroup(*mobs)

    def _prim_number_line(self, s, ctx):
        nl = NumberLine(x_range=s.get("x_range", [-5, 5]),
                        length=s.get("length", 6.0)).move_to(ctx.place(0, 1, s))
        return VGroup(nl, Dot(nl.n2p(float(s.get("value", 0))),
                              radius=ctx.dot(s), color=ctx.color(s, "accent")))

    def _prim_wave(self, s, ctx):
        ax = Axes(x_range=s.get("x_range", [-4, 4]), y_range=[-1.5, 1.5],
                  x_length=7.0, y_length=2.0).move_to(ctx.place(0, 1, s, (0, -1, 0)))
        amp, freq = float(s.get("amplitude", 0.6)), float(s.get("frequency", 1.0))
        curve = ax.plot(lambda t: amp * math.sin(2 * math.pi * freq * t / 4.0),
                        color=ctx.color(s), stroke_width=ctx.stroke())
        return VGroup(ax, curve)

    def _prim_energy_bar(self, s, ctx):
        col = ctx.color(s)
        bar = Rectangle(width=0.6, height=3.0, color=col,
                        stroke_width=ctx.stroke()).move_to(ctx.place(0, 1, s))
        fill = Rectangle(width=0.5, height=3.0 * float(s.get("fraction", 0.5)),
                         color=col, fill_opacity=ctx.opacity() * 0.7,
                         stroke_width=0).align_to(bar, DOWN)
        return VGroup(bar, fill)

    def _prim_pendulum(self, s, ctx):
        pivot = ctx.place(0, 1, s, (0, 2, 0))
        rod = Line(pivot, (pivot[0], pivot[1] - 2.0, 0),
                   color=ctx.color(s, "ink"), stroke_width=ctx.stroke())
        bob = Dot((pivot[0], pivot[1] - 2.0, 0), radius=ctx.dot(s) * 1.8,
                  color=ctx.color(s, "accent"))
        return VGroup(rod, bob)

    def _prim_spring(self, s, ctx):
        base = Line((-0.5, 2, 0), (0.5, 2, 0)).move_to(ctx.place(0, 1, s, (0, 2, 0)))
        coil = VGroup(*[Line(((-0.3) ** k, 2 - 0.2 * k, 0),
                             ((0.3) ** k, 2 - 0.2 * k - 0.1, 0),
                             stroke_width=ctx.stroke())
                        for k in range(6)]).move_to(ctx.place(0, 1, s, (0, 1, 0)))
        mass = Rectangle(width=0.5, height=0.5, color=ctx.color(s),
                         stroke_width=ctx.stroke()).move_to(ctx.place(0, 1, s, (0, -0.5, 0)))
        return VGroup(base, coil, mass)

    def _prim_orbit(self, s, ctx):
        el = Ellipse(width=s.get("width", 4.0), height=s.get("height", 2.5),
                     color=ctx.color(s, "field"),
                     stroke_width=ctx.stroke()).move_to(ctx.place(0, 1, s))
        return VGroup(el, Dot(el.point_from_proportion(0.0),
                              radius=ctx.dot(s), color=ctx.color(s, "accent")))

    def _prim_ray(self, s, ctx):
        return Arrow(tuple(s.get("start", [-3, 0, 0])),
                     tuple(s.get("end", [3, 0, 0])), buff=0,
                     color=ctx.color(s, "accent"), stroke_width=2)

    def _prim_particle_gas(self, s, ctx):
        c = ctx.place(0, 1, s)
        box = Rectangle(width=4.0, height=3.0, color=ctx.color(s, "ink"),
                        stroke_width=ctx.stroke()).move_to(c)
        dots = VGroup(*[Dot(c + UP * (0.3 * ((k * 7) % 5 - 2)) +
                            RIGHT * (0.4 * ((k * 3) % 7 - 3)),
                            radius=0.05, color=ctx.color(s, "accent"))
                        for k in range(int(s.get("count", 12)))])
        return VGroup(box, dots)

    def _prim_heat_flow(self, s, ctx):
        c = ctx.place(0, 1, s)
        hot = Rectangle(width=1.0, height=2.0, color=ctx.color(s, "alert"),
                        fill_opacity=0.6, stroke_width=ctx.stroke()).move_to(c + LEFT * 2)
        cold = Rectangle(width=1.0, height=2.0, color=ctx.color(s, "secondary"),
                         fill_opacity=0.6, stroke_width=ctx.stroke()).move_to(c + RIGHT * 2)
        arrows = VGroup(*[Arrow(c + LEFT * 1.2 + UP * (0.5 * (k - 1)),
                                c + RIGHT * 1.2 + UP * (0.5 * (k - 1)),
                                buff=0, color=ctx.color(s, "accent"),
                                stroke_width=2) for k in range(3)])
        return VGroup(hot, cold, arrows)

    def _prim_projectile_motion(self, s, ctx):
        v0 = float(s.get("v0", 20.0))
        ang = math.radians(float(s.get("angle", 45.0)))
        g = float(s.get("g", 9.8))
        t_end = 2 * v0 * math.sin(ang) / g
        scale = 6.0 / max(1e-9, v0 * math.cos(ang) * t_end)
        path = VMobject(color=ctx.color(s), stroke_width=ctx.stroke())
        pts = []
        for k in range(61):
            t = t_end * k / 60.0
            x = v0 * math.cos(ang) * t
            y = v0 * math.sin(ang) * t - 0.5 * g * t * t
            pts.append((-3.0 + scale * x, -2.5 + scale * y, 0.0))
        path.set_points_smoothly(pts)
        return VGroup(path, Dot(pts[0], radius=ctx.dot(s),
                                color=ctx.color(s, "accent")))

    def _prim_equation_morph(self, s, ctx):
        mobs = VGroup()
        for st in s.get("steps", [])[:6]:
            try:
                mobs.add(MathTex(st, font_size=ctx.font(26)))
            except Exception:
                self.failed.append(f"equation_morph:{st[:20]}")
        return mobs.arrange(DOWN, buff=0.25).move_to(ctx.place(0, 1, s))

    def _prim_numerical_chain(self, s, ctx):
        mobs = VGroup(*[Text(str(l), font_size=ctx.font(20),
                             color=ctx.color(s, "ink"))
                        for l in s.get("lines", [])[:8]])
        return mobs.arrange(DOWN, buff=0.2, aligned_edge=LEFT).move_to(ctx.place(0, 1, s))

    def _prim_warning_box(self, s, ctx):
        col = ctx.color(s, "alert")
        t = Text(str(s.get("text", "!")), font_size=ctx.font(22), color=col)
        box = Rectangle(width=t.width + 0.6, height=t.height + 0.4,
                        color=col, stroke_width=ctx.stroke())
        return VGroup(box, t.move_to(box.get_center())).move_to(ctx.place(0, 1, s))

    def _prim_quiz_frame(self, s, ctx):
        q = Text(str(s.get("question", "?")), font_size=ctx.font(22),
                 color=ctx.color(s, "ink"))
        opts = VGroup(*[Text(str(o), font_size=ctx.font(18),
                             color=ctx.color(s, "secondary"))
                        for o in s.get("options", [])[:4]])
        opts.arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        return VGroup(q, opts.next_to(q, DOWN, buff=0.3)).move_to(ctx.place(0, 1, s, (0, 1, 0)))

    def _prim_live_label(self, s, ctx):
        tracker = ValueTracker(0.0)
        label = always_redraw(lambda: Text(
            f"{s.get('prefix', 't')} = {tracker.get_value():.2f} {s.get('unit', '')}",
            font_size=ctx.font(20), color=ctx.color(s, "ink"))
            .move_to(ctx.place(0, 1, s)))
        self.add(label)
        self.play(tracker.animate.set_value(float(s.get("to", DURATION))),
                  run_time=min(4.0, DURATION / 2), rate_func=ctx.rate_func())
        return None

    def _prim_group(self, s, ctx):
        kids, _ = self.build_primitives(s.get("children", []), ctx)
        return VGroup(*kids.values()) if kids else None


# ---- 3D scene ---------------------------------------------------------------
class Universal3DScene(ReportMixin, ThreeDScene, SaemLabsBranding):
    def construct(self):
        self._init_report()
        self.ctx = make_context()
        ctx = self.ctx
        phi, theta = ctx.camera()
        self.set_camera_orientation(phi=phi, theta=theta)
        visuals = safe_json_loads(ROW.get("visual_data_json"), []) or []
        self.add(Text(ROW.get("header_title", ""),
                      font_size=ctx.font(30)).to_edge(UP))
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
                mob.set_color(ctx.color(spec))
                mob.move_to(spec.get("position", [0, 0, 0]))
                self.play(ctx.entrance(mob), run_time=ctx.run_time(1.0))
            except Exception as e:
                self.failed.append(f"3d:{kind}:{e}")
        self.wait(2.0)
        self.write_report(len(visuals))


# ---- parity hooks for tools/engine_check.py --------------------------------
def routed_types():
    own = {n[len("_prim_"):] for n in dir(UniversalPhysicsScene)
           if n.startswith("_prim_")}
    return own | set(engine_table())


def parity_report():
    try:
        import schema_validator as sv
        known = set(sv.KNOWN_PRIMITIVES)
    except Exception:
        known = set()
    routed = routed_types()
    return {"unrouted": sorted(known - routed),
            "unknown": sorted(routed - known)}


if __name__ == "__main__":
    print("render_universal (gen-3) is driven by manim with SAEM_JOB set; "
          "look evolves via tools/style_genome; see batch_runner.py")
