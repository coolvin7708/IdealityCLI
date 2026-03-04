"""
src/visualize/charts.py

Chart generation for scraped + stored JSON data.

Supports two output modes:
  terminal   — ASCII/Unicode charts rendered inline via plotext (no file saved)
  image      — PNG charts saved to /charts/ via matplotlib

Chart types:
  ratings    — distribution of star ratings (1–5)
  keywords   — top N most frequent words in body text
  timeline   — review/post volume over time (requires 'date' in metadata)
  quality    — quality score distribution (requires filter_and_annotate to have run)

Public API:
    render_chart(items, chart_type, output_mode, title, out_dir, top_n)
"""

from __future__ import annotations

import re
import math
from collections import Counter
from pathlib import Path
from datetime import datetime

# ── Stop words to exclude from keyword frequency ─────────────────────────────
_STOP_WORDS: set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "i", "you", "we", "they", "it", "he", "she",
    "this", "that", "these", "those", "my", "your", "our", "their", "its",
    "not", "no", "so", "as", "if", "up", "out", "about", "what", "which",
    "who", "how", "when", "where", "why", "can", "just", "more", "also",
    "very", "much", "any", "all", "get", "got", "like", "use", "used",
    "using", "than", "then", "there", "here", "one", "two", "new", "good",
    "great", "s", "t", "re", "ve", "m", "ll", "d",
}


# ── Data extraction helpers ───────────────────────────────────────────────────

def _extract_ratings(items: list[dict]) -> list[int]:
    """Extract numeric ratings (1–5) from items."""
    ratings: list[int] = []
    for item in items:
        raw = str(item.get("rating", "") or "").strip()
        m = re.search(r"\b([1-5])\b", raw)
        if m:
            ratings.append(int(m.group(1)))
    return ratings


def _extract_keywords(items: list[dict], top_n: int = 15) -> list[tuple[str, int]]:
    """Return the top_n most frequent content words across all body texts."""
    word_counts: Counter = Counter()
    for item in items:
        body = str(item.get("body", "") or "") + " " + str(item.get("title", "") or "")
        words = re.findall(r"[a-z]{3,}", body.lower())
        word_counts.update(w for w in words if w not in _STOP_WORDS)
    return word_counts.most_common(top_n)


def _extract_dates(items: list[dict]) -> list[str]:
    """Extract ISO date strings from metadata.date fields."""
    dates: list[str] = []
    for item in items:
        meta = item.get("metadata", {})
        if not isinstance(meta, dict):
            continue
        date_val = meta.get("date", "") or meta.get("posted_date", "") or ""
        if date_val and isinstance(date_val, str) and len(date_val) >= 7:
            # Normalise to YYYY-MM (month granularity for grouping)
            dates.append(date_val[:7])
    return dates


def _extract_quality_scores(items: list[dict]) -> list[int]:
    """Extract quality_score fields (only present after filter_and_annotate)."""
    return [
        int(item["quality_score"])
        for item in items
        if "quality_score" in item
    ]


# ── Terminal charts (plotext) ─────────────────────────────────────────────────

def _terminal_ratings(items: list[dict], title: str) -> None:
    import plotext as plt

    ratings = _extract_ratings(items)
    if not ratings:
        print("[visualize] No numeric ratings found in this dataset.")
        return

    counts = [ratings.count(i) for i in range(1, 6)]
    plt.bar(["★1", "★2", "★3", "★4", "★5"], counts, orientation="vertical")
    plt.title(f"{title} — Rating Distribution")
    plt.xlabel("Rating")
    plt.ylabel("Count")
    plt.show()

    avg = sum(ratings) / len(ratings)
    print(f"\n  Total rated items : {len(ratings)}")
    print(f"  Average rating    : {avg:.2f} / 5")


def _terminal_keywords(items: list[dict], title: str, top_n: int) -> None:
    import plotext as plt

    pairs = _extract_keywords(items, top_n)
    if not pairs:
        print("[visualize] No keyword data found.")
        return

    words  = [p[0] for p in pairs]
    counts = [p[1] for p in pairs]

    plt.bar(words, counts, orientation="horizontal")
    plt.title(f"{title} — Top {top_n} Keywords")
    plt.xlabel("Frequency")
    plt.show()


def _terminal_timeline(items: list[dict], title: str) -> None:
    import plotext as plt

    dates = _extract_dates(items)
    if not dates:
        print("[visualize] No date metadata found in this dataset.")
        return

    month_counts: Counter = Counter(dates)
    sorted_months = sorted(month_counts)
    counts = [month_counts[m] for m in sorted_months]

    plt.plot(sorted_months, counts)
    plt.title(f"{title} — Volume Over Time")
    plt.xlabel("Month")
    plt.ylabel("Count")
    plt.show()


def _terminal_quality(items: list[dict], title: str) -> None:
    import plotext as plt

    scores = _extract_quality_scores(items)
    if not scores:
        print(
            "[visualize] No quality scores found.\n"
            "            Run `store <source> <id> --annotate` first to add scores."
        )
        return

    # Bucket into 10-point bins: 0-9, 10-19, … 90-100
    bins   = [f"{i*10}-{i*10+9}" for i in range(10)]
    counts = [sum(1 for s in scores if i * 10 <= s < (i + 1) * 10) for i in range(10)]
    # Put 100 in the last bin
    counts[-1] += scores.count(100)

    plt.bar(bins, counts)
    plt.title(f"{title} — Quality Score Distribution")
    plt.xlabel("Score band")
    plt.ylabel("Count")
    plt.show()

    flagged = sum(1 for s in scores if s < 50)
    print(f"\n  Total items scored : {len(scores)}")
    print(f"  Flagged (< 50)     : {flagged}  ({flagged/len(scores)*100:.1f}%)")
    print(f"  Average score      : {sum(scores)/len(scores):.1f}")


# ── Image charts (matplotlib) ─────────────────────────────────────────────────

def _image_ratings(items: list[dict], title: str, out_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ratings = _extract_ratings(items)
    if not ratings:
        print("[visualize] No numeric ratings found.")
        return

    counts = [ratings.count(i) for i in range(1, 6)]
    colors = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#27ae60"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(["★1", "★2", "★3", "★4", "★5"], counts, color=colors, edgecolor="white")
    ax.set_title(f"{title}\nRating Distribution", fontsize=14, fontweight="bold")
    ax.set_xlabel("Rating")
    ax.set_ylabel("Count")
    for bar, count in zip(bars, counts):
        if count:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    str(count), ha="center", va="bottom", fontsize=10)
    avg = sum(ratings) / len(ratings)
    ax.set_facecolor("#f8f9fa")
    fig.tight_layout()
    fig.text(0.99, 0.01, f"avg {avg:.2f}/5 · n={len(ratings)}",
             ha="right", va="bottom", fontsize=9, color="gray")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def _image_keywords(items: list[dict], title: str, out_path: Path, top_n: int) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pairs = _extract_keywords(items, top_n)
    if not pairs:
        print("[visualize] No keyword data found.")
        return

    words  = [p[0] for p in reversed(pairs)]
    counts = [p[1] for p in reversed(pairs)]

    fig, ax = plt.subplots(figsize=(9, max(5, len(words) * 0.45)))
    bars = ax.barh(words, counts, color="#3498db", edgecolor="white")
    ax.set_title(f"{title}\nTop {top_n} Keywords", fontsize=14, fontweight="bold")
    ax.set_xlabel("Frequency")
    ax.set_facecolor("#f8f9fa")
    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                str(count), va="center", fontsize=9)
    fig.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def _image_timeline(items: list[dict], title: str, out_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dates = _extract_dates(items)
    if not dates:
        print("[visualize] No date metadata found.")
        return

    month_counts: Counter = Counter(dates)
    sorted_months = sorted(month_counts)
    counts = [month_counts[m] for m in sorted_months]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(sorted_months, counts, marker="o", color="#9b59b6", linewidth=2)
    ax.fill_between(range(len(sorted_months)), counts, alpha=0.15, color="#9b59b6")
    ax.set_xticks(range(len(sorted_months)))
    ax.set_xticklabels(sorted_months, rotation=45, ha="right", fontsize=9)
    ax.set_title(f"{title}\nVolume Over Time", fontsize=14, fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Count")
    ax.set_facecolor("#f8f9fa")
    fig.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def _image_quality(items: list[dict], title: str, out_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    scores = _extract_quality_scores(items)
    if not scores:
        print("[visualize] No quality scores found. Run `store --annotate` first.")
        return

    bins   = [f"{i*10}–{i*10+9}" for i in range(10)]
    counts = [sum(1 for s in scores if i * 10 <= s < (i + 1) * 10) for i in range(10)]
    counts[-1] += scores.count(100)
    colors = ["#e74c3c" if i < 5 else "#2ecc71" for i in range(10)]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(bins, counts, color=colors, edgecolor="white")
    ax.set_title(f"{title}\nQuality Score Distribution", fontsize=14, fontweight="bold")
    ax.set_xlabel("Score band")
    ax.set_ylabel("Count")
    ax.set_facecolor("#f8f9fa")
    flagged = sum(1 for s in scores if s < 50)
    fig.text(0.99, 0.01,
             f"flagged (< 50): {flagged}/{len(scores)} · avg {sum(scores)/len(scores):.1f}",
             ha="right", fontsize=9, color="gray")
    fig.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


# ── Public entry point ────────────────────────────────────────────────────────

def render_chart(
    items: list[dict],
    chart_type: str,
    output_mode: str = "terminal",
    title: str = "IdealityCLI",
    out_dir: Path | None = None,
    top_n: int = 15,
) -> Path | None:
    """
    Generate a chart from a list of scraped items.

    Args:
        items:       List of scraped dicts.
        chart_type:  One of 'ratings', 'keywords', 'timeline', 'quality'.
        output_mode: 'terminal' (inline plotext) or 'image' (save PNG).
        title:       Chart title prefix.
        out_dir:     Directory to save PNGs (only used in 'image' mode).
                     Defaults to <project_root>/charts/.
        top_n:       Number of top keywords to show (keywords chart only).

    Returns:
        Path to saved PNG in image mode, None in terminal mode.
    """
    chart_type = chart_type.lower().strip()
    output_mode = output_mode.lower().strip()

    valid_types = ("ratings", "keywords", "timeline", "quality")
    if chart_type not in valid_types:
        raise ValueError(
            f"Unknown chart type '{chart_type}'. "
            f"Valid types: {', '.join(valid_types)}"
        )

    if output_mode == "terminal":
        _TERMINAL_CHARTS[chart_type](items, title, **_extra_kwargs(chart_type, top_n))
        return None

    # ── image mode ────────────────────────────────────────────────────────────
    if out_dir is None:
        # Default to <project_root>/charts/
        out_dir = Path(__file__).resolve().parents[2] / "charts"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r"[^\w\-]", "_", title)
    out_path = out_dir / f"{safe_title}_{chart_type}_{timestamp}.png"

    _IMAGE_CHARTS[chart_type](items, title, out_path, **_extra_kwargs(chart_type, top_n))
    return out_path


def _extra_kwargs(chart_type: str, top_n: int) -> dict:
    """Return extra keyword args for charts that need them."""
    if chart_type == "keywords":
        return {"top_n": top_n}
    return {}


# Dispatch tables
_TERMINAL_CHARTS = {
    "ratings":  lambda items, title, **kw: _terminal_ratings(items, title),
    "keywords": lambda items, title, top_n=15, **kw: _terminal_keywords(items, title, top_n),
    "timeline": lambda items, title, **kw: _terminal_timeline(items, title),
    "quality":  lambda items, title, **kw: _terminal_quality(items, title),
}

_IMAGE_CHARTS = {
    "ratings":  lambda items, title, path, **kw: _image_ratings(items, title, path),
    "keywords": lambda items, title, path, top_n=15, **kw: _image_keywords(items, title, path, top_n),
    "timeline": lambda items, title, path, **kw: _image_timeline(items, title, path),
    "quality":  lambda items, title, path, **kw: _image_quality(items, title, path),
}
