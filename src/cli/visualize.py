"""
src/cli/visualize.py

Handler for the `visualize` CLI command.

Usage (via REPL):
    visualize <source> <identifier> --chart ratings
    visualize <source> <identifier> --chart keywords
    visualize <source> <identifier> --chart timeline
    visualize <source> <identifier> --chart quality
    visualize <source> <identifier> --chart ratings --output image
    visualize <source> <identifier> --chart keywords --top 20

Defaults:
    --chart    ratings
    --output   terminal
    --top      15
"""

import argparse
from pathlib import Path

from src.cli.store import get_data_path
from src.utils.fileio import read_json
from src.visualize.charts import render_chart

CHARTS_DIR = Path(__file__).resolve().parents[2] / "charts"


def handle_visualize(args: argparse.Namespace) -> None:
    """
    Entry point called from main.py for the `visualize` command.

    Loads stored JSON, then renders the requested chart.
    """
    source     = args.source
    identifier = args.identifier
    chart_type = getattr(args, "chart",  "ratings")
    output     = getattr(args, "output", "terminal")
    top_n      = getattr(args, "top",    15)

    data_path = get_data_path(source, identifier)

    if not data_path.exists():
        print(
            f"[error] No stored data found at {data_path}\n"
            f"        Run `store {source} {identifier}` first."
        )
        return

    try:
        items = read_json(data_path)
    except Exception as exc:
        print(f"[error] Failed to read data: {exc}")
        return

    if not items:
        print("[warn] JSON file is empty — nothing to chart.")
        return

    title = f"{source.capitalize()} / {identifier}"
    print(f"[visualize] {len(items)} items · chart={chart_type} · output={output}\n")

    try:
        saved_path = render_chart(
            items=items,
            chart_type=chart_type,
            output_mode=output,
            title=title,
            out_dir=CHARTS_DIR if output == "image" else None,
            top_n=int(top_n),
        )
    except ValueError as exc:
        print(f"[error] {exc}")
        return
    except Exception as exc:
        print(f"[error] Chart generation failed: {exc}")
        return

    if saved_path:
        print(f"\n[visualize] Chart saved → {saved_path}")
