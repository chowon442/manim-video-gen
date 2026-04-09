"""Parameterized templates for equation scenes."""

from __future__ import annotations

import re
from typing import Any

from manim_video_gen.models.script import SceneObjectState
from manim_video_gen.video.tex_template import has_cjk, scene_imports


_FADE_OUT_SECONDS = 0.35

_MOVE_RE = re.compile(
    r"^(ORIGIN|UP|DOWN|LEFT|RIGHT)(\s*\*\s*([-+]?[0-9]+(?:\.[0-9]+)?))?$"
)


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
        latex = str(params.get("latex", ""))
        font_size = int(params.get("font_size", 48))
        color = str(params.get("color", "WHITE"))

        fade_out = _FADE_OUT_SECONDS
        t_write = max(0.4, min(duration * 0.60, duration - fade_out - 0.15))
        t_wait = max(0.15, duration - t_write - fade_out)

        all_latex = _collect_latex_values(params, prev_scene_state)
        imports = scene_imports(*all_latex)
        prev_lines = _prev_state_lines(prev_scene_state)

        return f'''{imports}

class Segment(Scene):
    def construct(self):
{prev_lines}        eq = MathTex({repr(latex)}, font_size={font_size}).set_color({color})
        self.play(Write(eq), run_time={t_write:.3f})
        self.wait({t_wait:.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
'''


class EquationTransformTemplate:
    visual_type = "equation_transform"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None,
    ) -> str:
        from_latex = str(params.get("from_latex", ""))
        to_latex = str(params.get("to_latex", ""))

        all_latex = _collect_latex_values(params, prev_scene_state)
        imports = scene_imports(*all_latex)
        prev_lines = _prev_state_lines(prev_scene_state)
        fade_out = _FADE_OUT_SECONDS

        if prev_scene_state:
            t_tx = max(0.5, duration * 0.60)
            t_end = max(0.15, duration - t_tx - fade_out)
            core = f'''{prev_lines}        eq2 = MathTex({repr(to_latex)})
        self.play(TransformMatchingTex(_p0, eq2), run_time={t_tx:.3f})
        self.wait({t_end:.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
'''
            return f'''{imports}

class Segment(Scene):
    def construct(self):
{core}'''

        t_intro = max(0.25, duration * 0.22)
        t_mid = max(0.2, duration * 0.12)
        t_tx = max(0.35, duration * 0.40)
        t_end = max(0.15, duration - (t_intro + t_mid + t_tx + fade_out))

        return f'''{imports}

class Segment(Scene):
    def construct(self):
        eq1 = MathTex({repr(from_latex)})
        eq2 = MathTex({repr(to_latex)})
        self.play(Write(eq1), run_time={t_intro:.3f})
        self.wait({t_mid:.3f})
        self.play(TransformMatchingTex(eq1, eq2), run_time={t_tx:.3f})
        self.wait({t_end:.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
'''
