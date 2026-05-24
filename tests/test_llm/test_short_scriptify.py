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
    assert _ensure_tts_text("설명드리겠습니다") == "설명할게요"


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
    response = """
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
    """
    script = parse_short_scriptify_response(response)
    assert script.title == "테스트 비디오"
    assert len(script.segments) == 1
    assert script.segments[0].narration == "친구가 주식 차트를 보며 물었어요."


def test_parse_short_scriptify_response_applies_ensure_tts():
    """Parse function should apply _ensure_tts_text to empty tts_text."""
    response = """
    {
        "title": "테스트",
        "segments": [
            {
                "id": 0,
                "narration": "이 개념을 배워보겠습니다.",
                "tts_text": "",
                "visual_description": "화면",
                "visual_type": "title_card",
                "visual_params": {},
                "prev_scene_state": null
            }
        ]
    }
    """
    script = parse_short_scriptify_response(response)
    assert "알아볼게요" in script.segments[0].tts_text


def test_parse_short_scriptify_response_with_markdown_fences():
    """Parse function should handle markdown-wrapped JSON."""
    response = """```json
    {
        "title": "테스트",
        "segments": [
            {
                "id": 0,
                "narration": "안녕하세요",
                "tts_text": "안녕하세요",
                "visual_description": "화면",
                "visual_type": "title_card",
                "visual_params": {},
                "prev_scene_state": null
            }
        ]
    }
    ```"""
    script = parse_short_scriptify_response(response)
    assert script.title == "테스트"
