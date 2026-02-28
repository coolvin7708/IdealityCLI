"""
src/cli/scrape.py

Handler for the `scrape` CLI command.

Responsibilities:
  - Route the user's chosen source to the correct scraper module.
  - Print scraped items to stdout in a readable format.
  - Does NOT write to disk (that is `store`'s job).
"""

import argparse
import json

from src.scrapers import reddit, appstore, trustpilot, remoteok


# Map source names → scraper modules
_SCRAPERS = {
    "reddit":    reddit,
    "appstore":  appstore,
    "trustpilot": trustpilot,
    "remoteok":  remoteok,
}


def run_scraper(source: str, query: str) -> list[dict]:
    """
    Dispatch to the correct scraper and return items.

    Args:
        source: One of 'reddit', 'trustpilot', 'appstore', 'remoteok'.
        query:  The search term / identifier to pass to the scraper.

    Returns:
        A list of dicts (may be empty if the scrape found nothing).

    Raises:
        ValueError: If `source` is not a recognised scraper name.
    """
    if source not in _SCRAPERS:
        raise ValueError(
            f"Unknown source '{source}'. "
            f"Valid sources: {', '.join(_SCRAPERS)}"
        )

    scraper_module = _SCRAPERS[source]
    return scraper_module.scrape(query)


def handle_scrape(args: argparse.Namespace) -> None:
    """
    Entry point called from main.py for the `scrape` command.

    Prints each scraped item as pretty-printed JSON to stdout.
    """
    print(f"[scrape] source={args.source}  query={args.query}\n")

    try:
        items = run_scraper(args.source, args.query)
    except Exception as exc:
        print(f"[error] Scraping failed: {exc}")
        return

    if not items:
        print("[info] No items found.")
        return

    print(f"[info] {len(items)} item(s) returned:\n")
    for i, item in enumerate(items, start=1):
        print(f"── Item {i} " + "─" * 40)
        print(json.dumps(item, indent=2, ensure_ascii=False))
        print()
