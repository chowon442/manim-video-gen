# ShortTemplateRegistry + LLM Fallback + ASS Headline

## Purpose
쇼츠 전용 Manim 템플릿 레지스트리(10+종)와 short_visual_scene LLM fallback 경로, 상단 ASS headline 오버레이를 구현한다.

## Requirements
- `video/templates/short/` 디렉토리에 beat용 5종(short_hook, short_before, short_after, short_payoff_card, short_cta) + concept용 6종(short_concept_equation, short_concept_graph, short_concept_number_line, short_concept_annotated, short_concept_compare, short_concept_pattern) + domain용 3종(short_domain_icon, short_stat_chart, short_flow_arrow) MVP 템플릿 구현
- `video/templates/short/short_registry.py` — `ShortTemplateRegistry` 클래스. long-form `TemplateRegistry`와 동일한 인터페이스(`has()`, `get()`)를 따르되 쇼츠 전용 경로 사용
- `llm/prompts/short_manim_gen.py` — long-form `manim_gen.py` 파생. 9:16 프레임, headline 영역(상단 12%)/subtitle 영역(하단 20%) 침범 금지 few-shot 포함. retry 3회, 실패 시 `short_concept_equation` 또는 beat 적합 fallback 템플릿으로 degrade
- ASS headline 구현 — `ShortUnit.headline`을 영상 전체 구간 상단 중앙 고정 오버레이. `subtitle.py`의 PlayRes를 출력 해상도(1080×1920)에 연동. headline은 TTS로 읽지 않음(visual-only)
- `VideoFormatProfile` enum 추가(landscape/short_9_16) — 1080×1920 preset, 세로 safe zone 정의

## Approach
long-form의 3단 분기 패턴(Registry → LLM → fallback)을 그대로 따르되, 모든 렌더링 컴포넌트를 9:16 세로 레이아웃에 맞춘다. 템플릿은 기존 long-form `equation_write`/`graph_plot` 등을 참고하되 Manim 코드를 세로 전용으로 독립 구현한다. headline은 ASS `Dialogue` style로 `subtitle.py`에 통합하고, 기존 `subtitle.py`의 PlayRes 고정값을 `VideoFormatProfile`에 따라 동적으로 설정한다.

## Verification
- `ShortTemplateRegistry.has("short_concept_equation")` 등 주요 visual_type에 대해 true 반환
- 9:16 해상도에서 short_concept_equation 템플릿이 headline/subtitle safe area 침범 없이 렌더
- short_manim_gen 프롬프트가 9:16 few-shot 포함, 3회 retry 후 fallback 템플릿 degrade 동작
- ASS headline이 영상 전체 구간 상단 중앙에 표시되며 TTS 미포함
- `VideoFormatProfile.short_9_16` 설정 시 subtitle PlayRes가 1080×1920으로 변경
