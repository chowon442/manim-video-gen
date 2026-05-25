"""Prompts: short-form (9:16) segment -> full Manim Scene code."""

from __future__ import annotations

import json

from manim_video_gen.llm.prompts.manim_api_ref import MANIM_API_REFERENCE_TEXT
from manim_video_gen.models.script import Segment

SHORT_MANIM_FEW_SHOT_EXAMPLES = r"""
### Example A — Hook: headline text centered (9:16 portrait)
from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = 10.80
        self.camera.frame_height = 19.20

        title = Text("미적분이 세상을 바꾼다", font_size=52, color=YELLOW)
        title.move_to(ORIGIN)
        self.play(Write(title), run_time=1.2)
        self.wait(1.0)

### Example B — Equation display (safe zone: avoid top 12% and bottom 20%)
from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = 10.80
        self.camera.frame_height = 19.20

        eq = MathTex(r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}", font_size=44)
        eq.set_color(WHITE)
        eq.move_to(ORIGIN)
        self.play(Write(eq), run_time=1.5)
        self.wait(1.0)

### Example C — Axes + graph (compact for portrait)
from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = 10.80
        self.camera.frame_height = 19.20

        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 4, 1],
            x_length=7,
            y_length=8,
            axis_config={"include_numbers": True, "font_size": 28},
        )
        axes.move_to(ORIGIN)

        graph = axes.plot(lambda x: x ** 2, color=BLUE)
        label = MathTex(r"y = x^2", font_size=36, color=BLUE)
        label.next_to(graph, UR, buff=0.3)

        self.play(Create(axes), run_time=0.8)
        self.play(Create(graph), run_time=1.0)
        self.play(Write(label), run_time=0.6)
        self.wait(0.8)

### Example D — NumberLine + markers (portrait layout)
from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = 10.80
        self.camera.frame_height = 19.20

        nl = NumberLine(
            x_range=[-5, 5, 1],
            length=9,
            include_numbers=True,
            font_size=28,
        )
        nl.move_to(ORIGIN)

        d1 = Dot(nl.n2p(-2), color=RED, radius=0.12)
        d2 = Dot(nl.n2p(3), color=GREEN, radius=0.12)
        lbl1 = Text("-2", font_size=24, color=RED).next_to(d1, UP, buff=0.2)
        lbl2 = Text("3", font_size=24, color=GREEN).next_to(d2, UP, buff=0.2)

        self.play(Create(nl), run_time=0.8)
        self.play(FadeIn(d1), Write(lbl1), run_time=0.6)
        self.play(FadeIn(d2), Write(lbl2), run_time=0.6)
        self.wait(0.8)

### Example E — Stat / comparison card (two columns)
from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = 10.80
        self.camera.frame_height = 19.20

        left_title = Text("Before", font_size=36, color=RED)
        left_val = Text("12%", font_size=60, color=RED)
        left_group = VGroup(left_title, left_val).arrange(DOWN, buff=0.3)
        left_group.shift(LEFT * 2.5)

        right_title = Text("After", font_size=36, color=GREEN)
        right_val = Text("87%", font_size=60, color=GREEN)
        right_group = VGroup(right_title, right_val).arrange(DOWN, buff=0.3)
        right_group.shift(RIGHT * 2.5)

        vs = Text("VS", font_size=32, color=YELLOW)

        self.play(FadeIn(left_group), run_time=0.8)
        self.play(Write(vs), run_time=0.4)
        self.play(FadeIn(right_group), run_time=0.8)
        self.wait(1.0)

### Example F — Brace annotation with Korean label
from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = 10.80
        self.camera.frame_height = 19.20

        eq = MathTex(r"{{a}} x^2 + {{b}} x + {{c}} = 0", font_size=44)
        eq.move_to(ORIGIN)
        self.play(Write(eq), run_time=1.0)

        b0 = Brace(eq.get_part_by_tex("a"), UP, color=YELLOW)
        t0 = Text("계수", font_size=24)
        t0.next_to(b0, UP, buff=0.1)
        self.play(GrowFromCenter(b0), FadeIn(t0), run_time=0.8)
        self.wait(0.6)
"""

# 9:16 safe zone constants (Manim units)
_SHORT_FRAME_WIDTH = 10.80
_SHORT_FRAME_HEIGHT = 19.20
# Top 12% = headline zone, bottom 20% = subtitle zone
_SHORT_SAFE_ZONE_TOP_PCT = 0.12
_SHORT_SAFE_ZONE_BOTTOM_PCT = 0.20


def short_manim_system_prompt() -> str:
    """System prompt for short-form (9:16) Manim code generation."""
    return (
        "You generate a single Manim Community Edition Scene for a SHORT-FORM VERTICAL VIDEO (9:16 portrait).\n"
        "Resolution: 1080×1920 pixels.\n"
        "\n"
        "## CRITICAL layout constraints\n"
        "- ALWAYS set: self.camera.frame_width = 10.80 and self.camera.frame_height = 19.20\n"
        "- TOP 12% of the frame is reserved for a persistent headline overlay (DO NOT place any content there)\n"
        "- BOTTOM 20% of the frame is reserved for subtitles (DO NOT place any content there)\n"
        "- Keep all visual elements within the SAFE ZONE: y ∈ [-5.76, +5.76] Manim units (center 68% of frame)\n"
        "- Use compact layouts: smaller font_size (28-48), shorter axes, tighter spacing\n"
        "- Portrait frame is TALL and NARROW — prefer vertical arrangements over horizontal\n"
        "\n"
        + MANIM_API_REFERENCE_TEXT
        + "\n## Few-shot examples (follow structure and imports)\n"
        + SHORT_MANIM_FEW_SHOT_EXAMPLES
        + "\nOutput ONLY python code (no markdown fences).\n"
        + "No `if __name__ == \"__main__\":`, no `render()` calls, no test harness — only imports and `class Segment(Scene)`.\n"
    )


def build_short_manim_user_prompt(
    segment: Segment,
    *,
    duration_seconds: float,
    prior_errors: list[str] | None = None,
    prior_codes: list[str] | None = None,
) -> str:
    """Build user prompt for short-form Manim code generation."""
    prior = ""
    if prior_errors:
        prior += "\n\nPrevious errors (fix them):\n" + "\n".join(
            f"- {e}" for e in prior_errors
        )
        prior += (
            "\n\nRetry instruction:\n"
            "- Analyze the exact root causes in the previous errors above.\n"
            "- Rewrite the scene to avoid those failures.\n"
            "- Do not repeat the failing patterns from previous attempts.\n"
            "- Ensure camera.frame_width=10.80 and camera.frame_height=19.20 are set.\n"
            "- Explain briefly in code comments where you changed the risky part."
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
        "Generate (nothing after the Segment class; no __main__ block):\n"
        "from manim import *\n\n"
        "class Segment(Scene):\n"
        "    def construct(self):\n"
        "        ...\n"
    )


# Beat-type -> fallback template mapping for degrade on LLM failure.
# Maps both short-form keys (from registry) and long-form keys (from scriptify).
_BEAT_FALLBACK_MAP: dict[str, str] = {
    # short-form beat keys
    "hook": "short_hook",
    "before": "short_before",
    "after": "short_after",
    "payoff_card": "short_payoff_card",
    "cta": "short_cta",
    # long-form keys → short-form fallback (scriptify may output these)
    "title_card": "short_hook",
    "equation_write": "short_concept_equation",
    "equation_transform": "short_concept_equation",
    "graph_plot": "short_concept_graph",
    "number_line": "short_concept_number_line",
    "annotated_equation": "short_concept_annotated",
    "compare": "short_concept_compare",
    "pattern": "short_concept_pattern",
    "icon_display": "short_domain_icon",
    "bar_chart": "short_stat_chart",
    "flow_diagram": "short_flow_arrow",
    # concept/beat types as-is
    "concept": "short_concept_equation",
    "problem": "short_concept_equation",
    "application": "short_concept_equation",
    "payoff": "short_payoff_card",
}


def resolve_short_fallback_template(visual_type: str, beat: str | None = None) -> str:
    """Return the fallback template name when LLM generation fails.

    Priority:
    1. Direct visual_type match in mapping
    2. beat-based match
    3. Default to short_concept_equation
    """
    if visual_type in _BEAT_FALLBACK_MAP:
        return _BEAT_FALLBACK_MAP[visual_type]
    if beat and beat in _BEAT_FALLBACK_MAP:
        return _BEAT_FALLBACK_MAP[beat]
    return "short_concept_equation"
