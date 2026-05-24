"""Tests for canonical DB loader and fuzzy matching."""

from __future__ import annotations

import pytest

from manim_video_gen.models.short import ApplicationStory, StoryFormat
from manim_video_gen.pipeline.short_extractor import (
    CanonicalEntry,
    fuzzy_match_concept,
    load_canonical_db,
)


class TestLoadCanonicalDB:
    """Tests for load_canonical_db()."""

    def test_returns_list_of_canonical_entries(self):
        db = load_canonical_db()
        assert isinstance(db, list)
        assert len(db) >= 20
        for entry in db:
            assert isinstance(entry, CanonicalEntry)

    def test_pvalue_entry_exists(self):
        db = load_canonical_db()
        names = [e.concept_name for e in db]
        assert "p-value" in names

    def test_all_entries_have_valid_stories(self):
        db = load_canonical_db()
        for entry in db:
            assert isinstance(entry.story, ApplicationStory)
            assert entry.story.domain
            assert entry.story.scenario
            assert entry.story.story_format in StoryFormat
            assert 0.0 <= entry.story.confidence <= 1.0


class TestFuzzyMatchConcept:
    """Tests for fuzzy_match_concept()."""

    def test_exact_match_pvalue(self):
        db = load_canonical_db()
        results = fuzzy_match_concept("p-value", db)
        assert len(results) == 1
        assert results[0].confidence >= 0.9
        assert results[0].source == "canonical_db"

    def test_exact_match_gradient(self):
        db = load_canonical_db()
        results = fuzzy_match_concept("gradient", db)
        assert len(results) >= 1

    def test_case_insensitive_match(self):
        db = load_canonical_db()
        results = fuzzy_match_concept("P-Value", db)
        assert len(results) == 1

    def test_unknown_concept_returns_empty(self):
        db = load_canonical_db()
        results = fuzzy_match_concept("quantum_chromodynamics_xyz", db)
        assert results == []

    def test_low_confidence_forces_misconception_or_curiosity(self):
        db = load_canonical_db()
        results = fuzzy_match_concept("p valu", db)
        for r in results:
            if r.confidence < 0.6:
                assert r.story_format in (StoryFormat.MISCONCEPTION, StoryFormat.CURIOSITY)

    def test_empty_query_returns_empty(self):
        db = load_canonical_db()
        results = fuzzy_match_concept("", db)
        assert results == []
