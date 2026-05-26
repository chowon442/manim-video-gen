---
id: "2.04"
phase: 2
title: "TTS 배속 및 polish_tts_text 적용"
spec: "specs/phase-2/01-shorts-improvement.md"
depends_on: ["1.08"]
blocks: []
estimate: "M"
status: "todo"
owner: ""
sprint: ""
---

# Task 2.04 — TTS 배속 및 polish_tts_text 적용

> Spec: [`specs/phase-2/01-shorts-improvement.md`](../../specs/phase-2/01-shorts-improvement.md)

## 의존성

- 1.08 (Orchestrator + CLI) — TTS 합성 및 Manim duration 연동 로직이 존재해야 함

## 사전 준비

- [ ] `docs/shorts_improvement.md` P1-A, P1-B 섹션 확인
- [ ] 기존 `orchestrator.py` L520–538 `polish_tts_text()` 호출 지점 확인
- [ ] 기존 `short_orchestrator.py` L469–474 TTS 합성 → duration 사용 구간 확인
- [ ] ffmpeg `atempo` 필터 사용법 확인

## 구현 체크리스트

- [ ] `video/audio_speed.py` 신규 생성: ffmpeg atempo 배속 유틸리티
- [ ] `audio_speed.py`: `adjust_playback_rate(input_path, output_path, rate)` 함수 구현 (0.5–2.0 범위)
- [ ] `config.py`: `MANIM_VIDEO_GEN_TTS_PLAYBACK_RATE` env 추가 (default 1.0, 범위 0.5–2.0)
- [ ] `.env.example`: `MANIM_VIDEO_GEN_TTS_PLAYBACK_RATE` 문서화
- [ ] `short_orchestrator.py`: `tts.synthesize()` 이후 `adjust_playback_rate()` 호출
- [ ] `short_orchestrator.py`: 배속된 duration으로 Manim segment duration 계산 (`duration / rate`)
- [ ] `short_orchestrator.py`: scriptify 직후 `_ensure_tts_text(script, settings)` 호출 (long-form과 동일)
- [ ] `test_audio_speed.py` 신규: atempo duration 계산 단위 테스트
- [ ] `test_short_orchestrator.py` 또는 통합 테스트: 배속 적용 후 duration 감소 확인

## Definition of Done

- [ ] `MANIM_VIDEO_GEN_TTS_PLAYBACK_RATE=1.25` 설정 시 TTS 길이가 1/1.25로 줄어듦
- [ ] 배속 후 음성 품질이 기계음/왜곡 없이 유지
- [ ] `polish_tts_text`가 short pipeline에도 적용되어 강의체 → 구어체 변환
- [ ] long-form 파이프라인의 기본 playback rate는 1.0 (변경 없음)

## 리스크 / 메모

- ffmpeg atempo는 0.5–2.0 범위만 직접 지원, 그 외는 체이닝 필요 (초기에는 0.5–2.0 제한)
- TTS 배속 후 Manim duration 불일치 시 음성-영상 싱크 어긋남 — duration 전파 검증 필수
- `polish_tts_text`가 short narration에도 적합한지 사전 검토 (12~18자 짧은 문장 기준)
