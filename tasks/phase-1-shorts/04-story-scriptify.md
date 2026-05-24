---
id: "1.04"
phase: 1
title: "StoryScriptify 프롬프트"
spec: "specs/phase-1/01-short-unit-models-and-extract.md"
depends_on: ["1.01"]
blocks: ["1.08"]
estimate: "M"
status: "todo"
owner: ""
sprint: ""
---

# Task 1.04 — StoryScriptify 프롬프트

> Spec: [`specs/phase-1/01-short-unit-models-and-extract.md`](../../specs/phase-1/01-short-unit-models-and-extract.md)

## 의존성

- 1.01 (ShortUnit 데이터 모델 정의) — ShortUnit, ApplicationStory 모델 필요

## 사전 준비

- [ ] 기존 `llm/prompts/scriptify.py` 구조 확인 (intro_problem, outro_summary 패턴)
- [ ] 기존 `models/script.py`의 VideoScript/Segment 필드 확인

## 구현 체크리스트

- [ ] `src/manim_video_gen/llm/prompts/short_scriptify.py` 생성
- [ ] short_scriptify 시스템 프롬프트 작성 (story arc: Hook→Problem→Concept→Application→Payoff)
- [ ] 강의체 패턴 금지 지시 ("배워보겠습니다", "정리하면" 등 차단)
- [ ] delayed labeling 규칙 (첫 segment에 concept_name 미포함)
- [ ] concept_bridge 문장 Concept 직전 필수, payoff_line 마지막 segment 필수
- [ ] segment별 `beat` 태그 지정 (hook/problem/concept/application/payoff)
- [ ] `_ensure_tts_text()` 후처리 함수 — 강의체 → 구어체 변환
- [ ] narration 규칙: 짧은 문장(12~18자), 구어체, 1인칭/2인칭 허용
- [ ] story_format별 기본 visual_type 매핑 로직

## Definition of Done

- [ ] ShortUnit 입력 시 3~5개 segment VideoScript 생성
- [ ] 첫 segment narration에 concept_name 미포함 확인
- [ ] "배워보겠습니다" 등 강의체 패턴 검출 시 구어체로 변환
- [ ] Application/Payoff segment에 application_result/payoff_line 키워드 포함

## 리스크 / 메모

- `_ensure_tts_text()`의 강의체 패턴 사전은 초기에 수동 구축, 점진적 확장
