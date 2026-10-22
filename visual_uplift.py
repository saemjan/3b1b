#!/usr/bin/env python3
"""Visual Uplift v1 — 3b1b-style visual grammar for saemjan/3b1b pipeline.

Drop-in module. Wire via `tools/apply_uplift.py`.
Provides: MathTex rendering, construction animations, beat-driven camera,
palette, ambient loops, equation morphs on `law` beat.
"""
from __future__ import annotations
from typing import Any, List, Optional

PALETTE = {
    "bg":            "#0F0F13",
    "grid":          "#1E1E28",
    "cream":         "#F2F3F5",
    "title":         "#F2F3F5",
    "math":          "#8AC926",
    "caption":       "#F1C40F",
    "model_default": "#4CC9F0",
}


def setup_scene_background(scene, orientation: str):
    """Dark background + faint NumberPlane grid — 3b1b signature."""
    from manim import NumberPlane
    scene.camera.background_color = PALETTE["bg"]
    grid = NumberPlane(
        background_line_style=dict(
            stroke_color=PALETTE["grid"],
            stroke_opacity=0.15,
            stroke_width=1,
        ),
        x_range=(-10, 10, 1),
        y_range=(-10, 10, 1),
    )
    scene.add(grid)
    return grid


def build_title_text(scene, element: dict, orientation: str):
    """Title with Write(lag_ratio=0.04) construction."""
    from manim import Text, Write
    t = Text(
        element["text"],
        font_size=element.get("font_size", 34),
        color=element.get("color", PALETTE["title"]),
        weight="BOLD",
    ).move_to(element["pos"])
    scene.play(Write(t, lag_ratio=0.04, run_time=1.2))
    return t


def build_math_tex(scene, element: dict, equations: List[str], orientation: str):
    """Render first equation as MathTex (real LaTeX) replacing static text."""
    from manim import MathTex, Write
    latex = equations[0] if equations else element.get("text", "")
    m = MathTex(
        latex,
        color=element.get("color", PALETTE["math"]),
        font_size=int(element.get("font_size", 36) * 1.3),
    ).move_to(element["pos"])
    scene.play(Write(m, run_time=1.5))
    return m


def build_caption(scene, element: dict, orientation: str, keyword: Optional[str] = None):
    """Caption with shift-in + optional keyword Indicate."""
    from manim import Text, FadeIn, Indicate
    c = Text(
        element["text"],
        font_size=element.get("font_size", 24),
        color=element.get("color", PALETTE["caption"]),
    ).move_to(element["pos"])
    scene.play(FadeIn(c, shift=[0, 0.3, 0], run_time=0.8))
    return c


def morph_equations(scene, equations: List[str], anchor_pos, current_mobj=None):
    """Signature 3b1b move: TransformMatchingTex between equations.
    Called on `law` or `emphasis` beats when multiple equations exist."""
    from manim import MathTex, TransformMatchingTex, Write
    if not equations or len(equations) < 2:
        return current_mobj
    target_idx = 1 if current_mobj is not None else 0
    new_tex = MathTex(
        equations[target_idx],
        color=PALETTE["math"],
        font_size=46,
    ).move_to(anchor_pos)
    if current_mobj is not None:
        scene.play(TransformMatchingTex(current_mobj, new_tex, run_time=1.4))
    else:
        scene.play(Write(new_tex, run_time=1.2))
    return new_tex


def camera_beat(scene, beat: dict, orientation: str):
    """Wire beat transition to camera move."""
    transition = (beat.get("transition") or "").lower()
    cam = getattr(scene, "camera", None)
    if cam is None or not hasattr(cam, "frame"):
        return
    f = cam.frame
    try:
        if transition == "push":
            scene.play(f.animate.scale(0.95).shift([0, 0.15, 0]), run_time=1.2)
        elif transition == "zoom_blur":
            scene.play(f.animate.scale(0.90), run_time=1.0)
        elif transition == "wipe":
            scene.play(f.animate.shift([1.2, 0, 0]), run_time=1.2)
    except Exception:
        pass


def on_beat(scene, beat: dict, beat_index: int, beats: List[dict],
            equations: List[str], math_mobj, orientation: str):
    """Dispatcher: signature animations on specific beats."""
    btype = beat.get("type", "")
    new_math = math_mobj
    if btype in ("law", "emphasis") and len(equations) >= 2 and math_mobj is not None:
        new_math = morph_equations(
            scene, equations,
            math_mobj.get_center(),
            current_mobj=math_mobj if beat_index > 0 else None,
        )
    if btype == "midpoint":
        cam = getattr(scene, "camera", None)
        if cam is not None and hasattr(cam, "frame"):
            try:
                scene.play(cam.frame.animate.shift([0.3, 0, 0]), run_time=2.0)
            except Exception:
                pass
    if btype == "silent":
        scene.wait(0.8)
    camera_beat(scene, beat, orientation)
    return new_math
