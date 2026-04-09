"""Tests for animation duration caps (front-loaded motion)."""

import pytest

from manim_video_gen.video.anim_timing import (
    ANIM_CAP_TRANSFORM,
    ANIM_CAP_WRITE,
    split_n_writes,
    split_transform,
    split_write,
)


def test_split_write_caps_long_duration():
    t, w = split_write(10.0)
    assert t <= ANIM_CAP_WRITE
    assert t + w == pytest.approx(10.0, abs=0.02)


def test_split_transform_caps():
    t, w = split_transform(8.0)
    assert t <= ANIM_CAP_TRANSFORM
    assert t + w == pytest.approx(8.0, abs=0.02)


def test_split_n_writes_sums_to_duration():
    t_each, t_wait = split_n_writes(5.0, 3, fade_in=0.0)
    assert t_each <= ANIM_CAP_WRITE
    assert 3 * t_each + t_wait == pytest.approx(5.0, abs=0.02)
