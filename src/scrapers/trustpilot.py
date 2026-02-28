"""
src/scrapers/g2.py

Scrapes software product reviews from Trustpilot (replaces G2, which blocks
all non-browser requests with Cloudflare 403s).

Trustpilot is server-rendered and paginates cleanly via ?page=N.
This scraper fetches up to MAX_PAGES pages (20 reviews each).

Workflow:
  1. Search Trustpilot for the product name to find the canonical review URL.
  2. Paginate through review pages and extract each review card.

Each returned item contains:
    - title    : review headline
    - body     : review body text
    - rating   : star rating out of 5 (string)
    - url      : review page URL
    - author   : reviewer display name
    - metadata : dict with product_slug, date, verified
"""

import re
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup

from src.utils.text import clean_text

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SEARCH_URL  = "https://www.trustpilot.com/search?query={query}"
REVIEW_URL  = "https://www.trustpilot.com/review/{slug}?page={page}"
MAX_PAGES   = 10   # 20 reviews/page × 10 pages = up to 200 reviews
CRAWL_DELAY = 1.0


def _search_slug(query: str) -> str:
    """
    Search Trustpilot for `query` and return the first matching company slug
    (the path segment used in trustpilot.com/review/<slug>).

    Falls back to using the query directly as a slug if search fails.
    """
    encoded = urllib.parse.quote_plus(query)
    url = SEARCH_URL.format(query=encoded)
    print(f"[trustpilot] Searching for '{query}' …")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[trustpilot] Search request failed: {exc}")
        return query.lower().replace(" ", "-")

    time.sleep(CRAWL_DELAY)
    soup = BeautifulSoup(resp.text, "lxml")

    # Result cards link to /review/<slug>
    link = soup.select_one("a[href^='/review/']")
    if link:
        slug = link["href"].replace("/review/", "").split("?")[0].strip("/")
        print(f"[trustpilot] Found: trustpilot.com/review/{slug}")
        return slug

    # Fallback: try the query as-is
    fallback = query.strip().lower().replace(" ", "-")
    print(f"[trustpilot] No search result — trying slug '{fallback}' directly.")
    return fallback


def _parse_reviews(soup: BeautifulSoup, page_url: str) -> list[dict]:
    """Extract all review cards from a parsed Trustpilot page."""
    items: list[dict] = []

    # Trustpilot wraps each review in <article> with data-service-review-card-paper
    cards = soup.select("article[data-service-review-card-paper]")
    if not cards:
        # Fallback for older layout
        cards = soup.select("article.review")

    for card in cards:
        # ── Title ──────────────────────────────────────────────────────────
        title_tag = card.select_one("h2[data-service-review-title-typography], .review-content__title")
        title = clean_text(title_tag.get_text()) if title_tag else ""

        # ── Body ───────────────────────────────────────────────────────────
        body_tag = card.select_one("p[data-service-review-text-typography], .review-content__text")
        body = clean_text(body_tag.get_text()) if body_tag else ""

        # ── Rating — img alt says "Rated X out of 5 stars" ────────────────
        rating_img = card.select_one("img[alt*='Rated'], img[alt*='star']")
        rating = ""
        if rating_img:
            match = re.search(r"(\d+)", rating_img.get("alt", ""))
            rating = match.group(1) if match else ""
        if not rating:
            # Try data attribute on the star widget
            star_div = card.select_one("[data-service-review-rating]")
            if star_div:
                rating = star_div.get("data-service-review-rating", "")

        # ── Author ─────────────────────────────────────────────────────────
        author_tag = card.select_one("span[data-consumer-name-typography], .consumer-info__name")
        author = clean_text(author_tag.get_text()) if author_tag else ""

        # ── Date ───────────────────────────────────────────────────────────
        time_tag = card.select_one("time")
        date = time_tag.get("datetime", "") if time_tag else ""

        # ── Verified flag ──────────────────────────────────────────────────
        verified_tag = card.select_one("[data-review-label-verified], .review-content-header__verified")
        verified = bool(verified_tag)

        # ── Review permalink ───────────────────────────────────────────────
        link_tag = card.select_one("a[href*='/reviews/']")
        if link_tag and link_tag.get("href", "").startswith("/"):
            review_url = "https://www.trustpilot.com" + link_tag["href"]
        else:
            review_url = page_url

        items.append({
            "title":    title,
            "body":     body,
            "rating":   rating,
            "url":      review_url,
            "author":   author,
            "metadata": {
                "date":     date,
                "verified": verified,
            },
        })

    return items


def scrape(query: str) -> list[dict]:
    """
    Scrape Trustpilot reviews for a product.

    Args:
        query: Product name or slug (e.g. 'notion', 'slack', 'salesforce').
               Searches Trustpilot to find the canonical company page.

    Returns:
        List of review dicts; empty list on failure.
    """
    slug = _search_slug(query)
    all_items: list[dict] = []

    for page in range(1, MAX_PAGES + 1):
        page_url = REVIEW_URL.format(slug=slug, page=page)
        print(f"[trustpilot] Fetching page {page}/{MAX_PAGES}: {page_url}")

        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[trustpilot] Page {page} failed: {exc}")
            break

        time.sleep(CRAWL_DELAY)
        soup = BeautifulSoup(resp.text, "lxml")
        page_items = _parse_reviews(soup, page_url)

        if not page_items:
            print(f"[trustpilot] No reviews found on page {page}. Stopping.")
            break

        all_items.extend(page_items)
        print(f"[trustpilot] Page {page}: {len(page_items)} review(s) (total: {len(all_items)})")

    if not all_items:
        print(
            "[trustpilot] No reviews collected. "
            "The company may not exist on Trustpilot, or the slug is wrong."
        )

    return all_items
