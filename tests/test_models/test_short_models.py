"""Validation tests for ShortUnit data models."""

import pytest
from pydantic import ValidationError

from manim_video_gen.models.short import (
    STORY_FORMAT_TONE_MAP,
    ApplicationStory,
    ShortSeriesPlan,
    ShortUnit,
    StoryFormat,
)


class TestStoryFormat:
    def test_enum_values(self):
        assert StoryFormat.APPLICATION == "application"
        assert StoryFormat.MISCONCEPTION == "misconception"
        assert StoryFormat.STAKES == "stakes"
        assert StoryFormat.CURIOSITY == "curiosity"
        assert StoryFormat.PATTERN == "pattern"

    def test_enum_member_count(self):
        assert len(StoryFormat) == 5


class TestStoryFormatToneMap:
    def test_all_formats_mapped(self):
        for fmt in StoryFormat:
            assert fmt in STORY_FORMAT_TONE_MAP

    def test_mapping_values(self):
        assert STORY_FORMAT_TONE_MAP[StoryFormat.APPLICATION] == "casual"
        assert STORY_FORMAT_TONE_MAP[StoryFormat.MISCONCEPTION] == "dramatic"
        assert STORY_FORMAT_TONE_MAP[StoryFormat.STAKES] == "dramatic"
        assert STORY_FORMAT_TONE_MAP[StoryFormat.CURIOSITY] == "insider"
        assert STORY_FORMAT_TONE_MAP[StoryFormat.PATTERN] == "casual"


class TestApplicationStory:
    def _make_story(self, **overrides):
        data = {
            "story_format": StoryFormat.APPLICATION,
            "confidence": 0.8,
            "source": "document",
            "domain": "finance",
            "scenario": "주식 투자자가 수익률을 계산할 때",
            "problem_in_domain": "복리 계산이 복잡해서 실수하기 쉽다",
            "concept_bridge": "지수함수를 이용하면 정확한 복리를 계산할 수 있다",
            "application_result": "10년 후 투자 수익을 정확히 예측할 수 있다",
            "payoff_line": "수학이 당신의 지갑을 지켜줍니다",
        }
        data.update(overrides)
        return ApplicationStory(**data)

    def test_valid_story(self):
        story = self._make_story()
        assert story.story_format == StoryFormat.APPLICATION
        assert story.confidence == 0.8
        assert story.source == "document"

    def test_optional_fields_default(self):
        story = self._make_story()
        assert story.domain_label == ""
        assert story.result_visual == ""

    def test_confidence_must_be_between_0_and_1(self):
        with pytest.raises(ValidationError):
            self._make_story(confidence=-0.1)
        with pytest.raises(ValidationError):
            self._make_story(confidence=1.1)

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            ApplicationStory(
                story_format=StoryFormat.APPLICATION,
                confidence=0.8,
                # missing source, domain, scenario, etc.
            )


class TestShortUnit:
    def _make_unit(self, **overrides):
        story = ApplicationStory(
            story_format=StoryFormat.APPLICATION,
            confidence=0.9,
            source="document",
            domain="physics",
            scenario="물체를 던질 때",
            problem_in_domain="포물선 궤적을 예측해야 한다",
            concept_bridge="이차함수로 포물선을 모델링할 수 있다",
            application_result="정확한 착지 지점을 예측할 수 있다",
            payoff_line="물리학은 수학의 힘을 빌린다",
        )
        data = {
            "id": "unit-001",
            "headline": "이차함수로 포물선을 이해하자",
            "concept_name": "이차함수",
            "core_insight": "이차함수는 포물선 운동을 설명하는 핵심 도구다",
            "story": story,
            "explanation": "이차함수 y=ax²+bx+c에서 a의 부호에 따라 포물선이 위 또는 아래로 향합니다.",
            "visual_concept": "포물선 그래프가 화면에 그려지는 애니메이션",
            "difficulty": 2,
            "estimated_seconds": 45,
        }
        data.update(overrides)
        return ShortUnit(**data)

    def test_valid_unit(self):
        unit = self._make_unit()
        assert unit.id == "unit-001"
        assert unit.concept_name == "이차함수"
        assert unit.difficulty == 2

    def test_default_fields(self):
        unit = self._make_unit()
        assert unit.result_visual_concept == ""
        assert unit.visual_type == "equation_write"
        assert unit.prerequisites == []

    def test_difficulty_range(self):
        unit = self._make_unit(difficulty=1)
        assert unit.difficulty == 1
        unit = self._make_unit(difficulty=5)
        assert unit.difficulty == 5

    def test_difficulty_out_of_range(self):
        with pytest.raises(ValidationError):
            self._make_unit(difficulty=0)
        with pytest.raises(ValidationError):
            self._make_unit(difficulty=6)

    def test_estimated_seconds_must_be_positive(self):
        with pytest.raises(ValidationError):
            self._make_unit(estimated_seconds=0)

    def test_estimated_seconds_max(self):
        unit = self._make_unit(estimated_seconds=300)
        assert unit.estimated_seconds == 300
        with pytest.raises(ValidationError):
            self._make_unit(estimated_seconds=301)

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            ShortUnit(
                id="x",
                headline="h",
                # missing concept_name, core_insight, story, etc.
            )

    def test_prerequisites_list(self):
        unit = self._make_unit(prerequisites=["linear-equation", "graphing"])
        assert len(unit.prerequisites) == 2


class TestShortSeriesPlan:
    def _make_plan(self, **overrides):
        story = ApplicationStory(
            story_format=StoryFormat.APPLICATION,
            confidence=0.85,
            source="document",
            domain="finance",
            scenario="은행 이자 계산",
            problem_in_domain="단리와 복리의 차이를 모른다",
            concept_bridge="등차수열과 등비수열로 이해할 수 있다",
            application_result="이자 수익을 정확히 비교할 수 있다",
            payoff_line="현명한 선택은 수학에서 시작된다",
        )
        unit = ShortUnit(
            id="u1",
            headline="단리 vs 복리",
            concept_name="수열",
            core_insight="수열은 금융 수학의 기초다",
            story=story,
            explanation="등차수열은 단리, 등비수열은 복리를 설명합니다.",
            visual_concept="수열 그래프 비교",
            difficulty=3,
            estimated_seconds=50,
        )
        data = {
            "title": "금융 수학 시리즈",
            "units": [unit],
            "recommended_order": ["u1"],
        }
        data.update(overrides)
        return ShortSeriesPlan(**data)

    def test_valid_plan(self):
        plan = self._make_plan()
        assert plan.title == "금융 수학 시리즈"
        assert len(plan.units) == 1
        assert plan.recommended_order == ["u1"]

    def test_empty_units_rejected(self):
        with pytest.raises(ValidationError):
            self._make_plan(units=[])

    def test_recommended_order_defaults_empty(self):
        story = ApplicationStory(
            story_format=StoryFormat.PATTERN,
            confidence=0.7,
            source="synthesized",
            domain="math",
            scenario="패턴 찾기",
            problem_in_domain="규칙을 모른다",
            concept_bridge="수열로 규칙을 찾는다",
            application_result="패턴이 보인다",
            payoff_line="패턴은 수학의 언어다",
        )
        unit = ShortUnit(
            id="u2",
            headline="패턴의 비밀",
            concept_name="규칙성",
            core_insight="규칙성은 수학적 사고의 출발점이다",
            story=story,
            explanation="규칙성을 찾는 것이 수학의 첫걸음입니다.",
            visual_concept="패턴 시각화",
            difficulty=1,
            estimated_seconds=30,
        )
        plan = ShortSeriesPlan(title="패턴 시리즈", units=[unit])
        assert plan.recommended_order == []


class TestImportFromInit:
    def test_import_all_models(self):
        from manim_video_gen.models import (
            ApplicationStory,
            ShortSeriesPlan,
            ShortUnit,
            StoryFormat,
        )

        assert StoryFormat is not None
        assert ApplicationStory is not None
        assert ShortUnit is not None
        assert ShortSeriesPlan is not None
