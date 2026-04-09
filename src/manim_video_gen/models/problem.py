"""Input problem model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MathProblem(BaseModel):
    """User-provided math problem."""

    problem_text: str = Field(..., min_length=1, description="Problem statement in natural language / LaTeX mix")
    difficulty: str | None = Field(default=None, description="Optional difficulty hint")
    subject_area: str | None = Field(default=None, description="e.g. algebra, calculus")
