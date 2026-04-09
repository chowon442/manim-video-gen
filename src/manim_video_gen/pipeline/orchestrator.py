"""End-to-end pipeline orchestration."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from manim_video_gen.config import Settings, get_settings
from manim_video_gen.llm.client import OpenRouterClient
from manim_video_gen.llm.prompts.manim_gen import (
    build_manim_user_prompt,
    manim_system_prompt,
)
from manim_video_gen.llm.prompts.scriptify import (
    SCRIPTIFY_SYSTEM_PROMPT,
    scriptify_user_prompt,
)
from manim_video_gen.llm.prompts.solve import SOLVE_SYSTEM_PROMPT, solve_user_prompt
from manim_video_gen.models.problem import MathProblem
from manim_video_gen.models.script import ProcessedSegment, VideoScript
from manim_video_gen.models.solution import SolutionPlan
from manim_video_gen.tts.elevenlabs import ElevenLabsTTS
from manim_video_gen.utils.file_manager import SessionWorkspace
from manim_video_gen.video.code_validator import (
    normalize_llm_manim_tex_backslashes,
    validate_and_test_render,
)
from manim_video_gen.video.composer import VideoComposer
from manim_video_gen.video.duration_adjuster import adjust_duration_safe
from manim_video_gen.video.manim_renderer import render_manim_scene
from manim_video_gen.video.templates.equation import EquationWriteTemplate
from manim_video_gen.video.templates.registry import TemplateRegistry
from manim_video_gen.video.tex_template import inject_cjk_if_needed

logger = logging.getLogger(__name__)


async def _llm_manim_with_retries(
    *,
    client: OpenRouterClient,
    settings: Settings,
    segment,
    duration: float,
    workspace: Path,
    stem: str,
    max_retries: int = 3,
) -> str:
    errors: list[str] = []
    for attempt in range(max_retries):
        user = build_manim_user_prompt(segment, duration_seconds=duration, prior_errors=errors)
        code = await client.complete_text(
            model=settings.model_manim,
            messages=[
                {"role": "system", "content": manim_system_prompt()},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        # Strip accidental fences
        code = code.strip()
        if code.startswith("```"):
            lines = code.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines).strip()

        code = normalize_llm_manim_tex_backslashes(code)
        code = inject_cjk_if_needed(code)
        code = adjust_duration_safe(code, duration)
        ok, err = await asyncio.to_thread(
            validate_and_test_render,
            code=code,
            workspace=workspace,
            settings=settings,
            stem=f"{stem}_try{attempt}",
        )
        if ok:
            return code
        errors.append(err[:2000])

    logger.warning("LLM Manim failed after retries; falling back to equation_write")
    # visual_params에 LaTeX 키가 있으면 우선 사용. 없으면 visual_description으로 대체
    # (visual_description은 한국어 설명문이라 LaTeX로 쓰기 부적합하므로 최후 수단).
    fallback_latex = (
        segment.visual_params.get("latex")
        or segment.visual_params.get("to_latex")
        or segment.visual_params.get("from_latex")
        or segment.visual_description[:400]
    )
    return EquationWriteTemplate.render_code(
        params={"latex": str(fallback_latex)},
        duration=duration,
    )


async def generate_video(
    problem_text: str,
    *,
    settings: Settings | None = None,
) -> tuple[Path, SessionWorkspace]:
    """
    Run full pipeline. Returns (final_mp4_path, workspace).

    Caller should `copy` the mp4 elsewhere then `workspace.cleanup()`.
    """
    settings = settings or get_settings()

    problem = MathProblem(problem_text=problem_text)
    tts = ElevenLabsTTS(settings)
    registry = TemplateRegistry()
    composer = VideoComposer(crossfade_duration=settings.crossfade_duration)

    workspace = SessionWorkspace()

    try:
        async with OpenRouterClient(settings) as client:
            plan = await client.complete_json_model(
                model=settings.model_solve,
                messages=[
                    {"role": "system", "content": SOLVE_SYSTEM_PROMPT},
                    {"role": "user", "content": solve_user_prompt(problem.problem_text)},
                ],
                response_model=SolutionPlan,
            )
            script = await client.complete_json_model(
                model=settings.model_script,
                messages=[
                    {"role": "system", "content": SCRIPTIFY_SYSTEM_PROMPT},
                    {"role": "user", "content": scriptify_user_prompt(plan)},
                ],
                response_model=VideoScript,
            )

            processed: list[ProcessedSegment] = []

            for seg in script.segments:
                audio_path = workspace.root / f"seg_{seg.id:02d}.wav"
                tts_result = await tts.synthesize(seg.narration, output_path=audio_path)
                duration = float(tts_result.duration_seconds)

                if registry.has(seg.visual_type):
                    code = registry.render_code_for_segment(seg, duration)
                    code = normalize_llm_manim_tex_backslashes(code)
                    code = inject_cjk_if_needed(code)
                    code = adjust_duration_safe(code, duration)
                else:
                    code = await _llm_manim_with_retries(
                        client=client,
                        settings=settings,
                        segment=seg,
                        duration=duration,
                        workspace=workspace.root,
                        stem=f"scene_{seg.id:02d}",
                    )

                scene_path = workspace.root / f"scene_{seg.id:02d}.py"
                video_only = await asyncio.to_thread(
                    render_manim_scene,
                    code=code,
                    scene_path=scene_path,
                    workspace_media_dir=workspace.media_dir,
                    settings=settings,
                )

                merged = workspace.root / f"merged_{seg.id:02d}.mp4"
                await asyncio.to_thread(
                    composer.merge_segment,
                    video_path=video_only,
                    audio_path=Path(tts_result.audio_path),
                    output_path=merged,
                )

                processed.append(
                    ProcessedSegment(
                        segment=seg,
                        tts=tts_result,
                        manim_code=code,
                        video_path=video_only,
                        merged_segment_path=merged,
                    )
                )
                logger.debug(
                    "Segment %d processed: duration=%.2fs video=%s",
                    seg.id,
                    duration,
                    video_only.name,
                )

            merged_paths = [ps.merged_segment_path for ps in processed if ps.merged_segment_path]

        final_path = workspace.root / "final.mp4"
        await asyncio.to_thread(composer.compose_final, merged_paths, final_path)

        return final_path, workspace
    except Exception:
        workspace.cleanup()
        raise
