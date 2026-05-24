---
id: "1.08"
phase: 1
title: "short_orchestrator + CLI + quality guard"
spec: "specs/phase-1/03-short-orchestrator-and-cli.md"
depends_on: ["1.03", "1.04", "1.06", "1.07"]
blocks: ["1.09"]
estimate: "L"
status: "todo"
owner: ""
sprint: ""
---

# Task 1.08 — short_orchestrator + CLI + quality guard

> Spec: [`specs/phase-1/03-short-orchestrator-and-cli.md`](../../specs/phase-1/03-short-orchestrator-and-cli.md)

## 의존성

- 1.03 (Extract + short_extractor) — plan.json 생성 필요
- 1.04 (StoryScriptify) — VideoScript 생성 필요
- 1.06 (ShortTemplateRegistry) — 템플릿 렌더 필요
- 1.07 (short_manim_gen + ASS headline) — LLM fallback + headline 필요

## 사전 준비

- [ ] 기존 `orchestrator.py`의 `_build_manim_code_for_segment` 패턴 확인
- [ ] `__main__.py`의 argparse 구조 확인

## 구현 체크리스트

- [ ] `src/manim_video_gen/pipeline/short_orchestrator.py` 생성
- [ ] Extract→StoryScriptify→TTS→Manim→Compose E2E 파이프라인 조율
- [ ] `_build_short_manim_code_for_segment` — Registry → LLM → fallback 3단 분기
- [ ] plan.json 캐시 로직 (재렌더 시 Extract/StoryScriptify 생략)
- [ ] TTS factory, OpenRouter client, composer, diagnostics 재사용 연결
- [ ] `__main__.py`에 `short` subcommand subparser 추가
- [ ] `--mode single` (기본 #1 또는 `--topic` fuzzy match)
- [ ] `--mode series` (topological sort + `--max-shorts` cap)
- [ ] `--dry-run` (Extract까지만 + plan.json 저장)
- [ ] `--plan-only` (plan.json만 생성)
- [ ] `--from-plan plan.json --unit N` (특정 unit 재렌더)
- [ ] short_quality 가드 함수 구현 (ApplicationStory 5필드, hook 검증 등)
- [ ] single 출력: `artifacts/short_<id>/final.mp4` + metadata
- [ ] series 출력: `artifacts/series_<run_id>/short_01..N.mp4` + `series_metadata.json`

## Definition of Done

- [ ] `python -m manim_video_gen short -f problem2.md --mode single` E2E 동작
- [ ] `--dry-run` 실행 시 plan.json 생성 + Extract까지만 진행
- [ ] `--mode series --max-shorts 3` 실행 시 3개 영상 생성
- [ ] `--from-plan plan.json --unit 2`로 unit 재렌더 동작
- [ ] short_quality 가드 실패 시 명확한 에러 메시지 출력

## 리스크 / 메모

- 기존 long-form `orchestrator.py` 수정 없이 별도 파일로 분리 — regression 방지
- series topological sort cycle 감지 시 LLM fallback 순서 로직 추가 필요
