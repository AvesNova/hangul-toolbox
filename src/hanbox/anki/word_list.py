"""Reading and filtering the TOPIK vocabulary CSV.

The source file is pipe-delimited with a header row:

    Index|순위|단어|품사|풀이|등급
"""

from __future__ import annotations

import csv
from pathlib import Path

from .models import WordEntry


def load_word_list(
    path: Path,
    levels: set[str] | None = None,
    limit: int | None = None,
) -> list[WordEntry]:
    """Load word entries, optionally filtered by TOPIK level and truncated.

    Rows without a numeric index or without a word are skipped.
    """
    entries: list[WordEntry] = []
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="|")
        next(reader, None)  # header
        for row in reader:
            if len(row) < 6 or not row[0].strip().isdigit() or not row[2].strip():
                continue
            entry = WordEntry(
                index=int(row[0]),
                rank=int(row[1]) if row[1].strip().isdigit() else 0,
                word=row[2].strip(),
                pos=row[3].strip(),
                hint=row[4].strip(),
                level=row[5].strip(),
            )
            if levels and entry.level not in levels:
                continue
            entries.append(entry)
            if limit is not None and len(entries) >= limit:
                break
    return entries
