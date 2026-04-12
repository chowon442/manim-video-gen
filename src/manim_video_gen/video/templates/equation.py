"""Parameterized templates for equation scenes."""

from __future__ import annotations

import re
from typing import Any

from manim_video_gen.models.script import SceneObjectState
from manim_video_gen.video.latex_korean import wrap_korean_text_runs
from manim_video_gen.video.anim_timing import (
    split_transform,
    split_transform_no_prev,
    split_write,
)
from manim_video_gen.video.tex_template import has_cjk, scene_imports


_FADE_OUT_SECONDS = 0.35

_MOVE_RE = re.compile(
    r"^(ORIGIN|UP|DOWN|LEFT|RIGHT)(\s*\*\s*([-+]?[0-9]+(?:\.[0-9]+)?))?$"
)


def fit_tex_mobject_lines(
    name: str, *, max_width_expr: str = "config.frame_width - 1.2"
) -> str:
    """Return snippet that keeps MathTex-like mobject inside frame width."""
    return (
        f"if {name}.width > ({max_width_expr}):\n"
        f"    {name}.scale_to_fit_width({max_width_expr})\n"
    )


def fit_text_mobject_lines(
    name: str,
    *,
    max_width_expr: str = "config.frame_width - 1.2",
    top_edge: bool = False,
    top_buff: float = 0.5,
) -> str:
    """Return snippet that keeps Text mobject inside frame safely."""
    extra = ""
    if top_edge:
        extra = (
            f"{name}.to_edge(UP, buff={top_buff:.2f})\n"
            f"if {name}.get_top()[1] > config.frame_height/2 - 0.2:\n"
            f"    {name}.to_edge(UP, buff=0.2)\n"
        )
    return (
        f"if {name}.width > ({max_width_expr}):\n"
        f"    {name}.scale_to_fit_width({max_width_expr})\n" + extra
    )


def indent_lines(code: str, spaces: int = 8) -> str:
    """Indent multiline snippet by given spaces, preserving blank lines."""
    pad = " " * spaces
    out: list[str] = []
    for line in code.splitlines():
        out.append((pad + line) if line.strip() else line)
    return "\n".join(out) + ("\n" if code.endswith("\n") or code else "")


def sanitize_move_to_expr(expr: str) -> str:
    """Return a safe Manim move_to(...) expression string."""
    cleaned = expr.strip().replace(" ", "")
    if cleaned == "ORIGIN":
        return "ORIGIN"
    m = _MOVE_RE.match(cleaned)
    if not m:
        return "ORIGIN"
    base = m.group(1)
    if m.group(2) is None:
        return base
    num = m.group(3)
    return f"{base} * {num}"


def _collect_latex_values(
    params: dict[str, Any],
    prev_scene_state: list[SceneObjectState] | None,
) -> list[str]:
    """템플릿에서 사용되는 모든 LaTeX 문자열을 수집한다."""
    values: list[str] = []
    for key in ("latex", "from_latex", "to_latex"):
        v = params.get(key)
        if isinstance(v, str):
            values.append(v)
    steps_raw = params.get("steps")
    if isinstance(steps_raw, list):
        for item in steps_raw:
            if isinstance(item, dict) and "latex" in item:
                values.append(str(item["latex"]))
            elif isinstance(item, str):
                values.append(item)
    pts = params.get("points")
    if isinstance(pts, list):
        for p in pts:
            if isinstance(p, dict):
                lab = p.get("label")
                if isinstance(lab, str) and lab.strip() and not has_cjk(lab):
                    values.append(lab)
    if prev_scene_state:
        values.extend(st.latex for st in prev_scene_state)
    return values


def _prev_state_lines(prev: list[SceneObjectState] | None) -> str:
    if not prev:
        return ""
    lines: list[str] = []
    for i, st in enumerate(prev):
        pos = sanitize_move_to_expr(st.position_expr)
        lines.append(
            f"        _p{i} = MathTex({repr(st.latex)}).move_to({pos})\n"
            f"        self.add(_p{i})\n"
        )
    return "\n".join(lines) + "\n"


class EquationWriteTemplate:
    visual_type = "equation_write"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None = None,
    ) -> str:
        latex = wrap_korean_text_runs(str(params.get("latex", "")))
        font_size = int(params.get("font_size", 48))
        color = str(params.get("color", "WHITE"))

        t_write, t_wait = split_write(duration)

        all_latex = _collect_latex_values(params, prev_scene_state)
        imports = scene_imports(*all_latex)
        prev_lines = _prev_state_lines(prev_scene_state)

        return f"""{imports}

class Segment(Scene):
    def construct(self):
{prev_lines}        eq = MathTex({repr(latex)}, font_size={font_size}).set_color({color})
{indent_lines(fit_tex_mobject_lines("eq"), 8)}        eq.move_to(ORIGIN)
        self.play(Write(eq), run_time={t_write:.3f})
        self.wait({t_wait:.3f})
"""


class EquationTransformTemplate:
    visual_type = "equation_transform"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None,
    ) -> str:
        from_latex = wrap_korean_text_runs(str(params.get("from_latex", "")))
        to_latex = wrap_korean_text_runs(str(params.get("to_latex", "")))

        all_latex = _collect_latex_values(params, prev_scene_state)
        imports = scene_imports(*all_latex)
        prev_lines = _prev_state_lines(prev_scene_state)

        if prev_scene_state:
            t_tx, t_end = split_transform(duration)
            core = f"""{prev_lines}        eq2 = MathTex({repr(to_latex)})
{indent_lines(fit_tex_mobject_lines("eq2"), 8)}        eq2.move_to(ORIGIN)
        self.play(TransformMatchingTex(_p0, eq2), run_time={t_tx:.3f})
        self.wait({t_end:.3f})
"""
            return f"""{imports}

class Segment(Scene):
    def construct(self):
{core}"""

        t_intro, t_mid, t_tx, t_end = split_transform_no_prev(duration)

        return f"""{imports}

class Segment(Scene):
    def construct(self):
        eq1 = MathTex({repr(from_latex)})
{indent_lines(fit_tex_mobject_lines("eq1"), 8)}        eq1.move_to(ORIGIN)
        eq2 = MathTex({repr(to_latex)})
{indent_lines(fit_tex_mobject_lines("eq2"), 8)}        eq2.move_to(ORIGIN)
        self.play(Write(eq1), run_time={t_intro:.3f})
        self.wait({t_mid:.3f})
        self.play(TransformMatchingTex(eq1, eq2), run_time={t_tx:.3f})
        self.wait({t_end:.3f})
"""
