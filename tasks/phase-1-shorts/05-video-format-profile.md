---
id: "1.05"
phase: 1
title: "VideoFormatProfile + subtitle PlayRes 동적화"
spec: "specs/phase-1/02-short-template-registry.md"
depends_on: []
blocks: ["1.06", "1.07", "1.08"]
estimate: "S"
status: "todo"
owner: ""
sprint: ""
---

# Task 1.05 — VideoFormatProfile + subtitle PlayRes 동적화

> Spec: [`specs/phase-1/02-short-template-registry.md`](../../specs/phase-1/02-short-template-registry.md)

## 의존성

- 독립 task — 기존 config/subtitle 모듈 수정

## 사전 준비

- [ ] `config.py`의 VIDEO_WIDTH/HEIGHT 설정 확인
- [ ] `video/subtitle.py`의 PlayRes 고정값 확인

## 구현 체크리스트

- [ ] `config.py`에 `VideoFormatProfile` enum 추가 (landscape, short_9_16)
- [ ] `short_9_16` 프리셋: 1080×1920, safe zone(상단 12%, 하단 20%) 정의
- [ ] `config.py`에 format_profile 관련 설정 필드 추가
- [ ] `video/subtitle.py`에서 PlayRes를 `VideoFormatProfile`에 따라 동적 설정
- [ ] 9:16 해상도에서 Manim `--resolution` 파라미터 연동
- [ ] 기존 16:9 동작 regression 확인

## Definition of Done

- [ ] `VideoFormatProfile.short_9_16` 설정 시 해상도 1080×1920 적용
- [ ] subtitle ASS PlayRes가 1080×1920으로 변경됨 확인
- [ ] 기존 `landscape` 모드 동작 변화 없음

## 리스크 / Me모

- subtitle.py의 PlayRes 변경이 기존 long-form 영상에 영향 주지 않도록 분기 처리 필수
