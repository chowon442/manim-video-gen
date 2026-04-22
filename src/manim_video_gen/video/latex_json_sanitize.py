"""Repair LaTeX strings after JSON parsing (weak models often emit invalid JSON escapes).

In JSON, ``\\f`` is a form feed (U+000C). When a model writes LaTeX ``\\frac`` without
proper escaping (``\\\\frac``), the parser turns the leading ``\\f`` into U+000C and
leaves ``rac{...}``, which breaks MathTex / xelatex.
"""

from __future__ import annotations

import re
from typing import Any

from manim_video_gen.models.script import SceneObjectState, VideoScript


def sanitize_latex_string_after_json_load(s: str) -> str:
    """Remove C0 controls mistaken for TeX and repair common ``\\frac`` corruption."""
    if not s:
        return s
    t = s.replace("\x0c", "").replace("\f", "")
    # " rac{" was "\\frac{" before JSON ate the backslash before "f"
    t = re.sub(r"(\s)rac\{", r"\1\\frac{", t)
    # "{\rac{" (missing backslash before frac) after a lone "f" was eaten as \f
    t = re.sub(r"(\{)rac\{", r"\1\\frac{", t)
    # target_tex may be exactly "rac{1}{2}" with no leading space
    if t.startswith("rac{") and not t.startswith("\\"):
        t = "\\frac" + t[3:]
    return t


def sanitize_nested_strings(obj: Any) -> Any:
    """Recursively sanitize all str values (e.g. visual_params trees)."""
    if isinstance(obj, str):
        return sanitize_latex_string_after_json_load(obj)
    if isinstance(obj, list):
        return [sanitize_nested_strings(x) for x in obj]
    if isinstance(obj, dict):
        return {k: sanitize_nested_strings(v) for k, v in obj.items()}
    return obj


def sanitize_video_script_visual_params(script: VideoScript) -> VideoScript:
    """Sanitize ``visual_params`` and ``prev_scene_state[].latex`` strings."""
    segs: list = []
    for s in script.segments:
        vp = sanitize_nested_strings(s.visual_params or {})
        prev = s.prev_scene_state
        if prev:
            new_prev: list[SceneObjectState] = [
                st.model_copy(
                    update={
                        "latex": sanitize_latex_string_after_json_load(st.latex),
                    }
                )
                for st in prev
            ]
        else:
            new_prev = None
        segs.append(
            s.model_copy(
                update={"visual_params": vp, "prev_scene_state": new_prev}
            )
        )
    return script.model_copy(update={"segments": segs})
