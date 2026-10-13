#!/usr/bin/env python3
"""
visual_kit.py — Cinematic additions for render_universal.py (v2.2+).

Eight helpers:
  1. annotate()             — pointer arrow + label to a target
  2. spotlight()            — dim everything except the focus
  3. ambient()              — subtle continuous motion during waits
  4. kinetic_title()        — letter-by-letter title reveal
  5. term_bind()            — color-match equation terms to visuals
  6. camera_shake()         — brief impact shake
  7. vector_decomposition() — draw vx and vy components of a vector
  8. cinematic_transition() — wipe / push / iris / zoom_blur
"""
from __future__ import annotations
import numpy as np
from manim import (
    VGroup, Arrow, Line, DashedLine, Text, MathTex, Dot, Circle,
    Rectangle, RoundedRectangle, FadeIn, FadeOut, GrowArrow, Create,
    Write, UP, DOWN, LEFT, RIGHT, ORIGIN, TAU,
    there_and_back, rate_functions as rf, config, VMobject, ValueTracker,
)
try:
    from manim import LaggedStart
except ImportError:
    LaggedStart = None


COLOR = {
    "accent": "#F1C40F", "field": "#3498DB", "force": "#2ECC71",
    "pos": "#FF4B4B", "neg": "#00D2FF", "muted": "#8A8F9C",
    "white": "#F2F3F5", "card": "#15161D", "border": "#2A2C36",
}


def _is_latex(s):
    return any(c in str(s) for c in ("\\", "^", "_", "{"))


def _label(text, size=22, color=None):
    color = color or COLOR["accent"]
    try:
        if _is_latex(text):
            return MathTex(text, font_size=size, color=color)
        return Text(text, font_size=size, color=color)
    except Exception:
        return Text(str(text), font_size=size, color=color)


def _mob_edge(m, direction):
    try:
        if direction is UP:    return m.get_top()
        if direction is DOWN:  return m.get_bottom()
        if direction is LEFT:  return m.get_left()
        if direction is RIGHT: return m.get_right()
    except Exception:
        pass
    try:
        return m.get_center()
    except Exception:
        return np.zeros(3)


def annotate(scene, target, text, direction=UP, distance=1.2,
             color=None, font_size=22, run_time=0.6,
             hold=1.6, fade_out=True):
    color = color or COLOR["accent"]
    if target is None:
        return None
    try:
        edge = _mob_edge(target, direction)
        tip = edge
        tail = edge + direction * distance
        arrow = Arrow(tail, tip, buff=0.05, color=color, stroke_width=3,
                      max_tip_length_to_length_ratio=0.30)
    except Exception:
        return None
    lbl = _label(text, size=font_size, color=color)
    try:
        lbl.next_to(arrow.get_start(), direction, buff=0.10)
    except Exception:
        lbl.move_to(arrow.get_start() + direction * 0.4)
    group = VGroup(arrow, lbl)
    scene.play(GrowArrow(arrow),
               FadeIn(lbl, shift=direction * 0.10),
               run_time=run_time, rate_func=rf.ease_out_cubic)
    scene.wait(hold)
    if fade_out:
        scene.play(FadeOut(group, shift=direction * 0.15),
                   run_time=0.4, rate_func=rf.ease_in_cubic)
        return None
    return group


def story_callout(scene, target, header, subtitle=None, detail=None,
                  direction=UP, distance=0.8, color=None,
                  accent=None, run_time=0.8, hold=0.6,
                  fade_out=True):
    """Show a minimal, 3Blue1Brown/Feynman-style cue on a focal object."""
    if target is None:
        return None
    color = color or COLOR["white"]
    accent = accent or COLOR["accent"]

    try:
        edge = _mob_edge(target, direction)
        tip = edge + direction * 0.1
        tail = tip + direction * (distance + 0.4)
    except Exception:
        tail = np.array([0.0, 0.0, 0.0])
        tip = np.array([0.0, 0.0, 0.0])

    label = _label(str(header), size=20, color=accent)
    label.set_z_index(10)
    body = VGroup(label)
    if subtitle:
        sub = _label(str(subtitle), size=15, color=color)
        body = VGroup(label, sub)
        body.arrange(DOWN, buff=0.12, aligned_edge=LEFT)
    if detail:
        det = _label(str(detail), size=12, color=COLOR["muted"])
        try:
            body.add(det)
            body.arrange(DOWN, buff=0.08, aligned_edge=LEFT)
        except Exception:
            pass

    badge = RoundedRectangle(
        width=max(body.width + 0.5, 2.2),
        height=max(body.height + 0.35, 0.9),
        corner_radius=0.16,
        fill_color="#15161D",
        fill_opacity=0.92,
        stroke_color=accent,
        stroke_width=1.4,
    )
    badge.set_z_index(9)
    callout = VGroup(badge, body)
    callout.arrange(DOWN, buff=0.12, aligned_edge=LEFT)
    try:
        callout.next_to(target, direction, buff=distance)
    except Exception:
        callout.move_to(tail)

    arrow = Arrow(tail, tip, buff=0.05, color=accent, stroke_width=2.5,
                  max_tip_length_to_length_ratio=0.35)
    group = VGroup(arrow, callout)

    scene.play(FadeIn(callout, shift=direction * 0.15),
               GrowArrow(arrow),
               run_time=run_time, rate_func=rf.ease_out_cubic)
    if hold:
        scene.wait(hold)
    if fade_out:
        scene.play(FadeOut(group, shift=direction * 0.15),
                   run_time=0.35, rate_func=rf.ease_in_cubic)
    return group


def spotlight(scene, target, dim=0.20, run_time=0.5, exclude=None):
    exclude_ids = {id(m) for m in (exclude or [])}
    exclude_ids.add(id(target))
    dim_targets = []
    for m in scene.mobjects:
        if id(m) in exclude_ids:
            continue
        if getattr(m, "updaters", None):
            continue
        try:
            if m.get_opacity() < 0.05:
                continue
        except Exception:
            pass
        dim_targets.append(m)
    if not dim_targets:
        return []
    anims = [m.animate.set_opacity(dim) for m in dim_targets]
    scene.play(*anims, run_time=run_time,
               rate_func=rf.ease_in_out_sine)
    return dim_targets


def unspotlight(scene, dimmed, run_time=0.5):
    if not dimmed:
        return
    anims = [m.animate.set_opacity(1.0) for m in dimmed]
    scene.play(*anims, run_time=run_time,
               rate_func=rf.ease_in_out_sine)


_AMBIENT_INSTALLED = set()


def ambient(scene, mobs, amp=0.02, period=4.0):
    if not mobs:
        return
    gt = getattr(scene, "global_time", None)
    if gt is None:
        gt = ValueTracker(0.0)
        gt.add_updater(lambda m, dt: m.increment_value(dt))
        scene.add(gt)
        scene.global_time = gt

    for m in mobs:
        if id(m) in _AMBIENT_INSTALLED:
            continue
        if getattr(m, "updaters", None):
            continue
        try:
            base = m.get_center().copy()
        except Exception:
            continue

        def _mk(mob, base, amp=amp, period=period, gt=gt):
            def upd(mm, dt):
                t = gt.get_value()
                dy = amp * np.sin(2 * np.pi * t / period)
                try:
                    mm.move_to(base + np.array([0.0, dy, 0.0]))
                except Exception:
                    pass
            return upd

        m.add_updater(_mk(m, base))
        _AMBIENT_INSTALLED.add(id(m))


def kinetic_title(scene, text, pos=None, size=48, color=None,
                  stagger=0.04, run_time=1.2, hold=0.8, fade_out=True):
    color = color or COLOR["white"]
    if pos is None:
        pos = np.array([0.0, 0.0, 0.0])
    try:
        chars = [Text(c, font_size=size, color=color) for c in str(text)]
    except Exception:
        chars = [Text(str(text), font_size=size, color=color)]
    group = VGroup(*chars).arrange(RIGHT, buff=size * 0.006)
    group.move_to(pos)
    anims = [FadeIn(c, shift=UP * 0.10) for c in chars]
    if LaggedStart is not None and len(anims) > 1:
        scene.play(LaggedStart(*anims, lag_ratio=stagger),
                   run_time=run_time, rate_func=rf.ease_out_cubic)
    else:
        scene.play(*anims, run_time=run_time)
    scene.wait(hold)
    if fade_out:
        scene.play(FadeOut(group, shift=UP * 0.20),
                   run_time=0.5, rate_func=rf.ease_in_cubic)
        return None
    return group


def term_bind(scene, equation, term_indices, visuals, colors=None,
              pulse=True):
    if colors is None:
        colors = [COLOR["accent"], COLOR["force"],
                  COLOR["pos"], COLOR["field"]]
    eq_children = equation
    if not isinstance(eq_children, (list, tuple)):
        try:
            eq_children = list(equation)
        except Exception:
            eq_children = [equation]

    for i, idx in enumerate(term_indices):
        if i >= len(visuals):
            break
        col = colors[i % len(colors)]
        try:
            if idx < len(eq_children):
                eq_children[idx].set_color(col)
        except Exception:
            pass
        try:
            visuals[i].set_color(col)
        except Exception:
            pass

    if not pulse:
        return
    for i, idx in enumerate(term_indices):
        if i >= len(visuals):
            break
        try:
            scene.play(
                eq_children[idx].animate(
                    rate_func=there_and_back, run_time=0.6).scale(1.15),
                visuals[i].animate(
                    rate_func=there_and_back, run_time=0.6).scale(1.10),
                run_time=0.6,
            )
        except Exception:
            continue


def camera_shake(scene, amplitude=0.15, cycles=4, run_time=0.4):
    try:
        frame = scene.camera.frame
    except Exception:
        return
    try:
        base = frame.get_center().copy()
    except Exception:
        return
    per = run_time / max(1, cycles)
    for i in range(cycles):
        dx = amplitude * (1 if i % 2 == 0 else -1)
        scene.play(frame.animate.move_to(base + np.array([dx, 0, 0])),
                   run_time=per, rate_func=lambda t: t)
    scene.play(frame.animate.move_to(base), run_time=per)


def vector_decomposition(scene, vector, show_labels=True,
                         comp_color_x=None, comp_color_y=None,
                         run_time=1.0):
    comp_color_x = comp_color_x or COLOR["force"]
    comp_color_y = comp_color_y or COLOR["field"]
    try:
        start = vector.get_start()
        end = vector.get_end()
    except Exception:
        return None
    foot = np.array([end[0], start[1], 0.0])
    arrow_x = Arrow(start, foot, buff=0, color=comp_color_x,
                    stroke_width=3,
                    max_tip_length_to_length_ratio=0.30)
    arrow_y = Arrow(foot, end, buff=0, color=comp_color_y,
                    stroke_width=3,
                    max_tip_length_to_length_ratio=0.30)
    scene.play(Create(arrow_x), Create(arrow_y), run_time=run_time)
    labels = None
    if show_labels:
        lx = _label("v_x", size=20, color=comp_color_x)
        ly = _label("v_y", size=20, color=comp_color_y)
        try:
            lx.next_to(arrow_x, DOWN, buff=0.10)
            ly.next_to(arrow_y, RIGHT, buff=0.10)
        except Exception:
            pass
        scene.play(FadeIn(lx), FadeIn(ly), run_time=0.4)
        labels = VGroup(lx, ly)
    return VGroup(arrow_x, arrow_y, labels) if labels else \
           VGroup(arrow_x, arrow_y)


def cinematic_transition(scene, kind="wipe", direction="right",
                         duration=0.7):
    fw = config.frame_width
    fh = config.frame_height

    if kind == "wipe":
        cover = Rectangle(width=fw * 1.2, height=fh * 1.2,
                          fill_color=COLOR["card"], fill_opacity=1.0,
                          stroke_width=0)
        cover.move_to(np.array([-fw * 1.2, 0, 0]))
        scene.add(cover)
        scene.play(cover.animate.move_to(ORIGIN),
                   run_time=duration * 0.5, rate_func=rf.ease_in_cubic)
        scene.play(cover.animate.move_to(np.array([fw * 1.2, 0, 0])),
                   run_time=duration * 0.5, rate_func=rf.ease_out_cubic)
        scene.remove(cover)

    elif kind == "push":
        dx = -fw if direction == "left" else fw
        mobs = [m for m in scene.mobjects if m is not scene.camera.frame]
        if not mobs:
            return
        scene.play(*[m.animate.shift(RIGHT * dx) for m in mobs],
                   run_time=duration, rate_func=rf.ease_in_out_sine)
        scene.play(*[m.animate.shift(RIGHT * -dx) for m in mobs],
                   run_time=0.01)

    elif kind == "iris":
        max_r = float(np.hypot(fw, fh)) * 0.6
        cover = Circle(radius=max_r, fill_color=COLOR["card"],
                       fill_opacity=1.0, stroke_width=0).move_to(ORIGIN)
        scene.add(cover)
        scene.play(cover.animate.scale(0.01),
                   run_time=duration, rate_func=rf.ease_in_cubic)
        scene.remove(cover)

    elif kind == "zoom_blur":
        try:
            frame = scene.camera.frame
            base = frame.get_width()
            scene.play(frame.animate.set(width=base * 0.6),
                       run_time=duration * 0.5, rate_func=rf.ease_in_cubic)
            scene.play(frame.animate.set(width=base),
                       run_time=duration * 0.5, rate_func=rf.ease_out_cubic)
        except Exception:
            pass
