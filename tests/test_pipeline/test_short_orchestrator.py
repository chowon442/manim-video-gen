"""Tests for short_orchestrator quality guard and topological sort."""

from __future__ import annotations

import pytest

from manim_video_gen.llm.prompts.short_scriptify import _ensure_tts_text
from manim_video_gen.models.short import (
    ApplicationStory,
    ShortSeriesPlan,
    ShortUnit,
    StoryFormat,
)
from manim_video_gen.pipeline.short_orchestrator import (
    load_plan_json,
    save_plan_json,
    select_unit_by_index,
    select_unit_by_topic,
    short_quality,
    topological_sort_units,
)
from manim_video_gen.utils.math_notation import polish_tts_text


def _make_story(**overrides) -> ApplicationStory:
    defaults = {
        "story_format": StoryFormat.APPLICATION,
        "confidence": 0.9,
        "source": "document",
        "domain": "finance",
        "domain_label": "금융",
        "scenario": "친구가 주식 차트를 보며 물었어요",
        "problem_in_domain": "차트가 올라가는지 내려가는지 모르겠어요",
        "concept_bridge": "이때 기울기 개념이 등장합니다",
        "application_result": "기울기로 추세를 판단할 수 있어요",
        "result_visual": "상승 추세 그래프",
        "payoff_line": "기울기로 추세를 읽는 거예요",
    }
    defaults.update(overrides)
    return ApplicationStory(**defaults)


def _make_unit(**overrides) -> ShortUnit:
    defaults = {
        "id": "unit-001",
        "headline": "게임에서 지형을 만들 때 쓰는 특수한 수학 기법",
        "concept_name": "gradient",
        "core_insight": "기울기는 변화율을 나타냅니다",
        "story": _make_story(),
        "explanation": "기울기는 함수의 변화율을 나타내는 개념입니다",
        "visual_concept": "그래프 위의 기울기 화살표",
        "result_visual_concept": "상승 추세",
        "visual_type": "graph_plot",
        "difficulty": 2,
        "prerequisites": [],
        "estimated_seconds": 30,
    }
    defaults.update(overrides)
    return ShortUnit(**defaults)


class TestShortQuality:
    """Tests for short_quality() guard."""

    def test_valid_unit_passes(self):
        unit = _make_unit()
        errors = short_quality(unit)
        assert errors == []

    def test_empty_scenario_fails(self):
        unit = _make_unit(story=_make_story(scenario=""))
        errors = short_quality(unit)
        assert any("scenario" in e for e in errors)

    def test_empty_problem_in_domain_fails(self):
        unit = _make_unit(story=_make_story(problem_in_domain=""))
        errors = short_quality(unit)
        assert any("problem_in_domain" in e for e in errors)

    def test_empty_concept_bridge_fails(self):
        unit = _make_unit(story=_make_story(concept_bridge=""))
        errors = short_quality(unit)
        assert any("concept_bridge" in e for e in errors)

    def test_empty_application_result_fails(self):
        unit = _make_unit(story=_make_story(application_result=""))
        errors = short_quality(unit)
        assert any("application_result" in e for e in errors)

    def test_empty_payoff_line_fails(self):
        unit = _make_unit(story=_make_story(payoff_line=""))
        errors = short_quality(unit)
        assert any("payoff_line" in e for e in errors)

    def test_headline_with_concept_name_fails(self):
        unit = _make_unit(headline="Gradient란 무엇인가?")
        errors = short_quality(unit)
        assert any("delayed labeling" in e for e in errors)

    def test_headline_without_concept_name_passes(self):
        unit = _make_unit(headline="게임에서 지형을 만들 때 쓰는 특수한 수학 기법")
        errors = short_quality(unit)
        assert not any("delayed labeling" in e for e in errors)

    def test_estimated_seconds_too_short_fails(self):
        unit = _make_unit(estimated_seconds=10)
        errors = short_quality(unit)
        assert any("estimated_seconds" in e for e in errors)

    def test_estimated_seconds_too_long_fails(self):
        unit = _make_unit(estimated_seconds=90)
        errors = short_quality(unit)
        assert any("estimated_seconds" in e for e in errors)

    def test_estimated_seconds_boundary_15_passes(self):
        unit = _make_unit(estimated_seconds=15)
        errors = short_quality(unit)
        assert not any("estimated_seconds" in e for e in errors)

    def test_estimated_seconds_boundary_60_passes(self):
        unit = _make_unit(estimated_seconds=60)
        errors = short_quality(unit)
        assert not any("estimated_seconds" in e for e in errors)

    def test_korean_payoff_with_particle_variant_passes(self):
        """Korean payoff referencing app_result with different particles should pass."""
        unit = _make_unit(
            story=_make_story(
                application_result="p-value가 0.014(1.4%)로 유의미합니다",
                payoff_line="p-value 0.014로 유의미해요",
            )
        )
        errors = short_quality(unit)
        assert not any("payoff_line" in e for e in errors)

    def test_korean_payoff_semantic_connection_passes(self):
        """Korean payoff with same content words but different endings should pass."""
        unit = _make_unit(
            story=_make_story(
                application_result="기울기로 추세를 판단할 수 있어요",
                payoff_line="기울기로 추세를 읽는 거예요",
            )
        )
        errors = short_quality(unit)
        assert not any("payoff_line" in e for e in errors)

    def test_korean_payoff_unrelated_fails(self):
        """Korean payoff completely unrelated to app_result should fail."""
        unit = _make_unit(
            story=_make_story(
                application_result="기울기로 추세를 판단할 수 있어요",
                payoff_line="오늘 날씨가 좋네요",
            )
        )
        errors = short_quality(unit)
        assert any("payoff_line" in e for e in errors)


class TestTopologicalSort:
    """Tests for topological_sort_units()."""

    def test_empty_list(self):
        assert topological_sort_units([]) == []

    def test_single_unit(self):
        unit = _make_unit()
        result = topological_sort_units([unit])
        assert len(result) == 1
        assert result[0].concept_name == "gradient"

    def test_no_prerequisites_preserves_order(self):
        u1 = _make_unit(id="u1", concept_name="A", prerequisites=[])
        u2 = _make_unit(id="u2", concept_name="B", prerequisites=[])
        u3 = _make_unit(id="u3", concept_name="C", prerequisites=[])
        result = topological_sort_units([u1, u2, u3])
        names = [u.concept_name for u in result]
        assert "A" in names
        assert "B" in names
        assert "C" in names

    def test_prerequisite_ordering(self):
        u1 = _make_unit(id="u1", concept_name="B", prerequisites=["A"])
        u2 = _make_unit(id="u2", concept_name="A", prerequisites=[])
        result = topological_sort_units([u1, u2])
        names = [u.concept_name for u in result]
        assert names.index("A") < names.index("B")

    def test_cycle_falls_back_to_original_order(self):
        u1 = _make_unit(id="u1", concept_name="A", prerequisites=["B"])
        u2 = _make_unit(id="u2", concept_name="B", prerequisites=["A"])
        result = topological_sort_units([u1, u2])
        assert len(result) == 2
        # Fallback: original order preserved
        assert result[0].concept_name == "A"
        assert result[1].concept_name == "B"

    def test_unknown_prerequisite_ignored(self):
        u1 = _make_unit(id="u1", concept_name="A", prerequisites=["UNKNOWN"])
        result = topological_sort_units([u1])
        assert len(result) == 1


class TestSelectUnit:
    """Tests for select_unit_by_index and select_unit_by_topic."""

    def test_select_by_index_first(self):
        plan = ShortSeriesPlan(
            title="Test",
            units=[
                _make_unit(id="u1", concept_name="A"),
                _make_unit(id="u2", concept_name="B"),
            ],
        )
        unit = select_unit_by_index(plan, 0)
        assert unit.concept_name == "A"

    def test_select_by_index_clamps(self):
        plan = ShortSeriesPlan(
            title="Test",
            units=[
                _make_unit(id="u1", concept_name="A"),
                _make_unit(id="u2", concept_name="B"),
            ],
        )
        unit = select_unit_by_index(plan, 99)
        assert unit.concept_name == "B"

    def test_select_by_index_negative_clamps_to_zero(self):
        plan = ShortSeriesPlan(
            title="Test",
            units=[
                _make_unit(id="u1", concept_name="A"),
            ],
        )
        unit = select_unit_by_index(plan, -5)
        assert unit.concept_name == "A"


class TestPlanJson:
    """Tests for save_plan_json and load_plan_json roundtrip."""

    def test_roundtrip(self, tmp_path):
        plan = ShortSeriesPlan(
            title="Test Series",
            units=[_make_unit()],
            recommended_order=["unit-001"],
        )
        path = tmp_path / "plan.json"
        save_plan_json(plan, path)
        loaded = load_plan_json(path)
        assert loaded.title == "Test Series"
        assert len(loaded.units) == 1
        assert loaded.units[0].concept_name == "gradient"
        assert loaded.recommended_order == ["unit-001"]


class TestShortPolishTtsText:
    """Tests that polish_tts_text and _ensure_tts_text work for short pipeline."""

    def test_polish_converts_math_symbols(self):
        src = "x² + 6x + 9 = 0"
        out = polish_tts_text(src)
        assert "엑스" in out
        assert "제곱" in out
        assert "더하기" in out

    def test_polish_strips_spoken_parenthesis(self):
        src = "괄호 열기 엑스 괄호 닫기 제곱"
        out = polish_tts_text(src)
        assert "괄호" not in out

    def test_ensure_tts_text_converts_lecture_patterns(self):
        assert _ensure_tts_text("배워보겠습니다") == "알아볼게요"
        assert _ensure_tts_text("학습하겠습니다") == "배울게요"
        assert _ensure_tts_text("풀어보겠습니다") == "풀어볼게요"
        assert _ensure_tts_text("설명드리겠습니다") == "설명할게요"

    def test_ensure_tts_text_preserves_conversational(self):
        src = "이 함수의 기울기를 알아볼게요"
        assert _ensure_tts_text(src) == src

    def test_ensure_tts_text_applied_to_empty_tts_text(self):
        """When LLM omits tts_text, narration should be converted."""
        narration = "이차방정식의 근의 공식을 배워보겠습니다"
        result = _ensure_tts_text(narration)
        assert result == "이차방정식의 근의 공식을 알아볼게요"

    def test_ensure_tts_text_applied_to_existing_tts_text(self):
        """When LLM provides tts_text with lecture patterns, convert it."""
        tts_text = "이 함수를 설명드리겠습니다"
        result = _ensure_tts_text(tts_text)
        assert result == "이 함수를 설명할게요"
