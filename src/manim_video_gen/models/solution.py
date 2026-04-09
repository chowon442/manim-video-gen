"""Structured solution plan from LLM."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SolutionStep(BaseModel):
    """One step in a worked solution."""

    step_number: int = Field(..., ge=1)
    explanation: str = Field(..., description="Teacher-style explanation in Korean")
    latex_expression: str | None = Field(
        default=None,
        description="Key LaTeX for this step, if any",
    )


class SolutionPlan(BaseModel):
    """Full solution broken into steps."""

    title: str = Field(default="풀이", description="Short title for the solution")
    steps: list[SolutionStep] = Field(default_factory=list, min_length=1)
    visualization_hints: list[str] = Field(
        default_factory=list,
        description="Optional ideas for on-screen visuals (graphs, number line, geometry) for the video pass",
    )
