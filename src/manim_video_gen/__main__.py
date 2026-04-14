"""CLI: python -m manim_video_gen \"문제 텍스트\" | python -m manim_video_gen -f problem.md """

from __future__ import annotations

import argparse
import asyncio
import logging
import shutil
import sys
from pathlib import Path

from manim_video_gen.config import get_settings, project_root
from manim_video_gen.pipeline.orchestrator import generate_video


def _read_problem_file(path: Path) -> str:
    """Load UTF-8 problem text from a file; raises OSError/UnicodeError on failure."""
    return path.read_text(encoding="utf-8")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Generate a math explanation video")
    parser.add_argument(
        "problem",
        nargs="?",
        default=None,
        help="Math problem text (omit when using --file)",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        metavar="PATH",
        default=None,
        help="Read problem text from this file (UTF-8). Mutually exclusive with PROBLEM.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output MP4 path (default: artifacts/final.mp4)",
    )
    args = parser.parse_args()

    if args.file is not None and args.problem is not None:
        parser.error("Provide either PROBLEM text or --file, not both")
    if args.file is None and args.problem is None:
        parser.error("Provide problem text as PROBLEM or use --file PATH")

    problem_text: str
    if args.file is not None:
        fp = args.file.expanduser()
        if not fp.is_file():
            print(f"Error: not a file or missing: {fp}", file=sys.stderr)
            return 1
        try:
            problem_text = _read_problem_file(fp)
        except OSError as exc:
            print(f"Error: cannot read file {fp}: {exc}", file=sys.stderr)
            return 1
        except UnicodeError as exc:
            print(f"Error: file is not valid UTF-8 ({fp}): {exc}", file=sys.stderr)
            return 1
    else:
        problem_text = args.problem

    root = project_root()
    out = args.output or (root / "artifacts" / "final.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    async def _run() -> None:
        settings = get_settings()
        final_path, workspace = await generate_video(problem_text, settings=settings)
        try:
            shutil.copy2(final_path, out)
            print(f"Wrote: {out.resolve()}")
        finally:
            if not settings.keep_workspace:
                workspace.cleanup()

    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
