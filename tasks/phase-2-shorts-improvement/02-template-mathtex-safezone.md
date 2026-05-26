---
id: "2.02"
phase: 2
title: "쇼츠 템플릿 MathTex + safe zone 적용"
spec: "specs/phase-2/01-shorts-improvement.md"
depends_on: ["1.06"]
blocks: ["2.03"]
estimate: "M"
status: "todo"
owner: ""
sprint: ""
---

# Task 2.02 — 쇼츠 템플릿 MathTex + safe zone 적용

> Spec: [`specs/phase-2/01-shorts-improvement.md`](../../specs/phase-2/01-shorts-improvement.md)

## 의존성

- 1.06 (템플릿 레지스트리) — concept/beat 템플릿이 이미 존재하며 MathTex 및 fit 로직을 적용할 대상

## 사전 준비

- [ ] `docs/shorts_improvement.md` P0-C, P0-D 섹션 확인
- [ ] 기존 long-form `equation.py`의 `wrap_korean_text_runs`, `fit_tex_mobject_lines` 구조 파악
- [ ] 기존 `concept_templates.py`, `beat_templates.py` 현재 상태 확인

## 구현 체크리스트

- [ ] `video/templates/short/_layout.py` 신규 생성: safe zone y offset, scale_to_fit_width 헬퍼
- [ ] `concept_templates.py` `short_concept_equation`: `Text()` → `MathTex()` 교체
- [ ] `concept_templates.py`: `wrap_korean_text_runs` 적용
- [ ] `concept_templates.py`: `fit_tex_mobject_lines` 적용 (9:16 프레임 폭 내 스케일)
- [ ] `concept_templates.py` `short_concept_annotated`: `MathTex(latex) + Text(annotation)` 조합
- [ ] `concept_templates.py` compare/pattern 템플릿: `fit_text_mobject_lines` + `arrange(DOWN)`
- [ ] `beat_templates.py`: 모든 `Text()`에 `fit_text_mobject_lines` 적용
- [ ] `beat_templates.py` `short_hook`: `visual_params.headline` 없을 때 narration 첫 줄 fallback
- [ ] `_layout.py`: 상단 12% headline / 하단 20% subtitle safe zone 상수/함수 정의
- [ ] `test_short_templates.py` 수정: `"Text" in code` 검증 → `MathTex` 포함 검증

## Definition of Done

- [ ] `\beta_1 + \beta_2x` 수식이 `short_concept_equation`에서 MathTex로 렌더됨
- [ ] 긴 수식/분수가 9:16 프레임 좌우로 잘리지 않음
- [ ] `short_concept_annotated`에서 LaTeX 명령어가 raw 문자열로 표시되지 않음
- [ ] 기존 long-form 템플릿에 영향 없음

## 리스크 / 메모

- `fit_tex_mobject_lines`가 9:16 세로 프레임(10.80 Manim unit 폭)에서 예상대로 동작하는지 실제 렌더 검증 필요
- MathTex로 교체 시 LaTeX 의존성 오류 가능성 — wrap_korean_text_runs 조합 테스트 필수
