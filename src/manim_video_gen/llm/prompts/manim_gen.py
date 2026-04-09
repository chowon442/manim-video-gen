"""Prompts: segment -> full Manim Scene code (fallback path)."""

from __future__ import annotations

import json

from manim_video_gen.llm.prompts.manim_api_ref import MANIM_API_REFERENCE_TEXT
from manim_video_gen.models.script import Segment

# Verified-style Manim CE few-shots (short, common patterns).
MANIM_FEW_SHOT_EXAMPLES = r"""
### Example A — Arrow / vector
from manim import *

class Segment(Scene):
    def construct(self):
        v = Arrow(start=ORIGIN, end=RIGHT * 2, color=YELLOW, buff=0)
        lbl = MathTex(r"\vec{v}", font_size=48).next_to(v, UP)
        self.play(GrowFromCenter(v), Write(lbl), run_time=1.5)
        self.wait(0.5)

### Example B — Matrix
from manim import *

class Segment(Scene):
    def construct(self):
        m = Matrix([[1, 2], [3, 4]])
        self.play(Write(m), run_time=2.0)
        self.wait(0.5)

### Example C — Axes + plot (stable across Manim CE versions)
from manim import *

class Segment(Scene):
    def construct(self):
        ax = Axes(x_range=[0, 3, 1], y_range=[0, 4, 1], x_length=6, y_length=4)
        graph = ax.plot(lambda x: x ** 2, color=BLUE)
        self.play(Create(ax), run_time=0.8)
        self.play(Create(graph), run_time=1.2)
        self.wait(0.5)

### Example D — Triangle / angle hint
from manim import *

class Segment(Scene):
    def construct(self):
        a = np.array([-2.0, -1.0, 0.0])
        b = np.array([2.0, -1.0, 0.0])
        c = np.array([0.0, 2.0, 0.0])
        tri = Polygon(a, b, c, color=WHITE)
        self.play(Create(tri), run_time=1.5)
        self.wait(0.5)

### Example E — NumberLine + dots
from manim import *

class Segment(Scene):
    def construct(self):
        nl = NumberLine(x_range=[-3, 3, 1], length=6, include_numbers=True)
        d1 = Dot(nl.n2p(-1), color=RED)
        d2 = Dot(nl.n2p(2), color=GREEN)
        self.play(Create(nl), run_time=1.0)
        self.play(FadeIn(d1), FadeIn(d2), run_time=1.0)
        self.wait(0.5)
"""


def manim_system_prompt() -> str:
    return (
        "You generate a single Manim Community Edition Scene.\n"
        + MANIM_API_REFERENCE_TEXT
        + "\n## Few-shot examples (follow structure and imports)\n"
        + MANIM_FEW_SHOT_EXAMPLES
        + "\nOutput ONLY python code (no markdown fences).\n"
    )


def build_manim_user_prompt(
    segment: Segment,
    *,
    duration_seconds: float,
    prior_errors: list[str] | None = None,
    prior_codes: list[str] | None = None,
) -> str:
    prior = ""
    if prior_errors:
        prior += "\n\nPrevious errors (fix them):\n" + "\n".join(
            f"- {e}" for e in prior_errors
        )
    if prior_codes:
        prior += "\n\nPrevious full code attempts (rewrite or fix; do not repeat mistakes):\n"
        for i, code in enumerate(prior_codes):
            snippet = code if len(code) <= 12000 else code[:12000] + "\n# ... truncated ..."
            prior += f"\n--- attempt {i + 1} ---\n{snippet}\n"
    return (
        f"duration_seconds (target total time, approximate): {duration_seconds:.3f}\n"
        f"narration (for context only; do not print raw LaTeX as plain Text): {segment.narration}\n"
        f"visual_description: {segment.visual_description}\n"
        f"visual_params: {json.dumps(segment.visual_params, ensure_ascii=False)}\n"
        f"prev_scene_state: {json.dumps([s.model_dump() for s in segment.prev_scene_state] if segment.prev_scene_state else None, ensure_ascii=False)}\n"
        f"{prior}\n"
        "Generate:\n"
        "from manim import *\n\n"
        "class Segment(Scene):\n"
        "    def construct(self):\n"
        "        ...\n"
    )
