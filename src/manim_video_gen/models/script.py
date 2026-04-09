"""Video script and segment models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


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
    narration: str = Field(..., description="Korean TTS text only, no raw LaTeX")
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
