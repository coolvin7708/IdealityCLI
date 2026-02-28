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

    Scrapes data and writes it to disk as JSON.
    """
    source = args.source
    identifier = args.identifier

    print(f"[store] Scraping {source!r} for {identifier!r} …")

    try:
        items = run_scraper(source, identifier)
    except Exception as exc:
        print(f"[error] Scraping failed: {exc}")
        return

    if not items:
        print("[warn] Scraper returned 0 items — nothing written.")
        return

    path = get_data_path(source, identifier)

    try:
        write_json(path, items)
    except Exception as exc:
        print(f"[error] Could not write file: {exc}")
        return

    print(f"[store] {len(items)} item(s) saved → {path}")
