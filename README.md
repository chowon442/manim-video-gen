# manim-video-gen

수학 문제를 입력받아 풀이 해설 동영상을 자동 생성하는 파이프라인입니다.

## 요구 사항

- Python 3.11+
- FFmpeg / ffprobe (시스템 PATH; ElevenLabs MP3→WAV 변환 및 합성에 필요)
- LaTeX (Manim `MathTex`용, TeX Live 등)
- `OPENROUTER_API_KEY`, `ELEVENLABS_API_KEY`

OpenRouter는 공식 OpenAI 호환 REST(`httpx`)로 호출합니다. 모델은 `.env`의 `MANIM_VIDEO_GEN_MODEL_*`로 지정합니다.

## 설치

```bash
cd manim-video-gen
pip install -e ".[dev]"
cp .env.example .env
# .env에 API 키 입력
```

## 사용

```bash
python -m manim_video_gen "x^2 + 2x + 1 = 0 을 풀어라"
```

## TTS 사전 검증

```bash
python3 scripts/test_tts.py
```

생성된 `artifacts/tts_validation/*.wav`를 청취해 한국어·수학 발음이 데모에 적합한지 판단하세요. 부적절하면 `tts/base.py`에 다른 `TTSProvider` 구현체를 추가해 교체할 수 있습니다.

## LLM 연결 확인 (선택)

```bash
python3 scripts/test_openrouter.py
python3 scripts/test_prompt_chain.py
```
