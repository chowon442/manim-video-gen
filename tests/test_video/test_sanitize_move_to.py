"""sanitize_move_to_expr 경계값 및 악의적 입력 테스트."""

from manim_video_gen.video.templates.equation import sanitize_move_to_expr


def test_origin():
    assert sanitize_move_to_expr("ORIGIN") == "ORIGIN"


def test_origin_with_spaces():
    assert sanitize_move_to_expr("  ORIGIN  ") == "ORIGIN"


def test_direction_only():
    for direction in ("UP", "DOWN", "LEFT", "RIGHT"):
        assert sanitize_move_to_expr(direction) == direction


def test_direction_times_integer():
    assert sanitize_move_to_expr("UP * 2") == "UP * 2"


def test_direction_times_float():
    assert sanitize_move_to_expr("DOWN * 1.5") == "DOWN * 1.5"


def test_direction_times_negative():
    assert sanitize_move_to_expr("LEFT * -0.5") == "LEFT * -0.5"


def test_extra_spaces_normalized():
    result = sanitize_move_to_expr("UP * 2")
    assert result == "UP * 2"


def test_invalid_expression_returns_origin():
    assert sanitize_move_to_expr("__import__('os').system('rm -rf /')") == "ORIGIN"


def test_arbitrary_python_code_returns_origin():
    assert sanitize_move_to_expr("exec('malicious')") == "ORIGIN"


def test_unknown_direction_returns_origin():
    assert sanitize_move_to_expr("DIAGONAL * 2") == "ORIGIN"


def test_empty_string_returns_origin():
    assert sanitize_move_to_expr("") == "ORIGIN"


def test_multi_line_expression_normalizes():
    # 줄바꿈이 포함된 입력은 공백 제거 후 유효한 수식으로 파싱되어야 함.
    # regex의 \s*가 줄바꿈도 포함하므로 "UP * 2"로 정규화됨(보안상 안전).
    result = sanitize_move_to_expr("UP\n* 2")
    assert result == "UP * 2"


def test_direction_times_zero():
    result = sanitize_move_to_expr("UP * 0")
    assert result == "UP * 0"


def test_direction_no_multiplier():
    assert sanitize_move_to_expr("RIGHT") == "RIGHT"
