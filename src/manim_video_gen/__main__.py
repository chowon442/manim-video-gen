"""CLI: python -m manim_video_gen "문제 텍스트" | python -m manim_video_gen -f problem.md | python -m manim_video_gen short -f doc.md"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path

from manim_video_gen.config import get_settings, project_root
from manim_video_gen.pipeline.orchestrator import generate_video


def _read_problem_file(path: Path) -> str:
    """Load UTF-8 problem text from a file; raises OSError/UnicodeError on failure."""
    return path.read_text(encoding="utf-8")


def _run_short(args: argparse.Namespace) -> int:
    """Handle `short` subcommand."""
    from manim_video_gen.pipeline.short_orchestrator import (
        extract_shorts,
        generate_short_series,
        generate_short_video,
        load_plan_json,
        save_plan_json,
        select_unit_by_index,
        select_unit_by_topic,
        short_quality,
    )
    from manim_video_gen.llm.client import OpenRouterClient

    fp: Path = args.file.expanduser()
    if not fp.is_file():
        print(f"Error: not a file or missing: {fp}", file=sys.stderr)
        return 1
    try:
        document_text = _read_problem_file(fp)
    except OSError as exc:
        print(f"Error: cannot read file {fp}: {exc}", file=sys.stderr)
        return 1
    except UnicodeError as exc:
        print(f"Error: file is not valid UTF-8 ({fp}): {exc}", file=sys.stderr)
        return 1

    settings = get_settings()
    root = project_root()

    async def _run() -> None:
        plan = None

        # Load or extract plan
        if args.from_plan:
            plan = load_plan_json(args.from_plan)
        else:
            async with OpenRouterClient(settings) as client:
                plan = await extract_shorts(
                    client=client,
                    settings=settings,
                    document_text=document_text,
                )

            # Save plan.json
            plan_path = root / "artifacts" / "plan.json"
            save_plan_json(plan, plan_path)
            print(f"Plan saved: {plan_path.resolve()}")

        if args.dry_run or args.plan_only:
            return

        # Single mode
        if args.mode == "single":
            if args.from_plan and args.unit is not None:
                unit = select_unit_by_index(plan, args.unit - 1)
            elif args.topic:
                unit = select_unit_by_topic(plan, args.topic)
            else:
                unit = plan.units[0]

            # Quality guard
            errors = short_quality(unit)
            if errors:
                for err in errors:
                    print(f"Quality guard failed: {err}", file=sys.stderr)
                raise ValueError(f"short_quality failed with {len(errors)} error(s)")

            out = args.output or (root / "artifacts" / f"short_{unit.id}.mp4")
            out.parent.mkdir(parents=True, exist_ok=True)

            final_path, workspace = await generate_short_video(
                unit, settings=settings
            )
            try:
                shutil.copy2(final_path, out)
                print(f"Wrote: {out.resolve()}")
            finally:
                if not settings.keep_workspace:
                    workspace.cleanup()

        # Series mode
        elif args.mode == "series":
            final_paths, series_dir = await generate_short_series(
                plan,
                settings=settings,
                max_shorts=args.max_shorts,
            )
            print(f"Series complete: {len(final_paths)} videos in {series_dir}")

    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Route "short" subcommand before main parser
    if len(sys.argv) > 1 and sys.argv[1] == "short":
        parser = argparse.ArgumentParser(
            prog="manim_video_gen short",
            description="Generate short-form math videos",
        )
        parser.add_argument(
            "-f",
            "--file",
            type=Path,
            metavar="PATH",
            required=True,
            help="Source document path (UTF-8)",
        )
        parser.add_argument(
            "--mode",
            choices=["single", "series"],
            default="single",
            help="single: one short, series: multiple shorts (default: single)",
        )
        parser.add_argument(
            "--topic",
            type=str,
            default=None,
            help="Fuzzy-match topic for unit selection (single mode)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Extract only; save plan.json and stop",
        )
        parser.add_argument(
            "--plan-only",
            action="store_true",
            help="Same as --dry-run (alias)",
        )
        parser.add_argument(
            "--from-plan",
            type=Path,
            default=None,
            help="Load plan.json instead of extracting",
        )
        parser.add_argument(
            "--unit",
            type=int,
            default=None,
            help="Unit index (1-based) for --from-plan re-render",
        )
        parser.add_argument(
            "--max-shorts",
            type=int,
            default=None,
            help="Cap number of shorts in series mode",
        )
        parser.add_argument(
            "-o",
            "--output",
            type=Path,
            default=None,
            help="Output MP4 path (single mode only)",
        )
        args = parser.parse_args(sys.argv[2:])
        return _run_short(args)

    # Original long-form pipeline
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
