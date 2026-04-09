"""Example: run pipeline for a quadratic equation (requires API keys + manim + ffmpeg)."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from manim_video_gen.config import project_root
from manim_video_gen.pipeline.orchestrator import generate_video


async def main() -> None:
    problem = "이차방정식 x^2 + 2x + 1 = 0 을 풀어라."
    final_path, workspace = await generate_video(problem)
    try:
        out = project_root() / "artifacts" / "example_quadratic.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(final_path, out)
        print(out.resolve())
    finally:
        workspace.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
