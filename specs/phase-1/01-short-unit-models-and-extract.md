# ShortUnit Models + Extract + StoryScriptify

## Purpose
쇼츠 파이프라인의 핵심 데이터 모델(ShortUnit, ApplicationStory, StoryFormat)과 문서→ShortUnit 추출(Extract), ShortUnit→VideoScript 변환(StoryScriptify)을 구현한다.

## Requirements
- `models/short.py`에 `StoryFormat` enum(application, misconception, stakes, curiosity, pattern), `ApplicationStory`(story_format, confidence, source, domain, scenario 등 5-beat 필드), `ShortUnit`(id, headline, concept_name, core_insight, story, explanation, visual_concept, difficulty, prerequisites, estimated_seconds) 모델 정의
- `llm/prompts/extract_shorts.py` — MD/텍스트 입력 → `ShortSeriesPlan{title, units[], recommended_order[]}` 출력. LLM 모델은 `MANIM_VIDEO_GEN_MODEL_EXTRACT` env. 추출 후 로컬 필터(60초 초과 분할, prerequisites 기반 topological sort). Extract 0 unit일 때 min 1 prompt + validate + 1 retry → fail
- `llm/prompts/short_scriptify.py` — ShortUnit → VideoScript(3~5 segment). 고정 beat 구조: Hook(0~3s)→Problem(3~10s)→Concept(10~25s)→Application(5~15s)→Payoff(3~5s). 응용 맥락 안에서 개념이 "필요한 도구"로 등장. 강의체 패턴 감지 시 구어체로 치환하는 `_ensure_tts_text()` 후처리 포함
- `pipeline/short_extractor.py` — Extract 프롬프트 실행 + 로컬 필터 + `plan.json` 저장 로직. canonical 응용 DB 매칭(confidence < 0.6 → misconception/curiosity 강제) 포함
- story_format→tone 매핑(application→casual, misconception→dramatic, stakes→dramatic, curiosity→insider, pattern→casual) 고정

## Approach
기존 `models/script.py`의 `VideoScript`/`Segment` 구조를 재사용하되, 쇼츠 전용 중간 모델을 `models/short.py`에 독립 생성한다. Extract는 `llm/prompts/solve.py` 패턴을 참고하여 프롬프트를 설계하고, StoryScriptify는 기존 `scriptify.py`의 교사형 대본 규칙을 쇼츠용 story arc로 대체한다. canonical 응용 DB는 하드코딩 JSON(seed ~20개)으로 시작하고, source 필드(document/canonical_db/synthesized)로 출처를 명시한다.

## Verification
- `ShortUnit`, `ApplicationStory`, `StoryFormat` 모델이 pydantic validation 통과
- Extract 프롬프트가 `problem2.md` 입력 시 3~5개 ShortUnit 반환
- StoryScriptify가 3~5개 segment VideoScript 생성, 첫 segment에 concept_name 미포함(delayed labeling)
- 강의체 패턴("배워보겠습니다", "정리하면")이 후처리에서 구어체로 변환
- `estimated_seconds > 60`인 unit이 로컬 필터에서 분할 또는 경고
