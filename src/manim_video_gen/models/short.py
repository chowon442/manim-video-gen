"""Shorts pipeline core data models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class StoryFormat(str, Enum):
    """Story arc format for a ShortUnit."""

    APPLICATION = "application"
    MISCONCEPTION = "misconception"
    STAKES = "stakes"
    CURIOSITY = "curiosity"
    PATTERN = "pattern"


STORY_FORMAT_TONE_MAP: dict[StoryFormat, str] = {
    StoryFormat.APPLICATION: "casual",
    StoryFormat.MISCONCEPTION: "dramatic",
    StoryFormat.STAKES: "dramatic",
    StoryFormat.CURIOSITY: "insider",
    StoryFormat.PATTERN: "casual",
}


class ApplicationStory(BaseModel):
    """5-beat application story embedded in a ShortUnit."""

    story_format: StoryFormat = Field(
        ...,
        description="Arc format that determines tone and structure",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Extractor confidence in this story (0.0~1.0)",
    )
    source: str = Field(
        ...,
        description="Origin: 'document', 'canonical_db', or 'synthesized'",
    )
    domain: str = Field(
        ...,
        description="Application domain identifier (e.g. 'finance', 'physics')",
    )
    domain_label: str = Field(
        default="",
        description="Human-readable domain label for display",
    )
    scenario: str = Field(
        ...,
        description="Concrete situational setup (beat 1 — setting)",
    )
    problem_in_domain: str = Field(
        ...,
        description="What goes wrong or what needs solving (beat 2 — tension)",
    )
    concept_bridge: str = Field(
        ...,
        description="How the math concept is the needed tool (beat 3 — bridge)",
    )
    application_result: str = Field(
        ...,
        description="What happens when the concept is applied (beat 4 — resolution)",
    )
    result_visual: str = Field(
        default="",
        description="Visual description of the result for on-screen rendering",
    )
    payoff_line: str = Field(
        ...,
        description="Closing line that ties back to the hook (beat 5 — payoff)",
    )


class ShortUnit(BaseModel):
    """Atomic unit of a math short video."""

    id: str = Field(
        ...,
        description="Unique identifier for this unit",
    )
    headline: str = Field(
        ...,
        description="Attention-grabbing title for the short",
    )
    concept_name: str = Field(
        ...,
        description="Name of the math concept (e.g. '이차방정식의 근의 공식')",
    )
    core_insight: str = Field(
        ...,
        description="One-sentence explanation of why the concept matters",
    )
    story: ApplicationStory = Field(
        ...,
        description="Application story that motivates the concept",
    )
    explanation: str = Field(
        ...,
        description="Detailed explanation of the concept in Korean",
    )
    visual_concept: str = Field(
        ...,
        description="Description of main visual elements for the video",
    )
    result_visual_concept: str = Field(
        default="",
        description="Visual description of the story's result/outcome",
    )
    visual_type: str = Field(
        default="equation_write",
        description="Primary visual type for rendering",
    )
    difficulty: int = Field(
        ...,
        ge=1,
        le=5,
        description="Difficulty level from 1 (easiest) to 5 (hardest)",
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        description="concept_name values that should be understood first",
    )
    estimated_seconds: int = Field(
        ...,
        ge=1,
        le=300,
        description="Estimated video duration in seconds",
    )


class ShortSeriesPlan(BaseModel):
    """Plan for a series of related ShortUnits extracted from source material."""

    title: str = Field(
        ...,
        description="Overall title for the short series",
    )
    units: list[ShortUnit] = Field(
        ...,
        min_length=1,
        description="Extracted ShortUnits",
    )
    recommended_order: list[str] = Field(
        default_factory=list,
        description="Recommended playback order by unit id (topological)",
    )
