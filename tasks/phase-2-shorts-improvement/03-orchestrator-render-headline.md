---
id: "2.03"
phase: 2
title: "Orchestrator 렌더 분기 정리 및 headline/ASS 개선"
spec: "specs/phase-2/01-shorts-improvement.md"
depends_on: ["2.01", "2.02", "1.07", "1.08"]
blocks: ["2.05"]
estimate: "L"
status: "todo"
owner: ""
sprint: ""
---

# Task 2.03 — Orchestrator 렌더 분기 정리 및 headline/ASS 개선

> Spec: [`specs/phase-2/01-shorts-improvement.md`](../../specs/phase-2/01-shorts-improvement.md)

## 의존성

- 2.01 (Scriptify short_* 카탈로그 교체) — 정규화된 visual_type과 beat 필드가 orchestrator 분기에 전달되어야 함
- 2.02 (쇼츠 템플릿 MathTex + safe zone) — registry hit 시 사용할 템플릿이 MathTex/safe zone을 지원해야 함
- 1.07 (ManimGen + Headline) — headline ASS 스타일과 PlayRes 동적 설정 기반
- 1.08 (Orchestrator + CLI) — short_orchestrator.py와 short_manim_gen.py의 기존 분기 구조 기반

## 사전 준비

- [ ] `docs/shorts_improvement.md` P0-E, P0-F, P2 섹션 확인
- [ ] 기존 `short_orchestrator.py` L266–272 registry → LLM → fallback 분기 파악
- [ ] 기존 `short_manim_gen.py` L215–221 fallback 매핑 키 확인
- [ ] 기존 `subtitle.py` L398–428 headline ASS 스타일 확인

## 구현 체크리스트

- [ ] `short_orchestrator.py`: visual_type normalize 로직 (registry 우선)
- [ ] `short_orchestrator.py`: registry.has(vt) → template 직접 사용 (LLM skip)
- [ ] `short_orchestrator.py`: `vt == "short_visual_scene"` → LLM 분기
- [ ] `short_orchestrator.py`: 그 외 → beat/story_format 기반 nearest template
- [ ] `short_orchestrator.py`: LLM 3회 실패 시 `resolve_short_fallback_template(beat, vt)` 호출
- [ ] `short_manim_gen.py`: fallback 매핑 확장 ("hook"→short_hook, "before"→short_before 등)
- [ ] `subtitle.py`: `_HEADLINE_FONT_SIZE = 48` → format_profile 기반 동적 설정
- [ ] `subtitle.py`: 9:16 기본 headline 폰트 68px (subtitle ~1.6×)
- [ ] `config.py`: `MANIM_VIDEO_GEN_HEADLINE_FONT_SIZE`, `MANIM_VIDEO_GEN_HEADLINE_MARGIN_V` env 추가
- [ ] `short_orchestrator.py` L403: `subtitle_safe_area_px=0` 하드코딩 → `settings.subtitle_safe_area_px` 사용
- [ ] `short_orchestrator.py` L610: `project_root` import 누락 수정 (series mode bug)

## Definition of Done

- [ ] `--dry-run` 실행 시 beat별 다양한 템플릿(hook, graph, payoff 등)이 registry hit로 매핑
- [ ] LLM fallback 발생 빈도가 기존보다 현저히 감소
- [ ] 1080×1920 출력에서 headline이 자막보다 시각적으로 확실히 크게 표시
- [ ] series mode에서 `project_root` ImportError 미발생

## 리스크 / 메모

- `short_visual_scene`은 registry에도 orchestrator 분기에도 미구현 — 이번에 LLM 전용 분기만 추가, 실제 LLM 프롬프트는 추후
- headline 크기 변경 시 기존 ASS 렌더링 테스트 영상과 비교 필요
- orchestrator 분기 변경은 E2E 흐름 전체에 영향 — dry-run → 실제 렌더 단계별 검증 필수
