# Shorts 수식/템플릿/TTS 개선

## Purpose

쇼츠 E2E 파이프라인 구현 이후 발견된 수식 렌더링, 템플릿 다양성, TTS 속도, headline 가독성, 한국어 quality guard 오탐 문제를 개선한다.

## Requirements

- scriptify가 short_* 전용 visual_type 카탈로그를 출력하도록 교체하고, long-form 타입은 normalize하여 매핑한다.
- concept/beat 템플릿에 MathTex + wrap/fit 로직과 9:16 safe zone을 적용하여 수식 잘림과 raw LaTeX 표시를 방지한다.
- TTS 생성 후 ffmpeg atempo 배속과 polish_tts_text를 적용하여 느린 음성을 개선한다.
- 쇼츠 9:16 해상도에 맞춰 headline 폰트 크기를 자막보다 확실히 크게 조정하고 format_profile 기반 설정을 지원한다.
- short_quality의 한국어 payoff 연결성 검사를 조사/숫자 정규화 토큰 기반으로 교체하여 false positive를 제거한다.

## Approach

visual_type 정합성을 먼저 고치고 scriptify와 orchestrator의 분기 로직을 정리한 뒤, concept/beat 템플릿에 MathTex와 scale-to-fit 헬퍼를 적용한다. TTS는 synthesize 이후 ffmpeg atempo로 playback rate를 조절하고 adjusted duration을 Manim에 전달하며, headline은 subtitle보다 1.6배 큰 폰트로 ASS 스타일을 분리한다. 마지막으로 한국어 payoff 검증 로직에 content token 추출과 substring fallback을 도입한다.

## Verification

- `python -m manim_video_gen short -f problem.md --dry-run` 실행 시 beat별 다양한 템플릿(hook, graph, payoff 등)이 registry hit로 매핑된다.
- `\beta_1 + \beta_2x` 수식이 short_concept_equation에서 MathTex로 렌더되며 프레임 폭 내에 맞춰 스케일된다.
- `MANIM_VIDEO_GEN_TTS_PLAYBACK_RATE=1.25` 환경변수 설정 시 TTS 길이가 1/1.25로 줄어든다.
- 1080×1920 출력에서 headline이 자막보다 시각적으로 확실히 크게 표시된다.
- "p-value가 0.014(1.4%)로 유의미합니다" → "p-value 0.014로 유의미해요" 케이스가 payoff 검증에서 통과한다.
