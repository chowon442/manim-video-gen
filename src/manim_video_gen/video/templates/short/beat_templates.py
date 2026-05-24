"""Beat templates for short-form content."""

from __future__ import annotations

from typing import Any

from manim_video_gen.models.script import Segment

# 9:16 safe zone constants
FRAME_HEIGHT = 19.20  # Manim units for 1920px
FRAME_WIDTH = 10.80   # Manim units for 1080px
SAFE_TOP_BUFF = FRAME_HEIGHT * 0.12    # 12% from top
SAFE_BOTTOM_BUFF = FRAME_HEIGHT * 0.20  # 20% from bottom


def _render_short_hook(segment: Segment, duration: float) -> str:
    """Hook scene - attention-grabbing opening."""
    headline = str(segment.visual_params.get("headline", ""))
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        txt = Text("{headline}", font_size=48)
        txt.move_to(ORIGIN)
        self.play(Write(txt), run_time=min({duration:.3f} * 0.6, 1.5))
        self.wait(max({duration:.3f} - 1.5, 0.5))
"""


def _render_short_before(segment: Segment, duration: float) -> str:
    """Before scene - setup context."""
    text = str(segment.visual_params.get("text", ""))
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        txt = Text("{text}", font_size=40)
        txt.move_to(ORIGIN)
        self.play(FadeIn(txt), run_time=min({duration:.3f} * 0.5, 1.0))
        self.wait(max({duration:.3f} - 1.0, 0.5))
"""


def _render_short_after(segment: Segment, duration: float) -> str:
    """After scene - show result."""
    text = str(segment.visual_params.get("text", ""))
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        txt = Text("{text}", font_size=40)
        txt.move_to(ORIGIN)
        self.play(FadeIn(txt), run_time=min({duration:.3f} * 0.5, 1.0))
        self.wait(max({duration:.3f} - 1.0, 0.5))
"""


def _render_short_payoff_card(segment: Segment, duration: float) -> str:
    """Payoff card - key takeaway."""
    headline = str(segment.visual_params.get("headline", ""))
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        txt = Text("{headline}", font_size=52, color=YELLOW)
        txt.move_to(ORIGIN)
        self.play(Write(txt), run_time=min({duration:.3f} * 0.6, 1.5))
        self.wait(max({duration:.3f} - 1.5, 0.5))
"""


def _render_short_cta(segment: Segment, duration: float) -> str:
    """Call-to-action scene."""
    text = str(segment.visual_params.get("text", "구독!"))
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}

        txt = Text("{text}", font_size=56, color=BLUE)
        txt.move_to(ORIGIN)
        self.play(Write(txt), run_time=min({duration:.3f} * 0.6, 1.5))
        self.wait(max({duration:.3f} - 1.5, 0.5))
"""


BEAT_RENDERERS = {
    "short_hook": _render_short_hook,
    "short_before": _render_short_before,
    "short_after": _render_short_after,
    "short_payoff_card": _render_short_payoff_card,
    "short_cta": _render_short_cta,
}
