"""
src/cli/store.py

Handler for the `store` CLI command.

Responsibilities:
  - Call the appropriate scraper for source + identifier.
  - Persist the result to /data/<source>/<identifier>.json.
  - Create the target directory if it does not already exist.
"""

import argparse
from pathlib import Path

from src.cli.scrape import run_scraper
from src.utils.fileio import write_json
from src.utils.filter import filter_items, filter_and_annotate

# Root data directory — relative to the project root (i.e. alongside main.py)
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def get_data_path(source: str, identifier: str) -> Path:
    """
    Return the full path where JSON data for this source+identifier lives.

    Example:
        source="reddit", identifier="python"
        → <project_root>/data/reddit/python.json
    """
    # Sanitise the identifier so it is safe to use as a filename
    safe_id = identifier.replace(" ", "_").replace("/", "-")
    return DATA_DIR / source / f"{safe_id}.json"


def handle_store(args: argparse.Namespace) -> None:
    """
    Entry point called from main.py for the `store` command.

    Scrapes data, optionally filters by quality, and writes to disk as JSON.

    Optional flags on args:
        min_quality (int)  : drop items below this quality score (default 0 = keep all)
        annotate    (bool) : attach quality_score + flagged fields to each item
    """
    source     = args.source
    identifier = args.identifier
    min_q      = getattr(args, "min_quality", 0) or 0
    annotate   = getattr(args, "annotate",    False)

    print(f"[store] Scraping {source!r} for {identifier!r} …")

    try:
        items = run_scraper(source, identifier)
    except Exception as exc:
        print(f"[error] Scraping failed: {exc}")
        return

    if not items:
        print("[warn] Scraper returned 0 items — nothing written.")
        return

    original_count = len(items)

    # ── Quality annotation ────────────────────────────────────────────────
    if annotate:
        items = filter_and_annotate(items)
        flagged = sum(1 for it in items if it.get("flagged"))
        print(f"[store] Annotated {len(items)} items · {flagged} flagged as low-quality")

    # ── Quality filtering ─────────────────────────────────────────────────
    if min_q > 0:
        items = filter_items(items, min_quality=min_q)
        dropped = original_count - len(items)
        if dropped:
            print(f"[store] Filtered out {dropped} low-quality item(s) (min-quality={min_q})")
        if not items:
            print("[warn] All items were below the quality threshold — nothing written.")
            return

    path = get_data_path(source, identifier)

    try:
        write_json(path, items)
    except Exception as exc:
        print(f"[error] Could not write file: {exc}")
        return

    print(f"[store] {len(items)} item(s) saved → {path}")
