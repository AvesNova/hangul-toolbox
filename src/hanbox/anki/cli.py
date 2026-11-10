"""Command-line entry point.

Stages:
    enrich  — LLM translations + example chunks (checkpointed, resumable)
    audio   — TTS for every Korean chunk (skips files that already exist)
    export  — Anki TSV + media folder + ready-made .apkg deck
    run     — all three in order

Settings resolve as: CLI flags > config file (hanbox.toml) > environment
> built-in defaults. Credentials come from the environment only; a local
`.env` file is loaded automatically by the top-level `hanbox` CLI.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .audio import generate_audio
from .checkpoint import load_enriched, write_enriched
from .config import DEFAULT_CONFIG_FILE, DEFAULTS, load_config_file, resolve
from .enrich import enrich_words
from .export import write_apkg, write_tsv
from .llm import create_llm
from .tts import create_tts
from .word_list import load_word_list

logger = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Attach the `anki` command group to the top-level `hanbox` parser."""
    # Configurable options default to None so the config file layer can be
    # distinguished from "explicitly set on the command line" (see config.py).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--config",
        type=Path,
        default=None,
        help=f"TOML config file (default: {DEFAULT_CONFIG_FILE} if it exists)",
    )
    common.add_argument(
        "--input",
        type=Path,
        help=f"Pipe-delimited TOPIK word list (default: {DEFAULTS['input']})",
    )
    common.add_argument(
        "--output-dir",
        type=Path,
        help=f"Directory for checkpoint, media, TSV and .apkg (default: {DEFAULTS['output_dir']})",
    )
    common.add_argument(
        "--levels",
        help="Comma-separated TOPIK levels to include, e.g. A,B (default: all)",
    )
    common.add_argument(
        "--limit",
        type=int,
        help="Only process the first N words (useful for a test run)",
    )
    common.add_argument(
        "--chunks",
        type=int,
        help=f"Example chunks to generate per word (default: {DEFAULTS['chunks']})",
    )

    llm_args = argparse.ArgumentParser(add_help=False)
    llm_args.add_argument(
        "--llm-provider",
        choices=["anthropic", "openai"],
        help=f"LLM backend (default: {DEFAULTS['llm_provider']}). 'openai' means "
        "any OpenAI-compatible /chat/completions endpoint.",
    )
    llm_args.add_argument(
        "--llm-model",
        help="Model ID (default: claude-opus-4-8 for anthropic; required for openai)",
    )
    llm_args.add_argument(
        "--llm-base-url",
        help="Base URL for the openai provider (default: $OPENAI_BASE_URL, "
        "then https://api.openai.com/v1)",
    )
    llm_args.add_argument(
        "--batch-size",
        type=int,
        help=f"Words per LLM request (default: {DEFAULTS['batch_size']})",
    )

    tts_args = argparse.ArgumentParser(add_help=False)
    tts_args.add_argument(
        "--tts-provider",
        choices=["qwen", "openai"],
        help=f"TTS backend (default: {DEFAULTS['tts_provider']}). 'openai' means "
        "any OpenAI-compatible /audio/speech endpoint.",
    )
    tts_args.add_argument(
        "--tts-model",
        help="TTS model ID (defaults: Qwen3-TTS CustomVoice / tts-1)",
    )
    tts_args.add_argument(
        "--tts-base-url",
        help="Base URL for the openai TTS provider (default: $OPENAI_BASE_URL, "
        "then https://api.openai.com/v1)",
    )
    tts_args.add_argument(
        "--voices",
        help=f"Comma-separated voices rotated across chunks (default: {DEFAULTS['voices']})",
    )

    export_args = argparse.ArgumentParser(add_help=False)
    export_args.add_argument(
        "--deck-name",
        help=f"Name of the generated Anki deck (default: {DEFAULTS['deck_name']})",
    )

    anki = subparsers.add_parser(
        "anki",
        help="TOPIK word list -> LLM example phrases -> TTS audio -> Anki deck",
        description="TOPIK word list -> LLM example phrases -> TTS audio -> Anki deck.",
    )
    anki.set_defaults(handler=run_command)
    sub = anki.add_subparsers(dest="anki_command", required=True)
    sub.add_parser(
        "enrich",
        parents=[common, llm_args],
        help="Generate translations and example chunks with an LLM",
    )
    sub.add_parser(
        "audio", parents=[common, tts_args], help="Generate TTS audio for enriched words"
    )
    sub.add_parser(
        "export", parents=[common, export_args], help="Write the Anki TSV and .apkg deck"
    )
    sub.add_parser(
        "run",
        parents=[common, llm_args, tts_args, export_args],
        help="Run all stages: enrich, audio, export",
    )


def _resolve_settings(args: argparse.Namespace) -> argparse.Namespace:
    """Merge CLI args with the config file and defaults, in place."""
    if args.config is not None:
        if not args.config.exists():
            logger.error("Config file not found: %s", args.config)
            sys.exit(1)
        file_config = load_config_file(args.config)
    else:
        file_config = load_config_file(DEFAULT_CONFIG_FILE)
    for key, value in resolve(vars(args), file_config).items():
        setattr(args, key, value)
    return args


def _paths(args: argparse.Namespace) -> tuple[Path, Path]:
    checkpoint = args.output_dir / "enriched.jsonl"
    media_dir = args.output_dir / "media"
    return checkpoint, media_dir


def _load_entries(args: argparse.Namespace):
    levels = {s.strip().upper() for s in args.levels.split(",") if s.strip()} or None
    entries = load_word_list(args.input, levels=levels, limit=args.limit)
    if not entries:
        logger.error("No word entries found in %s.", args.input)
        sys.exit(1)
    logger.info("Loaded %d word entries from %s.", len(entries), args.input)
    return entries


def cmd_enrich(args: argparse.Namespace) -> None:
    entries = _load_entries(args)
    checkpoint, _ = _paths(args)
    llm = create_llm(args.llm_provider, model=args.llm_model, base_url=args.llm_base_url)
    enrich_words(
        llm,
        entries,
        checkpoint,
        batch_size=args.batch_size,
        chunk_count=args.chunks,
    )


def cmd_audio(args: argparse.Namespace) -> None:
    checkpoint, media_dir = _paths(args)
    records = list(load_enriched(checkpoint).values())
    if not records:
        logger.error("No enriched words at %s — run `hanbox anki enrich` first.", checkpoint)
        sys.exit(1)
    tts = create_tts(args.tts_provider, model=args.tts_model, base_url=args.tts_base_url)
    voices = [v.strip() for v in args.voices.split(",") if v.strip()]
    generate_audio(records, tts, media_dir, voices)
    write_enriched(checkpoint, records)


def cmd_export(args: argparse.Namespace) -> None:
    checkpoint, media_dir = _paths(args)
    records = sorted(load_enriched(checkpoint).values(), key=lambda r: r.entry.index)
    if not records:
        logger.error("No enriched words at %s — run `hanbox anki enrich` first.", checkpoint)
        sys.exit(1)
    write_tsv(records, args.output_dir / "topik_anki.tsv")
    write_apkg(records, media_dir, args.output_dir / "topik_anki.apkg", args.deck_name)


def cmd_run(args: argparse.Namespace) -> None:
    cmd_enrich(args)
    cmd_audio(args)
    cmd_export(args)


def run_command(args: argparse.Namespace) -> None:
    """Dispatch an `hanbox anki <stage>` invocation."""
    args = _resolve_settings(args)
    handlers = {
        "enrich": cmd_enrich,
        "audio": cmd_audio,
        "export": cmd_export,
        "run": cmd_run,
    }
    handlers[args.anki_command](args)
