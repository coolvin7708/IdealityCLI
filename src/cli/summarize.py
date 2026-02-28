"""
src/cli/summarize.py

Handler for the `summarize` CLI command.

Responsibilities:
  - Load the stored JSON for source + identifier.
  - Pass the items through the LLM summarizer.
  - Write the resulting Markdown to /summaries/<source>_<identifier>.md.
"""

import argparse
from pathlib import Path

from src.cli.store import get_data_path
from src.utils.fileio import read_json
from src.summarize.summarizer import summarize_items

# Root summaries directory — sibling of /data
SUMMARIES_DIR = Path(__file__).resolve().parents[2] / "summaries"


def get_summary_path(source: str, identifier: str) -> Path:
    """
    Return the Markdown output path for this source + identifier.

    Example:
        source="reddit", identifier="python"
        → <project_root>/summaries/reddit_python.md
    """
    safe_id = identifier.replace(" ", "_").replace("/", "-")
    return SUMMARIES_DIR / f"{source}_{safe_id}.md"


def handle_summarize(args: argparse.Namespace) -> None:
    """
    Entry point called from main.py for the `summarize` command.

    Reads JSON from disk, generates a Markdown summary, and writes it.
    """
    source = args.source
    identifier = args.identifier

    data_path = get_data_path(source, identifier)

    if not data_path.exists():
        print(
            f"[error] No stored data found at {data_path}\n"
            f"        Run `store {source} {identifier}` first."
        )
        return

    print(f"[summarize] Loading data from {data_path} …")

    try:
        items = read_json(data_path)
    except Exception as exc:
        print(f"[error] Failed to read JSON: {exc}")
        return

    if not items:
        print("[warn] JSON file contains 0 items — nothing to summarise.")
        return

    print(f"[summarize] Summarising {len(items)} item(s) …")

    try:
        markdown_text = summarize_items(items)
    except Exception as exc:
        print(f"[error] Summariser failed: {exc}")
        return

    out_path = get_summary_path(source, identifier)

    # Ensure the summaries directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        out_path.write_text(markdown_text, encoding="utf-8")
    except Exception as exc:
        print(f"[error] Could not write Markdown: {exc}")
        return

    print(f"[summarize] Markdown summary written → {out_path}")
