from manim_video_gen.models.script import Segment, VideoScript
from manim_video_gen.video.latex_json_sanitize import (
    sanitize_latex_string_after_json_load,
    sanitize_video_script_visual_params,
)


def test_repair_json_frac_formfeed() -> None:
    # After JSON load, valid \\frac was parsed as U+000C + "rac{...}"
    s = "eq = {{ " + "\x0c" + "rac{1}{2} }}"
    fixed = sanitize_latex_string_after_json_load(s)
    assert "\x0c" not in fixed
    assert "\\frac{" in fixed


def test_sanitize_script_visual_params() -> None:
    bad = "x = {{" + "\x0c" + "rac{1}{2}}}"
    script = VideoScript(
        title="t",
        segments=[
            Segment(
                id=0,
                narration="n",
                tts_text="",
                visual_description="d",
                visual_type="annotated_equation",
                visual_params={"latex": bad, "annotations": []},
            )
        ],
    )
    out = sanitize_video_script_visual_params(script)
    assert "\x0c" not in out.segments[0].visual_params["latex"]
