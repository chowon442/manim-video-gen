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
    split_write,
)
from manim_video_gen.video.latex_korean import (
    apply_text_glyph_fallback,
    sanitize_latex_for_text_label,
    wrap_korean_text_runs,
)
from manim_video_gen.video.templates.equation import (
    _FADE_OUT_SECONDS,
    _collect_latex_values,
    indent_lines,
    fit_text_mobject_lines,
    fit_tex_mobject_lines,
    _prev_state_lines,
)
from manim_video_gen.video.tex_template import has_cjk, scene_imports


def _text_imports(*texts: str) -> str:
    """Import block; enable CJK TeX only if any LaTeX path used — Text uses Pango, no TeX."""
    if any(has_cjk(t) for t in texts):
        return "from manim import *\nimport numpy as np"
    return "from manim import *\nimport numpy as np"


_MANIM_COLORS = frozenset(
    {
        "WHITE",
        "BLACK",
        "GRAY",
        "LIGHT_GRAY",
        "DARK_GRAY",
        "RED",
        "GREEN",
        "BLUE",
        "YELLOW",
        "ORANGE",
        "PURPLE",
        "TEAL",
        "PINK",
        "GOLD",
        "MAROON",
    }
)


def _safe_manim_color(name: str, default: str = "WHITE") -> str:
    u = str(name).strip().upper()
    return u if u in _MANIM_COLORS else default


def _direction_const(name: str) -> str:
    u = str(name).strip().upper()
    return u if u in ("UP", "DOWN", "LEFT", "RIGHT") else "UP"


def _inject_braces_for_annotations(
    latex: str, annotations: list[dict[str, Any]]
) -> str:
    """Wrap each target_tex in {{ }} for Brace / get_part_by_tex (first occurrence)."""
    out = latex
    for ann in annotations:
        tok = str(ann.get("target_tex", "")).strip()
        if not tok:
            continue
        needle = "{{" + tok + "}}"
        if needle in out:
            continue
        idx = out.find(tok)
        if idx < 0:
            continue
        out = out[:idx] + "{{" + tok + "}}" + out[idx + len(tok) :]
    return out


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
        steps = (
            [wrap_korean_text_runs(str(s)) for s in raw_steps]
            if isinstance(raw_steps, list)
            else []
        )
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
        imports = (
            scene_imports(*all_latex)
            if all_latex
            else "from manim import *\nimport numpy as np"
        )
        prev_lines = _prev_state_lines(prev_scene_state)

        return f"""{imports}

class Segment(Scene):
    def construct(self):
{prev_lines}        group = VGroup(
            {tex_lines}
        ).arrange({arrange_mob}, buff={buff})
        for _m in group:
{indent_lines(fit_tex_mobject_lines("_m"), 12)}        group.arrange({arrange_mob}, buff={buff})
        group.move_to(ORIGIN)
        for i, mob in enumerate(group):
            self.play(Write(mob), run_time={t_each:.3f})
        self.wait({t_wait:.3f})
"""


def _parse_derivation_steps(params: dict[str, Any]) -> list[tuple[str, str]]:
    raw = params.get("steps") or []
    out: list[tuple[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(
                (
                    wrap_korean_text_runs(str(item.get("latex", r"0=0"))),
                    str(item.get("annotation", "") or ""),
                )
            )
        elif isinstance(item, str):
            out.append((wrap_korean_text_runs(item), ""))
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
    plays = 1 + sum(
        2 + (1 if (j < len(has_ann) and has_ann[j]) else 0) for j in range(trans)
    )
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
            + indent_lines(fit_tex_mobject_lines("cur"), 8)
            + f"        cur.to_edge(UP, buff=0.55)\n"
            + f"        self.play(Write(cur), run_time={t0:.3f})\n"
        )
        for idx in range(1, n):
            latex_i, ann = parsed[idx]
            ta, ann_t, tw = per_trans[idx - 1]
            arr_name = f"arr_{idx}"
            lines.append(
                f'        {arr_name} = MathTex(r"\\Downarrow", font_size=38)\n'
                f"        {arr_name}.next_to(cur, DOWN, buff={ANIM_GAP:.2f})\n"
                f"        self.play(FadeIn({arr_name}), run_time={ta:.3f})\n"
            )
            if ann.strip():
                lab_name = f"lab_{idx}"
                lines.append(
                    f"        {lab_name} = Text({repr(apply_text_glyph_fallback(ann.strip()))}, font_size=26)\n"
                    f"        {lab_name}.next_to({arr_name}, RIGHT, buff=0.2)\n"
                    f"        self.play(FadeIn({lab_name}), run_time={ann_t:.3f})\n"
                )
            eq_name = f"eq_{idx}"
            lines.append(
                f"        {eq_name} = MathTex({repr(latex_i)})\n"
                + indent_lines(fit_tex_mobject_lines(eq_name), 8)
                + f"        {eq_name}.next_to({arr_name}, DOWN, buff={ANIM_GAP + 0.1:.2f})\n"
                + f"        self.play(Write({eq_name}), run_time={tw:.3f})\n"
                + f"        cur = {eq_name}\n"
            )

        body = "".join(lines)
        return f"""{imports}

class Segment(Scene):
    def construct(self):
{prev_lines}{body}        self.wait({t_end:.3f})
"""


class NumberLinePlotTemplate:
    """Number line with optional shaded segments and labeled dots."""

    visual_type = "number_line_plot"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None = None,
    ) -> str:
        x_range = params.get("x_range") or [-5, 5, 1]
        if not isinstance(x_range, list) or len(x_range) < 3:
            x_range = [-5, 5, 1]
        length = float(params.get("length", 8))

        points_raw = params.get("points") or []
        points: list[tuple[float, str, str]] = []
        for p in points_raw:
            if not isinstance(p, dict):
                continue
            points.append(
                (
                    float(p.get("value", 0)),
                    str(p.get("label", "")),
                    _safe_manim_color(str(p.get("color", "RED")), "RED"),
                )
            )

        regions_raw = params.get("regions") or []
        regions: list[tuple[float, float, str, float]] = []
        for r in regions_raw:
            if not isinstance(r, dict):
                continue
            regions.append(
                (
                    float(r.get("start", 0)),
                    float(r.get("end", 0)),
                    _safe_manim_color(str(r.get("color", "BLUE")), "BLUE"),
                    float(r.get("opacity", 0.28)),
                )
            )

        label_tex: list[str] = []
        for _v, lbl, _c in points:
            if lbl.strip() and not has_cjk(lbl):
                label_tex.append(lbl)
        imports = (
            scene_imports(*label_tex)
            if label_tex
            else "from manim import *\nimport numpy as np"
        )
        prev_lines = _prev_state_lines(prev_scene_state)

        n_plays = 1 + len(regions) + len(points)
        t_each, t_wait = split_n_writes(duration, max(n_plays, 1), fade_in=0.0)

        body: list[str] = []
        body.append(
            f"        nl = NumberLine(x_range={list(x_range)}, length={length}, include_numbers=True)\n"
        )
        body.append(f"        self.play(Create(nl), run_time={t_each:.3f})\n")

        for i, (r_start, r_end, col, opacity) in enumerate(regions):
            body.append(
                f"        seg_{i} = Line(nl.n2p({r_start}), nl.n2p({r_end}), stroke_width=14, color={col})\n"
                f"        seg_{i}.set_stroke(opacity={opacity})\n"
                f"        self.play(FadeIn(seg_{i}), run_time={t_each:.3f})\n"
            )

        for j, (val, lbl, col) in enumerate(points):
            body.append(
                f"        dot_{j} = Dot(nl.n2p({val}), color={col}, radius=0.09)\n"
            )
            if not lbl.strip():
                body.append(
                    f"        self.play(FadeIn(dot_{j}), run_time={t_each:.3f})\n"
                )
                continue
                if has_cjk(lbl):
                    plain_lbl = sanitize_latex_for_text_label(lbl)
                    body.append(
                        f"        lbl_{j} = Text({repr(apply_text_glyph_fallback(plain_lbl))}, font_size=26).next_to(dot_{j}, UP, buff=0.18)\n"
                        + indent_lines(
                            fit_text_mobject_lines(
                                f"lbl_{j}", max_width_expr="config.frame_width * 0.45"
                            ),
                            8,
                        )
                        + f"        self.play(FadeIn(dot_{j}), FadeIn(lbl_{j}), run_time={t_each:.3f})\n"
                    )
            else:
                body.append(
                    f"        lbl_{j} = MathTex({repr(lbl)}, font_size=30).next_to(dot_{j}, UP, buff=0.14)\n"
                    + indent_lines(
                        fit_tex_mobject_lines(
                            f"lbl_{j}", max_width_expr="config.frame_width * 0.45"
                        ),
                        8,
                    )
                    + f"        self.play(FadeIn(dot_{j}), FadeIn(lbl_{j}), run_time={t_each:.3f})\n"
                )

        body.append(f"        self.wait({t_wait:.3f})\n")

        return f"""{imports}

class Segment(Scene):
    def construct(self):
{prev_lines}{"".join(body)}"""


class AnnotatedEquationTemplate:
    """MathTex with sequential Brace + Text annotations on {{token}} parts."""

    visual_type = "annotated_equation"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None = None,
    ) -> str:
        raw_latex = wrap_korean_text_runs(str(params.get("latex", r"0=0")))
        ann_raw = params.get("annotations") or []
        annotations = [a for a in ann_raw if isinstance(a, dict)]
        braced = _inject_braces_for_annotations(raw_latex, annotations)

        all_latex = [braced]
        if prev_scene_state:
            all_latex.extend(st.latex for st in prev_scene_state)
        imports = (
            scene_imports(*all_latex)
            if all_latex
            else "from manim import *\nimport numpy as np"
        )
        prev_lines = _prev_state_lines(prev_scene_state)

        n_ann = len([a for a in annotations if str(a.get("target_tex", "")).strip()])
        t_w, t_rest = split_write(float(duration) * 0.38)
        budget = max(0.01, float(duration) - t_w - 0.12)
        t_br = min(0.85, max(0.22, budget / max(n_ann * 2, 1))) if n_ann else 0.0
        used = t_w + t_br * 2 * n_ann
        t_end = max(0.12, float(duration) - used)

        lines: list[str] = [
            f"        eq = MathTex({repr(braced)}, font_size=44)\n",
            indent_lines(fit_tex_mobject_lines("eq"), 8),
            f"        self.play(Write(eq), run_time={t_w:.3f})\n",
        ]
        idx = 0
        for ann in annotations:
            tok = str(ann.get("target_tex", "")).strip()
            if not tok:
                continue
            dire = _direction_const(str(ann.get("direction", "UP")))
            col = _safe_manim_color(str(ann.get("color", "YELLOW")), "YELLOW")
            txt = str(ann.get("text", "")).strip()
            bi = f"br_{idx}"
            lines.append(
                f"        {bi} = Brace(eq.get_part_by_tex({repr(tok)}), {dire}, color={col})\n"
            )
            if txt:
                lines.append(
                    f"        tx_{idx} = Text({repr(apply_text_glyph_fallback(txt))}, font_size=22)\n"
                    + f"        tx_{idx}.next_to({bi}, {dire}, buff=0.1)\n"
                    + indent_lines(
                        fit_text_mobject_lines(
                            f"tx_{idx}", max_width_expr="config.frame_width * 0.5"
                        ),
                        8,
                    )
                    + f"        self.play(GrowFromCenter({bi}), FadeIn(tx_{idx}), run_time={t_br:.3f})\n"
                )
            else:
                lines.append(
                    f"        self.play(GrowFromCenter({bi}), run_time={t_br:.3f})\n"
                )
            idx += 1

        lines.append(f"        self.wait({t_end:.3f})\n")

        return f"""{imports}

class Segment(Scene):
    def construct(self):
{prev_lines}{"".join(lines)}"""


class GraphPlotTemplate:
    visual_type = "graph_plot"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None = None,
    ) -> str:
        params = dict(params)
        func_python = str(params.get("func_python", "lambda x: x**2")).strip()
        if not func_python.startswith("lambda"):
            func_python = f"lambda x: ({func_python})"

        x_range = params.get("x_range") or [-3, 3, 1]
        y_range = params.get("y_range") or [-1, 5, 1]
        x_len = float(params.get("x_length", 6))
        y_len = float(params.get("y_length", 4))
        color = str(params.get("color", "BLUE"))
        func_latex = params.get("func_latex")
        points_raw = params.get("points") or []
        points: list[tuple[float, float, str, str]] = []
        for p in points_raw:
            if not isinstance(p, dict):
                continue
            points.append(
                (
                    float(p.get("x", 0.0)),
                    float(p.get("y", 0.0)),
                    _safe_manim_color(str(p.get("color", "RED")), "RED"),
                    str(p.get("label", "") or ""),
                )
            )

        extrema = params.get("extrema_points") or []
        for p in extrema:
            if not isinstance(p, dict):
                continue
            points.append(
                (
                    float(p.get("x", 0.0)),
                    float(p.get("y", 0.0)),
                    _safe_manim_color(str(p.get("color", "RED")), "RED"),
                    str(p.get("label", "") or ""),
                )
            )
        label_line = ""
        if func_latex and str(func_latex).strip():
            label_line = (
                f"        label = MathTex({repr(str(func_latex))}, font_size=36).to_corner(UL)\n"
                + indent_lines(
                    fit_tex_mobject_lines(
                        "label", max_width_expr="config.frame_width * 0.6"
                    ),
                    8,
                )
                + "        self.play(Write(label), run_time=0.4)\n"
            )

        latex_vals: list[str] = []
        if func_latex:
            latex_vals.append(str(func_latex))
        for _x, _y, _pc, pl in points:
            if pl.strip() and not has_cjk(pl):
                latex_vals.append(pl)
        imports = scene_imports(*latex_vals)
        prev_lines = _prev_state_lines(prev_scene_state)

        fade_out = _FADE_OUT_SECONDS
        t_axes, t_plot, t_end = split_axes_and_plot(
            duration,
            has_label_line=bool(func_latex and str(func_latex).strip()),
            fade_out=fade_out,
        )
        t_point = min(ANIM_CAP_FADE + 0.15, max(0.2, float(duration) * 0.12))

        point_lines = ""
        for i, (x, y, p_color, p_label) in enumerate(points):
            if p_label.strip():
                if has_cjk(p_label):
                    plain_label = sanitize_latex_for_text_label(p_label)
                    point_lines += (
                        f"        p_{i} = Dot(axes.c2p({x}, {y}), color={p_color}, radius=0.08)\n"
                        f"        p_{i}_lbl = Text({repr(apply_text_glyph_fallback(plain_label))}, font_size=24).next_to(p_{i}, UP, buff=0.14)\n"
                        + indent_lines(
                            fit_text_mobject_lines(
                                f"p_{i}_lbl", max_width_expr="config.frame_width * 0.45"
                            ),
                            8,
                        )
                        + f"        self.play(FadeIn(p_{i}), FadeIn(p_{i}_lbl), run_time={t_point:.3f})\n"
                    )
                else:
                    point_lines += (
                        f"        p_{i} = Dot(axes.c2p({x}, {y}), color={p_color}, radius=0.08)\n"
                        f"        p_{i}_lbl = MathTex({repr(p_label)}, font_size=30).next_to(p_{i}, UP, buff=0.12)\n"
                        + indent_lines(
                            fit_tex_mobject_lines(
                                f"p_{i}_lbl", max_width_expr="config.frame_width * 0.45"
                            ),
                            8,
                        )
                        + f"        self.play(FadeIn(p_{i}), FadeIn(p_{i}_lbl), run_time={t_point:.3f})\n"
                    )
            else:
                point_lines += (
                    f"        p_{i} = Dot(axes.c2p({x}, {y}), color={p_color}, radius=0.08)\n"
                    f"        self.play(FadeIn(p_{i}), run_time={t_point:.3f})\n"
                )

        return f"""{imports}

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
{label_line}{point_lines}        self.wait({t_end:.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
"""


class HighlightResultTemplate:
    visual_type = "highlight_result"

    @staticmethod
    def render_code(
        *,
        params: dict[str, Any],
        duration: float,
        prev_scene_state: list[SceneObjectState] | None = None,
    ) -> str:
        latex = wrap_korean_text_runs(str(params.get("latex", "x = -1")))
        box_color = str(params.get("box_color", "YELLOW"))
        all_latex = _collect_latex_values({"latex": latex}, prev_scene_state)
        imports = (
            scene_imports(*all_latex)
            if all_latex
            else "from manim import *\nimport numpy as np"
        )
        prev_lines = _prev_state_lines(prev_scene_state)

        t_in, t_box, t_hold, t_out = split_highlight_box(duration)

        return f"""{imports}

class Segment(Scene):
    def construct(self):
{prev_lines}        eq = MathTex({repr(latex)})
{indent_lines(fit_tex_mobject_lines("eq"), 8)}        eq.move_to(ORIGIN)
        box = SurroundingRectangle(eq, color={box_color}, buff=0.15)
        self.play(Write(eq), run_time={t_in:.3f})
        self.play(Create(box), run_time={t_box:.3f})
        self.wait({t_hold:.3f})
        self.play(FadeOut(box), run_time={min(t_out, ANIM_CAP_FADE):.3f})
"""


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
                f"        st = Text({repr(apply_text_glyph_fallback(subtitle))}, font_size=36)\n"
                + f"        st.next_to(tt, DOWN, buff=0.4)\n"
                + indent_lines(fit_text_mobject_lines("st"), 8)
                + f"        self.play(FadeIn(st, shift=UP*0.1), run_time={t2:.3f})\n"
            )

        return f"""{imports}

class Segment(Scene):
    def construct(self):
        tt = Text({repr(apply_text_glyph_fallback(title))}, font_size=48)
{indent_lines(fit_text_mobject_lines("tt", top_edge=True, top_buff=0.5), 8)}        tt.to_edge(UP, buff=0.5)
        self.play(FadeIn(tt, shift=DOWN*0.15), run_time={t1:.3f})
{sub_block}        self.wait({t_end:.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
"""


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

        return f"""{imports}

class Segment(Scene):
    def construct(self):
        head = Text({repr(apply_text_glyph_fallback(label))}, font_size=40)
{indent_lines(fit_text_mobject_lines("head", top_edge=True, top_buff=0.4), 8)}        head.to_edge(UP, buff=0.4)
        body = Text({repr(apply_text_glyph_fallback(problem_text))}, font_size=32).next_to(head, DOWN, buff=0.5)
{indent_lines(fit_text_mobject_lines("body", top_edge=True, top_buff=1.2), 8)}        body.to_edge(UP, buff=1.2)
        self.play(FadeIn(head), run_time={t1:.3f})
        self.play(FadeIn(body, shift=UP*0.1), run_time={t2:.3f})
        self.wait({t_end:.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
"""


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
        summary_lines = [ln.strip() for ln in summary.splitlines() if ln.strip()]
        if not summary_lines:
            summary_lines = [summary.strip() or "정리"]
        text_items = ",\n            ".join(
            f"Text({repr(apply_text_glyph_fallback(line))}, font_size=34)"
            for line in summary_lines
        )

        fade_out = _FADE_OUT_SECONDS
        t1 = min(0.85, max(0.3, duration * 0.22))
        t2 = min(0.9, max(0.3, duration * 0.36))
        t_end = max(0.12, duration - t1 - t2 - fade_out)

        eq_block = ""
        if extra_latex and str(extra_latex).strip():
            latex_s = wrap_korean_text_runs(str(extra_latex))
            imports = scene_imports(latex_s)
            eq_block = (
                f"        eq = MathTex({repr(latex_s)})\n"
                + indent_lines(fit_tex_mobject_lines("eq"), 8)
                + f"        eq.next_to(summary_group, DOWN, buff=0.45)\n"
                + f"        self.play(Write(eq), run_time={t2 * 0.55:.3f})\n"
            )
            t_end = max(0.12, duration - t1 - t2 * 1.55 - fade_out)

        return f"""{imports}

class Segment(Scene):
    def construct(self):
        summary_group = VGroup(
            {text_items}
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.32)
{indent_lines(fit_text_mobject_lines("summary_group", top_edge=True, top_buff=0.6), 8)}        summary_group.to_edge(UP, buff=0.6)
        self.play(FadeIn(summary_group), run_time={t1:.3f})
{eq_block}        self.wait({t_end:.3f})
        self.play(*[FadeOut(m) for m in self.mobjects], run_time={fade_out:.3f})
"""
