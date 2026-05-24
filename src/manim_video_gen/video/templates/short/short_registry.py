"""Registry for short-form (9:16) templates."""

from __future__ import annotations

from typing import Callable

from manim_video_gen.models.script import Segment
from manim_video_gen.video.templates.short.beat_templates import BEAT_RENDERERS


def _render_short_concept_equation(segment: Segment, duration: float) -> str:
    """Placeholder renderer for short_concept_equation."""
    return f"# short_concept_equation placeholder (duration={duration}s)"


_DEFAULT_RENDERERS: dict[str, Callable[[Segment, float], str]] = {
    "short_concept_equation": _render_short_concept_equation,
}
_DEFAULT_RENDERERS.update(BEAT_RENDERERS)


class ShortTemplateRegistry:
    """Dispatch segment.visual_type to short-form template renderers."""

    def __init__(self) -> None:
        self._renderers: dict[str, Callable[[Segment, float], str]] = dict(
            _DEFAULT_RENDERERS
        )

    def has(self, visual_type: str) -> bool:
        return visual_type in self._renderers

    def get(self, visual_type: str) -> Callable[[Segment, float], str] | None:
        return self._renderers.get(visual_type)

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
            raise KeyError(f"Unsupported short visual_type: {vt}") from exc
        return renderer(segment, duration)
