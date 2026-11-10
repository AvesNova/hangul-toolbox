"""Find words that are identical except for ONE jamo in ONE syllable.

Examples:
    소년 / 소녀    — same 소, then 년 vs 녀 differ only in the final consonant
    자라다 / 바라다 — same 라다, first syllable differs only in the initial

A Hangul syllable block in [U+AC00, U+D7A3] decomposes arithmetically:

    code     = ord(ch) - 0xAC00
    initial  = code // 588          (19 possible)
    vowel    = (code % 588) // 28   (21 possible)
    final    = code % 28            (28 slots, 0 = none)

Two words are a pair iff they have the same length, consist only of Hangul
syllables, and differ in exactly one position where exactly one of the three
components differs.

Pairs are ranked by `1 / (1/rank_a + 1/rank_b)` (lower = both words more
common), so the most useful pairs to study come first.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

HANGUL_BASE = 0xAC00
_INITIAL_STRIDE = 588
_VOWEL_STRIDE = 28


@dataclass(frozen=True)
class Word:
    text: str
    rank: int
    english: str = ""


def is_syllable(ch: str) -> bool:
    return 0xAC00 <= ord(ch) <= 0xD7A3


def decompose(ch: str) -> tuple[int, int, int]:
    """Return (initial, vowel, final) indices for a Hangul syllable block."""
    code = ord(ch) - HANGUL_BASE
    return code // _INITIAL_STRIDE, (code % _INITIAL_STRIDE) // _VOWEL_STRIDE, code % _VOWEL_STRIDE


def jamo_distance(a: str, b: str) -> int:
    """Number of components (0-3) that differ between two syllables."""
    return sum(x != y for x, y in zip(decompose(a), decompose(b), strict=True))


def is_minimal_pair(a: str, b: str) -> bool:
    """True iff `a` and `b` differ by exactly one jamo in exactly one syllable."""
    if len(a) != len(b) or a == b or not all(map(is_syllable, a + b)):
        return False
    diffs = [(x, y) for x, y in zip(a, b, strict=True) if x != y]
    return len(diffs) == 1 and jamo_distance(*diffs[0]) == 1


def pair_score(a: Word, b: Word) -> float:
    return 1.0 / (1.0 / a.rank + 1.0 / b.rank)


def find_pairs(words: list[Word]) -> list[tuple[Word, Word]]:
    """All minimal pairs among `words`, most common pairs first.

    Words are bucketed by "the word with one position wildcarded", so only
    words that already agree everywhere else are compared. This is
    O(n·L) rather than comparing every same-length pair.
    """
    best: dict[str, Word] = {}  # de-duplicate, keeping the best-ranked entry
    for w in words:
        if w.text not in best or w.rank < best[w.text].rank:
            best[w.text] = w

    buckets: dict[tuple[int, str], list[Word]] = defaultdict(list)
    for w in best.values():
        if not all(map(is_syllable, w.text)):
            continue
        for i in range(len(w.text)):
            buckets[(i, w.text[:i] + "\0" + w.text[i + 1 :])].append(w)

    pairs = []
    for group in buckets.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if is_minimal_pair(a.text, b.text):
                    pairs.append((a, b))
    pairs.sort(key=lambda p: (pair_score(*p), p[0].text, p[1].text))
    return pairs


def load_topik(path: Path) -> list[Word]:
    """Read `Index|순위|단어|품사|풀이|등급`; rank is the Index column."""
    words = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="|"):
            text = row.get("단어", "").strip()
            if text and row.get("Index", "").strip().isdigit():
                words.append(Word(text, int(row["Index"])))
    return words


def load_known(path: Path) -> dict[str, Word]:
    """Read an Anki export TSV: the words you are studying, ranked by order.

    Accepts the `hanbox anki` format (`word<TAB>english<TAB>...`) and the
    legacy format with a leading row number (`n<TAB>word<TAB>english`).
    """
    known: dict[str, Word] = {}
    with open(path, encoding="utf-8", newline="") as f:
        for line_no, row in enumerate(csv.reader(f, delimiter="\t"), 1):
            if not row:
                continue
            if row[0].strip().isdigit() and len(row) >= 2:
                rank, text, english = int(row[0]), row[1], row[2] if len(row) > 2 else ""
            else:
                rank, text, english = line_no, row[0], row[1] if len(row) > 1 else ""
            text = text.strip()
            if text and text not in known:
                known[text] = Word(text, rank, english.strip())
    return known


def restrict_to_known(words: list[Word], known: dict[str, Word]) -> list[Word]:
    """Keep only studied words, re-ranked by their position in the deck."""
    return [known[w.text] for w in words if w.text in known]


def write_pairs(pairs: list[tuple[Word, Word]], path: Path, english: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["Row", "Score", "Korean_1", "English_1", "Korean_2", "English_2"])
        for n, (a, b) in enumerate(pairs, 1):
            writer.writerow(
                [
                    n,
                    f"{pair_score(a, b):.6f}",
                    a.text,
                    english.get(a.text, a.english),
                    b.text,
                    english.get(b.text, b.english),
                ]
            )
