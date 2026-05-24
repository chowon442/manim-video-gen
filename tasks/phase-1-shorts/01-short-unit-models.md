---
id: "1.01"
phase: 1
title: "ShortUnit 데이터 모델 정의"
spec: "specs/phase-1/01-short-unit-models-and-extract.md"
depends_on: []
blocks: ["1.02", "1.03", "1.04"]
estimate: "S"
status: "todo"
owner: ""
sprint: ""
---

# Task 1.01 — ShortUnit 데이터 모델 정의

> Spec: [`specs/phase-1/01-short-unit-models-and-extract.md`](../../specs/phase-1/01-short-unit-models-and-extract.md)

## 의존성

- 독립 task — 다른 모델에 의존하지 않는 기초 타입 정의

## 사전 준비

- [ ] 기존 `models/script.py`, `models/solution.py` 구조 확인
- [ ] Pydantic v2 사용 여부 확인

## 구현 체크리스트

- [ ] `src/manim_video_gen/models/short.py` 생성
- [ ] `StoryFormat` enum 정의 (application, misconception, stakes, curiosity, pattern)
- [ ] `ApplicationStory` 모델 정의 (story_format, confidence, source, domain, domain_label, scenario, problem_in_domain, concept_bridge, application_result, result_visual, payoff_line)
- [ ] `ShortUnit` 모델 정의 (id, headline, concept_name, core_insight, story, explanation, visual_concept, result_visual_concept, visual_type, difficulty, prerequisites, estimated_seconds)
- [ ] `ShortSeriesPlan` 모델 정의 (title, units[], recommended_order[])
- [ ] `models/__init__.py`에 export 추가

## Definition of Done

- [ ] `python -c "from manim_video_gen.models.short import ShortUnit, ApplicationStory, StoryFormat"` import 성공
- [ ] Pydantic validation 테스트 통과 (필수 필드 누락 시 ValidationError)
- [ ] story_format→tone 매핑 상수 정의 (application→casual 등)

## 리스크 / 메모

- 기존 `models/script.py`의 `Segment` 구체 필드를 확인하여 `ShortUnit`의 visual 관련 필드 타입 일치 여부 검토 필요
