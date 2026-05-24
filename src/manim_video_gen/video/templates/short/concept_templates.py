"""Concept templates for short-form content."""

from __future__ import annotations

from manim_video_gen.models.script import Segment
from manim_video_gen.video.latex_korean import wrap_korean_text_runs
from manim_video_gen.video.tex_template import scene_imports
from manim_video_gen.video.templates.short._layout import (
    CONTENT_ZONE_BOTTOM,
    CONTENT_ZONE_TOP,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    safe_zone_y_offset,
    scale_to_fit_frame,
)

_VALID_COLORS = frozenset({
    "WHITE", "BLACK", "GRAY", "LIGHT_GRAY", "DARK_GRAY",
    "RED", "GREEN", "BLUE", "YELLOW", "ORANGE", "PURPLE",
    "TEAL", "PINK", "GOLD", "MAROON",
})


def _safe_color(name: str, default: str = "WHITE") -> str:
    u = str(name).strip().upper()
    return u if u in _VALID_COLORS else default


def _render_short_concept_equation(segment: Segment, duration: float) -> str:
    """Display a centered equation using MathTex.

    Uses wrap_korean_text_runs for Korean text support and
    scale_to_fit_frame to prevent overflow in 9:16 frames.
    """
    latex = str(segment.visual_params.get("latex", ""))
    if not latex:
        latex = str(segment.visual_params.get("text", "수식"))
    font_size = int(segment.visual_params.get("font_size", 48))
    color = _safe_color(segment.visual_params.get("color", "WHITE"))

    t_write = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_write, 0.5)

    # Apply Korean text wrapping for MathTex compatibility
    wrapped_latex = wrap_korean_text_runs(latex)
    imports = scene_imports(wrapped_latex)
    latex_repr = repr(wrapped_latex)

    # Safe zone Y offset (avoid headline/subtitle areas)
    y_offset = safe_zone_y_offset(has_headline=True, has_subtitle=True)

    # Scale to fit 9:16 frame width
    fit_code = scale_to_fit_frame("eq")

    return f"""{imports}

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        eq = MathTex({latex_repr}, font_size={font_size}).set_color({color})
{fit_code}
        eq.move_to([0, {y_offset:.3f}, 0])
        self.play(Write(eq), run_time={t_write:.3f})
        self.wait({t_wait:.3f})
"""


def _render_short_concept_graph(segment: Segment, duration: float) -> str:
    """Display a simple graph plot."""
    func = str(segment.visual_params.get("func", "lambda x: x"))
    if not func.startswith("lambda"):
        func = "lambda x: x"
    x_min = float(segment.visual_params.get("x_min", -3))
    x_max = float(segment.visual_params.get("x_max", 3))
    color = _safe_color(segment.visual_params.get("color", "BLUE"))

    t_draw = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_draw, 0.5)

    y_offset = safe_zone_y_offset(has_headline=True, has_subtitle=True)

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        axes = Axes(
            x_range=[{x_min}, {x_max}, 1],
            y_range=[-3, 3, 1],
            axis_config={{"include_numbers": True}},
        ).scale(0.7)
        axes.move_to([0, {y_offset:.3f}, 0])

        graph = axes.plot({func}, color={color})

        self.play(Create(axes), run_time=0.8)
        self.play(Create(graph), run_time={t_draw:.3f})
        self.wait({t_wait:.3f})
"""


def _render_short_concept_number_line(segment: Segment, duration: float) -> str:
    """Display a number line with marker."""
    value = float(segment.visual_params.get("value", 0))
    label = repr(str(segment.visual_params.get("label", "")))

    t_anim = min(duration * 0.6, 1.5)
    t_wait = max(duration - t_anim, 0.5)

    y_offset = safe_zone_y_offset(has_headline=True, has_subtitle=True)

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        nl = NumberLine(
            x_range=[-5, 5, 1],
            length=8,
            include_numbers=True,
        )
        nl.move_to([0, {y_offset:.3f}, 0])

        dot = Dot(nl.n2p({value}), color=YELLOW)
        lbl = Text({label}, font_size=36).next_to(dot, UP)

        self.play(Create(nl), run_time=0.8)
        self.play(Create(dot), Write(lbl), run_time={t_anim:.3f})
        self.wait({t_wait:.3f})
"""


def _render_short_concept_annotated(segment: Segment, duration: float) -> str:
    """Display equation with annotation.

    Uses MathTex for the equation and Text for the annotation.
    """
    latex = str(segment.visual_params.get("text", segment.visual_params.get("latex", "")))
    annotation = str(segment.visual_params.get("annotation", ""))

    t_write = min(duration * 0.5, 1.5)
    t_ann = min(duration * 0.3, 1.0)
    t_wait = max(duration - t_write - t_ann, 0.5)

    # Apply Korean text wrapping for MathTex
    wrapped_latex = wrap_korean_text_runs(latex)
    imports = scene_imports(wrapped_latex)
    latex_repr = repr(wrapped_latex)
    ann_repr = repr(annotation)

    y_offset = safe_zone_y_offset(has_headline=True, has_subtitle=True)
    fit_code = scale_to_fit_frame("eq")

    return f"""{imports}

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        eq = MathTex({latex_repr}, font_size=48)
{fit_code}
        eq.move_to([0, {y_offset:.3f}, 0])

        self.play(Write(eq), run_time={t_write:.3f})

        if {ann_repr}:
            brace = Brace(eq, DOWN)
            txt = brace.get_text({ann_repr})
            self.play(Create(brace), Write(txt), run_time={t_ann:.3f})

        self.wait({t_wait:.3f})
"""


def _render_short_concept_compare(segment: Segment, duration: float) -> str:
    """Compare two items side by side with fit_text."""
    left = repr(str(segment.visual_params.get("left", "")))
    right = repr(str(segment.visual_params.get("right", "")))

    t_show = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_show, 0.5)

    y_offset = safe_zone_y_offset(has_headline=True, has_subtitle=True)

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        left_txt = Text({left}, font_size=40)
        if left_txt.width > {FRAME_WIDTH - 2.0}:
            left_txt.scale_to_fit_width({FRAME_WIDTH - 2.0})

        right_txt = Text({right}, font_size=40)
        if right_txt.width > {FRAME_WIDTH - 2.0}:
            right_txt.scale_to_fit_width({FRAME_WIDTH - 2.0})

        vs = Text("VS", font_size=36, color=YELLOW)

        group = VGroup(left_txt, vs, right_txt).arrange(RIGHT, buff=0.5)
        group.move_to([0, {y_offset:.3f}, 0])

        self.play(Write(left_txt), run_time=0.8)
        self.play(Write(vs), run_time=0.4)
        self.play(Write(right_txt), run_time=0.8)
        self.wait({t_wait:.3f})
"""


def _render_short_concept_pattern(segment: Segment, duration: float) -> str:
    """Show a visual pattern with fit_text."""
    items = segment.visual_params.get("items", [])
    if not isinstance(items, list):
        items = []

    t_show = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_show, 0.5)

    items_str = ", ".join(repr(str(i)) for i in items[:5]) if items else repr("패턴")
    y_offset = safe_zone_y_offset(has_headline=True, has_subtitle=True)

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        items = VGroup(*[
            Text(t, font_size=36) for t in [{items_str}]
        ]).arrange(RIGHT, buff=0.5)
        if items.width > {FRAME_WIDTH - 2.0}:
            items.scale_to_fit_width({FRAME_WIDTH - 2.0})
        items.move_to([0, {y_offset:.3f}, 0])

        self.play(Write(items), run_time={t_show:.3f})
        self.wait({t_wait:.3f})
"""


CONCEPT_RENDERERS = {
    "short_concept_equation": _render_short_concept_equation,
    "short_concept_graph": _render_short_concept_graph,
    "short_concept_number_line": _render_short_concept_number_line,
    "short_concept_annotated": _render_short_concept_annotated,
    "short_concept_compare": _render_short_concept_compare,
    "short_concept_pattern": _render_short_concept_pattern,
}
