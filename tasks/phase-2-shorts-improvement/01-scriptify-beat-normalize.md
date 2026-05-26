---
id: "2.01"
phase: 2
title: "Scriptify short_* 카탈로그 교체 및 beat 필드 추가"
spec: "specs/phase-2/01-shorts-improvement.md"
depends_on: ["1.01", "1.04"]
blocks: ["2.03"]
estimate: "M"
status: "todo"
owner: ""
sprint: ""
---

# Task 2.01 — Scriptify short_* 카탈로그 교체 및 beat 필드 추가

> Spec: [`specs/phase-2/01-shorts-improvement.md`](../../specs/phase-2/01-shorts-improvement.md)

## 의존성

- 1.01 (ShortUnit 데이터 모델 정의) — Segment 모델에 beat 필드를 추가하려면 기존 모델 구조 파악 필요
- 1.04 (StoryScriptify 프롬프트) — short_scriptify.py 프롬프트 구조 및 beat 태그 지정 로직 기반

## 사전 준비

- [ ] `docs/shorts_improvement.md` P0-A, P0-B 섹션 확인
- [ ] 기존 `short_scriptify.py` L99–112 long-form 카탈로그 구조 파악
- [ ] 기존 `models/script.py` Segment 필드 목록 확인

## 구현 체크리스트

- [ ] `short_scriptify.py`: long-form 카탈로그 → short_* 14종 + `short_visual_scene` 카탈로그 교체
- [ ] `short_scriptify.py`: beat별 기본 visual_type 매핑 테이블 추가
- [ ] `short_scriptify.py`: `STORY_FORMAT_VISUAL_MAP` 값을 `short_*`로 변경
- [ ] `short_scriptify.py`: 각 visual_type별 `visual_params` 스키마 예시 추가
- [ ] `parse_short_scriptify_response`: `normalize_short_visual_type(vt, beat, story_format)` 함수 추가
- [ ] `normalize_short_visual_type`: long-form → short 매핑 (equation_write → short_concept_equation, graph_plot → short_concept_graph 등)
- [ ] `normalize_short_visual_type`: `visual_params` 키 정규화 (`title` → `headline`, `equation` → `latex`)
- [ ] `models/script.py`: `Segment` 모델에 `beat: str | None` 필드 추가 (hook|problem|concept|application|payoff)
- [ ] `test_short_scriptify.py` 또는 신규 테스트: normalize 로직 단위 테스트

## Definition of Done

- [ ] scriptify 응답이 `equation_write` 대신 `short_concept_equation`을 출력
- [ ] long-form visual_type 입력 시 normalize로 short_* 매핑
- [ ] Segment JSON 파싱 시 beat 필드가 유실되지 않음
- [ ] 기존 long-form 파이프라인에 영향 없음 (beat 필드는 optional)

## 리스크 / 메모

- `short_visual_scene`은 기획에는 있으나 코드베이스에 0건 — 이번에 신규 매핑만 추가, 실제 구현은 2.03에서 처리
- STORY_FORMAT_VISUAL_MAP 변경 시 기존 캐시/테스트 데이터 영향 확인 필요
