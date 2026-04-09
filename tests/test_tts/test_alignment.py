"""_alignment_to_words() 다양한 입력 및 타임스탬프 테스트."""

from manim_video_gen.tts.elevenlabs import _alignment_to_words


def test_empty_alignment():
    assert _alignment_to_words({}) == []


def test_empty_characters():
    alignment = {"characters": [], "character_start_times_seconds": [], "character_end_times_seconds": []}
    assert _alignment_to_words(alignment) == []


def test_single_word():
    alignment = {
        "characters": ["H", "i"],
        "character_start_times_seconds": [0.0, 0.1],
        "character_end_times_seconds": [0.1, 0.2],
    }
    result = _alignment_to_words(alignment)
    assert result == [{"word": "Hi", "start": 0.0, "end": 0.2}]


def test_two_words_separated_by_space():
    alignment = {
        "characters": ["H", "i", " ", "Y", "o", "u"],
        "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
        "character_end_times_seconds": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    }
    result = _alignment_to_words(alignment)
    assert len(result) == 2
    assert result[0] == {"word": "Hi", "start": 0.0, "end": 0.2}
    assert result[1] == {"word": "You", "start": 0.3, "end": 0.6}


def test_korean_characters():
    alignment = {
        "characters": ["안", "녕", " ", "세", "계"],
        "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3, 0.4],
        "character_end_times_seconds": [0.1, 0.2, 0.3, 0.4, 0.5],
    }
    result = _alignment_to_words(alignment)
    assert len(result) == 2
    assert result[0]["word"] == "안녕"
    assert result[1]["word"] == "세계"


def test_timestamps_are_floats():
    alignment = {
        "characters": ["A", "B"],
        "character_start_times_seconds": [0, 1],
        "character_end_times_seconds": [1, 2],
    }
    result = _alignment_to_words(alignment)
    assert isinstance(result[0]["start"], float)
    assert isinstance(result[0]["end"], float)


def test_trailing_space_ignored():
    alignment = {
        "characters": ["A", " "],
        "character_start_times_seconds": [0.0, 0.5],
        "character_end_times_seconds": [0.5, 1.0],
    }
    result = _alignment_to_words(alignment)
    assert len(result) == 1
    assert result[0]["word"] == "A"


def test_leading_space_ignored():
    alignment = {
        "characters": [" ", "B"],
        "character_start_times_seconds": [0.0, 0.5],
        "character_end_times_seconds": [0.5, 1.0],
    }
    result = _alignment_to_words(alignment)
    assert len(result) == 1
    assert result[0]["word"] == "B"


def test_mismatched_lengths_returns_empty():
    alignment = {
        "characters": ["A", "B", "C"],
        "character_start_times_seconds": [0.0, 0.5],
        "character_end_times_seconds": [0.5, 1.0],
    }
    assert _alignment_to_words(alignment) == []


def test_missing_keys_returns_empty():
    assert _alignment_to_words({"characters": ["A"]}) == []


def test_timestamps_in_order():
    alignment = {
        "characters": ["A", "B", " ", "C"],
        "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3],
        "character_end_times_seconds": [0.1, 0.2, 0.3, 0.4],
    }
    result = _alignment_to_words(alignment)
    for word in result:
        assert word["start"] <= word["end"]
