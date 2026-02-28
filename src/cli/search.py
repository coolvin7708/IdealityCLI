"""
src/cli/search.py

Handler for the `search` CLI command.

Responsibilities:
  - Walk every JSON file under /data.
  - Search each stored list of items for the given keyword (case-insensitive).
  - Print matching items with a reference to the source file.
"""

import argparse
import json
from pathlib import Path

from src.utils.text import contains_keyword

# Root data directory
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def search_all_files(keyword: str) -> list[dict]:
    """
    Walk all JSON files under DATA_DIR and return items that contain `keyword`.

    Each result dict carries an extra '_source_file' key indicating which
    file the match came from.

    Args:
        keyword: Case-insensitive search term.

    Returns:
        List of matching item dicts, each annotated with '_source_file'.
    """
    matches: list[dict] = []

    json_files = list(DATA_DIR.rglob("*.json"))

    if not json_files:
        return matches

    for filepath in json_files:
        try:
            with filepath.open(encoding="utf-8") as fh:
                items = json.load(fh)
        except (json.JSONDecodeError, OSError):
            # Skip corrupt or unreadable files silently
            continue

        if not isinstance(items, list):
            # All stored data is a list of dicts; skip anything malformed
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            if contains_keyword(item, keyword):
                annotated = dict(item)
                annotated["_source_file"] = str(
                    filepath.relative_to(DATA_DIR.parent)
                )
                matches.append(annotated)

    return matches


def handle_search(args: argparse.Namespace) -> None:
    """
    Entry point called from main.py for the `search` command.

    Searches all stored JSON and prints matching items to stdout.
    """
    keyword = args.keyword
    print(f'[search] Searching for "{keyword}" across all stored data …\n')

    if not DATA_DIR.exists():
        print("[info] No data directory found. Run `store` first.")
        return

    results = search_all_files(keyword)

    if not results:
        print(f'[info] No matches found for "{keyword}".')
        return

    print(f"[info] {len(results)} match(es):\n")
    for i, item in enumerate(results, start=1):
        source_file = item.pop("_source_file", "unknown")
        print(f"── Match {i}  [{source_file}] " + "─" * 30)
        print(json.dumps(item, indent=2, ensure_ascii=False))
        print()
