---
id: "1.03"
phase: 1
title: "Extract 프롬프트 + short_extractor"
spec: "specs/phase-1/01-short-unit-models-and-extract.md"
depends_on: ["1.01", "1.02"]
blocks: ["1.08"]
estimate: "M"
status: "todo"
owner: ""
sprint: ""
---

# Task 1.03 — Extract 프롬프트 + short_extractor

> Spec: [`specs/phase-1/01-short-unit-models-and-extract.md`](../../specs/phase-1/01-short-unit-models-and-extract.md)

## 의존성

- 1.01 (ShortUnit 데이터 모델 정의) — ShortSeriesPlan 모델 필요
- 1.02 (Canonical 응용 DB) — confidence 기반 format 선택 로직 필요

## 사전 준비

- [ ] 기존 `llm/prompts/solve.py` 프롬프트 패턴 확인
- [ ] `MANIM_VIDEO_GEN_MODEL_EXTRACT` env 설정 확인

## 구현 체크리스트

- [ ] `src/manim_video_gen/llm/prompts/extract_shorts.py` 생성
- [ ] extract 시스템 프롬프트 작성 (ShortUnit 추출 지시, headline 생성 규칙, story_format 선택 지침)
- [ ] extract 유저 프롬프트 함수 (`extract_user_prompt(content: str) -> str`)
- [ ] `src/manim_video_gen/pipeline/short_extractor.py` 생성
- [ ] Extract 실행 + JSON 파싱 + ShortSeriesPlan 생성 로직
- [ ] 로컬 필터: `estimated_seconds > 60` → 분할 제안/경고
- [ ] 로컬 필터: prerequisites 기반 topological sort (`graphlib.TopologicalSorter`)
- [ ] Extract 0 unit → min 1 prompt + validate + 1 retry → fail 로직
- [ ] `plan.json` 저장 로직 (Extract 결과 직렬화)

## Definition of Done

- [ ] `problem2.md` 입력 시 3~5개 ShortUnit이 포함된 ShortSeriesPlan 반환
- [ ] 각 unit에 headline, story_format, ApplicationStory 5-beat 필드 존재
- [ ] `plan.json`이 올바른 JSON 구조로 저장됨
- [ ] `estimated_seconds > 60` unit에 경고 메시지 출력

## 리스크 / 메모

- Extract 프롬프트의 few-shot 예시 품질이 결과에 큰 영향 — iterative tuning 필요 가능
