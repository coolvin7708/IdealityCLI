"""
src/scrapers/remoteok.py

Scrapes remote job listings from RemoteOK's free public JSON API.

RemoteOK provides a free public JSON API requiring no authentication:
    https://remoteok.com/api?tag=<tag>

Important: the API only matches exact single-word tags (e.g. 'python', 'ai').
Multi-word queries are handled by splitting into individual words and querying
each as a separate tag, then merging and deduplicating results by job ID.

Each returned item contains:
    - title    : job title
    - body     : job description (HTML stripped)
    - rating   : empty string (not provided by RemoteOK)
    - url      : direct link to the job posting
    - author   : company name
    - metadata : dict with tags, salary, location, posted_date
"""

import re
import time
import requests

from src.utils.text import clean_text

HEADERS = {
    "User-Agent": "IdealityCLI/1.0 (personal research tool)",
    "Accept": "application/json",
}

API_URL     = "https://remoteok.com/api"
CRAWL_DELAY = 1.5

# Common words that don't map to useful RemoteOK tags — skip them
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "in", "of", "to", "with",
    "at", "by", "from", "as", "on", "is", "it", "be", "are", "was",
}


def _fetch_tag(tag: str) -> list[dict]:
    """Fetch all jobs for a single tag from the RemoteOK API."""
    print(f"[remoteok] Querying tag '{tag}' …")
    try:
        response = requests.get(API_URL, headers=HEADERS, params={"tag": tag}, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[remoteok] Request failed for tag '{tag}': {exc}")
        return []

    time.sleep(CRAWL_DELAY)

    try:
        data = response.json()
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    items: list[dict] = []
    for job in data:
        if not isinstance(job, dict):
            continue
        # Skip the legal notice object prepended by the API
        if "id" not in job or "position" not in job:
            continue

        title    = clean_text(job.get("position", ""))
        raw_body = job.get("description", "") or ""
        body     = clean_text(re.sub(r"<[^>]+>", " ", raw_body))
        company  = clean_text(job.get("company", ""))
        url      = job.get("url", "") or f"https://remoteok.com/remote-jobs/{job.get('id', '')}"
        tags     = job.get("tags", []) or []
        location = job.get("location", "") or ""
        posted   = job.get("date", "") or ""
        sal_min  = job.get("salary_min", "") or ""
        sal_max  = job.get("salary_max", "") or ""
        salary   = f"{sal_min}–{sal_max}" if sal_min and sal_max else str(sal_min or sal_max or "")

        items.append({
            "title":    title,
            "body":     body,
            "rating":   "",
            "url":      url,
            "author":   company,
            "_job_id":  str(job.get("id", "")),
            "metadata": {
                "tags":        tags if isinstance(tags, list) else [],
                "salary":      salary,
                "location":    location,
                "posted_date": posted,
            },
        })

    return items


def scrape(query: str) -> list[dict]:
    """
    Fetch remote job listings from RemoteOK for a search term.

    Multi-word queries are split into individual tags and queried separately,
    then merged and deduplicated by job ID.

    Args:
        query: Job search term (e.g. 'ai engineer', 'data scientist', 'python').

    Returns:
        Deduplicated list of job dicts; empty list on failure.
    """
    # Build a deduplicated list of meaningful single-word tags from the query
    words  = query.strip().lower().replace("-", " ").split()
    tags   = list(dict.fromkeys(w for w in words if w not in _STOPWORDS and len(w) > 1))

    if not tags:
        tags = [query.strip().lower()]

    print(f"[remoteok] Searching for: {', '.join(tags)} …")

    all_items: list[dict] = []
    seen_ids: set[str] = set()

    for tag in tags:
        for item in _fetch_tag(tag):
            job_id = item.pop("_job_id", "")
            if job_id and job_id in seen_ids:
                continue
            if job_id:
                seen_ids.add(job_id)
            all_items.append(item)

    if all_items:
        print(f"[remoteok] {len(all_items)} unique job(s) found.")
    else:
        print(
            "[remoteok] No jobs found. "
            "Try simpler terms like 'python', 'ai', 'devops', 'react'."
        )

    return all_items
    return items
