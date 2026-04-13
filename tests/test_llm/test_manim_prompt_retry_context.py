"""Tests for retry context formatting in Manim user prompts."""

from manim_video_gen.llm.prompts.manim_gen import build_manim_user_prompt
from manim_video_gen.models.script import Segment


def _seg() -> Segment:
    return Segment(
        id=5,
        narration="그래프로 보면 아래로 볼록한 형태입니다.",
        tts_text="그래프로 보면 아래로 볼록한 형태입니다.",
        visual_description="3차원 좌표계에 볼록 곡면을 보여줍니다.",
        visual_type="visual_scene",
        visual_params={"hints": "ThreeDAxes + Surface"},
        prev_scene_state=None,
    )


def test_retry_prompt_includes_prior_error_and_code_with_attempt_numbers():
    seg = _seg()
    prompt = build_manim_user_prompt(
        seg,
        duration_seconds=8.5,
        prior_errors=[
            "attempt 1 failed: AttributeError: 'ThreeDCamera' object has no attribute 'animate'",
            "attempt 2 failed: TypeError: Unexpected argument None passed to Scene.play()",
        ],
        prior_codes=[
            "from manim import *\nclass Segment(Scene):\n    pass\n",
            "from manim import *\nclass Segment(ThreeDScene):\n    pass\n",
        ],
    )

    assert "Previous errors (fix them):" in prompt
    assert "attempt 1 failed" in prompt
    assert "attempt 2 failed" in prompt
    assert "Previous full code attempts" in prompt
    assert "--- attempt 1 ---" in prompt
    assert "--- attempt 2 ---" in prompt


def test_retry_prompt_explicitly_warns_against_repeating_failed_patterns():
    seg = _seg()
    prompt = build_manim_user_prompt(
        seg,
        duration_seconds=8.5,
        prior_errors=[
            "attempt 1 failed: AttributeError: 'ThreeDCamera' object has no attribute 'animate'",
        ],
        prior_codes=[
            "self.play(self.camera.animate.set_euler_angles(phi=65*DEGREES))",
        ],
    )

    assert "do not repeat mistakes" in prompt
    assert "Retry instruction:" in prompt
    assert "Analyze the exact root causes" in prompt
    assert "self.camera.animate" in prompt
