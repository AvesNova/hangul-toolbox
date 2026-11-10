"""`hanbox similar` subcommand."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import pairs

logger = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "similar",
        help="Find word pairs that differ by a single jamo (e.g. 소년/소녀)",
        description="Find minimal pairs among TOPIK words, optionally restricted to "
        "the words in your Anki deck.",
    )
    p.add_argument(
        "--words",
        type=Path,
        default=Path("data/topik_words.csv"),
        help="TOPIK word list (default: %(default)s)",
    )
    p.add_argument(
        "--known", type=Path, help="Anki export TSV; also writes a pairs file for just those words"
    )
    p.add_argument("--output-dir", type=Path, default=Path("output/similar_pairs"))
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> None:
    words = pairs.load_topik(args.words)
    known = pairs.load_known(args.known) if args.known else {}
    english = {w: k.english for w, k in known.items()}

    all_pairs = pairs.find_pairs(words)
    out = args.output_dir / "similar_pairs_all.tsv"
    pairs.write_pairs(all_pairs, out, english)
    logger.info("%d pairs among %d words -> %s", len(all_pairs), len(words), out)

    if known:
        mine = pairs.find_pairs(pairs.restrict_to_known(words, known))
        out = args.output_dir / "similar_pairs_known.tsv"
        pairs.write_pairs(mine, out, english)
        logger.info("%d pairs among your %d studied words -> %s", len(mine), len(known), out)
