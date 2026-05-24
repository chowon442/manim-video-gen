---
id: "1.02"
phase: 1
title: "Canonical 응용 DB seed"
spec: "specs/phase-1/01-short-unit-models-and-extract.md"
depends_on: ["1.01"]
blocks: ["1.03"]
estimate: "S"
status: "todo"
owner: ""
sprint: ""
---

# Task 1.02 — Canonical 응용 DB seed

> Spec: [`specs/phase-1/01-short-unit-models-and-extract.md`](../../specs/phase-1/01-short-unit-models-and-extract.md)

## 의존성

- 1.01 (ShortUnit 데이터 모델 정의) — `StoryFormat`, `ApplicationStory` 타입 필요

## 사전 준비

- [ ] STEM 교육 분야 대표 개념 20개 리스트업 (p-value, gradient, perlin_noise, budget_constraint 등)

## 구현 체크리스트

- [ ] `src/manim_video_gen/data/canonical_applications.json` 생성 (seed ~20개)
- [ ] 각 항목에 concept_name, domain, scenario, story_format, confidence 필드 포함
- [ ] `pipeline/short_extractor.py`에서 canonical DB를 로드하는 유틸 함수 구현
- [ ] concept_name 기반 fuzzy match 로직 (confidence < 0.6 → misconception/curiosity 강제)

## Definition of Done

- [ ] canonical DB JSON이 20개 이상 항목 포함
- [ ] `p-value` fuzzy match 시 confidence 0.9 이상 반환
- [ ] 존재하지 않는 개념 조회 시 빈 결과 반환 (에러 없음)

## 리스크 / 메모

- DB 항목의 domain/scenario는 LLM으로 보강 가능 — 초기 seed는 수동으로 핵심만
