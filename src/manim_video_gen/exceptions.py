"""Domain-specific exceptions for pipeline stages."""

from __future__ import annotations


class PipelineError(Exception):
    """Base class for manim-video-gen pipeline errors."""

    def __init__(
        self,
        message: str,
        *,
        stage: str | None = None,
        segment_id: int | None = None,
        detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.segment_id = segment_id
        self.detail = detail


class LLMError(PipelineError):
    """OpenRouter / LLM call or JSON parsing failure."""


class TTSError(PipelineError):
    """Text-to-speech synthesis or provider API failure."""


class RenderError(PipelineError):
    """Manim rendering failure."""


class CompositionError(PipelineError):
    """FFmpeg merge / concat failure."""
