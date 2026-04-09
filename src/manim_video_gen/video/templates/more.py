"""Additional parameterized templates: steps, graph, highlight, title, intro, outro."""

from __future__ import annotations

from typing import Any

from manim_video_gen.models.script import SceneObjectState
from manim_video_gen.video.templates.equation import (
    _FADE_OUT_SECONDS,
    _collect_latex_values,
    _prev_state_lines,
)
from manim_video_gen.video.tex_template import has_cjk, scene_imports


def _text_imports(*texts: str) -> str:
    """Import block; enable CJK TeX only if any LaTeX path used — Text uses Pango, no TeX."""
    if any(has_cjk(t) for t in texts):
        return "from manim import *\nimport numpy as np"
    return "from manim import *\nimport numpy as np"


class EquationStepsTemplate:
    visual_type = "equation_steps"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None = None,
    ) -> str:
        raw_steps = params.get("steps") or []
        steps = [str(s) for s in raw_steps] if isinstance(raw_steps, list) else []
        if not steps:
            steps = [r"0 = 0"]

        direction = str(params.get("arrange_direction", "DOWN")).upper()
        arrange_mob = "DOWN" if direction == "DOWN" else "RIGHT"
        buff = 0.45 if arrange_mob == "DOWN" else 0.35

        fade_out = _FADE_OUT_SECONDS
        n = len(steps)
        t_each = max(0.25, (duration - fade_out) / max(n + 1, 2))
        t_wait = max(0.12, duration - t_each * n - fade_out)
        t_wait = min(t_wait, t_each)

        tex_lines = ",\n            ".join(f"MathTex({repr(s)})" for s in steps)
        all_latex = list(steps)
        if prev_scene_state:
            all_latex.extend(st.latex for st in prev_scene_state)
        imports = scene_imports(*all_latex) if all_latex else "from manim import *\nimport numpy as np"
        prev_lines = _prev_state_lines(prev_scene_state)

        return f'''{imports}

class Segment(Scene):
    def construct(self):
{prev_lines}        group = VGroup(
            {tex_lines}
        ).arrange({arrange_mob}, buff={buff})
        group.move_to(ORIGIN)
        for i, mob in enumerate(group):
            self.play(Write(mob), run_time={t_each:.3f})
        self.wait({t_wait:.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
'''


class GraphPlotTemplate:
    visual_type = "graph_plot"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None = None,
    ) -> str:
        func_python = str(params.get("func_python", "lambda x: x**2")).strip()
        if not func_python.startswith("lambda"):
            func_python = f"lambda x: ({func_python})"

        x_range = params.get("x_range") or [-3, 3, 1]
        y_range = params.get("y_range") or [-1, 5, 1]
        x_len = float(params.get("x_length", 6))
        y_len = float(params.get("y_length", 4))
        color = str(params.get("color", "BLUE"))
        func_latex = params.get("func_latex")
        label_line = ""
        if func_latex and str(func_latex).strip():
            label_line = (
                f"        label = MathTex({repr(str(func_latex))}, font_size=36).to_corner(UL)\n"
                "        self.play(Write(label), run_time=0.4)\n"
            )

        latex_vals: list[str] = []
        if func_latex:
            latex_vals.append(str(func_latex))
        imports = scene_imports(*latex_vals)
        prev_lines = _prev_state_lines(prev_scene_state)

        fade_out = _FADE_OUT_SECONDS
        t_axes = max(0.35, duration * 0.18)
        t_plot = max(0.5, duration * 0.50)
        t_end = max(0.15, duration - t_axes - t_plot - 0.4 - fade_out)

        return f'''{imports}

class Segment(Scene):
    def construct(self):
{prev_lines}        axes = Axes(
            x_range={list(x_range)},
            y_range={list(y_range)},
            x_length={x_len},
            y_length={y_len},
            axis_config={{"include_tip": True}},
        )
        self.play(Create(axes), run_time={t_axes:.3f})
        graph = axes.plot({func_python}, color={color})
        self.play(Create(graph), run_time={t_plot:.3f})
{label_line}        self.wait({t_end:.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
'''


class HighlightResultTemplate:
    visual_type = "highlight_result"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None = None,
    ) -> str:
        latex = str(params.get("latex", "x = -1"))
        box_color = str(params.get("box_color", "YELLOW"))
        all_latex = _collect_latex_values({"latex": latex}, prev_scene_state)
        imports = scene_imports(*all_latex) if all_latex else "from manim import *\nimport numpy as np"
        prev_lines = _prev_state_lines(prev_scene_state)

        fade_out = _FADE_OUT_SECONDS
        t_in = max(0.35, duration * 0.30)
        t_hold = max(0.2, duration * 0.40)
        t_out = max(0.1, duration - t_in - t_hold - fade_out)

        return f'''{imports}

class Segment(Scene):
    def construct(self):
{prev_lines}        eq = MathTex({repr(latex)})
        box = SurroundingRectangle(eq, color={box_color}, buff=0.15)
        self.play(Write(eq), run_time={t_in:.3f})
        self.play(Create(box), run_time={t_in * 0.6:.3f})
        self.wait({t_hold:.3f})
        self.play(FadeOut(box), run_time={min(t_out, 0.4):.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
'''


class TitleCardTemplate:
    visual_type = "title_card"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None = None,
    ) -> str:
        title = str(params.get("title", ""))
        subtitle = str(params.get("subtitle", "") or "")
        imports = _text_imports(title, subtitle)

        fade_out = _FADE_OUT_SECONDS
        t1 = max(0.35, duration * 0.30)
        t2 = max(0.0, duration * 0.22) if subtitle else 0.0
        t_end = max(0.15, duration - t1 - t2 - fade_out)

        sub_block = ""
        if subtitle.strip():
            sub_block = (
                f"        st = Text({repr(subtitle)}, font_size=36)\n"
                f"        st.next_to(tt, DOWN, buff=0.4)\n"
                f"        self.play(FadeIn(st, shift=UP*0.1), run_time={t2:.3f})\n"
            )

        return f'''{imports}

class Segment(Scene):
    def construct(self):
        tt = Text({repr(title)}, font_size=48)
        self.play(FadeIn(tt, shift=DOWN*0.15), run_time={t1:.3f})
{sub_block}        self.wait({t_end:.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
'''


class IntroProblemTemplate:
    visual_type = "intro_problem"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None = None,
    ) -> str:
        problem_text = str(params.get("problem_text", ""))
        imports = _text_imports("문제", problem_text)
        label = str(params.get("label", "문제"))

        fade_out = _FADE_OUT_SECONDS
        t1 = max(0.3, duration * 0.18)
        t2 = max(0.4, duration * 0.50)
        t_end = max(0.12, duration - t1 - t2 - fade_out)

        return f'''{imports}

class Segment(Scene):
    def construct(self):
        head = Text({repr(label)}, font_size=40)
        head.to_edge(UP, buff=0.4)
        body = Text({repr(problem_text)}, font_size=32).next_to(head, DOWN, buff=0.5)
        self.play(FadeIn(head), run_time={t1:.3f})
        self.play(FadeIn(body, shift=UP*0.1), run_time={t2:.3f})
        self.wait({t_end:.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
'''


class OutroSummaryTemplate:
    visual_type = "outro_summary"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None = None,
    ) -> str:
        summary = str(params.get("summary_text", ""))
        imports = _text_imports("정리", summary)
        extra_latex = params.get("highlight_latex")

        fade_out = _FADE_OUT_SECONDS
        t1 = max(0.35, duration * 0.25)
        t2 = max(0.35, duration * 0.40)
        t_end = max(0.12, duration - t1 - t2 - fade_out)

        eq_block = ""
        if extra_latex and str(extra_latex).strip():
            latex_s = str(extra_latex)
            imports = scene_imports(latex_s)
            eq_block = (
                f"        eq = MathTex({repr(latex_s)})\n"
                f"        eq.next_to(tx, DOWN, buff=0.45)\n"
                f"        self.play(Write(eq), run_time={t2 * 0.55:.3f})\n"
            )
            t_end = max(0.12, duration - t1 - t2 * 1.55 - fade_out)

        return f'''{imports}

class Segment(Scene):
    def construct(self):
        tx = Text({repr(summary)}, font_size=36)
        self.play(FadeIn(tx), run_time={t1:.3f})
{eq_block}        self.wait({t_end:.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
'''
