"""`hanbox vocab ...` subcommands."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import merge as merge_mod
from . import yonsei

logger = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction) -> None:
    vocab = subparsers.add_parser(
        "vocab",
        help="Merge word lists (Kimchi/TOPIK/Yonsei) and clean Yonsei index files",
        description="Merge word lists and clean Yonsei textbook index files.",
    )
    sub = vocab.add_subparsers(dest="vocab_command", required=True)

    m = sub.add_parser("merge", help="Round-robin merge Kimchi, TOPIK and Yonsei lists")
    m.add_argument(
        "--kimchi",
        type=Path,
        default=Path("data/external/kimchi_words.csv"),
        help="Pipe-delimited `Rank|Word` frequency list (default: %(default)s)",
    )
    m.add_argument(
        "--topik",
        type=Path,
        default=Path("data/topik_words.csv"),
        help="TOPIK list (default: %(default)s)",
    )
    m.add_argument(
        "--yonsei",
        type=Path,
        default=Path("data/yonsei_words.csv"),
        help="`word|source_book` list (default: %(default)s)",
    )
    m.add_argument("--output", type=Path, default=Path("output/master_words.csv"))
    m.set_defaults(handler=_merge)

    y = sub.add_parser("yonsei", help="Raw Yonsei index files -> clean lemma list")
    y.add_argument(
        "--raw-dir", type=Path, required=True, help="Directory of raw per-book CSVs (e.g. 1-1.csv)"
    )
    y.add_argument(
        "--fixes",
        type=Path,
        default=Path("data/yonsei_word_fixes.csv"),
        help="`word|fixed_word` lemma corrections (default: %(default)s)",
    )
    y.add_argument(
        "--work-dir",
        type=Path,
        default=Path("output/yonsei"),
        help="Where cleaned intermediates go (default: %(default)s)",
    )
    y.add_argument("--output", type=Path, default=Path("output/yonsei_words.csv"))
    y.add_argument(
        "--shuffle-seed",
        type=int,
        default=None,
        help="Shuffle each book's words reproducibly (default: keep order)",
    )
    y.set_defaults(handler=_yonsei)


def _merge(args: argparse.Namespace) -> None:
    kimchi = merge_mod.load_kimchi(args.kimchi)
    topik = merge_mod.load_topik(args.topik)
    yonsei_words = merge_mod.load_yonsei(args.yonsei)
    logger.info(
        "Loaded %d Kimchi, %d TOPIK, %d Yonsei words", len(kimchi), len(topik), len(yonsei_words)
    )
    rows = merge_mod.merge(kimchi, topik, yonsei_words)
    merge_mod.write_master(rows, args.output)
    logger.info("Wrote %d unique words to %s", len(rows), args.output)


def _yonsei(args: argparse.Namespace) -> None:
    clean_dir = args.work_dir / "clean"
    n = yonsei.clean_books(args.raw_dir, clean_dir, shuffle_seed=args.shuffle_seed)
    logger.info("Cleaned %d book files into %s", n, clean_dir)
    rows = yonsei.combine_books(clean_dir)
    if args.fixes.exists():
        fixes = yonsei.load_fixes(args.fixes)
        rows = yonsei.apply_fixes(rows, fixes)
        logger.info("Applied %d lemma fixes", len(fixes))
    else:
        logger.warning("No fixes file at %s; skipping lemma corrections", args.fixes)
    yonsei.write_words(rows, args.output)
    suspects = yonsei.find_suspects(rows)
    suspect_path = args.work_dir / "suspect_words.csv"
    yonsei.write_words(suspects, suspect_path)
    logger.info(
        "Wrote %d words to %s; %d suspected non-lemmas listed in %s",
        len(rows),
        args.output,
        len(suspects),
        suspect_path,
    )
