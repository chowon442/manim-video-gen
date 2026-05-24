"""Beat templates for short-form content."""

from __future__ import annotations

from manim_video_gen.models.script import Segment
from manim_video_gen.video.templates.short._layout import (
    FRAME_HEIGHT,
    FRAME_WIDTH,
    safe_zone_y_offset,
    scale_to_fit_frame,
)

# Safe content width with margins
_CONTENT_WIDTH = FRAME_WIDTH - 2.0


def _fit_text(name: str) -> str:
    """Return code snippet to scale Text mobject to fit frame width."""
    return (
        f"        if {name}.width > {_CONTENT_WIDTH}:\n"
        f"            {name}.scale_to_fit_width({_CONTENT_WIDTH})\n"
    )


def _render_short_hook(segment: Segment, duration: float) -> str:
    """Hook scene - attention-grabbing opening.

    Falls back to narration first line if headline is not provided.
    """
    headline = segment.visual_params.get("headline", "")
    if not headline:
        # Fallback to narration first line
        narration = segment.narration or segment.tts_text or ""
        headline = narration.split("\n")[0].strip() if narration else "집중하세요"
    headline_repr = repr(headline)

    t_write = min(duration * 0.6, 1.5)
    t_wait = max(duration - t_write, 0.5)

    # Headline stays in top safe zone
    y_offset = safe_zone_y_offset(has_headline=False, has_subtitle=True)

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        txt = Text({headline_repr}, font_size=56, weight=BOLD)
{_fit_text("txt")}        txt.move_to([0, {y_offset:.3f}, 0])
        self.play(Write(txt), run_time={t_write:.3f})
        self.wait({t_wait:.3f})
"""


def _render_short_before(segment: Segment, duration: float) -> str:
    """Before scene - setup context."""
    text = repr(str(segment.visual_params.get("text", "")))

    t_write = min(duration * 0.5, 1.0)
    t_wait = max(duration - t_write, 0.5)

    y_offset = safe_zone_y_offset(has_headline=True, has_subtitle=True)

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        txt = Text({text}, font_size=40)
{_fit_text("txt")}        txt.move_to([0, {y_offset:.3f}, 0])
        self.play(FadeIn(txt), run_time={t_write:.3f})
        self.wait({t_wait:.3f})
"""


def _render_short_after(segment: Segment, duration: float) -> str:
    """After scene - show result."""
    text = repr(str(segment.visual_params.get("text", "")))

    t_write = min(duration * 0.5, 1.0)
    t_wait = max(duration - t_write, 0.5)

    y_offset = safe_zone_y_offset(has_headline=True, has_subtitle=True)

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        txt = Text({text}, font_size=40)
{_fit_text("txt")}        txt.move_to([0, {y_offset:.3f}, 0])
        self.play(FadeIn(txt), run_time={t_write:.3f})
        self.wait({t_wait:.3f})
"""


def _render_short_payoff_card(segment: Segment, duration: float) -> str:
    """Payoff card - key takeaway."""
    headline = repr(str(segment.visual_params.get("headline", "")))

    t_write = min(duration * 0.6, 1.5)
    t_wait = max(duration - t_write, 0.5)

    y_offset = safe_zone_y_offset(has_headline=True, has_subtitle=True)

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        txt = Text({headline}, font_size=52, color=YELLOW)
{_fit_text("txt")}        txt.move_to([0, {y_offset:.3f}, 0])
        self.play(Write(txt), run_time={t_write:.3f})
        self.wait({t_wait:.3f})
"""


def _render_short_cta(segment: Segment, duration: float) -> str:
    """Call-to-action scene."""
    text = repr(str(segment.visual_params.get("text", "구독!")))

    t_write = min(duration * 0.6, 1.5)
    t_wait = max(duration - t_write, 0.5)

    y_offset = safe_zone_y_offset(has_headline=True, has_subtitle=True)

    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        txt = Text({text}, font_size=56, color=BLUE)
{_fit_text("txt")}        txt.move_to([0, {y_offset:.3f}, 0])
        self.play(Write(txt), run_time={t_write:.3f})
        self.wait({t_wait:.3f})
"""


BEAT_RENDERERS = {
    "short_hook": _render_short_hook,
    "short_before": _render_short_before,
    "short_after": _render_short_after,
    "short_payoff_card": _render_short_payoff_card,
    "short_cta": _render_short_cta,
}
