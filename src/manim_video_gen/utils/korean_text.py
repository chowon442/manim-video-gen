"""Korean text utilities for short-form quality checks."""

from __future__ import annotations

import re

# Common English stopwords to exclude from token matching.
_ENGLISH_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "about",
        "between",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "so",
        "if",
        "then",
        "than",
        "too",
        "very",
        "just",
        "that",
        "this",
        "it",
        "its",
        "they",
        "them",
        "their",
        "we",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
    }
)
# Order matters: longer particles first to avoid partial matches.
_PARTICLES = (
    "으로",
    "로",
    "에서",
    "에게",
    "한테",
    "께",
    "까지",
    "부터",
    "만",
    "도",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "와",
    "과",
    "랑",
    "이랑",
)

_PARTICLE_RE = re.compile(
    r"(?<=[가-힣])(" + "|".join(re.escape(p) for p in _PARTICLES) + r")$"
)

# Matches numbers with optional decimal, percentage, parentheses, units.
# e.g. "0.014(1.4%)" → "0.014", "100원" → "100"
_NUM_WITH_EXTRAS = re.compile(r"\d+(?:\.\d+)?(?:\s*[%]|\s*\([^)]*\))?")

# Matches standalone alphanumeric tokens (English + digits).
_ALNUM_TOKEN = re.compile(r"[a-zA-Z][a-zA-Z0-9._-]*|[0-9]+(?:\.[0-9]+)?")


def _strip_particle(word: str) -> str:
    """Strip a trailing Korean particle from a word."""
    m = _PARTICLE_RE.search(word)
    if m:
        return word[: m.start()]
    return word


def _normalize_number(token: str) -> str:
    """Extract the core numeric value, stripping parentheses and units."""
    m = _NUM_WITH_EXTRAS.match(token)
    if m:
        return m.group(0).split("(")[0].strip().rstrip("%")
    return token


def extract_content_tokens(text: str) -> set[str]:
    """Extract normalized content tokens from Korean/mixed text.

    Steps:
    1. Split on whitespace
    2. Strip Korean particles from each word
    3. Extract alphanumeric tokens (English words, numbers)
    4. Normalize numbers (remove brackets, units, percentages)
    5. Lowercase all tokens
    6. Remove very short tokens (length < 2), stopwords
    """
    if not text:
        return set()

    tokens: set[str] = set()
    words = text.split()

    for word in words:
        # Strip Korean particles
        stripped = _strip_particle(word)
        if not stripped:
            continue

        # Extract alphanumeric tokens from the stripped word
        # This handles mixed text like "p-value가" → "p-value"
        alnum_matches = _ALNUM_TOKEN.findall(stripped)
        for tok in alnum_matches:
            # Normalize numbers
            if tok and tok[0].isdigit():
                tok = _normalize_number(tok)
            tok_lower = tok.lower()
            if len(tok_lower) >= 2 and tok_lower not in _ENGLISH_STOPWORDS:
                tokens.add(tok_lower)

        # Also check for pure Korean content words (after particle strip)
        remaining = _ALNUM_TOKEN.sub("", stripped).strip()
        if remaining and len(remaining) >= 2:
            tokens.add(remaining.lower())

    return tokens


def payoff_references_application(
    application_result: str,
    payoff_line: str,
) -> bool:
    """Check if payoff_line semantically references application_result.

    Uses normalized token overlap with substring fallback:
    1. Extract content tokens from both texts
    2. If overlap >= 1 → True
    3. Substring fallback: if any app_result token is a substring of
       payoff_line (or vice versa) → True
    4. Otherwise → False
    """
    if not application_result or not payoff_line:
        return False

    app_tokens = extract_content_tokens(application_result)
    payoff_tokens = extract_content_tokens(payoff_line)

    if not app_tokens or not payoff_tokens:
        return False

    # Direct token overlap
    overlap = app_tokens & payoff_tokens
    if len(overlap) >= 1:
        return True

    # Substring fallback: check if any app token appears as substring
    # in the raw payoff text (handles cases where tokenization differs).
    # For Korean we allow length >= 2 (many core nouns are 2 chars);
    # for ASCII we keep >= 3 to avoid false positives on stopwords.
    payoff_lower = payoff_line.lower()
    for tok in app_tokens:
        min_len = 2 if any(ord(c) > 127 for c in tok) else 3
        if len(tok) >= min_len and tok in payoff_lower:
            return True

    app_lower = application_result.lower()
    for tok in payoff_tokens:
        min_len = 2 if any(ord(c) > 127 for c in tok) else 3
        if len(tok) >= min_len and tok in app_lower:
            return True

    return False
