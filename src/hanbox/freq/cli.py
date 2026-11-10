"""`hanbox freq ...` subcommands."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import rank

logger = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction) -> None:
    freq = subparsers.add_parser(
        "freq",
        help="Scrape a frequency list and attach ranks to vocab files",
        description="Frequency list tools.",
    )
    sub = freq.add_subparsers(dest="freq_command", required=True)

    s = sub.add_parser("scrape", help="Scrape the kimchi-reader.app frequency list (needs Chrome)")
    s.add_argument("--pages", type=int, default=2, help="Pages to scrape (default: %(default)s)")
    s.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Base pause in seconds between actions (default: %(default)s)",
    )
    s.add_argument("--no-meanings", action="store_true", help="Skip the per-word meaning popups")
    s.add_argument("--output", type=Path, default=Path("data/external/frequency_scrape.csv"))
    s.set_defaults(handler=_scrape)

    a = sub.add_parser("add", help="Add a Frequency column to a vocab CSV")
    a.add_argument("input", type=Path, help="Vocab CSV to annotate")
    a.add_argument(
        "--ranks",
        type=Path,
        required=True,
        help="Frequency list: one word per line, or a `Rank|Word` table",
    )
    a.add_argument(
        "--word-column", default="Korean", help="Column with the word (default: %(default)s)"
    )
    a.add_argument("--delimiter", default="|", help="CSV delimiter (default: %(default)s)")
    a.add_argument(
        "--default-rank",
        type=int,
        default=rank.DEFAULT_RANK,
        help="Rank for words not in the list (default: %(default)s)",
    )
    a.add_argument("--output", type=Path, help="Output path (default: <input>.freq.csv)")
    a.set_defaults(handler=_add)


def _scrape(args: argparse.Namespace) -> None:
    from . import scrape  # imported lazily: Selenium is an optional extra

    rows = scrape.scrape(args.pages, args.delay, with_meanings=not args.no_meanings)
    scrape.write_csv(rows, args.output)
    logger.info("Wrote %d rows to %s", len(rows), args.output)


def _add(args: argparse.Namespace) -> None:
    output = args.output or args.input.with_suffix(".freq.csv")
    ranks = rank.load_ranks(args.ranks)
    written, missing = rank.add_rank_column(
        args.input,
        output,
        ranks,
        word_column=args.word_column,
        delimiter=args.delimiter,
        default=args.default_rank,
    )
    logger.info("Wrote %d rows to %s (%d not in the frequency list)", written, output, missing)
