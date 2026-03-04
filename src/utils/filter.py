"""
src/utils/filter.py

Rule-based quality scoring and filtering for scraped review/post items.

Each item receives a `quality_score` between 0 and 100.
Items below a threshold can be removed before storing or summarising.

Scoring rules (deductions from 100):
  -30  body is empty or missing
  -20  body is fewer than 20 words
  -15  body is ALL CAPS (>80% uppercase letters)
  -15  body matches a generic filler phrase
  -10  author is missing / [deleted]
  -10  title and body are identical (copy-paste artifact)
  - 5  body contains excessive punctuation (!!! or ???)

Functions:
    score_item(item)             → int 0–100
    flag_item(item)              → dict with added quality_score + flagged fields
    filter_items(items, min_q)   → filtered list
    filter_and_annotate(items)   → all items with scores attached (no removal)
"""

from __future__ import annotations

import re

# ── Generic filler phrases that signal low-quality/fake reviews ──────────────
_FILLER_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^(great|good|bad|nice|awesome|excellent|terrible|horrible)\s+(product|app|service|tool|software)\.?$",
        r"^highly recommend(ed)?\.?$",
        r"^(five|4|5|1|2|3)\s+stars?\.?$",
        r"^(love|hate)\s+(it|this)\.?$",
        r"^(best|worst)\s+(ever|product|app|purchase)\.?$",
        r"^(not\s+)?worth\s+(the\s+)?(money|price|time)\.?$",
        r"^(works?|does(n['\u2019]t)?\s+work)\.?$",
        r"^(perfect|amazing|wonderful|excellent)\.?$",
        r"^no\s+complaints?\.?$",
        r"^very\s+(good|bad|nice|helpful|useful)\.?$",
    ]
]


def _word_count(text: str) -> int:
    return len(text.split())


def _is_all_caps(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    return sum(1 for c in letters if c.isupper()) / len(letters) > 0.80


def _is_filler(text: str) -> bool:
    stripped = text.strip()
    return any(p.fullmatch(stripped) for p in _FILLER_PATTERNS)


def _has_excessive_punctuation(text: str) -> bool:
    return bool(re.search(r"[!?]{3,}", text))


def score_item(item: dict) -> int:
    """
    Compute a quality score (0–100) for a scraped item.

    Higher = better quality. Applied deductions are non-overlapping where
    possible; minimum score is clamped to 0.

    Args:
        item: A scraped dict with at least 'title', 'body', 'author' fields.

    Returns:
        Integer quality score 0–100.
    """
    score = 100
    body   = str(item.get("body",   "") or "").strip()
    title  = str(item.get("title",  "") or "").strip()
    author = str(item.get("author", "") or "").strip()

    # ── Body completeness ────────────────────────────────────────────────────
    if not body:
        score -= 30
    else:
        if _word_count(body) < 20:
            score -= 20
        if _is_all_caps(body):
            score -= 15
        if _is_filler(body):
            score -= 15
        if _has_excessive_punctuation(body):
            score -= 5

    # ── Author check ─────────────────────────────────────────────────────────
    if not author or author.lower() in ("[deleted]", "anonymous", "", "none"):
        score -= 10

    # ── Title == body (copy-paste artifact) ──────────────────────────────────
    if title and body and title.lower() == body.lower():
        score -= 10

    return max(0, score)


def flag_item(item: dict) -> dict:
    """
    Return a copy of `item` with two extra fields appended:
        quality_score  (int 0–100)
        flagged        (bool — True if score < 50)

    Args:
        item: Original scraped dict.

    Returns:
        New dict with quality metadata added.
    """
    annotated = dict(item)
    q = score_item(item)
    annotated["quality_score"] = q
    annotated["flagged"] = q < 50
    return annotated


def filter_items(items: list[dict], min_quality: int = 50) -> list[dict]:
    """
    Return only the items whose quality score meets or exceeds `min_quality`.

    Items that were not previously scored are scored on-the-fly.

    Args:
        items:       List of scraped dicts.
        min_quality: Minimum score threshold (default 50). Range 0–100.

    Returns:
        Filtered list. Items retain their original structure (no extra fields
        added by this function — use flag_item to annotate before storing).
    """
    return [item for item in items if score_item(item) >= min_quality]


def filter_and_annotate(items: list[dict]) -> list[dict]:
    """
    Score every item and return the full list with quality metadata attached.
    Does NOT remove any items — use this when you want all data preserved
    but annotated for downstream inspection.

    Args:
        items: List of scraped dicts.

    Returns:
        List of dicts each with `quality_score` and `flagged` fields.
    """
    return [flag_item(item) for item in items]
