#!/usr/bin/env python3
"""
IdealityCLI — main entrypoint.

Run `ideality` to enter the interactive shell.
Run `ideality <command> ...` to execute a single command directly.
"""

import sys
import shlex
import time
import argparse
import io
import contextlib
from pathlib import Path

# Make src/ importable regardless of where the script is invoked from
sys.path.insert(0, str(Path(__file__).parent))

from src.cli.scrape import handle_scrape
from src.cli.store import handle_store
from src.cli.summarize import handle_summarize
from src.cli.search import handle_search


BANNER = """
╔══════════════════════════════════════════╗
║           IdealityCLI v1.0.0             ║
║  Local Scraper · Storage · Summarizer    ║
╚══════════════════════════════════════════╝
"""

HELP_TEXT = """\
Commands:
  scrape reddit     <subreddit or search term>
  scrape trustpilot <product-name>
  scrape appstore   <app-id or name>
  scrape remoteok   <search term>

  store     <source> <identifier>
  summarize <source> <identifier>
  search    "<keyword>"

  help      show this message
  exit      quit the shell  (or press Ctrl+C twice)
"""


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="",
        add_help=False,
        exit_on_error=False,
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # ── scrape ────────────────────────────────────────────────────────────────
    scrape_parser = subparsers.add_parser("scrape", add_help=False)
    scrape_sub = scrape_parser.add_subparsers(dest="source", metavar="<source>")

    for source, meta in [
        ("reddit",   "Subreddit name or search term"),
        ("trustpilot", "Product name to search on Trustpilot"),
        ("appstore",   "App numeric ID or name slug"),
        ("remoteok", "Job search term"),
    ]:
        p = scrape_sub.add_parser(source, add_help=False)
        p.add_argument("query", metavar="<query>", help=meta)

    # ── store ─────────────────────────────────────────────────────────────────
    store_parser = subparsers.add_parser("store", add_help=False)
    store_parser.add_argument("source", choices=["reddit", "trustpilot", "appstore", "remoteok"])
    store_parser.add_argument("identifier")

    # ── summarize ─────────────────────────────────────────────────────────────
    summarize_parser = subparsers.add_parser("summarize", add_help=False)
    summarize_parser.add_argument("source", choices=["reddit", "trustpilot", "appstore", "remoteok"])
    summarize_parser.add_argument("identifier")

    # ── search ────────────────────────────────────────────────────────────────
    search_parser = subparsers.add_parser("search", add_help=False)
    search_parser.add_argument("keyword")

    # ── help / exit ───────────────────────────────────────────────────────────
    subparsers.add_parser("help",  add_help=False)
    subparsers.add_parser("exit",  add_help=False)
    subparsers.add_parser("quit",  add_help=False)

    return parser


def dispatch(args: argparse.Namespace) -> None:
    """Route a parsed Namespace to the correct handler."""
    if args.command == "scrape":
        if not getattr(args, "source", None):
            print("[error] Usage: scrape <reddit|trustpilot|appstore|remoteok> <query>")
            return
        if not getattr(args, "query", None):
            print(f"[error] Usage: scrape {args.source} <query>")
            return
        handle_scrape(args)
    elif args.command == "store":
        if not getattr(args, "identifier", None):
            print("[error] Usage: store <reddit|trustpilot|appstore|remoteok> <identifier>")
            return
        handle_store(args)
    elif args.command == "summarize":
        if not getattr(args, "identifier", None):
            print("[error] Usage: summarize <reddit|trustpilot|appstore|remoteok> <identifier>")
            return
        handle_summarize(args)
    elif args.command == "search":
        if not getattr(args, "keyword", None):
            print('[error] Usage: search "<keyword>"')
            return
        handle_search(args)


def run_repl() -> None:
    """
    Interactive REPL shell.

    - Stays open until the user types `exit`/`quit` or presses Ctrl+C twice
      within one second.
    - A single Ctrl+C prints a warning and continues.
    """
    parser = build_parser()
    last_ctrl_c: float = 0.0

    print(HELP_TEXT)
    print('Type "help" to see commands, or "exit" to quit.\n')

    while True:
        try:
            raw = input("ideality> ").strip()
        except KeyboardInterrupt:
            now = time.monotonic()
            if now - last_ctrl_c < 1.0:
                print("\nGoodbye.")
                sys.exit(0)
            last_ctrl_c = now
            print("\n(Press Ctrl+C again within 1 second to exit.)")
            continue
        except EOFError:
            # Handles Ctrl+D / piped input ending
            print("\nGoodbye.")
            sys.exit(0)

        if not raw:
            continue

        if raw.lower() in ("exit", "quit"):
            print("Goodbye.")
            sys.exit(0)

        if raw.lower() == "help":
            print(HELP_TEXT)
            continue

        try:
            tokens = shlex.split(raw)
        except ValueError as exc:
            print(f"[error] Could not parse input: {exc}")
            continue

        try:
            # Suppress argparse's built-in error printing — we handle it ourselves
            with contextlib.redirect_stderr(io.StringIO()):
                args, _ = parser.parse_known_args(tokens)
        except (argparse.ArgumentError, SystemExit) as exc:
            # SystemExit from subparsers on bad/missing required args
            # — show a usage hint rather than crashing the REPL
            if isinstance(exc, SystemExit) and exc.code == 0:
                # legitimate exit (e.g. --help on a subcommand)
                continue
            print('[error] Bad arguments. Type "help" for usage.')
            continue

        if args.command is None:
            print(f'[error] Unknown command. Type "help" for usage.')
            continue

        try:
            dispatch(args)
        except Exception as exc:
            print(f"[error] {exc}")

        print()


def main() -> None:
    print(BANNER)

    # If arguments were passed on the command line, run once and exit
    # (e.g. ideality store reddit python — useful for scripting)
    if len(sys.argv) > 1:
        # Build the one-shot parser (with full help/error handling)
        one_shot = argparse.ArgumentParser(
            prog="ideality",
            description="IdealityCLI — scrape, store, summarize, and search ideas.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=HELP_TEXT,
        )
        subparsers = one_shot.add_subparsers(dest="command", metavar="<command>")
        subparsers.required = True

        scrape_p = subparsers.add_parser("scrape")
        scrape_sub = scrape_p.add_subparsers(dest="source", metavar="<source>")
        scrape_sub.required = True
        for source, meta in [
            ("reddit",   "Subreddit name or keyword search"),
            ("trustpilot", "Product name to search on Trustpilot"),
            ("appstore",   "App ID or name slug"),
            ("remoteok", "Job search term"),
        ]:
            p = scrape_sub.add_parser(source)
            p.add_argument("query", metavar="<query>")

        store_p = subparsers.add_parser("store")
        store_p.add_argument("source", choices=["reddit", "trustpilot", "appstore", "remoteok"])
        store_p.add_argument("identifier")

        sum_p = subparsers.add_parser("summarize")
        sum_p.add_argument("source", choices=["reddit", "trustpilot", "appstore", "remoteok"])
        sum_p.add_argument("identifier")

        search_p = subparsers.add_parser("search")
        search_p.add_argument("keyword")

        args = one_shot.parse_args()
        dispatch(args)
        return

    # No arguments → enter the interactive REPL
    run_repl()


if __name__ == "__main__":
    main()
