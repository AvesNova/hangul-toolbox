"""JSONL checkpoint for enriched words.

Each line is one serialized EnrichedWord. The enrichment stage appends as it
goes, so an interrupted run resumes where it stopped; the audio stage rewrites
the file atomically once audio filenames are attached.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import EnrichedWord


def load_enriched(path: Path) -> dict[int, EnrichedWord]:
    """Load checkpointed records, keyed by word-list index."""
    records: dict[int, EnrichedWord] = {}
    if not path.exists():
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = EnrichedWord.from_dict(json.loads(line))
            records[record.entry.index] = record
    return records


def append_enriched(path: Path, records: list[EnrichedWord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        f.flush()


def write_enriched(path: Path, records: list[EnrichedWord]) -> None:
    """Atomically rewrite the checkpoint, sorted by word-list index."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for record in sorted(records, key=lambda r: r.entry.index):
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    os.replace(tmp, path)
