"""Map visual_type strings to templates."""

from __future__ import annotations

from typing import Any, Callable

from manim_video_gen.models.script import Segment
from manim_video_gen.video.templates.equation import (
    EquationTransformTemplate,
    EquationWriteTemplate,
)
from manim_video_gen.video.templates.more import (
    AnnotatedEquationTemplate,
    EquationDerivationTemplate,
    EquationStepsTemplate,
    GraphPlotTemplate,
    NumberLinePlotTemplate,
    HighlightResultTemplate,
    IntroProblemTemplate,
    OutroSummaryTemplate,
    TitleCardTemplate,
)


def _render_equation_write(segment: Segment, duration: float) -> str:
    return EquationWriteTemplate.render_code(
        params=segment.visual_params,
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    )


def _render_equation_transform(segment: Segment, duration: float) -> str:
    return EquationTransformTemplate.render_code(
        params=segment.visual_params,
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    )


def _render_steps(segment: Segment, duration: float) -> str:
    return EquationStepsTemplate.render_code(
        params=segment.visual_params,
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    )


def _render_equation_derivation(segment: Segment, duration: float) -> str:
    return EquationDerivationTemplate.render_code(
        params=segment.visual_params,
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    )


def _render_graph(segment: Segment, duration: float) -> str:
    return GraphPlotTemplate.render_code(
        params=segment.visual_params,
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    )


def _render_number_line(segment: Segment, duration: float) -> str:
    return NumberLinePlotTemplate.render_code(
        params=segment.visual_params,
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    )


def _render_annotated_equation(segment: Segment, duration: float) -> str:
    return AnnotatedEquationTemplate.render_code(
        params=segment.visual_params,
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    )


def _render_highlight(segment: Segment, duration: float) -> str:
    return HighlightResultTemplate.render_code(
        params=segment.visual_params,
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    )


def _render_title(segment: Segment, duration: float) -> str:
    return TitleCardTemplate.render_code(
        params=segment.visual_params,
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    )


def _render_intro(segment: Segment, duration: float) -> str:
    return IntroProblemTemplate.render_code(
        params=segment.visual_params,
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    )


def _render_outro(segment: Segment, duration: float) -> str:
    return OutroSummaryTemplate.render_code(
        params=segment.visual_params,
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    )


_TEMPLATE_RENDERERS: dict[str, Callable[[Segment, float], str]] = {
    EquationWriteTemplate.visual_type: _render_equation_write,
    EquationTransformTemplate.visual_type: _render_equation_transform,
    EquationStepsTemplate.visual_type: _render_steps,
    EquationDerivationTemplate.visual_type: _render_equation_derivation,
    GraphPlotTemplate.visual_type: _render_graph,
    NumberLinePlotTemplate.visual_type: _render_number_line,
    AnnotatedEquationTemplate.visual_type: _render_annotated_equation,
    HighlightResultTemplate.visual_type: _render_highlight,
    TitleCardTemplate.visual_type: _render_title,
    IntroProblemTemplate.visual_type: _render_intro,
    OutroSummaryTemplate.visual_type: _render_outro,
}


class TemplateRegistry:
    """Dispatch segment.visual_type to the corresponding template renderer."""

    def __init__(self) -> None:
        self._renderers: dict[str, Callable[[Segment, float], str]] = dict(
            _TEMPLATE_RENDERERS
        )

    def has(self, visual_type: str) -> bool:
        return visual_type in self._renderers

    def register(
        self,
        visual_type: str,
        renderer: Callable[[Segment, float], str],
    ) -> None:
        self._renderers[visual_type] = renderer

    def render_code_for_segment(self, segment: Segment, duration: float) -> str:
        vt = segment.visual_type
        try:
            renderer = self._renderers[vt]
        except KeyError as exc:
            raise KeyError(f"Unsupported visual_type: {vt}") from exc
        return renderer(segment, duration)
