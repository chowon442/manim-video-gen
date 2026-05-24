"""Short-form video pipeline orchestration."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
import uuid
from collections.abc import Callable
from graphlib import TopologicalSorter, CycleError
from pathlib import Path
from typing import Any

from manim_video_gen.config import Settings, VideoFormatProfile, get_settings
from manim_video_gen.llm.client import OpenRouterClient
from manim_video_gen.llm.prompts.extract_shorts import (
    EXTRACT_SHORTS_SYSTEM_PROMPT,
    extract_shorts_user_prompt,
    parse_extract_shorts_response,
)
from manim_video_gen.llm.prompts.short_manim_gen import (
    build_short_manim_user_prompt,
    resolve_short_fallback_template,
    short_manim_system_prompt,
)
from manim_video_gen.llm.prompts.short_scriptify import (
    short_scriptify_system_prompt,
    short_scriptify_user_prompt,
    parse_short_scriptify_response,
)
from manim_video_gen.models.script import (
    ProcessedSegment,
    Segment,
    TTSResult,
    VideoScript,
)
from manim_video_gen.models.short import (
    ApplicationStory,
    ShortSeriesPlan,
    ShortUnit,
)
from manim_video_gen.pipeline.short_extractor import (
    fuzzy_match_concept,
    load_canonical_db,
)
from manim_video_gen.tts.factory import get_tts_provider
from manim_video_gen.utils.file_manager import SessionWorkspace
from manim_video_gen.utils.math_notation import polish_tts_text
from manim_video_gen.video.code_validator import (
    normalize_llm_manim_tex_backslashes,
    validate_and_test_render,
)
from manim_video_gen.video.composer import VideoComposer, ffprobe_duration_seconds
from manim_video_gen.video.duration_adjuster import adjust_duration_safe, ensure_scene_cleanup
from manim_video_gen.video.latex_korean import wrap_korean_text_runs
from manim_video_gen.video.manim_renderer import render_manim_scene
from manim_video_gen.video.subtitle import (
    generate_ass_subtitle_with_headline,
)
from manim_video_gen.video.templates.short.short_registry import ShortTemplateRegistry
from manim_video_gen.video.tex_template import inject_cjk_if_needed

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[dict[str, Any]], None]


# ---------------------------------------------------------------------------
# Quality guard
# ---------------------------------------------------------------------------


def short_quality(unit: ShortUnit) -> list[str]:
    """Validate a ShortUnit for short-form readiness.

    Returns a list of error messages. Empty list means pass.
    """
    errors: list[str] = []
    story = unit.story

    # ApplicationStory 5 required fields non-empty
    required_fields = [
        ("scenario", story.scenario),
        ("problem_in_domain", story.problem_in_domain),
        ("concept_bridge", story.concept_bridge),
        ("application_result", story.application_result),
        ("payoff_line", story.payoff_line),
    ]
    for name, value in required_fields:
        if not value or not str(value).strip():
            errors.append(f"story.{name} is empty")

    # Hook must not contain concept_name (delayed labeling)
    headline_lower = unit.headline.lower()
    concept_lower = unit.concept_name.lower()
    if concept_lower in headline_lower:
        errors.append(
            f"headline contains concept_name '{unit.concept_name}' (delayed labeling violation)"
        )

    # Payoff must contain application_result reference
    if story.application_result and story.payoff_line:
        app_words = set(story.application_result.lower().split())
        payoff_words = set(story.payoff_line.lower().split())
        overlap = app_words & payoff_words
        if len(overlap) < 2:
            errors.append(
                "payoff_line does not reference application_result (too disconnected)"
            )

    # estimated_seconds range
    if unit.estimated_seconds < 15 or unit.estimated_seconds > 60:
        errors.append(
            f"estimated_seconds={unit.estimated_seconds} outside valid range 15-60"
        )

    return errors


def _emit_progress(
    cb: ProgressCallback | None,
    payload: dict[str, Any],
) -> None:
    if cb is not None:
        cb(payload)


# ---------------------------------------------------------------------------
# Extract step
# ---------------------------------------------------------------------------


async def extract_shorts(
    *,
    client: OpenRouterClient,
    settings: Settings,
    document_text: str,
) -> ShortSeriesPlan:
    """Extract ShortSeriesPlan from document text via LLM."""
    return await client.complete_json_model(
        model=settings.model_solve,
        messages=[
            {"role": "system", "content": EXTRACT_SHORTS_SYSTEM_PROMPT},
            {"role": "user", "content": extract_shorts_user_prompt(document_text)},
        ],
        response_model=ShortSeriesPlan,
    )


def save_plan_json(plan: ShortSeriesPlan, path: Path) -> None:
    """Save ShortSeriesPlan to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(plan.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_plan_json(path: Path) -> ShortSeriesPlan:
    """Load ShortSeriesPlan from JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return ShortSeriesPlan(**data)


# ---------------------------------------------------------------------------
# Unit selection
# ---------------------------------------------------------------------------


def select_unit_by_topic(
    plan: ShortSeriesPlan,
    topic: str,
) -> ShortUnit:
    """Select a unit by fuzzy-matching topic against concept_name and headline."""
    db = load_canonical_db()
    matches = fuzzy_match_concept(topic, db, limit=1)

    if matches:
        best_story = matches[0]
        best_score = 0.0
        best_unit = plan.units[0]
        for unit in plan.units:
            score = 0.0
            if unit.concept_name.lower() == best_story.scenario.lower():
                score = 1.0
            elif topic.lower() in unit.concept_name.lower():
                score = 0.8
            elif topic.lower() in unit.headline.lower():
                score = 0.6
            if score > best_score:
                best_score = score
                best_unit = unit
        return best_unit

    # Fallback: direct substring match
    topic_lower = topic.lower()
    for unit in plan.units:
        if topic_lower in unit.concept_name.lower() or topic_lower in unit.headline.lower():
            return unit

    # No match: return first unit
    return plan.units[0]


def select_unit_by_index(plan: ShortSeriesPlan, index: int) -> ShortUnit:
    """Select a unit by index (0-based). Clamps to valid range."""
    clamped = max(0, min(index, len(plan.units) - 1))
    return plan.units[clamped]


# ---------------------------------------------------------------------------
# Topological sort for series mode
# ---------------------------------------------------------------------------


def topological_sort_units(units: list[ShortUnit]) -> list[ShortUnit]:
    """Sort units by prerequisites using topological sort.

    Falls back to original order on cycle detection.
    """
    if len(units) <= 1:
        return units

    concept_to_unit: dict[str, ShortUnit] = {u.concept_name: u for u in units}
    graph: dict[str, set[str]] = {}

    for unit in units:
        prereqs = set()
        for prereq in unit.prerequisites:
            if prereq in concept_to_unit:
                prereqs.add(prereq)
        graph[unit.concept_name] = prereqs

    try:
        sorter = TopologicalSorter(graph)
        order = list(sorter.static_order())
        result = []
        for concept in order:
            if concept in concept_to_unit:
                result.append(concept_to_unit[concept])
        return result
    except CycleError:
        logger.warning("Cycle detected in prerequisites; falling back to original order")
        return units


# ---------------------------------------------------------------------------
# Short Manim code builder (Registry → LLM → fallback)
# ---------------------------------------------------------------------------


async def _build_short_manim_code_for_segment(
    *,
    seg: Segment,
    duration: float,
    workspace: SessionWorkspace,
    registry: ShortTemplateRegistry,
    client: OpenRouterClient,
    settings: Settings,
) -> tuple[str, int]:
    """Build short-form Manim code. Returns (code, llm_retries)."""
    llm_retries = 0

    if registry.has(seg.visual_type):
        code = registry.render_code_for_segment(seg, duration)
        code = normalize_llm_manim_tex_backslashes(code)
        code = inject_cjk_if_needed(code)
        code = adjust_duration_safe(code, duration)
        code = ensure_scene_cleanup(code)
        return code, 0

    # LLM fallback
    errors: list[str] = []
    prior_codes: list[str] = []
    max_retries = 3

    for attempt in range(max_retries):
        user = build_short_manim_user_prompt(
            seg,
            duration_seconds=duration,
            prior_errors=errors,
            prior_codes=prior_codes if prior_codes else None,
        )
        code = await client.complete_text(
            model=settings.model_manim,
            messages=[
                {"role": "system", "content": short_manim_system_prompt()},
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
            workspace=workspace.root,
            settings=settings,
            stem=f"short_{seg.id:02d}_try{attempt}",
        )
        if ok:
            return code, attempt
        errors.append(err[:2000])
        prior_codes.append(code)

    # Final fallback: template
    logger.warning(
        "LLM short manim failed after retries; using fallback template for seg %d",
        seg.id,
    )
    fallback_name = resolve_short_fallback_template(seg.visual_type)
    if registry.has(fallback_name):
        code = registry.render_code_for_segment(
            seg.model_copy(update={"visual_type": fallback_name}),
            duration,
        )
    else:
        code = registry.render_code_for_segment(
            seg.model_copy(update={"visual_type": "short_concept_equation"}),
            duration,
        )
    code = normalize_llm_manim_tex_backslashes(code)
    code = inject_cjk_if_needed(code)
    code = adjust_duration_safe(code, duration)
    code = ensure_scene_cleanup(code)
    return code, max_retries


# ---------------------------------------------------------------------------
# Single unit render
# ---------------------------------------------------------------------------


async def _render_short_segment(
    *,
    seg: Segment,
    tts_result: TTSResult,
    duration: float,
    workspace: SessionWorkspace,
    registry: ShortTemplateRegistry,
    client: OpenRouterClient,
    composer: VideoComposer,
    settings: Settings,
    headline: str = "",
) -> tuple[Path, Path, str, int]:
    """Render a single short segment. Returns (merged, video_only, code, retries)."""
    code, llm_retries = await _build_short_manim_code_for_segment(
        seg=seg,
        duration=duration,
        workspace=workspace,
        registry=registry,
        client=client,
        settings=settings,
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
    subtitle_path: Path | None = None
    if settings.burn_subtitles:
        ass_path = workspace.root / f"seg_{seg.id:02d}.ass"
        generate_ass_subtitle_with_headline(
            seg.narration,
            duration,
            ass_path,
            headline=headline,
            max_chars=settings.subtitle_max_chars,
            wrap_mode=settings.subtitle_wrap_mode,
            font_size=settings.subtitle_font_size,
            margin_l=settings.subtitle_margin_l,
            margin_r=settings.subtitle_margin_r,
            margin_v=settings.subtitle_margin_v,
            format_profile=VideoFormatProfile.SHORT_9_16,
        )
        subtitle_path = ass_path

    await asyncio.to_thread(
        composer.merge_segment,
        video_path=video_only,
        audio_path=Path(tts_result.audio_path),
        output_path=merged,
        subtitle_path=subtitle_path,
        subtitle_safe_area_px=0,
    )
    return merged, video_only, code, llm_retries


# ---------------------------------------------------------------------------
# Single unit E2E
# ---------------------------------------------------------------------------


async def generate_short_video(
    unit: ShortUnit,
    *,
    settings: Settings | None = None,
    on_progress: ProgressCallback | None = None,
    workspace: SessionWorkspace | None = None,
    client: OpenRouterClient | None = None,
) -> tuple[Path, SessionWorkspace]:
    """Run short-form E2E pipeline for a single ShortUnit.

    Returns (final_mp4_path, workspace).
    """
    settings = settings or get_settings()
    t0 = time.perf_counter()
    own_workspace = workspace is None
    workspace = workspace or SessionWorkspace()

    tts = get_tts_provider(settings)
    registry = ShortTemplateRegistry()
    composer = VideoComposer(
        crossfade_duration=settings.crossfade_duration,
        inter_scene_gap_seconds=settings.inter_scene_gap_seconds,
    )

    llm_retries_total = 0
    processed: list[ProcessedSegment] = []
    final_path: Path | None = None

    try:
        close_client = client is None
        client = client or OpenRouterClient(settings)
        async with client:
            # Scriptify
            _emit_progress(on_progress, {"stage": "scriptify", "message": "대본 생성 중"})
            t_script = time.perf_counter()
            response = await client.complete_text(
                model=settings.model_script,
                messages=[
                    {"role": "system", "content": short_scriptify_system_prompt(settings)},
                    {"role": "user", "content": short_scriptify_user_prompt(unit)},
                ],
            )
            script = parse_short_scriptify_response(response)
            logger.info("short scriptify done in %.2fs", time.perf_counter() - t_script)

            # TTS
            _emit_progress(on_progress, {"stage": "tts", "message": "TTS 생성 중"})
            tts_results: list[TTSResult] = []
            for seg in script.segments:
                audio_path = workspace.root / f"seg_{seg.id:02d}.wav"
                tts_result = await tts.synthesize(
                    seg.effective_tts_text, output_path=audio_path
                )
                tts_results.append(tts_result)

            # Render each segment
            merged_paths: list[Path] = []
            for seg, tts_res in zip(script.segments, tts_results):
                dur = float(tts_res.duration_seconds)
                _emit_progress(
                    on_progress,
                    {
                        "stage": "segment",
                        "segment_id": seg.id,
                        "message": "렌더링",
                    },
                )
                t_seg = time.perf_counter()
                merged, _video, code, n_try = await _render_short_segment(
                    seg=seg,
                    tts_result=tts_res,
                    duration=dur,
                    workspace=workspace,
                    registry=registry,
                    client=client,
                    composer=composer,
                    settings=settings,
                    headline=unit.headline,
                )
                llm_retries_total += n_try
                merged_paths.append(merged)
                processed.append(
                    ProcessedSegment(
                        segment=seg,
                        tts=tts_res,
                        manim_code=code,
                        video_path=_video,
                        merged_segment_path=merged,
                    )
                )
                logger.info(
                    "short segment %d done in %.2fs (dur=%.2fs)",
                    seg.id,
                    time.perf_counter() - t_seg,
                    dur,
                )

            # Compose final
            concat_out = workspace.root / "_concat.mp4"
            final_path = workspace.root / "final.mp4"
            await asyncio.to_thread(
                composer.compose_final_with_bridges,
                merged_paths,
                concat_out,
                bridge_specs=None,
            )

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
                    shutil.move(str(concat_out), str(final_path))
            else:
                shutil.move(str(concat_out), str(final_path))

            # Save metadata
            metadata = {
                "headline": unit.headline,
                "concept_name": unit.concept_name,
                "story_format": unit.story.story_format.value,
                "domain": unit.story.domain,
                "difficulty": unit.difficulty,
                "estimated_seconds": unit.estimated_seconds,
                "actual_seconds": float(ffprobe_duration_seconds(final_path)),
                "segments": len(processed),
                "llm_manim_retries": llm_retries_total,
                "elapsed_seconds": time.perf_counter() - t0,
            }
            meta_path = workspace.root / "metadata.json"
            meta_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            logger.info(
                "short pipeline complete in %.2fs segments=%d",
                time.perf_counter() - t0,
                len(processed),
            )
            _emit_progress(
                on_progress,
                {
                    "stage": "done",
                    "message": "완료",
                    "elapsed_seconds": time.perf_counter() - t0,
                },
            )

            return final_path, workspace

    except Exception:
        if own_workspace and not settings.keep_workspace:
            workspace.cleanup()
        raise


# ---------------------------------------------------------------------------
# Series mode
# ---------------------------------------------------------------------------


async def generate_short_series(
    plan: ShortSeriesPlan,
    *,
    settings: Settings | None = None,
    max_shorts: int | None = None,
    on_progress: ProgressCallback | None = None,
) -> tuple[list[Path], Path]:
    """Generate multiple shorts from a plan.

    Returns (list_of_final_mp4_paths, series_output_dir).
    """
    settings = settings or get_settings()
    t0 = time.perf_counter()

    units = topological_sort_units(plan.units)
    if max_shorts is not None and max_shorts > 0:
        units = units[:max_shorts]

    run_id = uuid.uuid4().hex[:8]
    series_dir = Path(settings.artifact_dir or "artifacts") / f"series_{run_id}"
    series_dir.mkdir(parents=True, exist_ok=True)

    final_paths: list[Path] = []
    series_metadata: list[dict[str, Any]] = []

    async with OpenRouterClient(settings) as client:
        for i, unit in enumerate(units):
            _emit_progress(
                on_progress,
                {
                    "stage": "series_unit",
                    "unit_index": i,
                    "unit_total": len(units),
                    "concept_name": unit.concept_name,
                    "message": f"유닛 {i + 1}/{len(units)}: {unit.concept_name}",
                },
            )

            unit_workspace = SessionWorkspace()
            try:
                final_path, ws = await generate_short_video(
                    unit,
                    settings=settings,
                    on_progress=on_progress,
                    workspace=unit_workspace,
                    client=client,
                )

                out_name = f"short_{i + 1:02d}.mp4"
                out_path = series_dir / out_name
                shutil.copy2(final_path, out_path)
                final_paths.append(out_path)

                actual_dur = float(ffprobe_duration_seconds(out_path))
                series_metadata.append({
                    "unit_id": unit.id,
                    "headline": unit.headline,
                    "concept_name": unit.concept_name,
                    "file": out_name,
                    "actual_seconds": actual_dur,
                })

                logger.info("series unit %d/%d done: %s", i + 1, len(units), out_name)
            finally:
                if not settings.keep_workspace:
                    unit_workspace.cleanup()

    # Save series metadata
    series_meta = {
        "title": plan.title,
        "total_units": len(final_paths),
        "units": series_metadata,
        "elapsed_seconds": time.perf_counter() - t0,
    }
    meta_path = series_dir / "series_metadata.json"
    meta_path.write_text(
        json.dumps(series_meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(
        "series complete in %.2fs units=%d",
        time.perf_counter() - t0,
        len(final_paths),
    )
    _emit_progress(
        on_progress,
        {
            "stage": "done",
            "message": f"시리즈 완료: {len(final_paths)}개 영상",
            "elapsed_seconds": time.perf_counter() - t0,
        },
    )

    return final_paths, series_dir
