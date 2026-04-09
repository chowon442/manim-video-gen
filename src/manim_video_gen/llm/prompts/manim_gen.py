"""Prompts: segment -> full Manim Scene code (fallback path)."""

from __future__ import annotations

import json

from manim_video_gen.llm.prompts.manim_api_ref import MANIM_API_REFERENCE_TEXT
from manim_video_gen.models.script import Segment


def manim_system_prompt() -> str:
    return (
        "You generate a single Manim Community Edition Scene.\n"
        + MANIM_API_REFERENCE_TEXT
        + "\nOutput ONLY python code (no markdown fences).\n"
    )


def build_manim_user_prompt(
    segment: Segment,
    *,
    duration_seconds: float,
    prior_errors: list[str] | None = None,
) -> str:
    prior = ""
    if prior_errors:
        prior = "\n\nPrevious errors (fix them):\n" + "\n".join(
            f"- {e}" for e in prior_errors
        )
    return (
        f"duration_seconds (target total time, approximate): {duration_seconds:.3f}\n"
        f"visual_description: {segment.visual_description}\n"
        f"visual_params: {json.dumps(segment.visual_params, ensure_ascii=False)}\n"
        f"prev_scene_state: {json.dumps([s.model_dump() for s in segment.prev_scene_state] if segment.prev_scene_state else None, ensure_ascii=False)}\n"
        f"{prior}\n"
        "Generate:\n"
        "from manim import *\n\n"
        "class Segment(Scene):\n"
        "    def construct(self):\n"
        "        ...\n"
    )
