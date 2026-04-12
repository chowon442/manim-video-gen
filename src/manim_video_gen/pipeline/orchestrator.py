"""End-to-end pipeline orchestration."""

from __future__ import annotations

import asyncio
import json
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
from manim_video_gen.pipeline.diagnostics import (
    dump_generation_diagnostics,
    new_run_id,
)
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
from manim_video_gen.video.duration_adjuster import ensure_scene_cleanup
from manim_video_gen.video.latex_korean import wrap_korean_text_runs
from manim_video_gen.video.manim_renderer import render_manim_scene
from manim_video_gen.video.consistency_validator import validate_script_consistency
from manim_video_gen.video.subtitle import (
    generate_ass_subtitle,
    generate_chain_ass_subtitle,
)
from manim_video_gen.video.templates.equation import (
    EquationTransformTemplate,
    EquationWriteTemplate,
)
from manim_video_gen.video.templates.registry import TemplateRegistry
from manim_video_gen.video.tex_template import inject_cjk_if_needed

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[dict[str, Any]], None]

_GRAPH_TRANSITION_TAILS = (
    "이제 그래프로 확인해 봅시다",
    "이제 그래프로 확인합니다",
    "그래프로 확인해 봅시다",
    "그래프로 확인합니다",
)

_BRIDGE_DURATION_SECONDS = 0.65


def _segment_bridge_latex(seg: Segment) -> str | None:
    """Return a representative latex string for bridge transforms.

    Conservative extraction: only equation-like visual types yield a bridge token.
    """
    vp = seg.visual_params or {}
    vt = seg.visual_type

    if vt == "equation_write":
        s = str(vp.get("latex", "")).strip()
        return wrap_korean_text_runs(s) if s else None

    if vt == "equation_transform":
        s = str(vp.get("to_latex") or vp.get("from_latex") or "").strip()
        return wrap_korean_text_runs(s) if s else None

    if vt == "equation_steps":
        steps = vp.get("steps") or []
        if isinstance(steps, list) and steps:
            last = steps[-1]
            if isinstance(last, str):
                s = last.strip()
                return wrap_korean_text_runs(s) if s else None
            if isinstance(last, dict):
                s = str(last.get("latex", "")).strip()
                return wrap_korean_text_runs(s) if s else None
        return None

    if vt == "equation_derivation":
        steps = vp.get("steps") or []
        if isinstance(steps, list) and steps:
            last = steps[-1]
            if isinstance(last, dict):
                s = str(last.get("latex", "")).strip()
                return wrap_korean_text_runs(s) if s else None
            if isinstance(last, str):
                s = last.strip()
                return wrap_korean_text_runs(s) if s else None
        return None

    if vt == "highlight_result":
        s = str(vp.get("latex", "")).strip()
        return wrap_korean_text_runs(s) if s else None

    if vt == "annotated_equation":
        s = str(vp.get("latex", "")).strip()
        return wrap_korean_text_runs(s) if s else None

    return None


def _norm_latex_key(s: str) -> str:
    return "".join(str(s).split())


def _build_bridge_specs_for_processed(
    processed: list[ProcessedSegment],
    *,
    merged_paths: list[Path] | None = None,
) -> list[dict[str, Any]]:
    """Build bridge specs across adjacent rendered segments.

    All scene boundaries are considered; only confident equation-latex pairs
    produce a bridge spec. Others are immediate hard-cut fallback.
    """
    out: list[dict[str, Any]] = []
    if len(processed) < 2:
        return out

    path_groups: dict[str, list[ProcessedSegment]] = {}
    for ps in processed:
        if ps.merged_segment_path is None:
            continue
        k = str(Path(ps.merged_segment_path).resolve())
        path_groups.setdefault(k, []).append(ps)

    if merged_paths:
        ordered_keys = [str(Path(p).resolve()) for p in merged_paths]
    else:
        ordered_keys = []
        seen: set[str] = set()
        for ps in processed:
            if ps.merged_segment_path is None:
                continue
            k = str(Path(ps.merged_segment_path).resolve())
            if k not in seen:
                seen.add(k)
                ordered_keys.append(k)

    for left_key, right_key in zip(ordered_keys, ordered_keys[1:]):
        left_group = path_groups.get(left_key) or []
        right_group = path_groups.get(right_key) or []
        if not left_group or not right_group:
            continue

        left_seg = left_group[-1].segment
        right_seg = right_group[0].segment
        left_latex = _segment_bridge_latex(left_seg)
        right_latex = _segment_bridge_latex(right_seg)
        if not left_latex or not right_latex:
            continue
        if _norm_latex_key(left_latex) == _norm_latex_key(right_latex):
            continue
        out.append(
            {
                "from_segment_id": left_seg.id,
                "to_segment_id": right_seg.id,
                "from_latex": left_latex,
                "to_latex": right_latex,
                "duration": _BRIDGE_DURATION_SECONDS,
                "fallback": "hard_cut",
            }
        )
    return out


async def _render_bridge_segment(
    *,
    workspace: SessionWorkspace,
    composer: VideoComposer,
    settings: Settings,
    from_segment_id: int,
    to_segment_id: int,
    from_latex: str,
    to_latex: str,
    duration: float,
) -> tuple[Path, str]:
    """Render a short semantic bridge clip (equation transform)."""
    code = EquationTransformTemplate.render_code(
        params={"from_latex": from_latex, "to_latex": to_latex},
        duration=float(duration),
        prev_scene_state=None,
    )
    code = normalize_llm_manim_tex_backslashes(code)
    code = inject_cjk_if_needed(code)
    code = adjust_duration_safe(code, float(duration))
    code = ensure_scene_cleanup(code)

    stem = f"bridge_{from_segment_id:02d}_{to_segment_id:02d}"
    scene_path = workspace.root / f"{stem}.py"
    video_only = await asyncio.to_thread(
        render_manim_scene,
        code=code,
        scene_path=scene_path,
        workspace_media_dir=workspace.media_dir,
        settings=settings,
    )

    silent_audio = workspace.root / f"{stem}.m4a"
    await asyncio.to_thread(
        composer.generate_silence_audio,
        duration=float(duration),
        output_path=silent_audio,
    )

    merged = workspace.root / f"merged_{stem}.mp4"
    await asyncio.to_thread(
        composer.merge_segment,
        video_path=video_only,
        audio_path=silent_audio,
        output_path=merged,
        subtitle_path=None,
        subtitle_safe_area_px=settings.subtitle_safe_area_px,
    )
    return merged, code


def _requires_custom_scene(seg: Segment) -> bool:
    """Return True when segment asks visuals that template cannot represent."""
    if seg.visual_type != "graph_plot":
        return False

    narration = (seg.narration or "").lower()
    vp = seg.visual_params or {}

    has_line_claim = (
        "직선" in narration
        or "line" in narration
        or "y=" in narration
        or "y =" in narration
    )
    has_curve_claim = (
        "곡선" in narration or "그래프" in narration or "curve" in narration
    )

    supports_multi = bool(vp.get("extra_functions") or vp.get("line_python"))
    if has_line_claim and has_curve_claim and not supports_multi:
        return True
    return False


def split_segment_for_transition_tail(seg: Segment) -> list[Segment]:
    """Split graph-transition tail into separate segment with role separation.

    Example:
    - lead: reasoning/result narration (converted to highlight_result)
    - tail: "이제 그래프로 ..." narration (keeps graph_plot)
    """
    if seg.visual_type != "graph_plot":
        return [seg]

    text = (seg.narration or "").strip()
    lower = text.lower()
    cut = -1
    phrase = ""
    for p in _GRAPH_TRANSITION_TAILS:
        pos = lower.find(p.lower())
        if pos != -1:
            cut = pos
            phrase = p
            break
    if cut <= 0:
        return [seg]

    lead_text = text[:cut].rstrip(" .")
    tail_text = text[cut:].strip()
    if len(lead_text) < 8 or len(tail_text) < 4:
        return [seg]

    # Build a non-graph lead segment to avoid duplicate graph rendering.
    line_expr = str(
        seg.visual_params.get("line_python")
        or seg.visual_params.get("line_latex")
        or ""
    )
    points = (
        seg.visual_params.get("points") or seg.visual_params.get("extrema_points") or []
    )
    points_text = ""
    if isinstance(points, list) and points:
        vals: list[str] = []
        for p in points:
            if isinstance(p, dict):
                x = p.get("x")
                y = p.get("y")
                if x is not None and y is not None:
                    vals.append(f"({x}, {y})")
        if vals:
            points_text = ", ".join(vals)
    highlight_latex = ""
    if line_expr.strip().startswith("lambda"):
        # keep fallback terse; no risky symbolic conversion
        highlight_latex = r"y = -2x + 6"
    elif line_expr.strip():
        highlight_latex = line_expr.strip()
    elif points_text:
        highlight_latex = points_text
    else:
        highlight_latex = seg.visual_params.get("func_latex", r"y=f(x)")

    lead = seg.model_copy(
        update={
            "narration": lead_text + ".",
            "tts_text": lead_text + ".",
            "visual_type": "highlight_result",
            "visual_description": "요약 결과를 강조",
            "visual_params": {
                "latex": str(highlight_latex),
                "box_color": "YELLOW",
            },
            "prev_scene_state": seg.prev_scene_state,
        }
    )
    tail = seg.model_copy(
        update={
            "narration": tail_text if tail_text.endswith(".") else (tail_text + "."),
            "tts_text": tail_text if tail_text.endswith(".") else (tail_text + "."),
            "prev_scene_state": None,
        }
    )
    return [lead, tail]


def split_script_transition_tails(script: VideoScript) -> VideoScript:
    new_segments: list[Segment] = []
    for seg in script.segments:
        new_segments.extend(split_segment_for_transition_tail(seg))

    # reindex IDs to keep monotonic 0-based order
    fixed: list[Segment] = []
    for i, s in enumerate(new_segments):
        fixed.append(s.model_copy(update={"id": i}))
    return script.model_copy(update={"segments": fixed})


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


def _consistency_error_prompt(
    *,
    plan: SolutionPlan,
    previous_script: VideoScript,
    report: Any,
) -> str:
    issue_lines = []
    for i in report.issues:
        if i.severity != "error":
            continue
        issue_lines.append(f"- seg={i.segment_id} code={i.code}: {i.message}")
    issues = "\n".join(issue_lines) if issue_lines else "- (none)"
    return (
        "기존 script JSON을 정합성 오류 없이 고쳐 다시 출력하세요.\n"
        "중요: 전체 schema를 그대로 유지하고, 오류가 난 세그먼트만 최소 변경하세요.\n"
        "가능하면 visual_type 유지, 불가능하면 visual_type/visual_params를 함께 바꿔 narration과 일치시켜야 합니다.\n"
        "\n"
        "[Detected error issues]\n"
        f"{issues}\n\n"
        "[Original script JSON]\n"
        f"{json.dumps(previous_script.model_dump(), ensure_ascii=False, indent=2)}\n\n"
        "[Original solution plan]\n"
        f"{scriptify_user_prompt(plan)}"
    )


async def _scriptify_with_consistency_repair(
    *,
    client: OpenRouterClient,
    settings: Settings,
    plan: SolutionPlan,
) -> tuple[VideoScript, Any | None]:
    """Run scriptify and optional consistency auto-repair loop."""
    script = await client.complete_json_model(
        model=settings.model_script,
        messages=[
            {"role": "system", "content": SCRIPTIFY_SYSTEM_PROMPT},
            {"role": "user", "content": scriptify_user_prompt(plan)},
        ],
        response_model=VideoScript,
    )
    script = _ensure_tts_text(script)

    if settings.consistency_mode == "off":
        return script, None

    report = validate_script_consistency(script.segments)
    if settings.consistency_mode != "error":
        return script, report

    if not any(i.severity == "error" for i in report.issues):
        return script, report

    if not settings.consistency_auto_repair:
        return script, report

    max_attempts = max(0, int(settings.consistency_auto_repair_max_attempts))
    for attempt in range(1, max_attempts + 1):
        logger.warning(
            "consistency auto-repair attempt %d/%d",
            attempt,
            max_attempts,
        )
        repaired = await client.complete_json_model(
            model=settings.model_script,
            messages=[
                {"role": "system", "content": SCRIPTIFY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _consistency_error_prompt(
                        plan=plan,
                        previous_script=script,
                        report=report,
                    ),
                },
            ],
            response_model=VideoScript,
        )
        repaired = _ensure_tts_text(repaired)
        new_report = validate_script_consistency(repaired.segments)
        if not any(i.severity == "error" for i in new_report.issues):
            return repaired, new_report
        script = repaired
        report = new_report

    return script, report


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
    force_llm = _requires_custom_scene(seg)
    if force_llm:
        logger.info(
            "Routing segment %d to LLM Manim due to template capability mismatch: visual_type=%s",
            seg.id,
            seg.visual_type,
        )

    if registry.has(seg.visual_type) and not force_llm:
        code = registry.render_code_for_segment(seg, duration)
        code = normalize_llm_manim_tex_backslashes(code)
        code = inject_cjk_if_needed(code)
        code = adjust_duration_safe(code, duration)
        code = ensure_scene_cleanup(code)
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
        code = ensure_scene_cleanup(code)

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
        generate_ass_subtitle(
            seg.narration,
            duration,
            ass_path,
            max_chars=settings.subtitle_max_chars,
            wrap_mode=settings.subtitle_wrap_mode,
            font_size=settings.subtitle_font_size,
            margin_l=settings.subtitle_margin_l,
            margin_r=settings.subtitle_margin_r,
            margin_v=settings.subtitle_margin_v,
        )
        subtitle_path = ass_path

    await asyncio.to_thread(
        composer.merge_segment,
        video_path=video_only,
        audio_path=Path(tts_result.audio_path),
        output_path=merged,
        subtitle_path=subtitle_path,
        subtitle_safe_area_px=settings.subtitle_safe_area_px,
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
        code = ensure_scene_cleanup(code)

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
                max_chars=settings.subtitle_max_chars,
                wrap_mode=settings.subtitle_wrap_mode,
                font_size=settings.subtitle_font_size,
                margin_l=settings.subtitle_margin_l,
                margin_r=settings.subtitle_margin_r,
                margin_v=settings.subtitle_margin_v,
            )
            subtitle_path = ass_path

        merged = workspace.root / f"merged_{stem}.mp4"
        await asyncio.to_thread(
            composer.merge_segment,
            video_path=video_only,
            audio_path=audio_out,
            output_path=merged,
            subtitle_path=subtitle_path,
            subtitle_safe_area_px=settings.subtitle_safe_area_px,
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
    run_id = new_run_id()
    plan: SolutionPlan | None = None
    script: VideoScript | None = None
    consistency_report = None
    processed: list[ProcessedSegment] = []
    final_path: Path | None = None

    try:
        async with OpenRouterClient(settings) as client:
            _emit_progress(on_progress, {"stage": "solve", "message": "풀이 생성 중"})
            t_solve = time.perf_counter()
            plan = await client.complete_json_model(
                model=settings.model_solve,
                messages=[
                    {"role": "system", "content": SOLVE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": solve_user_prompt(problem.problem_text),
                    },
                ],
                response_model=SolutionPlan,
            )
            logger.info("solve step done in %.2fs", time.perf_counter() - t_solve)

            _emit_progress(
                on_progress, {"stage": "scriptify", "message": "대본 생성 중"}
            )
            t_script = time.perf_counter()
            script, consistency_report = await _scriptify_with_consistency_repair(
                client=client,
                settings=settings,
                plan=plan,
            )
            script = split_script_transition_tails(script)
            logger.info("scriptify step done in %.2fs", time.perf_counter() - t_script)

            if consistency_report and consistency_report.issues:
                logger.warning(
                    "consistency issues found count=%d mode=%s details=%s",
                    len(consistency_report.issues),
                    settings.consistency_mode,
                    json.dumps(
                        [
                            {
                                "severity": i.severity,
                                "code": i.code,
                                "segment_id": i.segment_id,
                                "message": i.message,
                            }
                            for i in consistency_report.issues
                        ],
                        ensure_ascii=False,
                    ),
                )
            if (
                settings.consistency_mode == "error"
                and consistency_report is not None
                and any(i.severity == "error" for i in consistency_report.issues)
            ):
                first_error = next(
                    i for i in consistency_report.issues if i.severity == "error"
                )
                raise ValueError(
                    f"Consistency validation failed: [{first_error.code}] seg={first_error.segment_id} {first_error.message}"
                )

            _emit_progress(on_progress, {"stage": "tts", "message": "TTS 생성 중"})
            tts_results: list[TTSResult] = []
            for seg in script.segments:
                audio_path = workspace.root / f"seg_{seg.id:02d}.wav"
                tts_result = await tts.synthesize(
                    seg.effective_tts_text, output_path=audio_path
                )
                tts_results.append(tts_result)

            chains = group_into_chains(script.segments, tts_results)
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
                        (
                            merged_path,
                            video_only,
                            code,
                            n_try,
                        ) = await _render_standalone_segment(
                            seg=seg,
                            tts_result=tts_res,
                            duration=float(dur),
                            workspace=workspace,
                            registry=registry,
                            client=client,
                            composer=composer,
                            settings=settings,
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

            if settings.scene_bridge_enabled and len(processed) >= 2:
                bridge_specs = _build_bridge_specs_for_processed(
                    processed,
                    merged_paths=merged_paths,
                )
                if bridge_specs:
                    i = 0
                    while i < len(merged_paths) - 1:
                        left_path = merged_paths[i]
                        right_path = merged_paths[i + 1]
                        left_id = next(
                            (
                                ps.segment.id
                                for ps in processed
                                if ps.merged_segment_path is not None
                                and Path(ps.merged_segment_path) == left_path
                            ),
                            None,
                        )
                        right_id = next(
                            (
                                ps.segment.id
                                for ps in processed
                                if ps.merged_segment_path is not None
                                and Path(ps.merged_segment_path) == right_path
                            ),
                            None,
                        )
                        if left_id is None or right_id is None:
                            i += 1
                            continue

                        spec = next(
                            (
                                s
                                for s in bridge_specs
                                if s["from_segment_id"] == left_id
                                and s["to_segment_id"] == right_id
                            ),
                            None,
                        )
                        if spec is None:
                            i += 1
                            continue

                        try:
                            bridge_path, bridge_code = await _render_bridge_segment(
                                workspace=workspace,
                                composer=composer,
                                settings=settings,
                                from_segment_id=left_id,
                                to_segment_id=right_id,
                                from_latex=str(spec["from_latex"]),
                                to_latex=str(spec["to_latex"]),
                                duration=float(spec["duration"]),
                            )
                            merged_paths.insert(i + 1, bridge_path)
                            processed.append(
                                ProcessedSegment(
                                    segment=Segment(
                                        id=100000 + left_id * 100 + right_id,
                                        narration="",
                                        tts_text="",
                                        visual_description="semantic bridge",
                                        visual_type="equation_transform",
                                        visual_params={
                                            "from_latex": str(spec["from_latex"]),
                                            "to_latex": str(spec["to_latex"]),
                                        },
                                        prev_scene_state=None,
                                    ),
                                    tts=TTSResult(
                                        audio_path=workspace.root
                                        / f"bridge_{left_id:02d}_{right_id:02d}.m4a",
                                        duration_seconds=float(spec["duration"]),
                                    ),
                                    manim_code=bridge_code,
                                    video_path=None,
                                    merged_segment_path=bridge_path,
                                )
                            )
                            logger.info(
                                "inserted semantic bridge between seg %d -> %d",
                                left_id,
                                right_id,
                            )
                            i += 2
                        except Exception as exc:
                            logger.warning(
                                "bridge render failed %d->%d, fallback to hard cut: %s",
                                left_id,
                                right_id,
                                exc,
                            )
                            i += 1

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

        if settings.diagnostic_dump:
            dump_dir = dump_generation_diagnostics(
                run_id=run_id,
                problem_text=problem_text,
                workspace=workspace,
                plan=plan,
                script=script,
                consistency_report=consistency_report,
                processed_segments=processed,
                llm_manim_retries=llm_retries_total,
                elapsed_seconds=time.perf_counter() - t0,
                final_path=final_path,
                error=None,
            )
            logger.info("diagnostic dump saved: %s", dump_dir)

        return final_path, workspace
    except Exception as exc:
        if settings.diagnostic_dump:
            dump_dir = dump_generation_diagnostics(
                run_id=run_id,
                problem_text=problem_text,
                workspace=workspace,
                plan=plan,
                script=script,
                consistency_report=consistency_report,
                processed_segments=processed,
                llm_manim_retries=llm_retries_total,
                elapsed_seconds=time.perf_counter() - t0,
                final_path=final_path,
                error=str(exc),
            )
            logger.info("diagnostic dump saved (error): %s", dump_dir)
        if not settings.keep_workspace:
            workspace.cleanup()
        raise
