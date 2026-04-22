#!/usr/bin/env python3
"""Optional: run solve -> scriptify on a fixed problem (Phase 1-5e smoke test)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from manim_video_gen.config import get_settings
from manim_video_gen.llm.client import OpenRouterClient
from manim_video_gen.llm.prompts.scriptify import scriptify_system_prompt, scriptify_user_prompt
from manim_video_gen.llm.prompts.solve import SOLVE_SYSTEM_PROMPT, solve_user_prompt
from manim_video_gen.models.script import VideoScript
from manim_video_gen.models.solution import SolutionPlan


async def main() -> int:
    settings = get_settings()
    settings.require_openrouter()
    client = OpenRouterClient(settings)

    problem = "이차방정식 x^2 + 2x + 1 = 0 을 풀어라."
    plan = await client.complete_json_model(
        model=settings.model_solve,
        messages=[
            {"role": "system", "content": SOLVE_SYSTEM_PROMPT},
            {"role": "user", "content": solve_user_prompt(problem)},
        ],
        response_model=SolutionPlan,
    )
    print("=== SolutionPlan ===")
    print(plan.model_dump_json(indent=2, ensure_ascii=False))

    script = await client.complete_json_model(
        model=settings.model_script,
        messages=[
            {"role": "system", "content": scriptify_system_prompt(settings)},
            {"role": "user", "content": scriptify_user_prompt(plan)},
        ],
        response_model=VideoScript,
    )
    print("=== VideoScript ===")
    print(json.dumps(script.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
