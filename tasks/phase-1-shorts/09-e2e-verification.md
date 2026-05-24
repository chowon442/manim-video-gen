---
id: "1.09"
phase: 1
title: "Phase 1 E2E 검증"
spec: "specs/phase-1/03-short-orchestrator-and-cli.md"
depends_on: ["1.08"]
blocks: []
estimate: "M"
status: "todo"
owner: ""
sprint: ""
---

# Task 1.09 — Phase 1 E2E 검증

> Spec: [`specs/phase-1/03-short-orchestrator-and-cli.md`](../../specs/phase-1/03-short-orchestrator-and-cli.md)

## 의존성

- 1.08 (short_orchestrator + CLI) — 전체 파이프라인 통합 완료 필요

## 사전 준비

- [ ] `problem2.md` 테스트 입력 파일 확인
- [ ] TTS/OpenRouter API 키 설정 확인

## 구현 체크리스트

- [ ] `python -m manim_video_gen short -f problem2.md --mode single` 실행 → 15~60초 9:16 영상 생성 확인
- [ ] 영상 상단 중앙에 headline 전 구간 고정 표시 확인
- [ ] narration/tts_text가 스토리텔링 톤 (강의체 패턴 없음) 확인
- [ ] headline이 TTS로 읽지 않음 확인
- [ ] 각 쇼츠가 ApplicationStory 아크 따름 확인 (Hook→Problem→Concept→Payoff)
- [ ] ShortTemplateRegistry 템플릿 우선 + short_visual_scene LLM fallback 동작 확인
- [ ] LLM 실패 시 fallback 템플릿 degrade 확인
- [ ] `--mode series --max-shorts 5` 실행 시 5개 영상 + series_metadata.json 확인
- [ ] `--dry-run` 실행 시 plan.json만 생성 확인
- [ ] 기존 long-form 파이프라인 regression 테스트 실행

## Definition of Done

- [ ] `problem2.md` → 시리즈 3~5개, 각 15~60초, 9:16 영상 생성 성공
- [ ] 세로 화면에서 수식/그래프/자막/headline 겹침 없음
- [ ] `--mode single --topic "p-value"`로 1개만 생성 가능
- [ ] 기존 long-form 파이프라인 동작 변화 없음

## 리스크 / 메모

- E2E 테스트는 API 비용 수반 — 필수 케이스만 먼저 실행
- TTS duration check → 60초 초과 시 scriptify 재시도 로직 확인 필요
