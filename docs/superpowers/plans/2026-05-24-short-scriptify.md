# Short Scriptify Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `short_scriptify.py` that converts ShortUnit to VideoScript using a 5-beat story arc structure.

**Architecture:** Follow existing `scriptify.py` pattern with system prompt + user prompt functions + post-processing. The 5-beat arc maps ApplicationStory fields to VideoScript segments.

**Tech Stack:** Python, Pydantic, existing manim_video_gen models

---

## File Structure

- Create: `src/manim_video_gen/llm/prompts/short_scriptify.py`
- Modify: `src/manim_video_gen/llm/prompts/__init__.py` (add exports)
- Test: `tests/llm/prompts/test_short_scriptify.py`

## Tasks

### Task 1: Create short_scriptify.py with system prompt

**Files:**
- Create: `src/manim_video_gen/llm/prompts/short_scriptify.py`

- [ ] **Step 1: Create the file with system prompt**

```python
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
  - "배워보겠습니다" → use "알아볼게요"
  - "정리하면" → use "정리하면" (ok in context)
  - "풀어보겠습니다" → use "풀어볼게요"
  - "학습하겠습니다" → use "배울게요"
  - "설명드리겠습니다" → use "설명할게요"

## tts_text Rules

- Every symbol spelled out in Korean phonetics
- x → "엑스", y → "와이", z → "제트"
- x² → "엑스 제곱", + → "더하기", = → "은/는"
- NEVER leave raw LaTeX or $ in tts_text

## visual_type Mapping by story_format

Default visual_type based on story_format (you may override if content requires):
- application → graph_plot
- misconception → annotated_equation
- stakes → equation_write
- curiosity → visual_scene
- pattern → graph_plot

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
[BAD] tts_text: "x² + 6x + 9 = 0" (raw LaTeX)
"""
```

- [ ] **Step 2: Add user prompt function**

```python
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
```

- [ ] **Step 3: Add _ensure_tts_text post-processing**

```python
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


def _ensure_tts_text(narration: str) -> str:
    """Convert lecture-style Korean to conversational style for TTS.

    Detects 강의체 patterns and replaces with 구어체 equivalents.
    Returns the converted text.
    """
    result = narration
    for pattern, replacement in _LECTURE_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result
```

- [ ] **Step 4: Add story_format to visual_type mapping**

```python
STORY_FORMAT_VISUAL_MAP: dict[StoryFormat, str] = {
    StoryFormat.APPLICATION: "graph_plot",
    StoryFormat.MISCONCEPTION: "annotated_equation",
    StoryFormat.STAKES: "equation_write",
    StoryFormat.CURIOSITY: "visual_scene",
    StoryFormat.PATTERN: "graph_plot",
}


def default_visual_type(story_format: StoryFormat) -> str:
    """Get default visual_type for a story_format."""
    return STORY_FORMAT_VISUAL_MAP.get(story_format, "equation_write")
```

- [ ] **Step 5: Add parse function**

```python
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
```

### Task 2: Update __init__.py exports

**Files:**
- Modify: `src/manim_video_gen/llm/prompts/__init__.py`

- [ ] **Step 1: Add imports**

Add to imports:
```python
from manim_video_gen.llm.prompts.short_scriptify import (
    SHORT_SCRIPTIFY_SYSTEM_PROMPT,
    short_scriptify_system_prompt,
    short_scriptify_user_prompt,
    parse_short_scriptify_response,
    default_visual_type,
    _ensure_tts_text,
)
```

Add to `__all__`:
```python
"SHORT_SCRIPTIFY_SYSTEM_PROMPT",
"short_scriptify_system_prompt",
"short_scriptify_user_prompt",
"parse_short_scriptify_response",
"default_visual_type",
"_ensure_tts_text",
```

### Task 3: Write tests

**Files:**
- Create: `tests/llm/prompts/test_short_scriptify.py`

- [ ] **Step 1: Write test for _ensure_tts_text**

```python
"""Tests for short_scriptify module."""

from manim_video_gen.llm.prompts.short_scriptify import (
    _ensure_tts_text,
    default_visual_type,
    parse_short_scriptify_response,
    short_scriptify_user_prompt,
)
from manim_video_gen.models.short import ApplicationStory, ShortUnit, StoryFormat


def test_ensure_tts_text_converts_lecture_patterns():
    """Lecture-style patterns should be converted to conversational Korean."""
    assert _ensure_tts_text("배워보겠습니다") == "알아볼게요"
    assert _ensure_tts_text("이 개념을 학습하겠습니다") == "이 개념을 배울게요"
    assert _ensure_tts_text("문제를 풀어보겠습니다") == "문제를 풀어볼게요"


def test_ensure_tts_text_preserves_conversational():
    """Conversational Korean should remain unchanged."""
    text = "이건 정말 신기해요"
    assert _ensure_tts_text(text) == text


def test_default_visual_type_mapping():
    """Each StoryFormat should map to a visual_type."""
    assert default_visual_type(StoryFormat.APPLICATION) == "graph_plot"
    assert default_visual_type(StoryFormat.MISCONCEPTION) == "annotated_equation"
    assert default_visual_type(StoryFormat.STAKES) == "equation_write"
    assert default_visual_type(StoryFormat.CURIOSITY) == "visual_scene"
    assert default_visual_type(StoryFormat.PATTERN) == "graph_plot"


def test_short_scriptify_user_prompt_includes_fields():
    """User prompt should contain ShortUnit fields."""
    unit = ShortUnit(
        id="test-1",
        headline="주식으로 배우는 이차방정식",
        concept_name="이차방정식의 근의 공식",
        core_insight="차트에서 극값을 찾는 핵심 도구",
        story=ApplicationStory(
            story_format=StoryFormat.APPLICATION,
            confidence=0.9,
            source="document",
            domain="finance",
            scenario="친구가 주식 차트를 보며 물었어요",
            problem_in_domain="차트의 고점과 저점을 어떻게 찾지?",
            concept_bridge="이때 이차방정식의 근의 공식이 등장합니다",
            application_result="공식을 적용하니 고점이 정확히 계산됐어요",
            payoff_line="수학이 돈을 벌어다 줄 수도 있죠",
        ),
        explanation="이차방정식의 근의 공식은 ax²+bx+c=0의 해를 구하는 공식입니다",
        visual_concept="주식 차트 위에 포물선 그래프 겹쳐서 표시",
        difficulty=3,
        estimated_seconds=45,
    )
    prompt = short_scriptify_user_prompt(unit)
    assert "주식으로 배우는 이차방정식" in prompt
    assert "이차방정식의 근의 공식" in prompt
    assert "친구가 주식 차트를 보며 물었어요" in prompt


def test_parse_short_scriptify_response():
    """Parse function should extract VideoScript from JSON response."""
    response = '''
    {
        "title": "테스트 비디오",
        "segments": [
            {
                "id": 0,
                "beat": "hook",
                "narration": "친구가 주식 차트를 보며 물었어요.",
                "tts_text": "",
                "visual_description": "주식 차트 화면",
                "visual_type": "title_card",
                "visual_params": {"title": "주식 차트"},
                "prev_scene_state": null
            }
        ]
    }
    '''
    script = parse_short_scriptify_response(response)
    assert script.title == "테스트 비디오"
    assert len(script.segments) == 1
    assert script.segments[0].beat == "hook"
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/llm/prompts/test_short_scriptify.py -v`
Expected: All tests PASS

## Self-Review

1. **Spec coverage:** All requirements from task 1.04 are covered:
   - ✅ short_scriptify.py 생성
   - ✅ 시스템 프롬프트 (5-beat story arc)
   - ✅ 강의체 패턴 금지 지시
   - ✅ delayed labeling 규칙
   - ✅ concept_bridge/payoff_line 필수
   - ✅ beat 태그 지정
   - ✅ _ensure_tts_text() 후처리
   - ✅ narration 규칙 (12-18자, 구어체)
   - ✅ story_format별 visual_type 매핑

2. **Placeholder scan:** No TBD/TODO found.

3. **Type consistency:** All types match existing models (ShortUnit, VideoScript, StoryFormat).
