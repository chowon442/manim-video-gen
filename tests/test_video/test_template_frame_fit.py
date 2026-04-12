from manim_video_gen.video.templates.more import (
    IntroProblemTemplate,
    OutroSummaryTemplate,
    TitleCardTemplate,
)


def test_title_card_has_frame_fit_guard():
    code = TitleCardTemplate.render_code(
        params={
            "title": "아주 긴 제목 텍스트" * 8,
            "subtitle": "아주 긴 부제 텍스트" * 8,
        },
        duration=6.0,
        prev_scene_state=None,
    )
    assert "scale_to_fit_width" in code
    assert "config.frame_width - 1.2" in code
    assert "tt.to_edge(UP, buff=0.50)" in code


def test_intro_problem_has_frame_fit_guard():
    code = IntroProblemTemplate.render_code(
        params={"problem_text": "아주 긴 문제 본문" * 20},
        duration=8.0,
        prev_scene_state=None,
    )
    assert "body.scale_to_fit_width" in code
    assert "body.to_edge(UP, buff=1.20)" in code


def test_outro_summary_has_frame_fit_guard():
    code = OutroSummaryTemplate.render_code(
        params={"summary_text": "아주 긴 요약" * 20},
        duration=8.0,
        prev_scene_state=None,
    )
    assert "summary_group.scale_to_fit_width" in code
    assert "config.frame_width - 1.2" in code
    assert "summary_group.to_edge(UP, buff=0.60)" in code
    assert "arrange(DOWN, aligned_edge=LEFT, buff=0.32)" in code
