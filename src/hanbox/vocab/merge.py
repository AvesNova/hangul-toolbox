"""Merge the Kimchi, TOPIK and Yonsei word lists into one master list.

The lists are interleaved round-robin (one Kimchi word, one TOPIK word, one
Yonsei word, ...) so the merged order mixes frequency, official level and
textbook order instead of favouring any single source. Words are
de-duplicated after homograph normalisation (see `normalize`).
"""

from __future__ import annotations

import csv
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from .normalize import build_normalization_map

DELIMITER = "|"
FIELDNAMES = [
    "Word",
    "Kimchi Rank",
    "TOPIK POS",
    "TOPIK Definition",
    "TOPIK Level",
    "Yonsei Book",
]


@dataclass(frozen=True)
class KimchiWord:
    word: str
    rank: str


@dataclass(frozen=True)
class TopikWord:
    word: str
    pos: str
    definition: str
    level: str


@dataclass(frozen=True)
class YonseiWord:
    word: str
    book: str


def _read(path: Path):
    with open(path, encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f, delimiter=DELIMITER)


def load_kimchi(path: Path) -> list[KimchiWord]:
    return [KimchiWord(r["Word"].strip(), r["Rank"].strip()) for r in _read(path)]


def load_topik(path: Path) -> list[TopikWord]:
    return [
        TopikWord(r["단어"].strip(), r["품사"].strip(), r["풀이"].strip(), r["등급"].strip())
        for r in _read(path)
    ]


def load_yonsei(path: Path) -> list[YonseiWord]:
    return [YonseiWord(r["word"].strip(), r["source_book"].strip()) for r in _read(path)]


def merge(
    kimchi: list[KimchiWord],
    topik: list[TopikWord],
    yonsei: list[YonseiWord],
) -> list[dict[str, str]]:
    """Round-robin merge; returns rows keyed by `FIELDNAMES`.

    Iteration continues until the Yonsei list is exhausted (it is the
    shortest), matching the original behaviour; the tail of the longer
    lists is therefore not included unless it was matched by a word seen
    earlier.
    """
    norm = build_normalization_map(
        [t.word for t in topik], [k.word for k in kimchi] + [y.word for y in yonsei]
    )
    kimchi_by = {}
    for k in kimchi:
        kimchi_by.setdefault(norm[k.word], k)
    topik_by = {}
    for t in topik:
        topik_by.setdefault(norm[t.word], t)
    yonsei_by = {}
    for y in yonsei:
        yonsei_by.setdefault(norm[y.word], y)

    def row(word: str) -> dict[str, str]:
        k, t, y = kimchi_by.get(word), topik_by.get(word), yonsei_by.get(word)
        return {
            "Word": word,
            "Kimchi Rank": k.rank if k else "",
            "TOPIK POS": t.pos if t else "",
            "TOPIK Definition": t.definition if t else "",
            "TOPIK Level": t.level if t else "",
            "Yonsei Book": y.book if y else "",
        }

    seen: set[str] = set()
    out: list[dict[str, str]] = []

    def take_next(queue: deque) -> None:
        """Pop items until one adds a not-yet-seen word, then append it."""
        while queue:
            word = norm[queue.popleft().word]
            if word in seen:
                continue
            seen.add(word)
            out.append(row(word))
            return

    queues = [deque(kimchi), deque(topik), deque(yonsei)]
    yonsei_queue = queues[2]
    while yonsei_queue:
        take_next(queues[0])
        if not yonsei_queue:
            break
        take_next(queues[1])
        if not yonsei_queue:
            break
        take_next(yonsei_queue)
    return out


def write_master(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=DELIMITER, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
