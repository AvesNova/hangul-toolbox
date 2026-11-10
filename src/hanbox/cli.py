"""Top-level `hanbox` command. Each tool registers its own subcommand group."""

from __future__ import annotations

import argparse
import logging

from dotenv import load_dotenv

from . import __version__
from .anki import cli as anki_cli
from .freq import cli as freq_cli
from .similar import cli as similar_cli
from .vocab import cli as vocab_cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hanbox",
        description="hangul-toolbox: tools for building and analysing Korean vocabulary data.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")
    anki_cli.register(sub)
    vocab_cli.register(sub)
    freq_cli.register(sub)
    similar_cli.register(sub)
    return parser


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_dotenv()  # picks up ./.env if present; never overrides real env vars
    args = build_parser().parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    main()
