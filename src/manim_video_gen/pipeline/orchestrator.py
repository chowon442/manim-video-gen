"""End-to-end pipeline orchestration."""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

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
from manim_video_gen.models.script import (
    ProcessedSegment,
    Segment,
    SegmentChain,
    TTSResult,
    VideoScript,
)
from manim_video_gen.models.solution import SolutionPlan
from manim_video_gen.pipeline.chain_grouper import group_into_chains
from manim_video_gen.tts.factory import get_tts_provider
from manim_video_gen.utils.file_manager import SessionWorkspace
from manim_video_gen.utils.math_notation import polish_narration_math
from manim_video_gen.video.chain_renderer import ChainRenderer
from manim_video_gen.video.code_validator import (
    normalize_llm_manim_tex_backslashes,
    validate_and_test_render,
)
from manim_video_gen.video.composer import VideoComposer
from manim_video_gen.video.duration_adjuster import adjust_duration_safe
from manim_video_gen.video.manim_renderer import render_manim_scene
from manim_video_gen.video.subtitle import generate_ass_subtitle, generate_chain_ass_subtitle
from manim_video_gen.video.templates.equation import EquationWriteTemplate
from manim_video_gen.video.templates.registry import TemplateRegistry
from manim_video_gen.video.tex_template import inject_cjk_if_needed

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[dict[str, Any]], None]


def _ensure_tts_text(script: VideoScript) -> VideoScript:
    """Ensure every segment has a usable tts_text.

    If the LLM provided tts_text, apply polish as safety net.
    Otherwise, derive tts_text from narration via polish_narration_math.
    """
    updated = []
    for s in script.segments:
        tts = s.tts_text.strip() if s.tts_text else ""
        if not tts:
            tts = polish_narration_math(s.narration)
        else:
            tts = polish_narration_math(tts)
        updated.append(s.model_copy(update={"tts_text": tts}))
    return script.model_copy(update={"segments": updated})


def _emit_progress(
    cb: ProgressCallback | None,
    payload: dict[str, Any],
) -> None:
    if cb is not None:
        cb(payload)


async def _llm_manim_with_retries_counted(
    *,
    client: OpenRouterClient,
    settings: Settings,
    segment,
    duration: float,
    workspace: Path,
    stem: str,
    max_retries: int = 3,
) -> tuple[str, int]:
    """Returns (code, number of failed attempts before success or fallback)."""
    errors: list[str] = []
    prior_codes: list[str] = []
    for attempt in range(max_retries):
        user = build_manim_user_prompt(
            segment,
            duration_seconds=duration,
            prior_errors=errors,
            prior_codes=prior_codes if prior_codes else None,
        )
        code = await client.complete_text(
            model=settings.model_manim,
            messages=[
                {"role": "system", "content": manim_system_prompt()},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
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
            return code, attempt
        errors.append(err[:2000])
        prior_codes.append(code)

    logger.warning("LLM Manim failed after retries; falling back to equation_write")
    fallback_latex = (
        segment.visual_params.get("latex")
        or segment.visual_params.get("to_latex")
        or segment.visual_params.get("from_latex")
        or segment.visual_description[:400]
    )
    return (
        EquationWriteTemplate.render_code(
            params={"latex": str(fallback_latex)},
            duration=duration,
            prev_scene_state=segment.prev_scene_state,
        ),
        max_retries,
    )


async def _render_standalone_segment(
    *,
    seg: Segment,
    tts_result: TTSResult,
    duration: float,
    workspace: SessionWorkspace,
    registry: TemplateRegistry,
    client: OpenRouterClient,
    composer: VideoComposer,
    settings: Settings,
) -> tuple[Path, Path, str, int]:
    """Returns (merged_mp4_path, video_only_path, manim_code, llm_manim_retries)."""
    llm_retries = 0
    if registry.has(seg.visual_type):
        code = registry.render_code_for_segment(seg, duration)
        code = normalize_llm_manim_tex_backslashes(code)
        code = inject_cjk_if_needed(code)
        code = adjust_duration_safe(code, duration)
    else:
        code, n_try = await _llm_manim_with_retries_counted(
            client=client,
            settings=settings,
            segment=seg,
            duration=duration,
            workspace=workspace.root,
            stem=f"scene_{seg.id:02d}",
        )
        llm_retries = n_try

    scene_path = workspace.root / f"scene_{seg.id:02d}.py"
    video_only = await asyncio.to_thread(
        render_manim_scene,
        code=code,
        scene_path=scene_path,
        workspace_media_dir=workspace.media_dir,
        settings=settings,
    )

    merged = workspace.root / f"merged_{seg.id:02d}.mp4"
    subtitle_path: Path | None = None
    if settings.burn_subtitles:
        ass_path = workspace.root / f"seg_{seg.id:02d}.ass"
        generate_ass_subtitle(seg.narration, duration, ass_path)
        subtitle_path = ass_path

    await asyncio.to_thread(
        composer.merge_segment,
        video_path=video_only,
        audio_path=Path(tts_result.audio_path),
        output_path=merged,
        subtitle_path=subtitle_path,
    )
    return merged, video_only, code, llm_retries


async def _render_equation_chain(
    chain: SegmentChain,
    *,
    workspace: SessionWorkspace,
    composer: VideoComposer,
    settings: Settings,
    client: OpenRouterClient,
    registry: TemplateRegistry,
) -> tuple[Path, str, int]:
    """Render merged equation chain; fallback to per-segment on failure."""
    first_id = chain.segments[0].id
    stem = f"chain_{first_id:02d}"

    try:
        code = ChainRenderer().render_chain(chain)
        code = normalize_llm_manim_tex_backslashes(code)
        code = inject_cjk_if_needed(code)
        code = adjust_duration_safe(code, chain.total_duration)

        scene_path = workspace.root / f"{stem}.py"
        video_only = await asyncio.to_thread(
            render_manim_scene,
            code=code,
            scene_path=scene_path,
            workspace_media_dir=workspace.media_dir,
            settings=settings,
        )

        audio_out = workspace.root / f"{stem}_audio.m4a"
        await asyncio.to_thread(
            composer.concat_audio,
            [Path(t.audio_path) for t in chain.tts_results],
            audio_out,
        )

        subtitle_path: Path | None = None
        if settings.burn_subtitles:
            ass_path = workspace.root / f"{stem}.ass"
            generate_chain_ass_subtitle(
                [s.narration for s in chain.segments],
                chain.durations,
                ass_path,
            )
            subtitle_path = ass_path

        merged = workspace.root / f"merged_{stem}.mp4"
        await asyncio.to_thread(
            composer.merge_segment,
            video_path=video_only,
            audio_path=audio_out,
            output_path=merged,
            subtitle_path=subtitle_path,
        )
        return merged, code, 0
    except Exception as exc:
        logger.warning(
            "Equation chain render failed; falling back to per-segment: %s",
            exc,
        )
        parts: list[Path] = []
        codes: list[str] = []
        llm_retries = 0
        for seg, tts_res, dur in zip(
            chain.segments, chain.tts_results, chain.durations, strict=True
        ):
            p, _v, c, n = await _render_standalone_segment(
                seg=seg,
                tts_result=tts_res,
                duration=float(dur),
                workspace=workspace,
                registry=registry,
                client=client,
                composer=composer,
                settings=settings,
            )
            parts.append(p)
            codes.append(c)
            llm_retries += n
        fallback_out = workspace.root / f"merged_{stem}_fallback.mp4"
        await asyncio.to_thread(composer.concat_segments, parts, fallback_out)
        return fallback_out, "\n\n# --- chain fallback ---\n\n".join(codes), llm_retries


async def generate_video(
    problem_text: str,
    *,
    settings: Settings | None = None,
    on_progress: ProgressCallback | None = None,
) -> tuple[Path, SessionWorkspace]:
    """
    Run full pipeline. Returns (final_mp4_path, workspace).

    Caller should `copy` the mp4 elsewhere then `workspace.cleanup()`.
    """
    settings = settings or get_settings()
    t0 = time.perf_counter()

    problem = MathProblem(problem_text=problem_text)
    tts = get_tts_provider(settings)
    registry = TemplateRegistry()
    composer = VideoComposer(crossfade_duration=settings.crossfade_duration)

    workspace = SessionWorkspace()
    llm_retries_total = 0

    try:
        async with OpenRouterClient(settings) as client:
            _emit_progress(on_progress, {"stage": "solve", "message": "풀이 생성 중"})
            t_solve = time.perf_counter()
            plan = await client.complete_json_model(
                model=settings.model_solve,
                messages=[
                    {"role": "system", "content": SOLVE_SYSTEM_PROMPT},
                    {"role": "user", "content": solve_user_prompt(problem.problem_text)},
                ],
                response_model=SolutionPlan,
            )
            logger.info("solve step done in %.2fs", time.perf_counter() - t_solve)

            _emit_progress(on_progress, {"stage": "scriptify", "message": "대본 생성 중"})
            t_script = time.perf_counter()
            script = await client.complete_json_model(
                model=settings.model_script,
                messages=[
                    {"role": "system", "content": SCRIPTIFY_SYSTEM_PROMPT},
                    {"role": "user", "content": scriptify_user_prompt(plan)},
                ],
                response_model=VideoScript,
            )
            script = _ensure_tts_text(script)
            logger.info("scriptify step done in %.2fs", time.perf_counter() - t_script)

            _emit_progress(on_progress, {"stage": "tts", "message": "TTS 생성 중"})
            tts_results: list[TTSResult] = []
            for seg in script.segments:
                audio_path = workspace.root / f"seg_{seg.id:02d}.wav"
                tts_result = await tts.synthesize(
                    seg.effective_tts_text, output_path=audio_path
                )
                tts_results.append(tts_result)

            chains = group_into_chains(script.segments, tts_results)
            processed: list[ProcessedSegment] = []
            merged_paths: list[Path] = []

            for chain in chains:
                if chain.is_equation_chain:
                    for seg in chain.segments:
                        _emit_progress(
                            on_progress,
                            {
                                "stage": "segment",
                                "segment_id": seg.id,
                                "message": "equation chain 렌더",
                            },
                        )
                    t_chain = time.perf_counter()
                    merged_path, chain_code, n_try = await _render_equation_chain(
                        chain,
                        workspace=workspace,
                        composer=composer,
                        settings=settings,
                        client=client,
                        registry=registry,
                    )
                    llm_retries_total += n_try
                    merged_paths.append(merged_path)
                    for seg, tts_res in zip(
                        chain.segments, chain.tts_results, strict=True
                    ):
                        processed.append(
                            ProcessedSegment(
                                segment=seg,
                                tts=tts_res,
                                manim_code=chain_code,
                                video_path=None,
                                merged_segment_path=merged_path,
                            )
                        )
                    logger.info(
                        "equation chain ids=%s done in %.2fs",
                        chain.segment_ids,
                        time.perf_counter() - t_chain,
                    )
                else:
                    for seg, tts_res, dur in zip(
                        chain.segments,
                        chain.tts_results,
                        chain.durations,
                        strict=True,
                    ):
                        _emit_progress(
                            on_progress,
                            {
                                "stage": "segment",
                                "segment_id": seg.id,
                                "message": "TTS / 렌더 / 합성",
                            },
                        )
                        t_seg = time.perf_counter()
                        merged_path, video_only, code, n_try = (
                            await _render_standalone_segment(
                                seg=seg,
                                tts_result=tts_res,
                                duration=float(dur),
                                workspace=workspace,
                                registry=registry,
                                client=client,
                                composer=composer,
                                settings=settings,
                            )
                        )
                        llm_retries_total += n_try
                        merged_paths.append(merged_path)
                        processed.append(
                            ProcessedSegment(
                                segment=seg,
                                tts=tts_res,
                                manim_code=code,
                                video_path=video_only,
                                merged_segment_path=merged_path,
                            )
                        )
                        logger.info(
                            "segment %d done in %.2fs (duration=%.2fs)",
                            seg.id,
                            time.perf_counter() - t_seg,
                            float(dur),
                        )

        concat_out = workspace.root / "_concat.mp4"
        final_path = workspace.root / "final.mp4"
        await asyncio.to_thread(composer.compose_final, merged_paths, concat_out)

        bgm_raw = (settings.bgm_path or "").strip()
        if bgm_raw:
            bgm_p = Path(bgm_raw)
            if bgm_p.is_file():
                await asyncio.to_thread(
                    composer.mix_background_music,
                    video_path=concat_out,
                    bgm_path=bgm_p,
                    output_path=final_path,
                    bgm_volume=settings.bgm_volume,
                )
                concat_out.unlink(missing_ok=True)
            else:
                logger.warning("BGM path set but file missing: %s", bgm_p)
                shutil.move(str(concat_out), str(final_path))
        else:
            shutil.move(str(concat_out), str(final_path))

        logger.info(
            "pipeline complete in %.2fs segments=%d llm_manim_retries=%d",
            time.perf_counter() - t0,
            len(processed),
            llm_retries_total,
        )
        _emit_progress(
            on_progress,
            {
                "stage": "done",
                "message": "완료",
                "elapsed_seconds": time.perf_counter() - t0,
                "segments": len(processed),
            },
        )

        return final_path, workspace
    except Exception:
        workspace.cleanup()
        raise
