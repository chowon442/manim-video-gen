"""Generate a single Manim Scene from a SegmentChain (merged equation animations)."""

from __future__ import annotations

from manim_video_gen.models.script import Segment, SegmentChain
from manim_video_gen.video.anim_timing import (
    ANIM_CAP_FADE,
    ANIM_GAP,
    split_highlight_box,
    split_n_writes,
    split_transform,
    split_transform_no_prev,
    split_write,
)
from manim_video_gen.video.templates.equation import _collect_latex_values
from manim_video_gen.video.templates.more import (
    _derivation_segment_times,
    _parse_derivation_steps,
)
from manim_video_gen.video.tex_template import scene_imports

_CHAIN_FADE_OUT = 0.35


def _norm_latex(s: str) -> str:
    return "".join(str(s).split())


def _latex_values_from_segment(seg: Segment) -> list[str]:
    return _collect_latex_values(seg.visual_params, seg.prev_scene_state)


def _collect_all_latex(chain: SegmentChain) -> list[str]:
    values: list[str] = []
    for seg in chain.segments:
        values.extend(_latex_values_from_segment(seg))
    return values


def _snippet_equation_write(
    seg: Segment,
    duration: float,
    prev_var: str | None,
    var_name: str,
) -> tuple[str, str]:
    params = seg.visual_params
    latex = str(params.get("latex", ""))
    font_size = int(params.get("font_size", 48))
    color = str(params.get("color", "WHITE"))
    t_anim, t_wait = split_write(duration)

    if prev_var is None:
        block = f"""        {var_name} = MathTex({repr(latex)}, font_size={font_size}).set_color({color})
        self.play(Write({var_name}), run_time={t_anim:.3f})
        self.wait({t_wait:.3f})
"""
    else:
        block = f"""        {var_name} = MathTex({repr(latex)}, font_size={font_size}).set_color({color})
        self.play(ReplacementTransform({prev_var}, {var_name}), run_time={t_anim:.3f})
        self.wait({t_wait:.3f})
"""
    return block, var_name


def _snippet_equation_transform(
    seg: Segment,
    duration: float,
    prev_var: str | None,
    var_name: str,
) -> tuple[str, str]:
    params = seg.visual_params
    from_latex = str(params.get("from_latex", ""))
    to_latex = str(params.get("to_latex", ""))

    if prev_var is not None:
        t_tx, t_end = split_transform(duration)
        block = f"""        {var_name} = MathTex({repr(to_latex)})
        self.play(TransformMatchingTex({prev_var}, {var_name}), run_time={t_tx:.3f})
        self.wait({t_end:.3f})
"""
        return block, var_name

    t_intro, t_mid, t_tx, t_end = split_transform_no_prev(duration)
    block = f"""        {var_name}_a = MathTex({repr(from_latex)})
        {var_name} = MathTex({repr(to_latex)})
        self.play(Write({var_name}_a), run_time={t_intro:.3f})
        self.wait({t_mid:.3f})
        self.play(TransformMatchingTex({var_name}_a, {var_name}), run_time={t_tx:.3f})
        self.wait({t_end:.3f})
"""
    return block, var_name


def _snippet_equation_steps(
    seg: Segment,
    duration: float,
    prev_var: str | None,
    grp_name: str,
) -> tuple[str, str]:
    raw_steps = seg.visual_params.get("steps") or []
    steps = [str(s) for s in raw_steps] if isinstance(raw_steps, list) else []
    if not steps:
        steps = [r"0 = 0"]

    direction = str(seg.visual_params.get("arrange_direction", "DOWN")).upper()
    arrange_mob = "DOWN" if direction == "DOWN" else "RIGHT"
    buff = 0.45 if arrange_mob == "DOWN" else 0.35

    n = len(steps)
    fade_in = 0.3 if prev_var else 0.0
    t_each, t_wait = split_n_writes(duration, n, fade_in=fade_in)

    tex_lines = ",\n            ".join(f"MathTex({repr(s)})" for s in steps)

    prev_fade = ""
    if prev_var:
        prev_fade = f"        self.play(FadeOut({prev_var}), run_time={fade_in:.3f})\n"

    block = f"""{prev_fade}        {grp_name} = VGroup(
            {tex_lines}
        ).arrange({arrange_mob}, buff={buff})
        {grp_name}.move_to(ORIGIN)
        for _mob in {grp_name}:
            self.play(Write(_mob), run_time={t_each:.3f})
        self.wait({t_wait:.3f})
"""
    return block, grp_name


def _snippet_equation_derivation(
    seg: Segment,
    duration: float,
    prev_var: str | None,
) -> tuple[str, str]:
    """Stack equations with arrows; last mob name is `cur`."""
    parsed = _parse_derivation_steps(seg.visual_params)
    n = len(parsed)
    has_ann = [bool(parsed[i][1].strip()) for i in range(1, n)]
    fade_cost = min(0.35, float(duration) * 0.08) if prev_var else 0.0
    d_inner = max(0.01, float(duration) - fade_cost)
    t0, per_trans, t_end = _derivation_segment_times(d_inner, n, has_ann)

    prev_fade = ""
    if prev_var:
        prev_fade = f"        self.play(FadeOut({prev_var}), run_time={fade_cost:.3f})\n"

    lines: list[str] = [prev_fade]
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
    lines.append(f"        self.wait({t_end:.3f})\n")
    return "".join(lines), "cur"


def _snippet_highlight_result(
    seg: Segment,
    duration: float,
    prev_var: str | None,
    var_name: str,
    active_latex: str | None,
    idx: int,
) -> tuple[str, str, str | None]:
    params = seg.visual_params
    latex = str(params.get("latex", "x = -1"))
    box_color = str(params.get("box_color", "YELLOW"))
    box_var = f"box_{idx}"

    t_in, t_box, t_hold, t_out = split_highlight_box(duration)

    same = (
        prev_var is not None
        and active_latex is not None
        and _norm_latex(latex) == _norm_latex(active_latex)
    )

    if same:
        block = f"""        {box_var} = SurroundingRectangle({prev_var}, color={box_color}, buff=0.15)
        self.play(Create({box_var}), run_time={t_box:.3f})
        self.wait({t_hold:.3f})
        self.play(FadeOut({box_var}), run_time={min(t_out, ANIM_CAP_FADE):.3f})
"""
        return block, prev_var, active_latex

    if prev_var is not None:
        block = f"""        {var_name} = MathTex({repr(latex)})
        self.play(ReplacementTransform({prev_var}, {var_name}), run_time={min(t_in * 0.85, ANIM_CAP_FADE + 0.5):.3f})
        {box_var} = SurroundingRectangle({var_name}, color={box_color}, buff=0.15)
        self.play(Create({box_var}), run_time={t_box:.3f})
        self.wait({t_hold:.3f})
        self.play(FadeOut({box_var}), run_time={min(t_out, 0.4):.3f})
"""
        return block, var_name, latex

    block = f"""        {var_name} = MathTex({repr(latex)})
        {box_var} = SurroundingRectangle({var_name}, color={box_color}, buff=0.15)
        self.play(Write({var_name}), run_time={t_in:.3f})
        self.play(Create({box_var}), run_time={t_box:.3f})
        self.wait({t_hold:.3f})
        self.play(FadeOut({box_var}), run_time={min(t_out, ANIM_CAP_FADE):.3f})
"""
    return block, var_name, latex


_SNIPPET_MAP = {
    "equation_write": _snippet_equation_write,
    "equation_transform": _snippet_equation_transform,
    "equation_steps": _snippet_equation_steps,
}


def _active_latex_after_segment(seg: Segment, prev_active: str | None) -> str | None:
    vt = seg.visual_type
    p = seg.visual_params
    if vt == "equation_write":
        return str(p.get("latex", ""))
    if vt == "equation_transform":
        return str(p.get("to_latex", ""))
    if vt == "equation_steps":
        steps = p.get("steps") or []
        if isinstance(steps, list) and steps:
            last = steps[-1]
            return str(last) if isinstance(last, str) else str(last.get("latex", ""))
        return prev_active
    if vt == "equation_derivation":
        parsed = _parse_derivation_steps(seg.visual_params)
        return parsed[-1][0] if parsed else prev_active
    if vt == "highlight_result":
        return str(p.get("latex", ""))
    return prev_active


class ChainRenderer:
    """Build one Manim `Segment` scene from an equation chain."""

    def render_chain(self, chain: SegmentChain) -> str:
        if not chain.segments:
            raise ValueError("empty chain")
        if len(chain.segments) != len(chain.durations):
            raise ValueError("segments and durations length mismatch")

        all_latex = _collect_all_latex(chain)
        imports = scene_imports(*all_latex) if all_latex else "from manim import *\nimport numpy as np"

        body_parts: list[str] = []
        prev_var: str | None = None
        active_latex: str | None = None

        for i, (seg, duration) in enumerate(
            zip(chain.segments, chain.durations, strict=True)
        ):
            vt = seg.visual_type
            comment = f"        # chain seg {seg.id} ({vt}, {duration:.3f}s)\n"

            if vt == "highlight_result":
                var_name = f"eq_{i}"
                block, prev_var, new_active = _snippet_highlight_result(
                    seg, float(duration), prev_var, var_name, active_latex, i
                )
                body_parts.append(comment + block)
                active_latex = new_active
                continue

            if vt == "equation_derivation":
                block, prev_var = _snippet_equation_derivation(
                    seg, float(duration), prev_var
                )
                body_parts.append(comment + block)
                active_latex = _active_latex_after_segment(seg, active_latex)
                continue

            if vt not in _SNIPPET_MAP:
                raise KeyError(f"Unsupported visual_type in chain: {vt}")

            if vt == "equation_steps":
                grp_name = f"grp_{i}"
                block, prev_var = _snippet_equation_steps(
                    seg, float(duration), prev_var, grp_name
                )
            else:
                var_name = f"eq_{i}"
                fn = _SNIPPET_MAP[vt]
                block, prev_var = fn(seg, float(duration), prev_var, var_name)

            body_parts.append(comment + block)
            active_latex = _active_latex_after_segment(seg, active_latex)

        body_parts.append(
            f"        self.play(*[FadeOut(m) for m in self.mobjects], run_time={_CHAIN_FADE_OUT:.3f})\n"
        )

        construct_body = "".join(body_parts)
        return f"""{imports}

class Segment(Scene):
    def construct(self):
{construct_body}"""
