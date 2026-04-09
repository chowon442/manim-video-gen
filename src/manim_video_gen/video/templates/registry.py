"""Map visual_type strings to templates."""

from __future__ import annotations

from typing import Any

from manim_video_gen.models.script import SceneObjectState, Segment
from manim_video_gen.video.templates.equation import (
    EquationTransformTemplate,
    EquationWriteTemplate,
)


class TemplateRegistry:
    def __init__(self) -> None:
        self._types = {
            EquationWriteTemplate.visual_type: EquationWriteTemplate,
            EquationTransformTemplate.visual_type: EquationTransformTemplate,
        }

    def has(self, visual_type: str) -> bool:
        return visual_type in self._types

    def render_code_for_segment(self, segment: Segment, duration: float) -> str:
        vt = segment.visual_type
        if vt == EquationWriteTemplate.visual_type:
            return EquationWriteTemplate.render_code(
                params=segment.visual_params,
                duration=duration,
                prev_scene_state=segment.prev_scene_state,
            )
        if vt == EquationTransformTemplate.visual_type:
            return EquationTransformTemplate.render_code(
                params=segment.visual_params,
                duration=duration,
                prev_scene_state=segment.prev_scene_state,
            )
        raise KeyError(f"Unsupported visual_type: {vt}")
