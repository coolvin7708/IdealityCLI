"""
src/scrapers/appstore.py

Fetches App Store customer reviews using Apple's official iTunes RSS JSON API.

This avoids JavaScript rendering entirely. The API returns up to 500 reviews
(10 pages × 50 reviews) for any app.

Endpoints:
    Reviews RSS:
        https://itunes.apple.com/us/rss/customerreviews/page={n}/id={id}/sortby=mostrecent/json
    App lookup (name → ID):
        https://itunes.apple.com/search?term={name}&entity=software&limit=5

Each returned item contains:
    - title    : review title
    - body     : review text
    - rating   : star rating (1–5) as a string
    - url      : app store page URL
    - author   : reviewer display name
    - metadata : dict with app_id, date, version
"""

import re
import time
import urllib.parse
import requests

from src.utils.text import clean_text

HEADERS = {
    "User-Agent": "IdealityCLI/1.0 (personal research tool)",
    "Accept": "application/json",
}

RSS_URL    = "https://itunes.apple.com/us/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
LOOKUP_URL = "https://itunes.apple.com/search"
MAX_PAGES  = 10   # Apple's RSS API supports pages 1–10 (50 reviews each = 500 max)
CRAWL_DELAY = 0.5


def _resolve_app_id(query: str) -> tuple[str, str]:
    """
    Return (app_id, store_url) for the query.

    If the query is already a numeric ID, return it directly.
    Otherwise search the iTunes API for a matching app and return its ID.
    """
    query = query.strip()

    if re.fullmatch(r"\d+", query):
        store_url = f"https://apps.apple.com/us/app/id{query}"
        return query, store_url

    # Name slug → look up via iTunes Search API
    print(f"[appstore] Looking up app ID for '{query}' …")
    try:
        response = requests.get(
            LOOKUP_URL,
            params={"term": query, "entity": "software", "limit": 5},
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except Exception as exc:
        print(f"[appstore] Lookup failed: {exc}")
        return "", ""

    if not results:
        print(f"[appstore] No app found for '{query}'.")
        return "", ""

    app = results[0]
    app_id    = str(app.get("trackId", ""))
    app_name  = app.get("trackName", query)
    store_url = app.get("trackViewUrl", f"https://apps.apple.com/us/app/id{app_id}")
    print(f"[appstore] Resolved to: {app_name} (id={app_id})")
    time.sleep(CRAWL_DELAY)
    return app_id, store_url


def _fetch_page(app_id: str, page: int) -> list[dict]:
    """Fetch one page of reviews from the iTunes RSS API. Returns raw entry list."""
    url = RSS_URL.format(page=page, app_id=app_id)
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[appstore] Page {page} request failed: {exc}")
        return []

    time.sleep(CRAWL_DELAY)

    try:
        data = response.json()
    except Exception as exc:
        print(f"[appstore] Page {page} JSON parse failed: {exc}")
        return []

    return data.get("feed", {}).get("entry", [])


def scrape(query: str) -> list[dict]:
    """
    Fetch up to 500 App Store reviews for an app using Apple's RSS JSON API.

    Args:
        query: Numeric App Store ID (e.g. '6480417616') or name slug
               (e.g. 'notion').

    Returns:
        List of review dicts; empty list on failure.
    """
    app_id, store_url = _resolve_app_id(query)
    if not app_id:
        return []

    print(f"[appstore] Fetching reviews for app id={app_id} (up to {MAX_PAGES} pages) …")

    items: list[dict] = []

    for page in range(1, MAX_PAGES + 1):
        entries = _fetch_page(app_id, page)

        # Page 1 contains an extra "app info" entry at index 0 — skip it
        if page == 1 and entries:
            entries = entries[1:]

        if not entries:
            print(f"[appstore] No more reviews at page {page}. Stopping.")
            break

        for entry in entries:
            def _label(key: str) -> str:
                node = entry.get(key, {})
                return clean_text(str(node.get("label", ""))) if isinstance(node, dict) else ""

            title   = _label("title")
            body    = _label("content")
            rating  = _label("im:rating")
            author  = _label("author") or entry.get("author", {}).get("name", {}).get("label", "")
            version = _label("im:version")
            date    = _label("updated")

            items.append({
                "title":    title,
                "body":     body,
                "rating":   rating,
                "url":      store_url,
                "author":   clean_text(str(author)),
                "metadata": {
                    "app_id":  app_id,
                    "date":    date,
                    "version": version,
                },
            })

        print(f"[appstore] Page {page}: {len(entries)} review(s) collected (total so far: {len(items)})")

    print(f"[appstore] Done. Total reviews collected: {len(items)}")
    return items
