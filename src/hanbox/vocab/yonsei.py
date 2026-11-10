"""Turn raw Yonsei textbook word-index files into a clean lemma list.

Pipeline (each step is also exposed as its own function / subcommand):

    raw/<book>.csv --clean--> clean/<book>.csv --combine--> nonlemma list
                   --fix----> yonsei_words.csv        (+ suspect finder as a QA aid)

The raw files are index lines copied from the books: they contain page
numbers, section headings and bare consonant headers that must be removed.
"""

from __future__ import annotations

import csv
import random
import re
from pathlib import Path

DELIMITER = "|"

# Lines that are index noise rather than words.
_NOISE_PATTERNS = [
    re.compile(r"\s*\d+\s*"),  # bare number
    re.compile(r"\s*\d+\s*과\s*"),  # "3과"
    re.compile(r"\s*\d+\s*항\s*"),  # "2항"
    re.compile(r"\s*\d+\s*<\s*\d+\s*>\s*"),  # "3<2>"
]
_NOISE_WORDS = ("색인", "확장", "대화", "참고")
_BARE_CONSONANTS = set("ㅂㅈㄷㄱㅅㅁㄴㅇㄹㅎㅋㅌㅊㅍ")

# Patterns that suggest an entry is not a dictionary form (lemma).
_SUSPECT_PATTERNS = [
    re.compile(r"[^가-힣]"),  # digits, symbols, Latin
    re.compile(r"(을|를|이|가|은|는|에|와|과|의|로|에서)$"),  # trailing particle
    re.compile(r"(요|어요|아요|예요|이에요|세요|했어요|해요)$"),  # polite ending
    re.compile(r".*(는|은|운|한|던)$"),  # conjugated modifier form
    re.compile(r"^.{1}$"),  # single character
    re.compile(r"(.)\1{2,}"),  # repeated jamo (ㅋㅋㅋ)
]


def is_noise(cell: str) -> bool:
    """True if a raw index cell is empty or index furniture, not a word."""
    cell = cell.strip()
    if not cell:
        return True
    if any(w in cell for w in _NOISE_WORDS):
        return True
    if cell in _BARE_CONSONANTS:
        return True
    return any(p.fullmatch(cell) for p in _NOISE_PATTERNS)


def is_suspicious(word: str) -> bool:
    """True if the word looks like a non-lemma form or malformed entry."""
    w = word.strip()
    return not w or any(p.search(w) for p in _SUSPECT_PATTERNS)


def book_order(path: Path) -> tuple[int, int]:
    """Sort key for names like `2-1.csv`; non-matching names sort last."""
    m = re.fullmatch(r"(\d+)-(\d+)\.csv", path.name.lower())
    return (int(m[1]), int(m[2])) if m else (10**9, 10**9)


def clean_books(raw_dir: Path, clean_dir: Path, shuffle_seed: int | None = None) -> int:
    """Strip index noise from every raw CSV and de-duplicate, keeping order.

    Pass `shuffle_seed` to shuffle each book's rows reproducibly. Returns the
    number of files written.
    """
    clean_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(shuffle_seed) if shuffle_seed is not None else None
    count = 0
    for src in sorted(raw_dir.glob("*.csv"), key=book_order):
        with open(src, encoding="utf-8", newline="") as f:
            rows = [r for r in csv.reader(f) if any(not is_noise(c) for c in r)]
        unique = list(dict.fromkeys(tuple(r) for r in rows))  # ordered de-dup
        if rng:
            rng.shuffle(unique)
        with open(clean_dir / src.name, "w", encoding="utf-8", newline="") as f:
            csv.writer(f, lineterminator="\n").writerows(unique)
        count += 1
    return count


def combine_books(clean_dir: Path) -> list[tuple[str, str]]:
    """Concatenate the cleaned books in order as (word, book), first sighting wins."""
    seen: set[str] = set()
    rows: list[tuple[str, str]] = []
    for src in sorted(clean_dir.glob("*.csv"), key=book_order):
        with open(src, encoding="utf-8", newline="") as f:
            for row in csv.reader(f):
                word = row[0].strip() if row else ""
                if word and word not in seen:
                    seen.add(word)
                    rows.append((word, src.name))
    return rows


def load_fixes(path: Path) -> dict[str, str]:
    """Load a `word|fixed_word` table of manual lemma corrections."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=DELIMITER)
        return {
            r["word"].strip(): r["fixed_word"].strip()
            for r in reader
            if r["word"].strip() and r["fixed_word"].strip()
        }


def apply_fixes(rows: list[tuple[str, str]], fixes: dict[str, str]) -> list[tuple[str, str]]:
    """Apply lemma corrections, dropping duplicates created by the fixes."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for word, book in rows:
        fixed = fixes.get(word, word)
        if fixed not in seen:
            seen.add(fixed)
            out.append((fixed, book))
    return out


def find_suspects(rows: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return [r for r in rows if is_suspicious(r[0])]


def write_words(rows: list[tuple[str, str]], path: Path) -> None:
    """Write `word|source_book` rows (the format the merge step reads)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=DELIMITER, lineterminator="\n")
        writer.writerow(["word", "source_book"])
        writer.writerows(rows)
