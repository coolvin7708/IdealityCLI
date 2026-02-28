"""
src/utils/text.py

Text cleaning and search helper functions.

Functions:
    clean_text(raw)              — strip excess whitespace / control chars.
    contains_keyword(item, kw)   — case-insensitive keyword search in a dict.
    flatten_dict_values(d)       — recursively collect all string values from a dict.
"""

import re


def clean_text(raw: str) -> str:
    """
    Normalise a raw string scraped from HTML.

    - Collapses consecutive whitespace (spaces, tabs, newlines) into a
      single space.
    - Strips leading / trailing whitespace.
    - Removes common zero-width Unicode characters.

    Args:
        raw: The raw input string.

    Returns:
        Cleaned string.
    """
    if not isinstance(raw, str):
        raw = str(raw)

    # Remove zero-width spaces and similar invisible characters
    raw = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", raw)

    # Collapse all whitespace sequences into a single space
    raw = re.sub(r"\s+", " ", raw)

    return raw.strip()


def flatten_dict_values(d: dict) -> list[str]:
    """
    Recursively extract every string value from a (possibly nested) dict.

    Useful for full-text searching across all fields of a scraped item.

    Args:
        d: Input dictionary.

    Returns:
        Flat list of string values found anywhere in the dict tree.
    """
    results: list[str] = []

    for value in d.values():
        if isinstance(value, str):
            results.append(value)
        elif isinstance(value, dict):
            results.extend(flatten_dict_values(value))
        elif isinstance(value, list):
            for element in value:
                if isinstance(element, str):
                    results.append(element)
                elif isinstance(element, dict):
                    results.extend(flatten_dict_values(element))

    return results


def contains_keyword(item: dict, keyword: str) -> bool:
    """
    Return True if `keyword` appears (case-insensitively) anywhere in the
    string values of `item`.

    Searches: all top-level string fields and all values inside nested
    dict/list structures (via flatten_dict_values).

    Args:
        item:    A scraped data dict.
        keyword: Search term.

    Returns:
        True if the keyword matches at least one field value, else False.
    """
    needle = keyword.lower()
    for text in flatten_dict_values(item):
        if needle in text.lower():
            return True
    return False
