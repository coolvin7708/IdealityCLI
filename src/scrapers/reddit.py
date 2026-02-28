"""
src/scrapers/reddit.py

Scrapes Reddit posts using Reddit's public JSON API (no auth required).

Behaviour:
  - If the query looks like a subreddit name (no spaces, valid chars),
    fetch the subreddit using multiple sort orders (hot, top/all, top/year, new).
  - Otherwise treat the query as a search term and:
      1. Run site-wide searches across multiple sort orders and time filters.
      2. Discover related subreddits via /subreddits/search.json.
      3. Scrape hot posts from each discovered subreddit.
      4. Deduplicate all results by permalink.

Each returned item contains:
    - title    : post title
    - body     : selftext (empty string for link posts)
    - url      : full permalink URL
    - score    : upvote score (int as string)
    - comments : number of comments (int as string)
    - author   : post author username
    - metadata : dict with subreddit, flair
"""

import re
import time
import urllib.parse
import requests

from src.utils.text import clean_text

# Reddit requires a descriptive User-Agent; generic browser strings get blocked.
HEADERS = {
    "User-Agent": "IdealityCLI/1.0 (personal research tool)",
    "Accept": "application/json",
}

SEARCH_URL        = "https://www.reddit.com/search.json"
SUBREDDIT_URL     = "https://www.reddit.com/r/{subreddit}.json"
SUBREDDIT_SORT_URL = "https://www.reddit.com/r/{subreddit}/{sort}.json"
SUBREDDIT_SEARCH_URL = "https://www.reddit.com/subreddits/search.json"

CRAWL_DELAY = 1.5   # seconds between requests (polite rate limit)
MAX_SUBREDDITS = 10  # how many discovered subreddits to scrape


def _is_subreddit_name(query: str) -> bool:
    """Return True if query looks like a valid subreddit name (no spaces, safe chars)."""
    return bool(re.fullmatch(r"[A-Za-z0-9_]{1,21}", query.strip()))


def _fetch_json(url: str, params: dict | None = None) -> dict:
    """
    GET a Reddit JSON endpoint and return the parsed response.
    Returns an empty dict on any failure.
    """
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[reddit] Request failed ({url}): {exc}")
        return {}
    time.sleep(CRAWL_DELAY)
    try:
        return response.json()
    except Exception as exc:
        print(f"[reddit] Failed to parse JSON: {exc}")
        return {}


def _extract_posts(data: dict) -> list[dict]:
    """Parse a Reddit listing JSON response into a list of post dicts."""
    items: list[dict] = []
    children = data.get("data", {}).get("children", [])

    for child in children:
        post = child.get("data", {})
        if not post:
            continue

        title     = clean_text(post.get("title", ""))
        body      = clean_text(post.get("selftext", ""))
        score     = str(post.get("score", ""))
        comments  = str(post.get("num_comments", ""))
        author    = post.get("author", "[deleted]")
        flair     = post.get("link_flair_text") or ""
        subreddit = post.get("subreddit", "")
        permalink = "https://www.reddit.com" + post.get("permalink", "")

        items.append({
            "title":    title,
            "body":     body,
            "url":      permalink,
            "score":    score,
            "comments": comments,
            "author":   author,
            "metadata": {
                "subreddit": subreddit,
                "flair":     flair,
            },
        })

    return items


def _deduplicate(items: list[dict]) -> list[dict]:
    """Remove duplicate posts by URL, preserving insertion order."""
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(item)
    return unique


def _discover_subreddits(query: str) -> list[str]:
    """
    Search Reddit for subreddits related to `query`.
    Returns up to MAX_SUBREDDITS subreddit names.
    """
    print(f"[reddit] Discovering related subreddits for '{query}' …")
    data = _fetch_json(SUBREDDIT_SEARCH_URL, params={
        "q": query,
        "limit": MAX_SUBREDDITS,
        "include_over_18": "off",
    })

    subreddits: list[str] = []
    for child in data.get("data", {}).get("children", []):
        name = child.get("data", {}).get("display_name", "")
        if name:
            subreddits.append(name)

    if subreddits:
        print(f"[reddit] Found subreddits: {', '.join(f'r/{s}' for s in subreddits)}")
    else:
        print("[reddit] No related subreddits found.")

    return subreddits


def _scrape_subreddit(subreddit: str) -> list[dict]:
    """
    Scrape a single subreddit using hot, top/all, and top/year sort orders.
    Returns a deduplicated list of posts.
    """
    all_posts: list[dict] = []
    passes = [
        ("hot",  {}),
        ("top",  {"t": "all"}),
        ("top",  {"t": "year"}),
        ("new",  {}),
    ]

    for sort, extra_params in passes:
        url = SUBREDDIT_SORT_URL.format(subreddit=subreddit, sort=sort)
        params = {"limit": 100, **extra_params}
        label = f"r/{subreddit} [{sort}" + (f"/{extra_params['t']}" if extra_params else "") + "]"
        print(f"[reddit] Fetching {label} …")
        data = _fetch_json(url, params=params)
        posts = _extract_posts(data)
        all_posts.extend(posts)

    return _deduplicate(all_posts)


def scrape(query: str) -> list[dict]:
    """
    Fetch Reddit posts for a subreddit name or keyword search term.

    For a subreddit name: scrapes hot, top/all, top/year, and new.
    For a search term:
        - Site-wide search across relevance, top/all, top/year, and new sort orders.
        - Discovers related subreddits and scrapes each of them.
        - Deduplicates all results.

    Args:
        query: Subreddit name (e.g. 'python') OR a search term
               (e.g. 'b2b saas pain points').

    Returns:
        Deduplicated list of post dicts.
    """
    query = query.strip().lstrip("r/")
    all_posts: list[dict] = []

    if _is_subreddit_name(query):
        # ── Direct subreddit mode ─────────────────────────────────────────────
        print(f"[reddit] Scraping subreddit r/{query} (multiple sort orders) …")
        all_posts.extend(_scrape_subreddit(query))

    else:
        # ── Keyword search mode ───────────────────────────────────────────────
        search_passes = [
            {"sort": "relevance", "limit": 100},
            {"sort": "top",       "limit": 100, "t": "all"},
            {"sort": "top",       "limit": 100, "t": "year"},
            {"sort": "new",       "limit": 100},
        ]

        encoded = urllib.parse.quote_plus(query)
        for params in search_passes:
            label = f"sort={params['sort']}" + (f"&t={params['t']}" if "t" in params else "")
            print(f"[reddit] Site-wide search for '{query}' [{label}] …")
            data = _fetch_json(SEARCH_URL, params={"q": encoded, **params})
            all_posts.extend(_extract_posts(data))

        # ── Subreddit discovery + per-subreddit scrape ────────────────────────
        related_subs = _discover_subreddits(query)
        for sub in related_subs:
            all_posts.extend(_scrape_subreddit(sub))

    results = _deduplicate(all_posts)
    print(f"[reddit] Total unique posts collected: {len(results)}")
    return results
