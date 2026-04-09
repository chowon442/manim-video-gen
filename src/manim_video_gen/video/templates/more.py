"""Additional parameterized templates: steps, graph, highlight, title, intro, outro."""

from __future__ import annotations

from typing import Any

from manim_video_gen.models.script import SceneObjectState
from manim_video_gen.video.anim_timing import (
    ANIM_CAP_FADE,
    ANIM_GAP,
    split_axes_and_plot,
    split_highlight_box,
    split_n_writes,
)
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

        n = len(steps)
        t_each, t_wait = split_n_writes(duration, n, fade_in=0.0)

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
'''


def _parse_derivation_steps(params: dict[str, Any]) -> list[tuple[str, str]]:
    raw = params.get("steps") or []
    out: list[tuple[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(
                (
                    str(item.get("latex", r"0=0")),
                    str(item.get("annotation", "") or ""),
                )
            )
        elif isinstance(item, str):
            out.append((item, ""))
    if not out:
        out = [(r"0=0", "")]
    return out


def _derivation_segment_times(
    duration: float,
    n: int,
    has_ann: list[bool],
) -> tuple[float, list[tuple[float, float, float]], float]:
    """First Write, then per transition (arrow, ann_or_0, eq_write), final wait."""
    d = float(duration)
    if n <= 0:
        n = 1
    trans = max(n - 1, 0)
    plays = 1 + sum(2 + (1 if (j < len(has_ann) and has_ann[j]) else 0) for j in range(trans))
    share = d / max(plays, 1)
    t0 = min(1.2, max(0.3, share))
    per_trans: list[tuple[float, float, float]] = []
    for j in range(trans):
        ta = min(ANIM_CAP_FADE, max(0.12, share * 0.7))
        ann_t = (
            min(ANIM_CAP_FADE, max(0.12, share * 0.7))
            if j < len(has_ann) and has_ann[j]
            else 0.0
        )
        tw = min(1.2, max(0.28, share))
        per_trans.append((ta, ann_t, tw))
    used = t0 + sum(a + an + w for a, an, w in per_trans)
    t_end = max(0.12, d - used)
    return t0, per_trans, t_end


class EquationDerivationTemplate:
    """Stack related equations with arrows and optional Korean annotations (Text)."""

    visual_type = "equation_derivation"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None = None,
    ) -> str:
        parsed = _parse_derivation_steps(params)
        n = len(parsed)
        has_ann = [bool(parsed[i][1].strip()) for i in range(1, n)]
        t0, per_trans, t_end = _derivation_segment_times(duration, n, has_ann)

        latex_list = [p[0] for p in parsed]
        if prev_scene_state:
            latex_list.extend(st.latex for st in prev_scene_state)
        imports = (
            scene_imports(*latex_list)
            if latex_list
            else "from manim import *\nimport numpy as np"
        )
        prev_lines = _prev_state_lines(prev_scene_state)

        lines: list[str] = []
        first_latex = parsed[0][0]
        lines.append(
            f"        cur = MathTex({repr(first_latex)})\n"
            f"        cur.to_edge(UP, buff=0.55)\n"
            f"        self.play(Write(cur), run_time={t0:.3f})\n"
        )
        for idx in range(1, n):
            latex_i, ann = parsed[idx]
            ta, ann_t, tw = per_trans[idx - 1]
            arr_name = f"arr_{idx}"
            lines.append(
                f"        {arr_name} = MathTex(r\"\\Downarrow\", font_size=38)\n"
                f"        {arr_name}.next_to(cur, DOWN, buff={ANIM_GAP:.2f})\n"
                f"        self.play(FadeIn({arr_name}), run_time={ta:.3f})\n"
            )
            if ann.strip():
                lab_name = f"lab_{idx}"
                lines.append(
                    f"        {lab_name} = Text({repr(ann.strip())}, font_size=26)\n"
                    f"        {lab_name}.next_to({arr_name}, RIGHT, buff=0.2)\n"
                    f"        self.play(FadeIn({lab_name}), run_time={ann_t:.3f})\n"
                )
            eq_name = f"eq_{idx}"
            lines.append(
                f"        {eq_name} = MathTex({repr(latex_i)})\n"
                f"        {eq_name}.next_to({arr_name}, DOWN, buff={ANIM_GAP + 0.1:.2f})\n"
                f"        self.play(Write({eq_name}), run_time={tw:.3f})\n"
                f"        cur = {eq_name}\n"
            )

        body = "".join(lines)
        return f'''{imports}

class Segment(Scene):
    def construct(self):
{prev_lines}{body}        self.wait({t_end:.3f})
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
        t_axes, t_plot, t_end = split_axes_and_plot(
            duration,
            has_label_line=bool(func_latex and str(func_latex).strip()),
            fade_out=fade_out,
        )

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

        t_in, t_box, t_hold, t_out = split_highlight_box(duration)

        return f'''{imports}

class Segment(Scene):
    def construct(self):
{prev_lines}        eq = MathTex({repr(latex)})
        box = SurroundingRectangle(eq, color={box_color}, buff=0.15)
        self.play(Write(eq), run_time={t_in:.3f})
        self.play(Create(box), run_time={t_box:.3f})
        self.wait({t_hold:.3f})
        self.play(FadeOut(box), run_time={min(t_out, ANIM_CAP_FADE):.3f})
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
        t1 = min(1.0, max(0.35, duration * 0.26))
        t2 = min(0.85, max(0.12, duration * 0.18)) if subtitle else 0.0
        t_end = max(0.12, duration - t1 - t2 - fade_out)

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
        t1 = min(0.75, max(0.28, duration * 0.16))
        t2 = min(1.15, max(0.35, duration * 0.42))
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
        t1 = min(0.85, max(0.3, duration * 0.22))
        t2 = min(0.9, max(0.3, duration * 0.36))
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
