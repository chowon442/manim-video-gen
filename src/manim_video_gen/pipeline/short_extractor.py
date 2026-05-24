"""Canonical application DB loader and fuzzy matching utilities."""

from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from manim_video_gen.models.short import ApplicationStory, StoryFormat

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CANDB_PATH = _DATA_DIR / "canonical_applications.json"

_CONFIDENCE_THRESHOLD = 0.6


class CanonicalEntry(BaseModel):
    """A canonical DB entry: concept_name + its application story."""

    concept_name: str = Field(
        ...,
        description="Name of the math concept (e.g. 'p-value')",
    )
    story: ApplicationStory = Field(
        ...,
        description="The application story for this concept",
    )


def load_canonical_db() -> list[CanonicalEntry]:
    """Load canonical applications DB from JSON seed file.

    Returns:
        List of CanonicalEntry objects parsed from the canonical DB.
    """
    with open(_CANDB_PATH, encoding="utf-8") as f:
        raw: list[dict[str, Any]] = json.load(f)
    entries: list[CanonicalEntry] = []
    for item in raw:
        concept_name = item.pop("concept_name")
        entries.append(CanonicalEntry(
            concept_name=concept_name,
            story=ApplicationStory(**item),
        ))
    return entries


def _similarity(a: str, b: str) -> float:
    """Compute case-insensitive similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def fuzzy_match_concept(
    query: str,
    db: list[CanonicalEntry],
    *,
    limit: int = 5,
) -> list[ApplicationStory]:
    """Fuzzy-match a concept name against the canonical DB.

    Args:
        query: Concept name to search for.
        db: List of CanonicalEntry entries to search against.
        limit: Maximum number of results to return.

    Returns:
        Matched ApplicationStory entries sorted by descending confidence.
        Entries with confidence < 0.6 are forced to MISCONCEPTION or CURIOSITY.
        Empty list if no match exceeds threshold or query is empty.
    """
    if not query or not query.strip():
        return []

    scored: list[tuple[float, ApplicationStory]] = []
    for entry in db:
        sim = _similarity(query, entry.concept_name)
        if sim >= _CONFIDENCE_THRESHOLD:
            adjusted_confidence = round(entry.story.confidence * sim, 2)
            forced_format = _maybe_force_format(entry.story.story_format, adjusted_confidence)
            scored.append((
                adjusted_confidence,
                entry.story.model_copy(update={
                    "confidence": adjusted_confidence,
                    "story_format": forced_format,
                }),
            ))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [story for _, story in scored[:limit]]


def _maybe_force_format(fmt: StoryFormat, confidence: float) -> StoryFormat:
    """Force low-confidence matches to misconception or curiosity format."""
    if confidence < _CONFIDENCE_THRESHOLD:
        return StoryFormat.MISCONCEPTION if fmt != StoryFormat.CURIOSITY else StoryFormat.CURIOSITY
    return fmt
