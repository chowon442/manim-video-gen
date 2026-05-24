"""Prompts: ShortUnit -> VideoScript JSON (5-beat story arc)."""

from __future__ import annotations

import json
import re

from manim_video_gen.config import Settings
from manim_video_gen.models.script import VideoScript
from manim_video_gen.models.short import ShortUnit, StoryFormat

SHORT_SCRIPTIFY_SYSTEM_PROMPT = """You are a script writer for a Korean math short video (60 seconds or less).
Return ONLY valid JSON (no markdown fences) matching this schema:
{
  "title": string,
  "segments": [
    {
      "id": int (0-based),
      "beat": string (one of: "hook", "problem", "concept", "application", "payoff"),
      "narration": string (readable Korean subtitle text),
      "tts_text": string (fully phonetic Korean for TTS),
      "visual_description": string (what should appear on screen),
      "visual_type": string,
      "visual_params": object,
      "prev_scene_state": null | [{"latex": string, "position_expr": string}]
    }
  ]
}

In JSON string values, every LaTeX backslash must be doubled (e.g. \\\\frac, \\\\quad).

## 5-Beat Story Arc Structure

Your script MUST follow this arc. Each beat maps to specific content:

1. **Hook** (0-3s, 1 segment)
   - Content: Use the `scenario` field from the story
   - Goal: Grab attention with a concrete situation
   - NEVER mention the concept_name here (delayed labeling)
   - visual_type: title_card or visual_scene

2. **Problem** (3-10s, 1 segment)
   - Content: Use the `problem_in_domain` field
   - Goal: Show what goes wrong or what needs solving
   - visual_type: equation_write or annotated_equation

3. **Concept** (10-25s, 1-2 segments)
   - Content: Use `concept_bridge` + `explanation` fields
   - Goal: Reveal the math concept as the needed tool
   - concept_bridge MUST appear in the first Concept segment
   - visual_type: equation_write, equation_transform, or graph_plot

4. **Application** (5-15s, 1 segment)
   - Content: Use the `application_result` field
   - Goal: Show the concept solving the problem
   - visual_type: graph_plot, equation_transform, or visual_scene

5. **Payoff** (3-5s, 1 segment)
   - Content: Use the `payoff_line` field
   - Goal: Close with a line that ties back to the hook
   - payoff_line MUST appear in narration
   - visual_type: highlight_result or title_card

Total segments: 3-5 (you may split Concept into 2 segments if needed)

## Delayed Labeling (CRITICAL)

- The concept_name MUST NOT appear in Hook or Problem segments
- First mention of the concept name happens in the Concept beat
- Use the concept_bridge to naturally introduce the name

## Narration Style (CRITICAL)

- Conversational Korean (구어체), NOT lecture-style (강의체)
- Short sentences: 12-18 characters per sentence
- Use 1st/2nd person: "나는", "당신은", "우리가"
- FORBIDDEN patterns (will be caught by post-processing):
  - "배워보겠습니다" -> use "알아볼게요"
  - "학습하겠습니다" -> use "배울게요"
  - "풀어보겠습니다" -> use "풀어볼게요"
  - "설명드리겠습니다" -> use "설명할게요"

## tts_text Rules

- Every symbol spelled out in Korean phonetics
- x -> "엑스", y -> "와이", z -> "제트"
- x^2 -> "엑스 제곱", + -> "더하기", = -> "은/는"
- NEVER leave raw LaTeX or $ in tts_text

## visual_type Mapping by story_format

Default visual_type based on story_format (you may override if content requires):
- application -> graph_plot
- misconception -> annotated_equation
- stakes -> equation_write
- curiosity -> visual_scene
- pattern -> graph_plot

## Available visual_type catalog

1) equation_write - one equation appears with Write animation
2) equation_transform - equation A becomes equation B
3) equation_steps - multiple equations stacked
4) equation_derivation - continuous derivation board
5) graph_plot - coordinate axes and function graph
6) highlight_result - equation with surrounding rectangle
7) title_card - title and optional subtitle
8) intro_problem - problem statement (opening)
9) outro_summary - short closing summary
10) number_line_plot - horizontal NumberLine
11) annotated_equation - MathTex with Brace labels
12) visual_scene - custom Manim code generation

## Good vs Bad Examples

[GOOD] Hook: "친구가 주식 차트를 보며 물었어요."
[GOOD] Concept: "이때 이차방정식의 근의 공식이 등장합니다."
[BAD] Hook: "오늘 이차방정식의 근의 공식을 배워보겠습니다." (concept_name in Hook, lecture style)

[GOOD] tts_text: "엑스 제곱 더하기 육엑스 더하기 구는 영"
[BAD] tts_text: "x^2 + 6x + 9 = 0" (raw LaTeX)
"""

# Lecture-style patterns to conversational Korean
_LECTURE_PATTERNS: list[tuple[str, str]] = [
    (r"배워보겠습니다", "알아볼게요"),
    (r"학습하겠습니다", "배울게요"),
    (r"풀어보겠습니다", "풀어볼게요"),
    (r"설명드리겠습니다", "설명할게요"),
    (r"살펴보겠습니다", "살펴볼게요"),
    (r"확인해 보겠습니다", "확인해 볼게요"),
    (r"이해해 보겠습니다", "이해해 볼게요"),
    (r"알아보겠습니다", "알아볼게요"),
    (r"진행하겠습니다", "진행할게요"),
    (r"시작하겠습니다", "시작할게요"),
]

# Default visual_type for each story_format
STORY_FORMAT_VISUAL_MAP: dict[StoryFormat, str] = {
    StoryFormat.APPLICATION: "graph_plot",
    StoryFormat.MISCONCEPTION: "annotated_equation",
    StoryFormat.STAKES: "equation_write",
    StoryFormat.CURIOSITY: "visual_scene",
    StoryFormat.PATTERN: "graph_plot",
}


def short_scriptify_system_prompt(settings: Settings) -> str:
    """Return the short scriptify system prompt."""
    return SHORT_SCRIPTIFY_SYSTEM_PROMPT


def short_scriptify_user_prompt(unit: ShortUnit) -> str:
    """Build user prompt from ShortUnit data."""
    payload = {
        "headline": unit.headline,
        "concept_name": unit.concept_name,
        "core_insight": unit.core_insight,
        "story": unit.story.model_dump(),
        "explanation": unit.explanation,
        "visual_concept": unit.visual_concept,
        "difficulty": unit.difficulty,
        "estimated_seconds": unit.estimated_seconds,
    }
    return (
        "다음 ShortUnit을 5-beat story arc 구조의 영상 세그먼트로 나누어 JSON으로 만드세요.\n"
        "나레이션은 한국어 구어체로 쓰고, 각 세그먼트에서 말하는 내용과 화면이 반드시 일치해야 합니다.\n"
        "첫 세그먼트(Hook)에는 concept_name을 절대 포함하지 마세요.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
    )


def _ensure_tts_text(narration: str) -> str:
    """Convert lecture-style Korean to conversational style for TTS.

    Detects 강의체 patterns and replaces with 구어체 equivalents.
    Returns the converted text.
    """
    result = narration
    for pattern, replacement in _LECTURE_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


def default_visual_type(story_format: StoryFormat) -> str:
    """Get default visual_type for a story_format."""
    return STORY_FORMAT_VISUAL_MAP.get(story_format, "equation_write")


def parse_short_scriptify_response(response: str) -> VideoScript:
    """Parse LLM response into VideoScript.

    Handles JSON extraction and validation.
    """
    # Strip markdown fences if present
    text = response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    data = json.loads(text)

    # Apply _ensure_tts_text to all segments
    for seg in data.get("segments", []):
        if not seg.get("tts_text"):
            seg["tts_text"] = _ensure_tts_text(seg.get("narration", ""))
        else:
            seg["tts_text"] = _ensure_tts_text(seg["tts_text"])

    return VideoScript(**data)
