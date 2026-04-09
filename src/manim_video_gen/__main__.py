"""CLI: python -m manim_video_gen \"문제 텍스트\""""

from __future__ import annotations

import argparse
import asyncio
import logging
import shutil
import sys
from pathlib import Path

from manim_video_gen.config import project_root
from manim_video_gen.pipeline.orchestrator import generate_video


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Generate a math explanation video")
    parser.add_argument("problem", help="Math problem text")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output MP4 path (default: artifacts/final.mp4)",
    )
    args = parser.parse_args()

    root = project_root()
    out = args.output or (root / "artifacts" / "final.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    async def _run() -> None:
        final_path, workspace = await generate_video(args.problem)
        try:
            shutil.copy2(final_path, out)
            print(f"Wrote: {out.resolve()}")
        finally:
            workspace.cleanup()

    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
