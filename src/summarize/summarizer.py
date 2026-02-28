"""
src/summarize/summarizer.py

LLM-powered summarizer for scraped item lists.
Uses the Google Gemini API (gemini-2.5-flash — free tier).

Get a free API key at: https://aistudio.google.com/app/apikey
Set GEMINI_API_KEY in the .env file at the project root.

Functions:
    summarize_items(items)   — public entry point; returns Markdown string.
    _call_llm(prompt)        — sends prompt to Gemini and returns response.
    _build_prompt(items)     — construct the prompt from item data.
    _extract_stats(items)    — derive summary statistics from items.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from google import genai
from dotenv import load_dotenv

from src.utils.chunk import items_to_text, chunk_items

# Load variables from the .env file in the project root
# parents: [0]=src/summarize  [1]=src  [2]=project root (IdealityCLI)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


# ── Gemini API configuration ──────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # loaded from .env

# Free-tier model — fast, generous quota, no billing required
GEMINI_MODEL = "gemini-2.5-flash"

# Gemini 2.5-flash supports ~1M token context; 800k chars ≈ 200k tokens — fits ~500 reviews in one call
CHUNK_MAX_CHARS = 800_000


# ── Gemini LLM call ──────────────────────────────────────────────────────────

def _call_llm(prompt: str) -> str:
    """
    Send `prompt` to the Gemini API and return the model's response text.

    Uses the model specified in GEMINI_MODEL (default: gemini-2.0-flash).
    Raises a RuntimeError with a clear message if the API key is not set.

    Args:
        prompt: Full prompt string to send to the model.

    Returns:
        Model response as a plain string.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY_HERE":
        raise RuntimeError(
            "Gemini API key not set.\n"
            "Open src/summarize/summarizer.py and set GEMINI_API_KEY, or\n"
            "get a free key at https://aistudio.google.com/app/apikey"
        )

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(item_text: str) -> str:
    """
    Build the summarisation prompt from pre-rendered item text.

    Args:
        item_text: String output of items_to_text().

    Returns:
        Prompt string ready to pass to the LLM.
    """
    return (
        "You are an expert analyst specialising in user research and "
        "product strategy.\n\n"
        "Below is a collection of scraped data items (reviews, posts, "
        "or job listings). Analyse them and produce a structured Markdown "
        "report covering:\n\n"
        "1. **Top recurring themes** (what do people mention most?)\n"
        "2. **Pain points** (frustrations, complaints, unmet needs)\n"
        "3. **Positive signals** (what users love)\n"
        "4. **Opportunities** (product/market gaps visible in the data)\n"
        "5. **Notable quotes** (2-4 verbatim excerpts worth highlighting)\n\n"
        "---\n\n"
        f"{item_text}"
    )


def _build_merge_prompt(partial_summaries: str) -> str:
    """
    Build a prompt that merges multiple partial summaries into one final report.
    """
    return (
        "You are an expert analyst specialising in user research and product strategy.\n\n"
        "The following are partial summaries from different batches of the same dataset. "
        "Synthesise them into a single cohesive Markdown report covering:\n\n"
        "1. **Top recurring themes**\n"
        "2. **Pain points**\n"
        "3. **Positive signals**\n"
        "4. **Opportunities**\n"
        "5. **Notable quotes** (2-4 verbatim excerpts)\n\n"
        "Eliminate redundancy — produce one unified report, not a list of summaries.\n\n"
        "---\n\n"
        f"{partial_summaries}"
    )


# ── Statistics extractor ──────────────────────────────────────────────────────

def _extract_stats(items: list[dict]) -> dict:
    """
    Derive simple statistics from the scraped items.

    Returns a dict with:
        total         — total number of items
        with_rating   — items that have a non-empty 'rating' field
        avg_rating    — average numeric rating (None if not applicable)
        sources       — set of unique source URLs (domains)
    """
    import re
    from urllib.parse import urlparse

    ratings: list[float] = []
    sources: set[str] = set()

    for item in items:
        raw_rating = item.get("rating", "")
        if raw_rating:
            match = re.search(r"[\d.]+", str(raw_rating))
            if match:
                try:
                    ratings.append(float(match.group()))
                except ValueError:
                    pass

        url = item.get("url", "")
        if url:
            parsed = urlparse(url)
            if parsed.netloc:
                sources.add(parsed.netloc)

    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

    return {
        "total":       len(items),
        "with_rating": len(ratings),
        "avg_rating":  avg_rating,
        "sources":     sorted(sources),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def summarize_items(items: list[dict]) -> str:
    """
    Generate a Markdown summary for a list of scraped items.

    If the items are too large to fit in a single LLM context window
    (> 12 000 rendered characters), they are chunked and each chunk is
    summarised separately; the results are then concatenated.

    Args:
        items: List of scraped dicts (from any scraper).

    Returns:
        Markdown string — the LLM synthesis (or placeholder summary).
    """
    if not items:
        return "# Summary\n\nNo items to summarise."

    stats = _extract_stats(items)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Header block
    header = (
        "# IdealityCLI Summary\n\n"
        f"**Generated:** {generated_at}  \n"
        f"**Items analysed:** {stats['total']}  \n"
    )

    if stats["avg_rating"] is not None:
        header += f"**Average rating:** {stats['avg_rating']} / 5  \n"

    if stats["sources"]:
        sources_list = ", ".join(f"`{s}`" for s in stats["sources"])
        header += f"**Sources:** {sources_list}  \n"

    header += "\n---\n\n"

    # Chunk if needed and summarise
    chunks = chunk_items(items, max_chars=CHUNK_MAX_CHARS)
    total_chunks = len(chunks)

    if total_chunks == 1:
        print(f"[summarize] Sending all {len(items)} items to Gemini in 1 request …")
        llm_text = _call_llm(_build_prompt(items_to_text(items)))
        body = llm_text
    else:
        # Multi-chunk: summarise each chunk then merge into one final report
        print(f"[summarize] Input too large — splitting into {total_chunks} chunks …")
        chunk_summaries: list[str] = []

        for idx, chunk in enumerate(chunks, start=1):
            print(f"[summarize] Chunk {idx}/{total_chunks} — calling Gemini …")
            llm_text = _call_llm(_build_prompt(items_to_text(chunk)))
            chunk_summaries.append(llm_text)

        print(f"[summarize] Merging {total_chunks} partial summaries …")
        body = _call_llm(_build_merge_prompt("\n\n---\n\n".join(chunk_summaries)))

    return header + body
