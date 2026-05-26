---
id: "2.05"
phase: 2
title: "한국어 payoff 연결성 검사 개선"
spec: "specs/phase-2/01-shorts-improvement.md"
depends_on: ["2.03"]
blocks: []
estimate: "S"
status: "todo"
owner: ""
sprint: ""
---

# Task 2.05 — 한국어 payoff 연결성 검사 개선

> Spec: [`specs/phase-2/01-shorts-improvement.md`](../../specs/phase-2/01-shorts-improvement.md)

## 의존성

- 2.03 (Orchestrator 렌더 분기 정리) — `short_quality` payoff 검사 로직이 `short_orchestrator.py`에 존재하며, 이를 개선해야 함

## 사전 준비

- [ ] `docs/shorts_improvement.md` P1-C 섹션 확인
- [ ] 기존 `short_orchestrator.py` L103–111 payoff overlap 검사 코드 확인
- [ ] 기존 E2E 검증 실패 사례 (`p-value가` vs `p-value`, `0.014(1.4%)로` vs `0.014`) 확인

## 구현 체크리스트

- [ ] `utils/korean_text.py` 신규 생성
- [ ] `korean_text.py`: `extract_content_tokens(text)` — 조사(은/는/이/가) strip, 영문/숫자 토큰 추출, 불용어 제거
- [ ] `korean_text.py`: `payoff_references_application(application_result, payoff_line)` — 정규화 토큰 overlap >= 1 + substring fallback
- [ ] `short_orchestrator.py`: 기존 `set(...).split()` 기반 overlap 검사 → `payoff_references_application()` 교체
- [ ] `test_korean_text.py` 신규: 한국어 토큰 추출 단위 테스트
- [ ] `test_korean_text.py`: payoff_references_application 케이스
  - `p-value가 0.014(1.4%)로 유의미합니다` → `p-value 0.014로 유의미해요` = pass
  - `기울기로 추세를 판단할 수 있어요` → `오늘 날씨가 좋네요` = fail
- [ ] `test_short_quality.py` 또는 통합 테스트: KO false positive 감소 확인

## Definition of Done

- [ ] 한국어 의미상 payoff가 application_result를 참조할 때 false positive 미발생
- [ ] 영어 payoff 검사도 기존과 동등하거나 개선된 정확도 유지
- [ ] `short_quality failed` → `ValueError` raise 빈도가 한국어 케이스에서 감소

## 리스크 / 메모

- 한국어 조사 처리는 완벽하지 않을 수 있음 — 초기에는 주요 조사(은/는/이/가/을/를/로/으로)만 처리, 추후 확장
- 숫자 변형(`0.014(1.4%)` → `0.014`) 처리 시 괄호/단위 제거 로직이 너무 aggressive하면 의도치 않은 match 가능성
