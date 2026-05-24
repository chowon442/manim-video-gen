"""Tests for short_scriptify module."""

from manim_video_gen.llm.prompts.short_scriptify import (
    LONG_TO_SHORT_VISUAL_MAP,
    _ensure_tts_text,
    default_visual_type,
    normalize_short_visual_type,
    normalize_visual_params,
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
    """Each StoryFormat should map to a short_* visual_type."""
    assert default_visual_type(StoryFormat.APPLICATION) == "short_concept_graph"
    assert default_visual_type(StoryFormat.MISCONCEPTION) == "short_concept_compare"
    assert default_visual_type(StoryFormat.STAKES) == "short_concept_equation"
    assert default_visual_type(StoryFormat.CURIOSITY) == "short_concept_graph"
    assert default_visual_type(StoryFormat.PATTERN) == "short_concept_pattern"


def test_normalize_short_visual_type_already_short():
    """short_* types should be returned as-is."""
    assert normalize_short_visual_type("short_hook") == "short_hook"
    assert normalize_short_visual_type("short_concept_equation") == "short_concept_equation"
    assert normalize_short_visual_type("short_visual_scene") == "short_visual_scene"


def test_normalize_short_visual_type_long_form_mapping():
    """Long-form types should map to short_* equivalents."""
    assert normalize_short_visual_type("equation_write") == "short_concept_equation"
    assert normalize_short_visual_type("equation_transform") == "short_concept_equation"
    assert normalize_short_visual_type("graph_plot") == "short_concept_graph"
    assert normalize_short_visual_type("annotated_equation") == "short_concept_annotated"
    assert normalize_short_visual_type("title_card") == "short_hook"
    assert normalize_short_visual_type("number_line_plot") == "short_concept_number_line"


def test_normalize_short_visual_type_unknown_with_beat():
    """Unknown types should fallback to beat mapping."""
    assert normalize_short_visual_type("unknown_type", beat="hook") == "short_hook"
    assert normalize_short_visual_type("unknown_type", beat="concept") == "short_concept_equation"
    assert normalize_short_visual_type("unknown_type", beat="payoff") == "short_payoff_card"


def test_normalize_short_visual_type_unknown_with_story_format():
    """Unknown types should fallback to story_format mapping."""
    assert normalize_short_visual_type("unknown", story_format=StoryFormat.APPLICATION) == "short_concept_graph"
    assert normalize_short_visual_type("unknown", story_format=StoryFormat.STAKES) == "short_concept_equation"


def test_normalize_short_visual_type_ultimate_fallback():
    """Unknown type with no beat/format should fallback to short_concept_equation."""
    assert normalize_short_visual_type("totally_unknown") == "short_concept_equation"


def test_normalize_visual_params_title_to_headline():
    """title key should be renamed to headline."""
    params = {"title": "제목", "other": "값"}
    result = normalize_visual_params("short_hook", params)
    assert "headline" in result
    assert "title" not in result
    assert result["headline"] == "제목"
    assert result["other"] == "값"


def test_normalize_visual_params_equation_to_latex():
    """equation key should be renamed to latex."""
    params = {"equation": "x^2", "other": "값"}
    result = normalize_visual_params("short_concept_equation", params)
    assert "latex" in result
    assert "equation" not in result
    assert result["latex"] == "x^2"


def test_normalize_visual_params_no_overwrite():
    """Should not overwrite existing headline/latex keys."""
    params = {"title": "제목A", "headline": "제목B"}
    result = normalize_visual_params("short_hook", params)
    assert result["headline"] == "제목B"
    assert "title" in result  # title stays since headline already exists


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
    # beat field should be preserved
    assert script.segments[0].beat == "hook"
    # visual_type should be normalized to short_*
    assert script.segments[0].visual_type == "short_hook"
    # visual_params.title should be renamed to headline
    assert "headline" in script.segments[0].visual_params


def test_parse_short_scriptify_response_normalizes_long_form():
    """Parse function should normalize long-form visual_type to short_*."""
    response = """
    {
        "title": "테스트",
        "segments": [
            {
                "id": 0,
                "beat": "concept",
                "narration": "수식을 보여드릴게요.",
                "tts_text": "",
                "visual_description": "수식 화면",
                "visual_type": "equation_write",
                "visual_params": {"equation": "x^2 + 1 = 0"},
                "prev_scene_state": null
            }
        ]
    }
    """
    script = parse_short_scriptify_response(response)
    assert script.segments[0].visual_type == "short_concept_equation"
    assert "latex" in script.segments[0].visual_params
    assert script.segments[0].visual_params["latex"] == "x^2 + 1 = 0"


def test_parse_short_scriptify_response_applies_ensure_tts():
    """Parse function should apply _ensure_tts_text to empty tts_text."""
    response = """
    {
        "title": "테스트",
        "segments": [
            {
                "id": 0,
                "beat": "hook",
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
                "beat": "hook",
                "narration": "안녕하세요",
                "tts_text": "안녕하세요",
                "visual_description": "화면",
                "visual_type": "short_hook",
                "visual_params": {},
                "prev_scene_state": null
            }
        ]
    }
    ```"""
    script = parse_short_scriptify_response(response)
    assert script.title == "테스트"
