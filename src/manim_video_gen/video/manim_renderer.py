"""Render a Manim scene file to MP4 (high quality)."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from manim_video_gen.config import Settings
from manim_video_gen.exceptions import RenderError

logger = logging.getLogger(__name__)


def _find_rendered_segment_mp4(*, media_dir: Path, module_stem: str) -> Path:
    base = media_dir / "videos" / module_stem
    if not base.exists():
        raise RenderError(
            f"Expected Manim output under {base}, but it does not exist",
            stage="render",
        )

    matches = list(base.rglob("Segment.mp4"))
    if not matches:
        raise RenderError(
            f"Could not find rendered Segment.mp4 under {base}",
            stage="render",
        )

    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def render_manim_scene(
    *,
    code: str,
    scene_path: Path,
    workspace_media_dir: Path,
    settings: Settings,
) -> Path:
    """Write code to scene_path, render into workspace_media_dir, return mp4 path."""
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    workspace_media_dir.mkdir(parents=True, exist_ok=True)
    scene_path.write_text(code, encoding="utf-8")

    cmd = [
        "manim",
        "render",
        f"-q{settings.manim_quality_high}",
        str(scene_path),
        "Segment",
        "--media_dir",
        str(workspace_media_dir),
    ]
    if settings.video_width > 0 and settings.video_height > 0:
        cmd.extend(
            [
                "--resolution",
                f"{settings.video_width},{settings.video_height}",
            ]
        )
    if settings.video_fps > 0:
        cmd.extend(["--frame_rate", str(settings.video_fps)])
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=settings.manim_render_timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise RenderError(
            "manim CLI not found on PATH",
            stage="render",
            detail=str(exc),
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RenderError(
            "manim render timed out",
            stage="render",
            detail=str(exc),
        ) from exc

    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout)[-8000:]
        raise RenderError(
            "manim render failed",
            stage="render",
            detail=tail,
        )

    out = _find_rendered_segment_mp4(
        media_dir=workspace_media_dir, module_stem=scene_path.stem
    )
    logger.info("Rendered Manim video: %s", out)
    return out
