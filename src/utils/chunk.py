"""
src/utils/chunk.py

Text chunking utilities for preparing content for LLM context windows.

LLMs have a finite context window (e.g. 4 096, 8 192, 128 000 tokens).
When a list of scraped items is too large to fit in a single prompt,
it must be split into overlapping or non-overlapping chunks.

Functions:
    chunk_items(items, max_chars, overlap)
        — Split a list of items into groups whose combined text stays
          under `max_chars` characters.

    items_to_text(items)
        — Convert a list of scraped dicts into a single readable string
          suitable for feeding to an LLM.
"""

from __future__ import annotations


def items_to_text(items: list[dict]) -> str:
    """
    Convert a list of scraped item dicts into a single formatted string.

    Each item is rendered as:

        ## <title>
        <body>
        Rating: <rating>   URL: <url>

    Missing fields are silently omitted.

    Args:
        items: List of scraped dicts.

    Returns:
        Multi-line string representation of all items.
    """
    parts: list[str] = []

    for i, item in enumerate(items, start=1):
        title  = item.get("title", "").strip()
        body   = item.get("body", "").strip()
        rating = item.get("rating", "").strip()
        url    = item.get("url", "").strip()

        lines: list[str] = [f"## Item {i}: {title}"] if title else [f"## Item {i}"]
        if body:
            lines.append(body)
        if rating:
            lines.append(f"Rating: {rating}")
        if url:
            lines.append(f"URL: {url}")

        parts.append("\n".join(lines))

    return "\n\n---\n\n".join(parts)


def chunk_items(
    items: list[dict],
    max_chars: int = 12_000,
    overlap: int = 0,
) -> list[list[dict]]:
    """
    Split `items` into chunks so that the rendered text of each chunk
    does not exceed `max_chars` characters.

    Args:
        items:     List of scraped item dicts.
        max_chars: Maximum number of characters per chunk (default 12 000,
                   roughly ~3 000 tokens at 4 chars/token).
        overlap:   Number of items from the previous chunk to repeat at the
                   start of the next chunk (default 0 = no overlap).

    Returns:
        A list of item-lists (chunks). Each inner list is a subset of `items`.

    Example:
        >>> chunks = chunk_items(items, max_chars=8000, overlap=1)
        >>> for chunk in chunks:
        ...     summary = summarize_items(chunk)
    """
    if not items:
        return []

    chunks: list[list[dict]] = []
    current_chunk: list[dict] = []
    current_chars = 0

    for item in items:
        item_text = items_to_text([item])
        item_len  = len(item_text)

        # If a single item already exceeds the limit, put it alone
        if item_len >= max_chars:
            if current_chunk:
                chunks.append(current_chunk)
            chunks.append([item])
            current_chunk = []
            current_chars = 0
            continue

        if current_chars + item_len > max_chars and current_chunk:
            chunks.append(current_chunk)
            # Start new chunk, optionally carrying over `overlap` items
            current_chunk = current_chunk[-overlap:] if overlap > 0 else []
            current_chars = len(items_to_text(current_chunk))

        current_chunk.append(item)
        current_chars += item_len

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
