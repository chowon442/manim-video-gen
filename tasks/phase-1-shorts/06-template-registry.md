---
id: "1.06"
phase: 1
title: "ShortTemplateRegistry + MVP 템플릿"
spec: "specs/phase-1/02-short-template-registry.md"
depends_on: ["1.05"]
blocks: ["1.07", "1.08"]
estimate: "L"
status: "todo"
owner: ""
sprint: ""
---

# Task 1.06 — ShortTemplateRegistry + MVP 템플릿

> Spec: [`specs/phase-1/02-short-template-registry.md`](../../specs/phase-1/02-short-template-registry.md)

## 의존성

- 1.05 (VideoFormatProfile) — 9:16 해상도/레이아웃 설정 필요

## 사전 준비

- [ ] 기존 long-form `TemplateRegistry` 인터페이스 확인 (`has()`, `get()`)
- [ ] 기존 `equation_write`, `graph_plot` 등 템플릿 구조 참고

## 구현 체크리스트

- [ ] `src/manim_video_gen/video/templates/short/` 디렉토리 생성
- [ ] `short_registry.py` — `ShortTemplateRegistry` 클래스 (has/get 인터페이스)
- [ ] beat 템플릿 5종: short_hook, short_before, short_after, short_payoff_card, short_cta
- [ ] concept 템플릿 4종 (MVP): short_concept_equation, short_concept_graph, short_concept_number_line, short_concept_annotated
- [ ] concept 템플릿 2종: short_concept_compare, short_concept_pattern
- [ ] domain 템플릿 3종: short_domain_icon, short_stat_chart, short_flow_arrow
- [ ] 모든 템플릿이 9:16 safe zone (상단 12%, 하단 20%) 침범 금지 확인
- [ ] long-form 템플릿과 경로/네임스페이스 격리

## Definition of Done

- [ ] `ShortTemplateRegistry.has("short_concept_equation")` → True
- [ ] `ShortTemplateRegistry.has("nonexistent")` → False
- [ ] 9:16 해상도에서 주요 템플릿 렌더 시 headline/subtitle 영역과 겹침 없음
- [ ] 템플릿 14종 모두 import 및 인스턴스화 가능

## 리스크 / 메모

- 템플릿 수가 많아 MVP 우선순위 설정 필요: beat 5종 + concept equation/graph가 최우선
- 나머지 템플릿은 placeholder Manim Scene으로 구현 후 점진적 고도화
