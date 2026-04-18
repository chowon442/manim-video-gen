"""Video script and segment models."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class SceneObjectState(BaseModel):
    """Object left on screen from a previous segment (for continuity)."""

    latex: str = Field(..., description="LaTeX string for MathTex")
    position_expr: str = Field(
        default="ORIGIN",
        description="Manim position expression e.g. UP*0.5, ORIGIN",
    )


class Segment(BaseModel):
    """One narrated segment with visual instructions."""

    id: int = Field(..., ge=0)
    narration: str = Field(
        ...,
        description="Readable Korean for subtitles; may include light math notation like x², 6x",
    )
    tts_text: str = Field(
        default="",
        description="Fully phonetic Korean for TTS engine (e.g. '엑스 제곱 더하기 육엑스')",
    )
    speaker: Literal["teacher", "student"] = Field(
        default="teacher",
        description="Narration speaker role for this segment.",
    )
    turn: Literal["explain", "question", "answer"] = Field(
        default="explain",
        description="Dialogue turn type for this segment.",
    )
    visual_description: str = Field(
        ...,
        description="What should appear on screen",
    )
    visual_type: str = Field(
        ...,
        description="equation_write | equation_transform | ...",
    )
    visual_params: dict[str, Any] = Field(default_factory=dict)
    prev_scene_state: list[SceneObjectState] | None = Field(
        default=None,
        description="Objects that should already be on screen at segment start",
    )

    @property
    def effective_tts_text(self) -> str:
        """Return tts_text if available, otherwise fall back to narration."""
        return (
            self.tts_text.strip()
            if self.tts_text and self.tts_text.strip()
            else self.narration
        )


class VideoScript(BaseModel):
    """Full script for a video."""

    title: str = Field(default="수학 해설")
    segments: list[Segment] = Field(default_factory=list, min_length=1)


class TTSResult(BaseModel):
    """Output of TTS synthesis for one segment."""

    audio_path: Path
    duration_seconds: float = Field(..., ge=0.0)
    word_timestamps: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of {word,start,end} or provider-specific keys",
    )


class ProcessedSegment(BaseModel):
    """Segment after TTS + optional Manim + paths."""

    segment: Segment
    tts: TTSResult
    manim_code: str | None = None
    video_path: Path | None = None
    merged_segment_path: Path | None = None


class SegmentChain(BaseModel):
    """Rendering unit: one or more consecutive script segments."""

    segments: list[Segment] = Field(default_factory=list)
    durations: list[float] = Field(default_factory=list)
    tts_results: list[TTSResult] = Field(default_factory=list)
    is_equation_chain: bool = False

    @model_validator(mode="after")
    def _lengths_match(self) -> SegmentChain:
        n = len(self.segments)
        if len(self.durations) != n or len(self.tts_results) != n:
            raise ValueError(
                "segments, durations, and tts_results must have the same length"
            )
        return self

    @property
    def total_duration(self) -> float:
        return float(sum(self.durations))

    @property
    def segment_ids(self) -> list[int]:
        return [s.id for s in self.segments]
