"""Prompts: rewrite base VideoScript into dialogue QA mode."""

from __future__ import annotations

import json

from manim_video_gen.models.script import VideoScript
from manim_video_gen.models.solution import SolutionPlan

_DIALOGUE_REWRITE_SYSTEM_PROMPT = """You rewrite a Korean math video script into a dialogue QA format.

Return ONLY valid JSON (no markdown fences) matching this schema:
{
  "title": string,
  "segments": [
    {
      "id": int (0-based, contiguous),
      "narration": string,
      "tts_text": string,
      "speaker": "teacher" | "student",
      "turn": "explain" | "question" | "answer",
      "visual_description": string,
      "visual_type": string,
      "visual_params": object,
      "prev_scene_state": null | [
        {"latex": string, "position_expr": string}
      ]
    }
  ]
}

Hard requirements:
1) Keep mathematical correctness and final conclusion intact.
2) Keep visual continuity. Do NOT introduce title_card/intro_problem/outro_summary just for dialogue.
3) Insert student question turns and teacher answer turns naturally.
4) Question count MUST equal target_question_count.
5) For every student question turn, add exactly one teacher answer turn immediately after it.
6) `speaker=student` only for question turns; `speaker=teacher` for explain/answer turns.
7) For question turns, narration MUST be plain subtitle-safe Korean (no $ delimiters). tts_text must be phonetic Korean.
8) Keep `visual_type` / `visual_params` compatible with narration and existing rendering templates.
9) Keep patch_ops small and avoid visual_scene unless absolutely necessary.
10) It is okay to freely re-structure segment boundaries as long as hard rules are met.
"""


def dialogue_rewrite_user_prompt(
    *,
    plan: SolutionPlan,
    base_script: VideoScript,
    target_question_count: int,
    slot_windows: list[tuple[float, float]],
) -> str:
    slot_text = ", ".join(f"[{a:.2f},{b:.2f}]" for a, b in slot_windows)
    return (
        "다음 base script를 학생 질문+선생 답변 대화형 스크립트로 재작성하세요.\n"
        f"질문 개수는 반드시 {target_question_count}개여야 합니다.\n"
        f"질문 위치 가이드(전체 진행 비율): {slot_text}\n"
        "질문은 해당 구간 근처에서 자연스럽게 배치하고, 각 질문 직후에 별도 답변 세그먼트를 두세요.\n"
        "수학 핵심(핵심 식/정답/논리)은 유지해야 합니다.\n\n"
        "[Solution plan]\n"
        f"{json.dumps(plan.model_dump(), ensure_ascii=False, indent=2)}\n\n"
        "[Base script]\n"
        f"{json.dumps(base_script.model_dump(), ensure_ascii=False, indent=2)}\n"
    )


def dialogue_rewrite_system_prompt() -> str:
    return _DIALOGUE_REWRITE_SYSTEM_PROMPT
