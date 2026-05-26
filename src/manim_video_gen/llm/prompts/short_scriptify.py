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

## visual_description Guidelines (CRITICAL)

`visual_description` is the ONLY channel that tells the video generator what Manim objects to draw.
Write it as a concrete, visual instruction — NOT a summary of the narration.

[GOOD] "A vertical 9:16 frame. Top: a red Circle that grows from center. Middle: the text '오차항' in bold yellow. Bottom: a small MathTex epsilon fades in."
[BAD] "Explain the error term concept" (this is narration, not visual)

- Mention specific Manim objects: Circle, Dot, Arrow, Axes, NumberLine, Brace, VGroup, MathTex
- Mention colors: RED, BLUE, YELLOW, GREEN
- Mention animation: FadeIn, Write, Create, Transform, GrowFromCenter
- Keep it under 80 words but be specific.

## visual_params Guidelines (CRITICAL)

`visual_params` provides exact data for the chosen template. If left empty, the system FALLS BACK to copying the narration text into the scene, creating an ugly DUPLICATE (same text as subtitle AND scene).

You MUST fill `visual_params` with keys that DIFFER from the narration text.

### Beat templates — required keys
- short_hook:    {"headline": "짧은 훅 텍스트 (12-18자, 자막과 다르게)"}
- short_before:  {"text": "문제 상황 요약 (자막과 다르게, 10-15자)"}
- short_after:   {"text": "결과 요약 (자막과 다르게, 10-15자)"}
- short_payoff_card: {"headline": "한 줄 결론 (자막과 다르게, 12-18자)"}
- short_cta:     {"text": "구독 / 다음 영상 문구"}

### Concept templates — required keys
- short_concept_equation: {"latex": "수식 LaTeX", "font_size": 48}
- short_concept_graph:    {"func": "lambda x: x**2", "x_min": -3, "x_max": 3, "color": "BLUE"}
- short_concept_number_line: {"value": 2.5, "label": "임계값"}
- short_concept_annotated: {"latex": "수식", "annotation": "한글 설명"}
- short_concept_compare:   {"left": "틀린 수식", "right": "맞는 수식"}
- short_concept_pattern:   {"items": ["케이스1", "케이스2", "케이스3"]}

### Domain templates — required keys
- short_domain_icon: {"label": "라벨", "shape": "circle"}
- short_stat_chart:  {"values": [10, 20, 30], "labels": ["A", "B", "C"]}
- short_flow_arrow:  {"steps": ["단계1", "단계2", "단계3"]}

### LLM-only (not in registry)
- short_visual_scene: {"prompt": "(optional) extra hint for LLM"}
  → Use this when the scene needs custom animation (moving dots, multiple shapes, transforms).
  → RECOMMENDED for Concept and Application beats if the description is rich.
  → Max 2 per unit.

## Avoid Narration Duplication (CRITICAL)

If you leave visual_params empty or set text/headline equal to narration, the viewer sees THE SAME TEXT twice:
- Once as a burned-in subtitle at the bottom
- Once as a large text object in the middle of the screen

This looks amateur. Always make the on-screen text SHORTER, BOLDER, and DIFFERENT from the full narration sentence.

Example:
- narration: "소득이 똑같은 두 집이 있어요. 그런데 식비 지출은 왜 다를까요?"
- visual_params.headline (for short_hook): "같은 소득, 다른 지출"

## Beat → visual_type Freedom

You are NOT locked to defaults. Pick the type that best serves the content:
- Hook: short_hook OR short_visual_scene (if dramatic icon/animation fits better)
- Problem: short_before OR short_concept_compare (if misconception) OR short_domain_icon
- Concept: short_concept_equation, short_concept_graph, short_concept_annotated, short_concept_pattern, OR short_visual_scene
- Application: short_after, short_concept_graph, short_flow_arrow, OR short_visual_scene
- Payoff: short_payoff_card OR short_visual_scene (if celebratory animation fits)

## Available visual_type catalog (short_* only)

### Beat templates (5)
1) short_hook - Hook: question text + simple icon/silhouette
2) short_before - Application Problem: before state
3) short_after - Application Payoff: after result (sequential)
4) short_payoff_card - Non-application Payoff: one-line conclusion + highlight
5) short_cta - Optional: "Part 2" / series link

### Concept templates (6)
6) short_concept_equation - vertical center, 1-2 line equation large
7) short_concept_graph - vertical axes, curve/point 1 focal
8) short_concept_number_line - vertical number line, interval, point
9) short_concept_annotated - equation + brace annotation 1
10) short_concept_compare - misconception: wrong vs correct 2 lines
11) short_concept_pattern - pattern format: 3 cases → arrow → concept

### Domain templates (3)
12) short_domain_icon - domain atmosphere (game/medical/finance silhouette)
13) short_stat_chart - bar/distribution simple chart (p-value, α etc.)
14) short_flow_arrow - procedure 2-3 step arrows (stakes, curiosity)

### LLM-only (not in registry)
15) short_visual_scene - custom 9:16 Manim code generation

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
    StoryFormat.APPLICATION: "short_concept_graph",
    StoryFormat.MISCONCEPTION: "short_concept_compare",
    StoryFormat.STAKES: "short_concept_equation",
    StoryFormat.CURIOSITY: "short_concept_graph",
    StoryFormat.PATTERN: "short_concept_pattern",
}

# Beat → default visual_type mapping
BEAT_VISUAL_MAP: dict[str, str] = {
    "hook": "short_hook",
    "problem": "short_before",
    "concept": "short_concept_equation",
    "application": "short_after",
    "payoff": "short_payoff_card",
}

# Long-form → short_* visual_type mapping for normalize
LONG_TO_SHORT_VISUAL_MAP: dict[str, str] = {
    "equation_write": "short_concept_equation",
    "equation_transform": "short_concept_equation",
    "equation_steps": "short_concept_equation",
    "equation_derivation": "short_concept_equation",
    "graph_plot": "short_concept_graph",
    "highlight_result": "short_concept_equation",
    "title_card": "short_hook",
    "intro_problem": "short_hook",
    "outro_summary": "short_payoff_card",
    "number_line_plot": "short_concept_number_line",
    "annotated_equation": "short_concept_annotated",
    "visual_scene": "short_visual_scene",
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
    return STORY_FORMAT_VISUAL_MAP.get(story_format, "short_concept_equation")


def normalize_visual_params(visual_type: str, params: dict) -> dict:
    """Normalize visual_params keys for short_* types."""
    if not params:
        return params

    normalized = dict(params)

    # title → headline
    if "title" in normalized and "headline" not in normalized:
        normalized["headline"] = normalized.pop("title")

    # equation → latex
    if "equation" in normalized and "latex" not in normalized:
        normalized["latex"] = normalized.pop("equation")

    return normalized


def normalize_short_visual_type(
    visual_type: str,
    beat: str | None = None,
    story_format: StoryFormat | None = None,
) -> str:
    """Normalize visual_type to short_* format.

    1. If already short_* → return as-is
    2. If long-form type → map to short_*
    3. If unknown → use beat mapping, then story_format fallback
    """
    # Already short_* type
    if visual_type.startswith("short_"):
        return visual_type

    # Long-form → short mapping
    if visual_type in LONG_TO_SHORT_VISUAL_MAP:
        return LONG_TO_SHORT_VISUAL_MAP[visual_type]

    # Fallback: use beat mapping
    if beat and beat in BEAT_VISUAL_MAP:
        return BEAT_VISUAL_MAP[beat]

    # Fallback: use story_format
    if story_format:
        return default_visual_type(story_format)

    # Ultimate fallback
    return "short_concept_equation"


def parse_short_scriptify_response(response: str) -> VideoScript:
    """Parse LLM response into VideoScript.

    Handles JSON extraction and validation.
    Normalizes visual_type to short_* format.
    """
    # Strip markdown fences if present
    text = response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    data = json.loads(text)

    # Apply _ensure_tts_text and normalize visual_type
    for seg in data.get("segments", []):
        if not seg.get("tts_text"):
            seg["tts_text"] = _ensure_tts_text(seg.get("narration", ""))
        else:
            seg["tts_text"] = _ensure_tts_text(seg["tts_text"])

        # Normalize visual_type to short_*
        beat = seg.get("beat")
        vt = seg.get("visual_type", "")
        seg["visual_type"] = normalize_short_visual_type(vt, beat)

        # Normalize visual_params keys
        if "visual_params" in seg:
            seg["visual_params"] = normalize_visual_params(
                seg["visual_type"], seg["visual_params"]
            )

    return VideoScript(**data)
