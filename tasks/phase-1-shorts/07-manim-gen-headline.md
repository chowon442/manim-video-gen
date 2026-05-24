---
id: "1.07"
phase: 1
title: "short_manim_gen + ASS headline"
spec: "specs/phase-1/02-short-template-registry.md"
depends_on: ["1.05", "1.06"]
blocks: ["1.08"]
estimate: "M"
status: "todo"
owner: ""
sprint: ""
---

# Task 1.07 — short_manim_gen + ASS headline

> Spec: [`specs/phase-1/02-short-template-registry.md`](../../specs/phase-1/02-short-template-registry.md)

## 의존성

- 1.05 (VideoFormatProfile) — 9:16 safe zone 정의 필요
- 1.06 (ShortTemplateRegistry) — fallback 템플릿 대상 필요

## 사전 준비

- [ ] 기존 `llm/prompts/manim_gen.py` 구조 확인 (few-shot, retry 패턴)
- [ ] `video/subtitle.py`의 ASS 스타일 구조 확인

## 구현 체크리스트

- [ ] `src/manim_video_gen/llm/prompts/short_manim_gen.py` 생성
- [ ] 9:16 프레임 few-shot 예시 포함 (hook, before-after terrain, stat chart)
- [ ] headline 영역(상단 12%)/subtitle 영역(하단 20%) 침범 금지 지시
- [ ] retry 3회 로직 (prior code + error 전달)
- [ ] 3회 실패 시 short_concept_equation 또는 beat 적합 fallback degrade
- [ ] ASS headline 구현 — `Dialogue` style, 상단 중앙, MarginV 큼
- [ ] headline을 전 세그먼트 duration 동안 1개 이벤트로 설정
- [ ] headline은 TTS로 읽지 않음 (visual-only 플래그)

## Definition of Done

- [ ] short_manim_gen 프롬프트에 9:16 few-shot 포함 확인
- [ ] 3회 retry 후 fallback 템플릿 degrade 동작 확인
- [ ] ASS headline이 영상 전체 구간 상단 중앙에 표시
- [ ] headline이 TTS audio에 포함되지 않음 확인

## 리스크 / 메모

- LLM Manim 코드 생성 품질은 few-shot 예시에 크게 의존 — 세로 전용 예시 반복 튜닝 필요
