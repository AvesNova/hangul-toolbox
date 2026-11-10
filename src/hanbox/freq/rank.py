"""Attach frequency ranks to a vocabulary CSV."""

from __future__ import annotations

import csv
import re
from pathlib import Path

DEFAULT_RANK = 30000  # rank assigned to words missing from the frequency list


def load_ranks(path: Path) -> dict[str, int]:
    """Load a frequency list into {word: rank} (lower = more common).

    Two formats are accepted:
      * one word per line, most common first (rank = line number, from 0)
      * a `Rank|Word` table as written by `hanbox freq scrape`
    The first occurrence of a word wins.
    """
    ranks: dict[str, int] = {}
    with open(path, encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f if line.strip()]
    if lines and lines[0].lower().startswith("rank|"):
        for line in lines[1:]:
            rank, _, word = line.partition("|")
            ranks.setdefault(word.strip(), int(rank.split(".")[0]))
    else:
        for i, line in enumerate(lines):
            ranks.setdefault(line.strip(), i)
    return ranks


def strip_homograph_number(word: str) -> str:
    """`하다01` -> `하다`: frequency lists don't number homographs."""
    return re.sub(r"\d+$", "", word)


def add_rank_column(
    input_path: Path,
    output_path: Path,
    ranks: dict[str, int],
    *,
    word_column: str,
    delimiter: str = "|",
    default: int = DEFAULT_RANK,
) -> tuple[int, int]:
    """Write a copy of `input_path` with a `Frequency` column added.

    Returns (rows written, rows that had no rank and got `default`).
    """
    with open(input_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        if word_column not in (reader.fieldnames or []):
            raise ValueError(f"column {word_column!r} not in {reader.fieldnames}")
        rows = list(reader)
        fieldnames = [*reader.fieldnames, "Frequency"]

    missing = 0
    for row in rows:
        rank = ranks.get(strip_homograph_number(row[word_column].strip()))
        if rank is None:
            rank, missing = default, missing + 1
        row["Frequency"] = rank

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows), missing
