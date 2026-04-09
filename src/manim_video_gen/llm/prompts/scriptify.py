"""Prompts: SolutionPlan -> VideoScript JSON."""

from __future__ import annotations

import json

from manim_video_gen.models.solution import SolutionPlan

SCRIPTIFY_SYSTEM_PROMPT = """You are a script writer for a Korean math explanation video.
Return ONLY valid JSON (no markdown fences) matching this schema:
{
  "title": string,
  "segments": [
    {
      "id": int (0-based),
      "narration": string (Korean ONLY; speakable; no LaTeX),
      "visual_description": string (what should appear on screen),
      "visual_type": string,
      "visual_params": object,
      "prev_scene_state": null | [
        {"latex": string, "position_expr": string}
      ]
    }
  ]
}

visual_type MUST be one of:
- equation_write
- equation_transform

visual_params for equation_write:
- latex: string (valid LaTeX)
- font_size: number (optional, default 48)
- color: string (optional, default WHITE)

visual_params for equation_transform:
- from_latex: string
- to_latex: string

LaTeX rules:
- Korean text in LaTeX is allowed ONLY inside \\text{} commands (e.g. \\text{또는}, \\text{따라서}).
- Do NOT place Korean characters directly in math mode — always wrap them with \\text{}.
- Prefer mathematical notation when possible (e.g. \\Rightarrow over \\text{따라서}).

Continuity rules:
- For segment id>0, set prev_scene_state to objects that should already be visible at the start
  (typically the final equation from the previous step), so the next transformation feels continuous.
- position_expr must be one of: ORIGIN, UP, DOWN, LEFT, RIGHT, UP*0.5, DOWN*0.5, LEFT*0.5, RIGHT*0.5,
  UP*1, DOWN*1, LEFT*1, RIGHT*1 (only these patterns).
"""


def scriptify_user_prompt(plan: SolutionPlan) -> str:
    payload = plan.model_dump()
    return (
        "다음 풀이를 영상 세그먼트로 나누어 JSON으로 만드세요.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
    )
