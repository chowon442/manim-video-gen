"""Concept templates for short-form content."""

from __future__ import annotations

from manim_video_gen.models.script import Segment

_VALID_COLORS = frozenset({
    "WHITE", "BLACK", "GRAY", "LIGHT_GRAY", "DARK_GRAY",
    "RED", "GREEN", "BLUE", "YELLOW", "ORANGE", "PURPLE",
    "TEAL", "PINK", "GOLD", "MAROON",
})


def _safe_color(name: str, default: str = "WHITE") -> str:
    u = str(name).strip().upper()
    return u if u in _VALID_COLORS else default

FRAME_HEIGHT = 19.20
FRAME_WIDTH = 10.80


def _render_short_concept_equation(segment: Segment, duration: float) -> str:
    """Display a centered equation (fallback: Text if no latex param)."""
    latex = str(segment.visual_params.get("latex", ""))
    if not latex:
        latex = str(segment.visual_params.get("text", "수식"))
    font_size = int(segment.visual_params.get("font_size", 48))
    color = _safe_color(segment.visual_params.get("color", "WHITE"))

    t_write = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_write, 0.5)

    # Use Text for better compatibility (no LaTeX dependency)
    text_repr = repr(latex)

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        eq = Text({text_repr}, font_size={font_size}).set_color({color})
        eq.move_to(ORIGIN)
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
        axes.move_to(ORIGIN)

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
        nl.move_to(ORIGIN)

        dot = Dot(nl.n2p({value}), color=YELLOW)
        lbl = Text({label}, font_size=36).next_to(dot, UP)

        self.play(Create(nl), run_time=0.8)
        self.play(Create(dot), Write(lbl), run_time={t_anim:.3f})
        self.wait({t_wait:.3f})
"""


def _render_short_concept_annotated(segment: Segment, duration: float) -> str:
    """Display text with annotations (fallback-safe, no LaTeX)."""
    text = str(segment.visual_params.get("text", segment.visual_params.get("latex", "")))
    annotation = str(segment.visual_params.get("annotation", ""))

    t_write = min(duration * 0.5, 1.5)
    t_ann = min(duration * 0.3, 1.0)
    t_wait = max(duration - t_write - t_ann, 0.5)

    text_repr = repr(text)
    ann_repr = repr(annotation)

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        eq = Text({text_repr}, font_size=48)
        eq.move_to(ORIGIN)

        self.play(Write(eq), run_time={t_write:.3f})

        if {ann_repr}:
            brace = Brace(eq, DOWN)
            txt = brace.get_text({ann_repr})
            self.play(Create(brace), Write(txt), run_time={t_ann:.3f})

        self.wait({t_wait:.3f})
"""


def _render_short_concept_compare(segment: Segment, duration: float) -> str:
    """Compare two items side by side."""
    left = repr(str(segment.visual_params.get("left", "")))
    right = repr(str(segment.visual_params.get("right", "")))

    t_show = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_show, 0.5)

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        left_txt = Text({left}, font_size=40).shift(LEFT * 2.5)
        right_txt = Text({right}, font_size=40).shift(RIGHT * 2.5)
        vs = Text("VS", font_size=36, color=YELLOW)

        self.play(Write(left_txt), run_time=0.8)
        self.play(Write(vs), run_time=0.4)
        self.play(Write(right_txt), run_time=0.8)
        self.wait({t_wait:.3f})
"""


def _render_short_concept_pattern(segment: Segment, duration: float) -> str:
    """Show a visual pattern."""
    items = segment.visual_params.get("items", [])
    if not isinstance(items, list):
        items = []

    t_show = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_show, 0.5)

    items_str = ", ".join(repr(str(i)) for i in items[:5]) if items else repr("패턴")

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        items = VGroup(*[
            Text(t, font_size=36) for t in [{items_str}]
        ]).arrange(RIGHT, buff=0.5)
        items.move_to(ORIGIN)

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
