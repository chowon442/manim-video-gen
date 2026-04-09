"""Render a Manim scene file to MP4 (high quality)."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from manim_video_gen.config import Settings

logger = logging.getLogger(__name__)


def _find_rendered_segment_mp4(*, media_dir: Path, module_stem: str) -> Path:
    base = media_dir / "videos" / module_stem
    if not base.exists():
        raise RuntimeError(f"Expected Manim output under {base}, but it does not exist")

    matches = list(base.rglob("Segment.mp4"))
    if not matches:
        raise RuntimeError(f"Could not find rendered Segment.mp4 under {base}")

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
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=settings.manim_render_timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("manim CLI not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("manim render timed out") from exc

    if completed.returncode != 0:
        raise RuntimeError(
            "manim render failed:\n" + (completed.stderr or completed.stdout)[-8000:]
        )

    out = _find_rendered_segment_mp4(
        media_dir=workspace_media_dir, module_stem=scene_path.stem
    )
    logger.info("Rendered Manim video: %s", out)
    return out
