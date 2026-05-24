"""Prompts: document -> ShortSeriesPlan JSON extraction."""

from __future__ import annotations

import json
import re

from manim_video_gen.models.short import ShortSeriesPlan

EXTRACT_SHORTS_SYSTEM_PROMPT = """You extract math concepts from a document and produce a ShortSeriesPlan JSON.
Return ONLY valid JSON (no markdown fences) matching this schema:
{
  "title": string,
  "units": [
    {
      "id": string (e.g. "unit-001"),
      "headline": string (attention-grabbing Korean title, NO concept name),
      "concept_name": string (math concept name),
      "core_insight": string (one-sentence why-it-matters),
      "story": {
        "story_format": "application" | "misconception" | "stakes" | "curiosity" | "pattern",
        "confidence": float (0.0~1.0),
        "source": "document" | "canonical_db" | "synthesized",
        "domain": string,
        "domain_label": string,
        "scenario": string (beat 1 — concrete situation),
        "problem_in_domain": string (beat 2 — what goes wrong),
        "concept_bridge": string (beat 3 — how math solves it),
        "application_result": string (beat 4 — what happens),
        "result_visual": string (visual description of result),
        "payoff_line": string (beat 5 — closing line)
      },
      "explanation": string (detailed Korean explanation),
      "visual_concept": string (main visual elements),
      "result_visual_concept": string,
      "visual_type": string (default visual type),
      "difficulty": int (1-5),
      "prerequisites": [string],
      "estimated_seconds": int (15-60)
    }
  ],
  "recommended_order": [string]
}

## Rules
- Extract 1-5 distinct math concepts from the document
- Each unit must be self-contained (watchable as a standalone short)
- headline must NOT contain the concept_name (delayed labeling)
- estimated_seconds must be between 15 and 60
- story.scenario must be a concrete, relatable situation
- story.problem_in_domain must create tension
- story.payoff_line must tie back to the hook
- recommended_order uses unit ids; order by difficulty (easiest first)
- If concepts have prerequisites, respect dependency order
"""


def extract_shorts_user_prompt(document_text: str) -> str:
    """Build user prompt for ShortSeriesPlan extraction."""
    return (
        "다음 문서에서 수학 개념을 추출하여 ShortSeriesPlan JSON으로 만드세요.\n"
        "각 개념은 독립적인 숏폼 영상이 될 수 있어야 합니다.\n"
        "headline에는 개념 이름을 절대 포함하지 마세요.\n\n"
        f"[문서]\n{document_text}\n"
    )


def parse_extract_shorts_response(response: str) -> ShortSeriesPlan:
    """Parse LLM response into ShortSeriesPlan."""
    text = response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    data = json.loads(text)
    return ShortSeriesPlan(**data)
